""" Screener Controller Module """
__docformat__ = "numpy"

import argparse
import datetime
import logging
from pathlib import Path
from typing import List

from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal.core.config.paths import USER_PRESETS_DIRECTORY
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_classes import AllowArgsWithWhiteSpace
from openbb_terminal.helper_funcs import (
    EXPORT_BOTH_RAW_DATA_AND_FIGURES,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
    check_positive,
    valid_date,
    parse_and_split_input,
)
from openbb_terminal.menu import session
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText
from openbb_terminal.stocks.comparison_analysis import ca_controller
from openbb_terminal.stocks.screener import (
    finviz_model,
    finviz_view,
    yahoofinance_view,
    screener_view,
)

logger = logging.getLogger(__name__)

# pylint: disable=E1121

# TODO: HELP WANTED! This menu required some refactoring. Things that can be addressed:
#       - better preset management (MVC style).
PRESETS_PATH = USER_PRESETS_DIRECTORY / "stocks" / "screener"


class ScreenerController(BaseController):
    """Screener Controller class"""

    CHOICES_COMMANDS = [
        "view",
        "set",
        "historical",
        "overview",
        "valuation",
        "financial",
        "ownership",
        "performance",
        "technical",
        "ca",
    ]

    PRESETS_PATH_DEFAULT = Path(__file__).parent / "presets"
    preset_choices = {
        filepath.name.replace(".ini", ""): filepath
        for filepath in PRESETS_PATH.iterdir()
        if filepath.suffix == ".ini"
    }
    preset_choices.update(
        {
            filepath.name.replace(".ini", ""): filepath
            for filepath in PRESETS_PATH_DEFAULT.iterdir()
            if filepath.suffix == ".ini"
        }
    )
    preset_choices.update(finviz_model.d_signals)

    historical_candle_choices = ["o", "h", "l", "c", "a"]
    PATH = "/stocks/scr/"

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        self.preset = "top_gainers"
        self.screen_tickers: List = list()

        if session and obbff.USE_PROMPT_TOOLKIT:
            choices: dict = {c: {} for c in self.controller_choices}

            choices["view"] = {c: {} for c in self.preset_choices}
            choices["set"] = {c: {} for c in self.preset_choices}
            choices["historical"] = {
                "--start": None,
                "-s": "--start",
                "--type": {c: {} for c in self.historical_candle_choices},
                "--no-scale": {},
                "-n": "--no-scale",
                "--limit": None,
                "-l": "--limit",
            }
            screener_standard = {
                "--preset": {c: {} for c in self.preset_choices},
                "-p": "--preset",
                "--sort": {c: {} for c in finviz_view.d_cols_to_sort["overview"]},
                "-s": "--sort",
                "--limit": None,
                "-l": "--limit",
                "--reverse": {},
                "-r": "--reverse",
            }
            choices["overview"] = screener_standard
            choices["valuation"] = screener_standard
            choices["financial"] = screener_standard
            choices["ownership"] = screener_standard
            choices["performance"] = screener_standard
            choices["technical"] = screener_standard

            self.completer = NestedCompleter.from_nested_dict(choices)

    def parse_input(self, an_input: str) -> List:
        """Parse controller input

        Overrides the parent class function to handle github org/repo path convention.
        See `BaseController.parse_input()` for details.
        """
        # Filtering out sorting parameters with forward slashes like P/E
        sort_filter = r"((\ -s |\ --sort ).*?(P\/E|Fwd P\/E|P\/S|P\/B|P\/C|P\/FCF)*)"

        custom_filters = [sort_filter]

        commands = parse_and_split_input(
            an_input=an_input, custom_filters=custom_filters
        )
        return commands

    def print_help(self):
        """Print help"""
        mt = MenuText("stocks/scr/")
        mt.add_cmd("view")
        mt.add_cmd("set")
        mt.add_raw("\n")
        mt.add_param("_preset", self.preset)
        mt.add_raw("\n")
        mt.add_cmd("historical")
        mt.add_cmd("overview")
        mt.add_cmd("valuation")
        mt.add_cmd("financial")
        mt.add_cmd("ownership")
        mt.add_cmd("performance")
        mt.add_cmd("technical")
        mt.add_raw("\n")
        mt.add_param("_screened_tickers", ", ".join(self.screen_tickers))
        mt.add_raw("\n")
        mt.add_menu("ca", self.screen_tickers)
        console.print(text=mt.menu_text, menu="Stocks - Screener")

    @log_start_end(log=logger)
    def call_view(self, other_args: List[str]):
        """Process view command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="view",
            description="""View available presets under presets folder.""",
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            help="View specific custom preset",
            default="",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if ns_parser.preset:
                if ns_parser.preset in finviz_model.d_signals:
                    console.print("This is a Finviz preset.\n")
                    return
                ns_parser.preset += ".ini"
            screener_view.display_presets(ns_parser.preset)

    @log_start_end(log=logger)
    def call_set(self, other_args: List[str]):
        """Process set command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="set",
            description="""Set preset from custom and default ones.""",
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            default="template",
            help="Filter presets",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            self.preset = ns_parser.preset + ".ini"

    @log_start_end(log=logger)
    def call_historical(self, other_args: List[str]):
        """Process historical command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="historical",
            description="""Historical price comparison between similar companies [Source: Yahoo Finance]
            """,
        )
        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            type=check_positive,
            default=10,
            help="Limit of the most shorted stocks to retrieve.",
        )
        parser.add_argument(
            "-n",
            "--no-scale",
            action="store_false",
            dest="no_scale",
            default=False,
            help="Flag to not put all prices on same 0-1 scale",
        )
        parser.add_argument(
            "-s",
            "--start",
            type=valid_date,
            default=(
                datetime.datetime.now() - datetime.timedelta(days=6 * 30)
            ).strftime("%Y-%m-%d"),
            dest="start",
            help="The starting date (format YYYY-MM-DD) of the historical price to plot",
        )
        parser.add_argument(
            "-t",
            "--type",
            action="store",
            dest="type_candle",
            choices=self.historical_candle_choices,
            default="a",  # in case it's adjusted close
            help="type of candles: o-open, h-high, l-low, c-close, a-adjusted close.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-l")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )
        if ns_parser:
            self.screen_tickers = yahoofinance_view.historical(
                self.preset,
                ns_parser.limit,
                ns_parser.start,
                ns_parser.type_candle,
                not ns_parser.no_scale,
                ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_overview(self, other_args: List[str]):
        """Process overview command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="overview",
            description="""
                Prints overview data of the companies that meet the pre-set filtering.
            """,
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            default=self.preset,
            help="Filter presets",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            type=check_positive,
            default=10,
            help="Limit of stocks to print",
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
        parser.add_argument(
            "-s",
            "--sort",
            action=AllowArgsWithWhiteSpace,
            dest="sort",
            default="",
            nargs="+",
            help="Sort elements of the table.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-l")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            if self.preset.strip(".ini") in finviz_model.d_signals:
                preset = self.preset.strip(".ini")
            else:
                preset = self.preset

            if ns_parser.sort:
                if ns_parser.sort not in finviz_view.d_cols_to_sort["overview"]:
                    console.print(f"{ns_parser.sort} not a valid sort choice.\n")
                else:
                    self.screen_tickers = finviz_view.screener(
                        loaded_preset=preset,
                        data_type="overview",
                        limit=ns_parser.limit,
                        ascend=ns_parser.reverse,
                        sortby=ns_parser.sort,
                        export=ns_parser.export,
                    )

            else:

                self.screen_tickers = finviz_view.screener(
                    loaded_preset=preset,
                    data_type="overview",
                    limit=ns_parser.limit,
                    ascend=ns_parser.ascend,
                    sortby=ns_parser.sort,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_valuation(self, other_args: List[str]):
        """Process valuation command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="valuation",
            description="""
                Prints valuation data of the companies that meet the pre-set filtering.
            """,
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            default=self.preset,
            help="Filter presets",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            type=check_positive,
            default=10,
            help="Limit of stocks to print",
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
        parser.add_argument(
            "-s",
            "--sort",
            dest="sort",
            default="",
            nargs="+",
            action=AllowArgsWithWhiteSpace,
            help="Sort elements of the table.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-l")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            if ns_parser.sort:
                if ns_parser.sort not in finviz_view.d_cols_to_sort["valuation"]:
                    console.print(f"{ns_parser.sort} not a valid sort choice.\n")
                else:
                    self.screen_tickers = finviz_view.screener(
                        loaded_preset=self.preset,
                        data_type="valuation",
                        limit=ns_parser.limit,
                        ascend=ns_parser.reverse,
                        sortby=ns_parser.sort,
                        export=ns_parser.export,
                    )

            else:

                self.screen_tickers = finviz_view.screener(
                    loaded_preset=self.preset,
                    data_type="valuation",
                    limit=ns_parser.limit,
                    ascend=ns_parser.reverse,
                    sortby=ns_parser.sort,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_financial(self, other_args: List[str]):
        """Process financial command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="financial",
            description="""
                Prints financial data of the companies that meet the pre-set filtering.
            """,
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            default=self.preset,
            help="Filter presets",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            type=check_positive,
            default=10,
            help="Limit of stocks to print",
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
        parser.add_argument(
            "-s",
            "--sort",
            action=AllowArgsWithWhiteSpace,
            dest="sort",
            default="",
            nargs="+",
            help="Sort elements of the table.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-l")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            if ns_parser.sort:
                if ns_parser.sort not in finviz_view.d_cols_to_sort["financial"]:
                    console.print(f"{ns_parser.sort} not a valid sort choice.\n")
                else:
                    self.screen_tickers = finviz_view.screener(
                        loaded_preset=self.preset,
                        data_type="financial",
                        limit=ns_parser.limit,
                        ascend=ns_parser.reverse,
                        sortby=ns_parser.sort,
                        export=ns_parser.export,
                    )

            else:

                self.screen_tickers = finviz_view.screener(
                    loaded_preset=self.preset,
                    data_type="financial",
                    limit=ns_parser.limit,
                    ascend=ns_parser.reverse,
                    sortby=ns_parser.sort,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_ownership(self, other_args: List[str]):
        """Process ownership command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="ownership",
            description="""
                Prints ownership data of the companies that meet the pre-set filtering.
            """,
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            default=self.preset,
            help="Filter presets",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            type=check_positive,
            default=10,
            help="Limit of stocks to print",
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
        parser.add_argument(
            "-s",
            "--sort",
            dest="sort",
            default="",
            nargs="+",
            action=AllowArgsWithWhiteSpace,
            help="Sort elements of the table.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-l")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:

            if ns_parser.sort:
                if ns_parser.sort not in finviz_view.d_cols_to_sort["ownership"]:
                    console.print(f"{ns_parser.sort} not a valid sort choice.\n")
                else:
                    self.screen_tickers = finviz_view.screener(
                        loaded_preset=self.preset,
                        data_type="ownership",
                        limit=ns_parser.limit,
                        ascend=ns_parser.reverse,
                        sortby=ns_parser.sort,
                        export=ns_parser.export,
                    )

            else:

                self.screen_tickers = finviz_view.screener(
                    loaded_preset=self.preset,
                    data_type="ownership",
                    limit=ns_parser.limit,
                    ascend=ns_parser.reverse,
                    sortby=ns_parser.sort,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_performance(self, other_args: List[str]):
        """Process performance command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="performance",
            description="""
                Prints performance data of the companies that meet the pre-set filtering.
            """,
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            default=self.preset,
            help="Filter presets",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            type=check_positive,
            default=10,
            help="Limit of stocks to print",
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
        parser.add_argument(
            "-s",
            "--sort",
            action=AllowArgsWithWhiteSpace,
            dest="sort",
            default="",
            nargs="+",
            help="Sort elements of the table.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-l")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:

            if ns_parser.sort:
                if ns_parser.sort not in finviz_view.d_cols_to_sort["performance"]:
                    console.print(f"{ns_parser.sort} not a valid sort choice.\n")
                else:
                    self.screen_tickers = finviz_view.screener(
                        loaded_preset=self.preset,
                        data_type="performance",
                        limit=ns_parser.limit,
                        ascend=ns_parser.reverse,
                        sortby=ns_parser.sort,
                        export=ns_parser.export,
                    )

            else:

                self.screen_tickers = finviz_view.screener(
                    loaded_preset=self.preset,
                    data_type="performance",
                    limit=ns_parser.limit,
                    ascend=ns_parser.store_true,
                    sortby=ns_parser.sort,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_technical(self, other_args: List[str]):
        """Process technical command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="technical",
            description="""
                Prints technical data of the companies that meet the pre-set filtering.
            """,
        )
        parser.add_argument(
            "-p",
            "--preset",
            action="store",
            dest="preset",
            type=str,
            default=self.preset,
            help="Filter presets",
            choices=self.preset_choices,
            metavar="Desired preset.",
        )
        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            type=check_positive,
            default=10,
            help="Limit of stocks to print",
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
        parser.add_argument(
            "-s",
            "--sort",
            action=AllowArgsWithWhiteSpace,
            dest="sort",
            default="",
            nargs="+",
            help="Sort elements of the table.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-l")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:

            if ns_parser.sort:
                if ns_parser.sort not in finviz_view.d_cols_to_sort["technical"]:
                    console.print(f"{ns_parser.sort} not a valid sort choice.\n")
                else:
                    self.screen_tickers = finviz_view.screener(
                        loaded_preset=self.preset,
                        data_type="technical",
                        limit=ns_parser.limit,
                        ascend=ns_parser.reverse,
                        sortby=ns_parser.sort,
                        export=ns_parser.export,
                    )

            else:

                self.screen_tickers = finviz_view.screener(
                    loaded_preset=self.preset,
                    data_type="technical",
                    limit=ns_parser.limit,
                    ascend=ns_parser.reverse,
                    sortby=ns_parser.sort,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_ca(self, _):
        """Call the comparison analysis menu with selected tickers"""
        if self.screen_tickers:
            self.queue = ca_controller.ComparisonAnalysisController(
                self.screen_tickers, self.queue
            ).menu(custom_path_menu_above="/stocks/")
        else:
            console.print(
                "Some tickers must be screened first through one of the presets!\n"
            )
