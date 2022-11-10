""" Futures Controller """
__docformat__ = "numpy"

# pylint:disable=too-many-lines

import argparse
import logging
from datetime import datetime, timedelta
from typing import List

from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal.decorators import log_start_end

from openbb_terminal.helper_funcs import (
    EXPORT_BOTH_RAW_DATA_AND_FIGURES,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
    valid_date,
    parse_and_split_input,
)
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText
from openbb_terminal.menu import session
from openbb_terminal.futures import yfinance_model, yfinance_view

logger = logging.getLogger(__name__)


def valid_expiry_date(s: str) -> str:
    """Argparse type to check date is in valid format"""
    try:
        if not s:
            return s
        return datetime.strptime(s, "%Y-%m").strftime("%Y-%m")
    except ValueError as value_error:
        logging.exception(str(value_error))
        raise argparse.ArgumentTypeError(f"Not a valid date: {s}") from value_error


class FuturesController(BaseController):
    """Futures Controller class"""

    CHOICES_COMMANDS = [
        "search",
        "curve",
        "historical",
    ]

    curve_type = "futures"

    PATH = "/futures/"

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        self.all_tickers = yfinance_model.FUTURES_DATA["Ticker"].unique().tolist()
        self.all_exchanges = yfinance_model.FUTURES_DATA["Exchange"].unique().tolist()
        self.all_categories = yfinance_model.FUTURES_DATA["Category"].unique().tolist()

        if session and obbff.USE_PROMPT_TOOLKIT:
            self.choices: dict = {c: {} for c in self.controller_choices}

            self.choices["search"] = {
                "--category": {c: None for c in self.all_categories},
                "-c": "--category",
                "--exchange": {c: None for c in self.all_exchanges},
                "-e": "--exchange",
                "--description": {},
                "-d": "--description",
            }

            self.choices["support"] = self.SUPPORT_CHOICES
            self.choices["about"] = self.ABOUT_CHOICES

            self.choices["historical"] = {c: None for c in self.all_tickers}
            self.choices["historical"]["--ticker"] = {c: None for c in self.all_tickers}
            self.choices["historical"]["-t"] = "--ticker"
            self.choices["historical"]["--start"] = {}
            self.choices["historical"]["-s"] = "--start"
            self.choices["historical"]["--expiry"] = {}
            self.choices["historical"]["-e"] = "--expiry"
            self.choices["curve"] = {c: None for c in self.all_tickers}
            self.choices["curve"]["--ticker"] = {c: None for c in self.all_tickers}
            self.choices["curve"]["-t"] = "--ticker"

            self.completer = NestedCompleter.from_nested_dict(self.choices)  # type: ignore

    def parse_input(self, an_input: str) -> List:
        """Parse controller input

        Overrides the parent class function to handle github org/repo path convention.
        See `BaseController.parse_input()` for details.
        """
        # Filtering out sorting parameters with forward slashes like P/E
        sort_filter = r"((\ -s |\ --sortby ).*?(P\/E|Fwd P\/E|P\/S|P\/B|P\/C|P\/FCF)*)"

        custom_filters = [sort_filter]

        commands = parse_and_split_input(
            an_input=an_input, custom_filters=custom_filters
        )
        return commands

    def print_help(self):
        """Print help"""
        mt = MenuText("futures/")
        mt.add_cmd("search")
        mt.add_raw("\n")
        mt.add_cmd("historical")
        mt.add_cmd("curve")
        console.print(text=mt.menu_text, menu="Futures")

    @log_start_end(log=logger)
    def call_search(self, other_args: List[str]):
        """Process search command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="search",
            description="""Search futures. [Source: YahooFinance]""",
        )
        parser.add_argument(
            "-e",
            "--exchange",
            dest="exchange",
            type=str,
            choices=self.all_exchanges,
            default="",
            help="Select the exchange where the future exists",
        )
        parser.add_argument(
            "-c",
            "--category",
            dest="category",
            type=str,
            choices=self.all_categories,
            default="",
            help="Select the category where the future exists",
        )
        parser.add_argument(
            "-d",
            "--description",
            dest="description",
            type=str,
            nargs="+",
            default="",
            help="Select the description future you are interested in",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            yfinance_view.display_search(
                category=ns_parser.category,
                exchange=ns_parser.exchange,
                description=" ".join(ns_parser.description),
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_historical(self, other_args: List[str]):
        """Process historical command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="historical",
            description="""Display futures historical. [Source: YahooFinance]""",
        )
        parser.add_argument(
            "-t",
            "--ticker",
            dest="ticker",
            type=str,
            default="",
            help="Future ticker to display timeseries separated by comma when multiple, e.g.: BLK,QI",
            required="-h" not in other_args,
        )
        parser.add_argument(
            "-s",
            "--start",
            dest="start",
            type=valid_date,
            help="Initial date. Default: 3 years ago",
            default=(datetime.now() - timedelta(days=3 * 365)),
        )
        parser.add_argument(
            "-e",
            "--expiry",
            dest="expiry",
            type=valid_expiry_date,
            help="Select future expiry date with format YYYY-MM",
            default="",
        )

        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-t")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
        )
        if ns_parser:
            yfinance_view.display_historical(
                symbols=ns_parser.ticker.upper().split(","),
                expiry=ns_parser.expiry,
                start_date=ns_parser.start.strftime("%Y-%m-%d"),
                raw=ns_parser.raw,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_curve(self, other_args: List[str]):
        """Process curve command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="curve",
            description="""Display futures curve. [Source: YahooFinance]""",
        )
        parser.add_argument(
            "-t",
            "--ticker",
            dest="ticker",
            type=str,
            default="",
            help="Future curve to be selected",
            metavar="Futures symbol",
            required="-h" not in other_args,
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-t")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
            raw=True,
        )

        if ns_parser:
            yfinance_view.display_curve(
                symbol=ns_parser.ticker.upper(),
                raw=ns_parser.raw,
                export=ns_parser.export,
            )
