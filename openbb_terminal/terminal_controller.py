#!/usr/bin/env python
"""Main Terminal Module."""
__docformat__ = "numpy"

import argparse
import difflib
import logging
import os
import csv
from pathlib import Path
from datetime import datetime
import sys
import webbrowser
from typing import List

import dotenv
from rich import panel

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
import pandas as pd
from openbb_terminal import feature_flags as obbff
from openbb_terminal.terminal_helper import is_packaged_application

from openbb_terminal.core.config.paths import (
    HOME_DIRECTORY,
    MISCELLANEOUS_DIRECTORY,
    REPOSITORY_ENV_FILE,
    USER_DATA_DIRECTORY,
    USER_ENV_FILE,
    USER_ROUTINES_DIRECTORY,
)

from openbb_terminal.helper_funcs import (
    check_positive,
    get_flair,
    parse_simple_args,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
)
from openbb_terminal.loggers import setup_logging
from openbb_terminal.core.log.generation.settings_logger import log_all_settings
from openbb_terminal.menu import session, is_papermill
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText
from openbb_terminal.terminal_helper import (
    bootup,
    check_for_updates,
    is_reset,
    print_goodbye,
    reset,
    suppress_stdout,
    update_terminal,
    welcome_message,
)
from openbb_terminal.helper_funcs import parse_and_split_input
from openbb_terminal.keys_model import first_time_user
from openbb_terminal.common import feedparser_view
from openbb_terminal.reports.reports_model import ipykernel_launcher

# pylint: disable=too-many-public-methods,import-outside-toplevel, too-many-function-args
# pylint: disable=too-many-branches,no-member,C0302,too-many-return-statements

logger = logging.getLogger(__name__)

env_file = str(USER_ENV_FILE)


