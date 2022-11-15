"""Mutual Fund Controller"""
__docformat__ = "numpy"

import argparse
import logging
import os
from datetime import datetime, timedelta
from typing import List

import investpy
import pandas as pd

from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    EXPORT_BOTH_RAW_DATA_AND_FIGURES,
    EXPORT_ONLY_FIGURES_ALLOWED,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
    check_non_negative_float,
    check_positive,
    valid_date,
)
from openbb_terminal.menu import session
from openbb_terminal.mutual_funds import (
    investpy_model,
    investpy_view,
    yfinance_view,
    avanza_view,
)
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText

logger = logging.getLogger(__name__)


class FundController(BaseController):
    """Fund Controller class"""

    CHOICES_COMMANDS = [
        "resources",
        "country",
        "search",
        "info",
        "load",
        "plot",
        "sector",
        "equity",
        "alswe",
        "infoswe",
        "forecast",
    ]

    fund_countries = investpy.funds.get_fund_countries()
    search_by_choices = ["name", "issuer", "isin", "symbol"]
    search_cols = [
        "country",
        "name",
        "symbol",
        "issuer",
        "isin",
        "asset_class",
        "currency",
        "underlying",
    ]
    focus_choices = ["all", "country", "sector", "holding"]
    PATH = "/funds/"
    FILE_PATH = os.path.join(os.path.dirname(__file__), "README.md")

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        self.country = "united states"
        self.data = pd.DataFrame()
        self.fund_name = ""
        self.fund_symbol = ""
        self.TRY_RELOAD = True

        if session and obbff.USE_PROMPT_TOOLKIT:
            choices: dict = {c: {} for c in self.controller_choices}

            one_to_hundred: dict = {str(c): {} for c in range(1, 100)}
            choices["country"] = {c: {} for c in self.fund_countries}
            choices["overview"] = {
                "--limit": None,
                "-l": "--limit",
            }
            choices["search"] = {
                "--by": {c: {} for c in self.search_by_choices},
                "-b": "--by",
                "--fund": None,
                "--sortby": {c: None for c in self.search_cols},
                "-s": "--sortby",
                "--limit": None,
                "-l": "--limit",
                "--reverse": {},
                "-r": "--reverse",
            }
            choices["load"] = {
                "--fund": None,
                "--name": {},
                "-n": "--name",
                "--start": None,
                "-s": "--start",
                "--end": None,
                "-e": "--end",
            }
            choices["sector"] = {
                "--min": one_to_hundred,
                "-m": "--min",
            }
            choices["alswe"] = {"--focus": {c: {} for c in self.focus_choices}}

            choices["support"] = self.SUPPORT_CHOICES
            choices["about"] = self.ABOUT_CHOICES

            self.completer = NestedCompleter.from_nested_dict(choices)

    def print_help(self):
        """Print help"""
        if self.fund_name:
            if self.fund_symbol:
                fund_string = f"{self.fund_name} ({self.fund_symbol})"
            else:
                fund_string = f"{self.fund_name}"
        else:
            fund_string = ""
        mt = MenuText("funds/")
        mt.add_cmd("country")
        mt.add_raw("\n")
        mt.add_param("_country", self.country.title())
        mt.add_raw("\n")
        mt.add_cmd("search")
        mt.add_cmd("load")
        mt.add_raw("\n")
        mt.add_param("_fund", fund_string)
        mt.add_raw("\n")
        mt.add_cmd("info", self.fund_symbol)
        mt.add_cmd("plot", self.fund_symbol)
        if self.country == "united states":
            mt.add_cmd("sector", self.fund_symbol)
            mt.add_cmd("equity", self.fund_symbol)
        if self.country == "sweden":
            mt.add_cmd("alswe", self.fund_symbol)
            mt.add_cmd("infoswe", self.fund_symbol)
            mt.add_cmd("forecast", self.fund_symbol)
        console.print(text=mt.menu_text, menu="Mutual Funds")

    def custom_reset(self):
        """Class specific component of reset command"""
        if self.fund_name:
            return ["funds", f"load {self.fund_name} --name"]
        return []

    @log_start_end(log=logger)
    def call_country(self, other_args: List[str]):
        """Process country command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="country",
            description="Set a country for funds",
        )
        parser.add_argument(
            "-n",
            "--name",
            type=str,
            dest="name",
            nargs="+",
            help="country to select",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-n")
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            country_candidate = " ".join(ns_parser.name)
            if country_candidate.lower() in self.fund_countries:
                self.country = " ".join(ns_parser.name)
            else:
                console.print(
                    f"{country_candidate.lower()} not a valid country to select."
                )
        return self.queue

    @log_start_end(log=logger)
    def call_search(self, other_args: List[str]):
        """Process country command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="search",
            description="Search mutual funds in selected country based on selected field.",
        )
        parser.add_argument(
            "-b",
            "--by",
            choices=self.search_by_choices,
            default="name",
            dest="by",
            help="Field to search by",
        )
        parser.add_argument(
            "--fund",
            help="Fund string to search for",
            dest="fund",
            type=str,
            nargs="+",
            required="-h" not in other_args,
        )
        parser.add_argument(
            "-s",
            "--sortby",
            dest="sortby",
            choices=self.search_cols,
            help="Column to sort by",
            default="name",
        )
        parser.add_argument(
            "-l",
            "--limit",
            help="Number of search results to show",
            type=check_positive,
            dest="limit",
            default=10,
        )
        parser.add_argument(
            "-r",
            "--reverse",
            action="store_true",
            dest="reverse",
            default=False,
            help=(
                "Data is sorted in descending order by default. "
                "Reverse flag will sort it in an ascending way. "
                "Only works when raw data is displayed."
            ),
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "--fund")
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            search_string = " ".join(ns_parser.fund)
            investpy_view.display_search(
                by=ns_parser.by,
                value=search_string,
                country=self.country,
                limit=ns_parser.limit,
                sortby=ns_parser.sortby,
                ascend=ns_parser.reverse,
            )
        return self.queue

    @log_start_end(log=logger)
    def call_overview(self, other_args: List[str]):
        """Process country command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="overview",
            description="Show overview of funds from selected country.",
        )
        parser.add_argument(
            "-l",
            "--limit",
            help="Number of search results to show",
            type=check_positive,
            dest="limit",
            default=10,
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            investpy_view.display_overview(
                self.country, limit=ns_parser.limit, export=ns_parser.export
            )
        return self.queue

    @log_start_end(log=logger)
    def call_info(self, other_args: List[str]):
        """Process country command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="info",
            description="Get fund information.",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if not self.fund_name:
                console.print(
                    "No fund loaded.  Please use `load` first to plot.\n", style="bold"
                )
                return self.queue
            investpy_view.display_fund_info(self.fund_name, country=self.country)
        return self.queue

    @log_start_end(log=logger)
    def call_load(self, other_args: List[str]):
        """Process country command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="load",
            description="Get historical data.",
        )
        parser.add_argument(
            "--fund",
            help="Fund string to search for",
            dest="fund",
            type=str,
            nargs="+",
            required="-h" not in other_args,
        )
        parser.add_argument(
            "-n",
            "--name",
            action="store_true",
            default=False,
            dest="name",
            help="Flag to indicate name provided instead of symbol.",
        )
        # Keeping the date format constant for investpy even though it needs to be reformatted in model
        parser.add_argument(
            "-s",
            "--start",
            type=valid_date,
            default=(datetime.now() - timedelta(days=366)).strftime("%Y-%m-%d"),
            dest="start",
            help="The starting date (format YYYY-MM-DD) of the fund",
        )
        parser.add_argument(
            "-e",
            "--end",
            type=valid_date,
            default=datetime.now().strftime("%Y-%m-%d"),
            dest="end",
            help="The ending date (format YYYY-MM-DD) of the fund",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "--fund")
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            parsed_fund = " ".join(ns_parser.fund)
            (
                self.data,
                self.fund_name,
                self.fund_symbol,
                self.country,
            ) = investpy_model.get_fund_historical(
                name=parsed_fund,
                by_name=ns_parser.name,
                country=self.country,
                start_date=ns_parser.start,
                end_date=ns_parser.end,
            )
            if self.data.empty:
                console.print(
                    """No data found.