class TerminalController(BaseController):
    """Terminal Controller class."""

    CHOICES_COMMANDS = [
        "keys",
        "settings",
        "survey",
        "update",
        "featflags",
        "exe",
        "guess",
        "news",
        "intro",
    ]
    CHOICES_MENUS = [
        "stocks",
        "economy",
        "crypto",
        "portfolio",
        "forex",
        "etf",
        "reports",
        "dashboards",
        "alternative",
        "econometrics",
        "sources",
        "forecast",
        "futures",
    ]

    PATH = "/"

    GUESS_TOTAL_TRIES = 0
    GUESS_NUMBER_TRIES_LEFT = 0
    GUESS_SUM_SCORE = 0.0
    GUESS_CORRECTLY = 0

    def __init__(self, jobs_cmds: List[str] = None):
        """Construct terminal controller."""
        super().__init__(jobs_cmds)

        self.queue: List[str] = list()

        if jobs_cmds:
            self.queue = parse_and_split_input(
                an_input=" ".join(jobs_cmds), custom_filters=[]
            )

        self.update_success = False

        self.update_runtime_choices()

    def update_runtime_choices(self):
        """Update runtime choices."""
        self.ROUTINE_FILES = {
            filepath.name: filepath
            for filepath in (MISCELLANEOUS_DIRECTORY / "routines").rglob("*.openbb")
        }
        self.ROUTINE_FILES.update(
            {
                filepath.name: filepath
                for filepath in USER_ROUTINES_DIRECTORY.rglob("*.openbb")
            }
        )
        self.ROUTINE_CHOICES = {filename: None for filename in self.ROUTINE_FILES}
        if session and obbff.USE_PROMPT_TOOLKIT:
            choices: dict = {c: {} for c in self.controller_choices}
            choices["support"] = self.SUPPORT_CHOICES
            choices["exe"] = self.ROUTINE_CHOICES

            self.completer = NestedCompleter.from_nested_dict(choices)

    def print_help(self):
        """Print help."""
        mt = MenuText("")
        mt.add_info("_home_")
        mt.add_cmd("intro")
        mt.add_cmd("about")
        mt.add_cmd("support")
        mt.add_cmd("survey")
        if not is_packaged_application():
            mt.add_cmd("update")
        mt.add_cmd("wiki")
        mt.add_cmd("record")
        mt.add_cmd("stop")
        mt.add_raw("\n")
        mt.add_info("_configure_")
        mt.add_menu("keys")
        mt.add_menu("featflags")
        mt.add_menu("sources")
        mt.add_menu("settings")
        mt.add_raw("\n")
        mt.add_cmd("news")
        mt.add_cmd("exe")
        mt.add_raw("\n")
        mt.add_info("_main_menu_")
        mt.add_menu("stocks")
        mt.add_menu("crypto")
        mt.add_menu("etf")
        mt.add_menu("economy")
        mt.add_menu("forex")
        mt.add_menu("futures")
        mt.add_menu("alternative")
        mt.add_raw("\n")
        mt.add_info("_others_")
        mt.add_menu("econometrics")
        mt.add_menu("forecast")
        mt.add_menu("portfolio")
        mt.add_menu("dashboards")
        mt.add_menu("reports")
        console.print(text=mt.menu_text, menu="Home")
        self.update_runtime_choices()

    def call_news(self, other_args: List[str]) -> None:
        """Process news command."""
        parse = argparse.ArgumentParser(
            add_help=False,
            prog="news",
            description="display news articles based on term and data sources",
        )
        parse.add_argument(
            "-t",
            "--term",
            dest="term",
            default=[""],
            nargs="+",
            help="search for a term on the news",
        )
        parse.add_argument(
            "-s",
            "--sources",
            dest="sources",
            default="bloomberg",
            type=str,
            help="sources from where to get news from (separated by comma)",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-t")
        news_parser = self.parse_known_args_and_warn(
            parse, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED, limit=5
        )
        if news_parser:
            feedparser_view.display_news(
                term=" ".join(news_parser.term),
                sources=news_parser.sources,
                limit=news_parser.limit,
                export=news_parser.export,
            )

    def call_guess(self, other_args: List[str]) -> None:
        """Process guess command."""
        import time
        import json
        import random

        if self.GUESS_NUMBER_TRIES_LEFT == 0 and self.GUESS_SUM_SCORE < 0.01:
            parser_exe = argparse.ArgumentParser(
                add_help=False,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                prog="guess",
                description="Guess command to achieve task successfully.",
            )
            parser_exe.add_argument(
                "-l",
                "--limit",
                type=check_positive,
                help="Number of tasks to attempt.",
                dest="limit",
                default=1,
            )
            if other_args and "-" not in other_args[0][0]:
                other_args.insert(0, "-l")
                ns_parser_guess = parse_simple_args(parser_exe, other_args)

                if self.GUESS_TOTAL_TRIES == 0:
                    self.GUESS_NUMBER_TRIES_LEFT = ns_parser_guess.limit
                    self.GUESS_SUM_SCORE = 0
                    self.GUESS_TOTAL_TRIES = ns_parser_guess.limit

        try:
            with open(obbff.GUESS_EASTER_EGG_FILE) as f:
                # Load the file as a JSON document
                json_doc = json.load(f)

                task = random.choice(list(json_doc.keys()))  # nosec
                solution = json_doc[task]

                start = time.time()
                console.print(f"\n[yellow]{task}[/yellow]\n")
                if isinstance(session, PromptSession):
                    an_input = session.prompt("GUESS / $ ")
                else:
                    an_input = ""
                time_dif = time.time() - start

                # When there are multiple paths to same solution
                if isinstance(solution, List):
                    if an_input.lower() in [s.lower() for s in solution]:
                        self.queue = an_input.split("/") + ["home"]
                        console.print(
                            f"\n[green]You guessed correctly in {round(time_dif, 2)} seconds![green]\n"
                        )
                        # If we are already counting successes
                        if self.GUESS_TOTAL_TRIES > 0:
                            self.GUESS_CORRECTLY += 1
                            self.GUESS_SUM_SCORE += time_dif
                    else:
                        solutions_texts = "\n".join(solution)
                        console.print(
                            f"\n[red]You guessed wrong! The correct paths would have been:\n{solutions_texts}[/red]\n"
                        )

                # When there is a single path to the solution
                else:
                    if an_input.lower() == solution.lower():
                        self.queue = an_input.split("/") + ["home"]
                        console.print(
                            f"\n[green]You guessed correctly in {round(time_dif, 2)} seconds![green]\n"
                        )
                        # If we are already counting successes
                        if self.GUESS_TOTAL_TRIES > 0:
                            self.GUESS_CORRECTLY += 1
                            self.GUESS_SUM_SCORE += time_dif
                    else:
                        console.print(
                            f"\n[red]You guessed wrong! The correct path would have been:\n{solution}[/red]\n"
                        )

                # Compute average score and provide a result if it's the last try
                if self.GUESS_TOTAL_TRIES > 0:

                    self.GUESS_NUMBER_TRIES_LEFT -= 1
                    if self.GUESS_NUMBER_TRIES_LEFT == 0 and self.GUESS_TOTAL_TRIES > 1:
                        color = (
                            "green"
                            if self.GUESS_CORRECTLY == self.GUESS_TOTAL_TRIES
                            else "red"
                        )
                        console.print(
                            f"[{color}]OUTCOME: You got {int(self.GUESS_CORRECTLY)} out of"
                            f" {int(self.GUESS_TOTAL_TRIES)}.[/{color}]\n"
                        )
                        if self.GUESS_CORRECTLY == self.GUESS_TOTAL_TRIES:
                            avg = self.GUESS_SUM_SCORE / self.GUESS_TOTAL_TRIES
                            console.print(
                                f"[green]Average score: {round(avg, 2)} seconds![/green]\n"
                            )
                        self.GUESS_TOTAL_TRIES = 0
                        self.GUESS_CORRECTLY = 0
                        self.GUESS_SUM_SCORE = 0
                    else:
                        self.queue += ["guess"]

        except Exception as e:
            console.print(
                f"[red]Failed to load guess game from file: "
                f"{obbff.GUESS_EASTER_EGG_FILE}[/red]"
            )
            console.print(f"[red]{e}[/red]")

    @staticmethod
    def call_survey(_) -> None:
        """Process survey command."""
        webbrowser.open("https://openbb.co/survey")

    def call_update(self, _):
        """Process update command."""
        if not is_packaged_application():
            self.update_success = not update_terminal()
        else:
            console.print(
                "Find the most recent release of the OpenBB Terminal here: "
                "https://openbb.co/products/terminal#get-started\n"
            )

    def call_keys(self, _):
        """Process keys command."""
        from openbb_terminal.keys_controller import KeysController

        self.queue = self.load_class(KeysController, self.queue, env_file)

    def call_settings(self, _):
        """Process settings command."""
        from openbb_terminal.settings_controller import SettingsController

        self.queue = self.load_class(SettingsController, self.queue, env_file)

    def call_featflags(self, _):
        """Process feature flags command."""
        from openbb_terminal.featflags_controller import FeatureFlagsController

        self.queue = self.load_class(FeatureFlagsController, self.queue)

    def call_stocks(self, _):
        """Process stocks command."""
        from openbb_terminal.stocks.stocks_controller import StocksController

        self.queue = self.load_class(StocksController, self.queue)

    def call_crypto(self, _):
        """Process crypto command."""
        from openbb_terminal.cryptocurrency.crypto_controller import CryptoController

        self.queue = self.load_class(CryptoController, self.queue)

    def call_economy(self, _):
        """Process economy command."""
        from openbb_terminal.economy.economy_controller import EconomyController

        self.queue = self.load_class(EconomyController, self.queue)

    def call_etf(self, _):
        """Process etf command."""
        from openbb_terminal.etf.etf_controller import ETFController

        self.queue = self.load_class(ETFController, self.queue)

    def call_forex(self, _):
        """Process forex command."""
        from openbb_terminal.forex.forex_controller import ForexController

        self.queue = self.load_class(ForexController, self.queue)

    def call_reports(self, _):
        """Process reports command."""
        from openbb_terminal.reports.reports_controller import (
            ReportController,
        )

        self.queue = self.load_class(ReportController, self.queue)

    def call_dashboards(self, _):
        """Process dashboards command."""
        if not is_packaged_application():
            from openbb_terminal.dashboards.dashboards_controller import (
                DashboardsController,
            )

            self.queue = self.load_class(DashboardsController, self.queue)
        else:
            console.print("This feature is coming soon.")
            console.print(
                "Use the source code and an Anaconda environment if you are familiar with Python."
            )

    def call_alternative(self, _):
        """Process alternative command."""
        from openbb_terminal.alternative.alt_controller import (
            AlternativeDataController,
        )

        self.queue = self.load_class(AlternativeDataController, self.queue)

    def call_econometrics(self, _):
        """Process econometrics command."""
        from openbb_terminal.econometrics.econometrics_controller import (
            EconometricsController,
        )

        self.queue = EconometricsController(self.queue).menu()

    def call_forecast(self, _):
        """Process forecast command."""
        from openbb_terminal.forecast.forecast_controller import (
            ForecastController,
        )

        self.queue = self.load_class(ForecastController, "", pd.DataFrame(), self.queue)

    def call_portfolio(self, _):
        """Process portfolio command."""
        from openbb_terminal.portfolio.portfolio_controller import (
            PortfolioController,
        )

        self.queue = self.load_class(PortfolioController, self.queue)

    def call_sources(self, _):
        """Process sources command."""
        from openbb_terminal.sources_controller import SourcesController

        self.queue = self.load_class(SourcesController, self.queue)

    def call_futures(self, _):
        """Process futures command."""
        from openbb_terminal.futures.futures_controller import FuturesController

        self.queue = self.load_class(FuturesController, self.queue)

    def call_intro(self, _):
        """Process intro command."""
        console.print(panel.Panel("[purple]Welcome to the OpenBB Terminal.[/purple]"))
        console.print(
            "\nThe following walkthrough will guide you towards making the most out of the OpenBB Terminal.\n\n"
            "Press Enter to continue or 'q' followed by Enter to exit."
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#1 - Commands vs menu.[/purple]"))
        console.print(
            "\nMenus are a collection of 'commands' and 'sub-menus'.\n"
            "You can identify them through their distinct color and a '>' at the beginning of the line\n\n"
            "For instance:\n"
            "[menu]>   stocks             access historical pricing data, options, sector [/menu]"
            "[menu]and industry, and overall due diligence [/menu]\n\n\n"
            "Commands are expected to return data either as a chart or table.\n"
            "You can identify them through their distinct color\n\n"
            "For instance:\n"
            "[cmds]>   news               display news articles based on term and data sources [/cmds]"
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#2 - Using commands[/purple]"))
        console.print(
            "\nCommands throughout the terminal can have additional arguments.\n\n"
            "Let's say that in the current menu, you want to have more information about the command 'news'. \n\n"
            "You can either see the available arguments in the terminal, using: [param]news -h[/param]\n\n",
            "or you can find out more about it with an output example on the browser, using: [param]about news[/param]",
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#3 - Setting API Keys[/purple]"))
        console.print(
            "\nThe OpenBB Terminal does not own any of the data you have access to.\n\n"
            "Instead, we provide the infrastructure to access over 100 different data sources "
            "from a single location.\n\n"
            "Thus, it is necessary for each user to set their own API keys for the various third party sources\n\n"
            "You can find more about this on the '[param]keys[/param]' menu.\n\n"
            "For many commands, there are multiple data sources that can be selected.\n\n"
            "The help menu shows the data sources supported by each command.\n\n"
            "For instance:\n"
            "[cmds]    load               load a specific stock ticker and additional info for analysis   [/cmds]"
            "[src][YahooFinance, IEXCloud, AlphaVantage, Polygon, EODHD] [/src]\n\n"
            "The user can go into the '[param]sources[/param]' menu and select their preferred default data source."
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(
            panel.Panel("[purple]#4 - Symbol dependent menus and commands[/purple]")
        )
        console.print(
            "\nThroughout the terminal, you will see commands and menus greyed out.\n\n"
            "These menus or commands cannot be accessed until an object is loaded.\n\n"
            "Let's take as an example the '[param]stocks[/param]' menu.\n\n"
            "You will see that the command '[param]disc[/param]' is available as its goal is to discover new tickers:\n"
            "[menu]>   stocks             access historical pricing data, options, sector [/menu]\n\n"
            "On the other hand, '[param]fa[/param]' menu (fundamental analysis) requires a ticker to be loaded.\n\n"
            "And therefore, appears as:\n"
            "[dim]>   fa                 fundamental analysis of loaded ticker [/dim]\n\n"
            "Once a ticker is loaded with: [param]load TSLA[/param]\n\n"
            "The '[param]fa[/param]' menu will be available as:\n"
            "[menu]>   fa                 fundamental analysis of loaded ticker [/menu]"
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#5 - Terminal Navigation[/purple]"))
        console.print(
            "\nThe terminal has a tree like structure, where menus branch off into new menus.\n\n"
            "The users current location is displayed before the text prompt.\n\n"
            "For instance, if the user is inside the menu disc which is inside stocks, the following prompt "
            "will appear: \n2022 Oct 18, 21:53 (🦋) [param]/stocks/disc/[/param] $\n\n"
            "If the user wants to go back to the menu above, all they need to do is type '[param]q[/param]'.\n\n"
            "If the user wants to go back to the home of the terminal, they can type '[param]/[/param]' instead.\n\n"
            "Note: Always type '[param]h[/param]' to know what commands are available in each menu"
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#6 - Command Pipeline[/purple]"))
        console.print(
            "\nThe terminal offers the capability of allowing users to speed up their "
            "navigation and command execution."
            "\n\nTherefore, typing the following prompt is valid:\n"
            "2022 Oct 18, 21:53 (🦋) / $ [param]stocks/load TSLA/dd/pt[/param]\n\n"
            "In this example, the terminal - in a single action - will go into '[param]stocks[/param]' menu, "
            "run command '[param]load[/param]' with '[param]TSLA[/param]' as input, \n"
            "go into sub-menu '[param]dd[/param]' (due diligence) and run the command "
            "'[param]pt[/param]' (price target)."
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#6 - OpenBB Scripts[/purple]"))
        console.print(
            "\nThe command pipeline capability is great, but the user experience wasn't great copy-pasting large "
            "lists of commands.\n\n"
            "We allow the user to create a text file of the form:\n\n"
            "[param]FOLDER_PATH/my_script.openbb[/param]\n"
            "stocks\nload TSLA\ndd\npt\n\n"
            "which can be run through the '[param]exe[/param]' command in the home menu, with:\n"
            "2022 Oct 18, 22:33 (🦋) / $ [param]exe FOLDER_PATH/my_script.openbb[/param]\n\n"
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(
            panel.Panel("[purple]#7 - OpenBB Scripts with Arguments[/purple]")
        )
        console.print(
            "\nThe user can create a script that includes arguments for the commands.\n\n"
            "Example:\n\n"
            "[param]FOLDER_PATH/my_script_with_variable_input.openbb[/param]\n"
            "stocks\n# this is a comment\nload $ARGV[0]\ndd\npt\nq\nload $ARGV[1]\ncandle\n\n"
            "and then, if this script is run with:\n"
            "2022 Oct 18, 22:33 (🦋) / $ [param]exe FOLDER_PATH/my_script_with_variable_input.openbb "
            "-i AAPL,MSFT[/param]\n\n"
            "This means that the [param]pt[/param] will run on [param]AAPL[/param] while "
            "[param]candle[/param] on [param]MSFT[/param]"
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#8 - OpenBB Script Generation/purple]"))
        console.print(
            "\n"
            "To make it easier for users to create scripts, we have created a "
            "command that 'records' user commands "
            "directly into a script.\n\n"
            "From the home menu, the user can run:\n"
            "2022 Oct 18, 22:33 (🦋) / $ [param]record[/param]\n\n"
            "and then perform your typical investment research workflow before entering\n\n"
            "2022 Oct 18, 22:33 (🦋) / $ [param]stop[/param]\n\n"
            "After stopping, the script will be saved to the 'scripts' folder."
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#9 - Terminal Customization[/purple]"))
        console.print(
            "\nUsers should explore the [param]settings[/param] and [param]featflags[/param] menus "
            "to configure their terminal.\n\n"
            "The fact that our terminal is fully open source allows users to be able to customize "
            "anything they want.\n\n"
            "If you are interested in contributing to the project, please check:\n"
            "[param]https://github.com/OpenBB-finance/OpenBBTerminal[/param]"
        )
        if input("") == "q":
            return
        console.print("\n")

        console.print(panel.Panel("[purple]#10 - Support[/purple]"))
        console.print(
            "\n"
            "We are nothing without our community, hence we put a lot of effort in being here for you.\n\n"
            "If you find any bug that you wish to report to improve the terminal you can do so with:\n"
            "2022 Oct 18, 22:33 (🦋) / $ [param]support CMD[/param]\n\n"
            "which should open a form in your browser where you can report the bug in said 'CMD'.\n\n"
            "If you want to know more, or have any further question. Please join us on Discord:\n"
            "[param]https://openbb.co/discord[/param]"
        )

    def call_exe(self, other_args: List[str]):
        """Process exe command."""
        # Merge rest of string path to other_args and remove queue since it is a dir
        other_args += self.queue

        if not other_args:
            console.print(
                "[red]Provide a path to the routine you wish to execute.\n[/red]"
            )
            return

        full_input = " ".join(other_args)
        if " " in full_input:
            other_args_processed = full_input.split(" ")
        else:
            other_args_processed = [full_input]
        self.queue = []

        path_routine = ""
        args = list()
        for idx, path_dir in enumerate(other_args_processed):
            if path_dir in ("-i", "--input"):
                args = [path_routine[1:]] + other_args_processed[idx:]
                break
            if path_dir not in ("--file"):
                path_routine += f"/{path_dir}"

        if not args:
            args = [path_routine[1:]]

        parser_exe = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="exe",
            description="Execute automated routine script.",
        )
        parser_exe.add_argument(
            "--file",
            help="The path or .openbb file to run.",
            dest="path",
            default="",
            required="-h" not in args,
        )
        parser_exe.add_argument(
            "-i",
            "--input",
            help="Select multiple inputs to be replaced in the routine and separated by commas. E.g. GME,AMC,BTC-USD",
            dest="routine_args",
            type=lambda s: [str(item) for item in s.split(",")],
        )
        if args and "-" not in args[0][0]:
            args.insert(0, "--file")
        ns_parser_exe = parse_simple_args(parser_exe, args)
        if ns_parser_exe:
            if ns_parser_exe.path:
                if ns_parser_exe.path in self.ROUTINE_CHOICES:
                    path = self.ROUTINE_FILES[ns_parser_exe.path]
                else:
                    path = ns_parser_exe.path

                with open(path) as fp:
                    raw_lines = [
                        x for x in fp if (not is_reset(x)) and ("#" not in x) and x
                    ]
                    raw_lines = [
                        raw_line.strip("\n")
                        for raw_line in raw_lines
                        if raw_line.strip("\n")
                    ]

                    lines = list()
                    for rawline in raw_lines:
                        templine = rawline

                        # Check if dynamic parameter exists in script
                        if "$ARGV" in rawline:
                            # Check if user has provided inputs through -i or --input
                            if ns_parser_exe.routine_args:
                                for i, arg in enumerate(ns_parser_exe.routine_args):
                                    # Check what is the location of the ARGV to be replaced
                                    if f"$ARGV[{i}]" in templine:
                                        templine = templine.replace(f"$ARGV[{i}]", arg)

                                # Check if all ARGV have been removed, otherwise means that there are less inputs
                                # when running the script than the script expects
                                if "$ARGV" in templine:
                                    console.print(
                                        "[red]Not enough inputs were provided to fill in dynamic variables. "
                                        "E.g. --input VAR1,VAR2,VAR3[/red]\n"
                                    )
                                    return

                                lines.append(templine)
                            # The script expects a parameter that the user has not provided
                            else:
                                console.print(
                                    "[red]The script expects parameters, "
                                    "run the script again with --input defined.[/red]\n"
                                )
                                return
                        else:
                            lines.append(templine)

                    simulate_argv = f"/{'/'.join([line.rstrip() for line in lines])}"
                    file_cmds = simulate_argv.replace("//", "/home/").split()
                    file_cmds = (
                        insert_start_slash(file_cmds) if file_cmds else file_cmds
                    )
                    cmds_with_params = " ".join(file_cmds)
                    self.queue = [
                        val
                        for val in parse_and_split_input(
                            an_input=cmds_with_params, custom_filters=[]
                        )
                        if val
                    ]

                    if "export" in self.queue[0]:
                        export_path = self.queue[0].split(" ")[1]
                        # If the path selected does not start from the user root, give relative location from root
                        if export_path[0] == "~":
                            export_path = export_path.replace(
                                "~", HOME_DIRECTORY.as_posix()
                            )
                        elif export_path[0] != "/":
                            export_path = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)), export_path
                            )

                        # Check if the directory exists
                        if os.path.isdir(export_path):
                            console.print(
                                f"Export data to be saved in the selected folder: '{export_path}'"
                            )
                        else:
                            os.makedirs(export_path)
                            console.print(
                                f"[green]Folder '{export_path}' successfully created.[/green]"
                            )
                        obbff.EXPORT_FOLDER_PATH = export_path
                        self.queue = self.queue[1:]


# pylint: disable=global-statement
def terminal(jobs_cmds: List[str] = None, test_mode=False):
    """Terminal Menu."""
    if not test_mode:
        setup_logging()
    logger.info("START")
    log_all_settings()

    if jobs_cmds is not None and jobs_cmds:
        logger.info("INPUT: %s", "/".join(jobs_cmds))

    export_path = ""
    if jobs_cmds and "export" in jobs_cmds[0]:
        export_path = jobs_cmds[0].split("/")[0].split(" ")[1]
        jobs_cmds = ["/".join(jobs_cmds[0].split("/")[1:])]

    ret_code = 1
    t_controller = TerminalController(jobs_cmds)
    an_input = ""

    if export_path:
        # If the path selected does not start from the user root,
        # give relative location from terminal root
        if export_path[0] == "~":
            export_path = export_path.replace("~", HOME_DIRECTORY.as_posix())
        elif export_path[0] != "/":
            export_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), export_path
            )

        # Check if the directory exists
        if os.path.isdir(export_path):
            console.print(
                f"Export data to be saved in the selected folder: '{export_path}'"
            )
        else:
            os.makedirs(export_path)
            console.print(
                f"[green]Folder '{export_path}' successfully created.[/green]"
            )
        obbff.EXPORT_FOLDER_PATH = export_path

    bootup()
    if not jobs_cmds:
        welcome_message()

        if first_time_user():
            t_controller.call_intro(None)

        t_controller.print_help()
        check_for_updates()

    dotenv.load_dotenv(USER_ENV_FILE)
    dotenv.load_dotenv(REPOSITORY_ENV_FILE, override=True)

    while ret_code:
        if obbff.ENABLE_QUICK_EXIT:
            console.print("Quick exit enabled")
            break

        # There is a command in the queue
        if t_controller.queue and len(t_controller.queue) > 0:
            # If the command is quitting the menu we want to return in here
            if t_controller.queue[0] in ("q", "..", "quit"):
                print_goodbye()
                break

            # Consume 1 element from the queue
            an_input = t_controller.queue[0]
            t_controller.queue = t_controller.queue[1:]

            # Print the current location because this was an instruction and we want user to know what was the action
            if an_input and an_input.split(" ")[0] in t_controller.CHOICES_COMMANDS:
                console.print(f"{get_flair()} / $ {an_input}")

        # Get input command from user
        else:
            # Get input from user using auto-completion
            if session and obbff.USE_PROMPT_TOOLKIT:
                try:
                    if obbff.TOOLBAR_HINT:
                        an_input = session.prompt(
                            f"{get_flair()} / $ ",
                            completer=t_controller.completer,
                            search_ignore_case=True,
                            bottom_toolbar=HTML(
                                '<style bg="ansiblack" fg="ansiwhite">[h]</style> help menu    '
                                '<style bg="ansiblack" fg="ansiwhite">[q]</style> return to previous menu    '
                                '<style bg="ansiblack" fg="ansiwhite">[e]</style> exit terminal    '
                                '<style bg="ansiblack" fg="ansiwhite">[cmd -h]</style> '
                                "see usage and available options    "
                                '<style bg="ansiblack" fg="ansiwhite">[about]</style> Getting Started Documentation'
                            ),
                            style=Style.from_dict(
                                {
                                    "bottom-toolbar": "#ffffff bg:#333333",
                                }
                            ),
                        )
                    else:
                        an_input = session.prompt(
                            f"{get_flair()} / $ ",
                            completer=t_controller.completer,
                            search_ignore_case=True,
                        )
                except (KeyboardInterrupt, EOFError):
                    print_goodbye()
                    break
            elif is_papermill():
                pass
            else:
                # Get input from user without auto-completion
                an_input = input(f"{get_flair()} / $ ")

        try:
            # Process the input command
            t_controller.queue = t_controller.switch(an_input)
            if an_input in ("q", "quit", "..", "exit", "e"):
                print_goodbye()
                break

            # Check if the user wants to reset application
            if an_input in ("r", "reset") or t_controller.update_success:
                ret_code = reset(t_controller.queue if t_controller.queue else [])
                if ret_code != 0:
                    print_goodbye()
                    break

        except SystemExit:
            logger.exception(
                "The command '%s' doesn't exist on the / menu.",
                an_input,
            )
            console.print(
                f"[red]The command '{an_input}' doesn't exist on the / menu.[/red]\n",
            )
            similar_cmd = difflib.get_close_matches(
                an_input.split(" ")[0] if " " in an_input else an_input,
                t_controller.controller_choices,
                n=1,
                cutoff=0.7,
            )
            if similar_cmd:
                if " " in an_input:
                    candidate_input = (
                        f"{similar_cmd[0]} {' '.join(an_input.split(' ')[1:])}"
                    )
                    if candidate_input == an_input:
                        an_input = ""
                        t_controller.queue = []
                        console.print("\n")
                        continue
                    an_input = candidate_input
                else:
                    an_input = similar_cmd[0]

                console.print(f"[green]Replacing by '{an_input}'.[/green]")
                t_controller.queue.insert(0, an_input)


def insert_start_slash(cmds: List[str]) -> List[str]:
    """Insert a slash at the beginning of a command sequence."""
    if not cmds[0].startswith("/"):
        cmds[0] = f"/{cmds[0]}"
    if cmds[0].startswith("/home"):
        cmds[0] = f"/{cmds[0][5:]}"
    return cmds


def run_scripts(
    path: Path,
    test_mode: bool = False,
    verbose: bool = False,
    routines_args: List[str] = None,
):
    """Run given .openbb scripts.

    Parameters
    ----------
    path : str
        The location of the .openbb file
    test_mode : bool
        Whether the terminal is in test mode
    verbose : bool
        Whether to run tests in verbose mode
    routines_args : List[str]
        One or multiple inputs to be replaced in the routine and separated by commas.
        E.g. GME,AMC,BTC-USD
    """
    if path.exists():
        with path.open() as fp:
            raw_lines = [x for x in fp if (not is_reset(x)) and ("#" not in x) and x]
            raw_lines = [
                raw_line.strip("\n") for raw_line in raw_lines if raw_line.strip("\n")
            ]

            if routines_args:
                lines = list()
                for rawline in raw_lines:
                    templine = rawline
                    for i, arg in enumerate(routines_args):
                        templine = templine.replace(f"$ARGV[{i}]", arg)
                    lines.append(templine)
            else:
                lines = raw_lines

            if test_mode and "exit" not in lines[-1]:
                lines.append("exit")

            export_folder = ""
            if "export" in lines[0]:
                export_folder = lines[0].split("export ")[1].rstrip()
                lines = lines[1:]

            simulate_argv = f"/{'/'.join([line.rstrip() for line in lines])}"
            file_cmds = simulate_argv.replace("//", "/home/").split()
            file_cmds = insert_start_slash(file_cmds) if file_cmds else file_cmds
            if export_folder:
                file_cmds = [f"export {export_folder}{' '.join(file_cmds)}"]
            else:
                file_cmds = [" ".join(file_cmds)]

            if not test_mode:
                terminal(file_cmds, test_mode=True)
            else:
                if verbose:
                    terminal(file_cmds, test_mode=True)
                else:
                    with suppress_stdout():
                        terminal(file_cmds, test_mode=True)
    else:
        console.print(f"File '{path}' doesn't exist. Launching base terminal.\n")
        if not test_mode:
            terminal()


def build_test_path_list(path_list: List[str], filtert: str) -> List[Path]:
    """Build the paths to use in test mode."""
    if path_list == "":
        console.print("Please send a path when using test mode")
        return []

    test_files = []

    for path in path_list:
        user_script_path = USER_DATA_DIRECTORY / "scripts" / path
        default_script_path = MISCELLANEOUS_DIRECTORY / path

        if user_script_path.exists():
            chosen_path = user_script_path
        elif default_script_path.exists():
            chosen_path = default_script_path
        else:
            console.print(f"\n[red]Can't find the file:{path}[/red]\n")
            continue

        if chosen_path.is_file() and str(chosen_path).endswith(".openbb"):
            test_files.append(chosen_path)
        elif chosen_path.is_dir():
            script_directory = chosen_path
            script_list = script_directory.glob("**/*.openbb")
            script_list = [script for script in script_list if script.is_file()]
            script_list = [script for script in script_list if filtert in str(script)]
            test_files.extend(script_list)

    return test_files


def run_test_list(path_list: List[str], filtert: str, verbose: bool):
    """Run commands in test mode."""
    os.environ["DEBUG_MODE"] = "true"

    test_files = build_test_path_list(path_list=path_list, filtert=filtert)
    SUCCESSES = 0
    FAILURES = 0
    fails = {}
    length = len(test_files)
    i = 0
    console.print("[green]OpenBB Terminal Integrated Tests:\n[/green]")
    for file in test_files:
        console.print(f"{((i/length)*100):.1f}%  {file}")
        try:
            run_scripts(file, test_mode=True, verbose=verbose)
            SUCCESSES += 1
        except Exception as e:
            fails[file] = e
            FAILURES += 1
        i += 1
    if fails:
        console.print("\n[red]Failures:[/red]\n")
        for file, exception in fails.items():
            logger.error("%s: %s failed", file, exception)
        # Write results to CSV
        timestamp = datetime.now().timestamp()
        output_path = f"{timestamp}_tests.csv"
        with open(output_path, "w") as file:  # type: ignore
            header = ["File", "Error"]
            writer = csv.DictWriter(file, fieldnames=header)  # type: ignore
            writer.writeheader()
            for file, exception in fails.items():
                writer.writerow({"File": file, "Error": exception})

        console.print(f"CSV of errors saved to {output_path}")

    console.print(
        f"Summary: [green]Successes: {SUCCESSES}[/green] [red]Failures: {FAILURES}[/red]"
    )


def run_routine(file: str, routines_args=List[str]):
    """Execute command routine from .openbb file."""
    user_routine_path = USER_DATA_DIRECTORY / "routines" / file
    default_routine_path = MISCELLANEOUS_DIRECTORY / "routines" / file

    if user_routine_path.exists():
        run_scripts(path=user_routine_path, routines_args=routines_args)
    elif default_routine_path.exists():
        run_scripts(path=default_routine_path, routines_args=routines_args)
    else:
        print(
            f"Routine not found, please put your `.openbb` file into : {user_routine_path}."
        )


def main(
    debug: bool,
    test: bool,
    filtert: str,
    path_list: List[str],
    verbose: bool,
    routines_args: List[str] = None,
    **kwargs,
):
    """Run the terminal with various options.

    Parameters
    ----------
    debug : bool
        Whether to run the terminal in debug mode
    test : bool
        Whether to run the terminal in integrated test mode
    filtert : str
        Filter test files with given string in name
    paths : List[str]
        The paths to run for scripts or to test
    verbose : bool
        Whether to show output from tests
    routines_args : List[str]
        One or multiple inputs to be replaced in the routine and separated by commas.
        E.g. GME,AMC,BTC-USD
    """
    if kwargs["module"] == "ipykernel_launcher":
        ipykernel_launcher(kwargs["module_file"], kwargs["module_hist_file"])

    if test:
        run_test_list(path_list=path_list, filtert=filtert, verbose=verbose)
        return

    if debug:
        os.environ["DEBUG_MODE"] = "true"

    if isinstance(path_list, list) and path_list[0].endswith(".openbb"):
        run_routine(file=path_list[0], routines_args=routines_args)
    elif path_list:
        argv_cmds = list([" ".join(path_list).replace(" /", "/home/")])
        argv_cmds = insert_start_slash(argv_cmds) if argv_cmds else argv_cmds
        terminal(argv_cmds)
    else:
        terminal()


def parse_args_and_run():
    """Parse input arguments and run terminal."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="terminal",
        description="The OpenBB Terminal.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Runs the terminal in debug mode.",
    )
    parser.add_argument(
        "--file",
        help="The path or .openbb file to run.",
        dest="path",
        nargs="+",
        default="",
        type=str,
    )
    parser.add_argument(
        "-t",
        "--test",
        dest="test",
        action="store_true",
        default=False,
        help="Whether to run in test mode.",
    )
    parser.add_argument(
        "--filter",
        help="Send a keyword to filter in file name",
        dest="filtert",
        default="",
        type=str,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose output for debugging",
        dest="verbose",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-i",
        "--input",
        help=(
            "Select multiple inputs to be replaced in the routine and separated by commas."
            "E.g. GME,AMC,BTC-USD"
        ),
        dest="routine_args",
        type=lambda s: [str(item) for item in s.split(",")],
        default=None,
    )
    # The args -m, -f and --HistoryManager.hist_file are used only in reports menu
    # by papermill and that's why they have suppress help.
    parser.add_argument(
        "-m",
        help=argparse.SUPPRESS,
        dest="module",
        default="",
        type=str,
    )
    parser.add_argument(
        "-f",
        help=argparse.SUPPRESS,
        dest="module_file",
        default="",
        type=str,
    )
    parser.add_argument(
        "--HistoryManager.hist_file",
        help=argparse.SUPPRESS,
        dest="module_hist_file",
        default="",
        type=str,
    )
    if sys.argv[1:] and "-" not in sys.argv[1][0]:
        sys.argv.insert(1, "--file")
    ns_parser, unknown = parser.parse_known_args()

    # This ensures that if terminal.py receives unknown args it will not start.
    # Use -d flag if you want to see the unknown args.
    if unknown:
        if ns_parser.debug:
            console.print(unknown)
        else:
            sys.exit(-1)

    main(
        ns_parser.debug,
        ns_parser.test,
        ns_parser.filtert,
        ns_parser.path,
        ns_parser.verbose,
        ns_parser.routine_args,
        module=ns_parser.module,
        module_file=ns_parser.module_file,
        module_hist_file=ns_parser.module_hist_file,
    )


if __name__ == "__main__":
    parse_args_and_run()