Potential errors
    -- Incorrect country specified
    -- ISIN supplied instead of symbol
    -- Name used, but --name flag not passed"""
                )
        return self.queue

    @log_start_end(log=logger)
    def call_plot(self, other_args: List[str]):
        """Process country command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="plot",
            description="Plot historical data.",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_FIGURES_ALLOWED
        )
        if ns_parser:
            if not self.fund_symbol:
                console.print(
                    "No fund loaded.  Please use `load` first to plot.\n", style="bold"
                )
                return self.queue
            investpy_view.display_historical(
                self.data, name=self.fund_name, export=ns_parser.export
            )
        return self.queue

    @log_start_end(log=logger)
    def call_sector(self, other_args: List[str]):
        """Process sector command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="sector",
            description="Show fund sector weighting.",
        )
        parser.add_argument(
            "-m",
            "--min",
            type=check_non_negative_float,
            dest="min",
            help="Minimum positive float to display sector",
            default=5,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )
        if ns_parser:
            if self.country != "united states":
                console.print(
                    "YFinance implementation currently only supports funds from united states"
                )
                return self.queue
            if not self.fund_symbol or not self.fund_name:
                console.print(
                    "No fund loaded.  Please use `load` first to plot.\n", style="bold"
                )
                return self.queue
            yfinance_view.display_sector(
                self.fund_symbol,
                min_pct_to_display=ns_parser.min,
                export=ns_parser.export,
            )

        return self.queue

    @log_start_end(log=logger)
    def call_equity(self, other_args: List[str]):
        """Process equity command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="equity",
            description="Show fund equity holdings.",
        )

        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if self.country != "united states":
                console.print(
                    "YFinance implementation currently only supports funds from united states"
                )
                return self.queue
            if not self.fund_symbol or not self.fund_name:
                console.print(
                    "No fund loaded.  Please use `load` first to plot.\n", style="bold"
                )
                return self.queue
            yfinance_view.display_equity(self.fund_symbol)

        return self.queue

    @log_start_end(log=logger)
    def call_alswe(self, other_args: List[str]):
        """Process alswe command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="alswe",
            description="Show allocation of a swedish fund.",
        )
        parser.add_argument(
            "--focus",
            dest="focus",
            type=str,
            choices=self.focus_choices,
            default="all",
            help="The focus of the funds exposure/allocation",
        )

        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            ava_fund = pd.read_csv(
                os.path.join("openbb_terminal", "mutual_funds", "avanza_fund_ID.csv"),
                index_col=0,
            )
            if self.country != "sweden":
                console.print(
                    "Avanza implementation currently only supports funds from sweden."
                )
                return self.queue
            if self.fund_name == "":
                if self.fund_symbol != "":
                    self.fund_symbol = investpy_model.get_fund_name_from_symbol(
                        self.fund_symbol
                    )
                else:
                    console.print(
                        "No fund loaded. Please use `load` first.\n", style="bold"
                    )
                    return self.queue
            if self.fund_name.upper() not in ava_fund.index.str.upper().to_numpy():
                console.print("No fund data. Please use another fund", style="bold")
                return self.queue
            avanza_view.display_allocation(self.fund_name, ns_parser.focus)

        return self.queue

    @log_start_end(log=logger)
    def call_infoswe(self, other_args: List[str]):
        """Process infoswe command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="infoswe",
            description="Show fund info of a swedish fund.",
        )

        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            ava_fund = pd.read_csv(
                os.path.join("openbb_terminal", "mutual_funds", "avanza_fund_ID.csv"),
                index_col=0,
            )
            if self.country != "sweden":
                console.print(
                    "Avanza implementation currently only supports funds from sweden."
                )
                return self.queue
            if self.fund_name == "":
                if self.fund_symbol != "":
                    self.fund_symbol = investpy_model.get_fund_name_from_symbol(
                        self.fund_symbol
                    )
                else:
                    console.print(
                        "No fund loaded. Please use `load` first.\n", style="bold"
                    )
                    return self.queue
            if self.fund_name.upper() not in ava_fund.index.str.upper().to_numpy():
                console.print("No fund data. Please use another fund", style="bold")
                return self.queue
            avanza_view.display_info(self.fund_name)

        return self.queue

    @log_start_end(log=logger)
    def call_forecast(self, _):
        """Process forecast command"""
        # pylint: disable=import-outside-toplevel
        from openbb_terminal.forecast import forecast_controller

        self.queue = self.load_class(
            forecast_controller.ForecastController,
            self.fund_name,
            self.data,
            self.queue,
        )
