"""Maps Controller Module"""
__docformat__ = "numpy"

import argparse
import logging
from typing import List, Tuple
from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import EXPORT_ONLY_RAW_DATA_ALLOWED
from openbb_terminal.maps.maps_view import (
    display_bitcoin_hash,
    display_interest_rates,
    display_map_explorer,
    display_macro,
    display_openbb,
    display_stocks,
)
from openbb_terminal.economy.econdb_model import PARAMETERS
from openbb_terminal.menu import session
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText

logger = logging.getLogger(__name__)
# pylint:disable=import-outside-toplevel


class MapsController(BaseController):
    """Maps Controller class"""

    CHOICES_COMMANDS: List[str] = []
    CHOICES_MENUS = ["bh", "ir", "me", "macro", "openbb", "stocks"]
    PATH = "/maps/"

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        if session and obbff.USE_PROMPT_TOOLKIT:
            self.choices: dict = {c: {} for c in self.controller_choices}

            self.choices["macro"] = {
                "--indicator": {c: {} for c in PARAMETERS},
                "-i": "--indicator",
            }

            self.choices["support"] = self.SUPPORT_CHOICES
            self.choices["about"] = self.ABOUT_CHOICES

            self.completer = NestedCompleter.from_nested_dict(self.choices)

    def print_help(self):
        """Print help"""
        mt = MenuText("maps/")
        mt.add_cmd("bh")
        mt.add_cmd("ir")
        mt.add_cmd("me")
        mt.add_cmd("macro")
        mt.add_cmd("openbb")
        mt.add_cmd("stocks")
        console.print(text=mt.menu_text, menu="Maps")

    @log_start_end(log=logger)
    def call_bh(self, other_args: List[str]):
        """Process bh command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="bh",
            description="Display bitcoin hash rate per country.",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            display_bitcoin_hash(export=ns_parser.export)

    @log_start_end(log=logger)
    def call_ir(self, other_args: List[str]):
        """Process bh command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="ir",
            description="Display interest rates per country.",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            display_interest_rates(export=ns_parser.export)

    @log_start_end(log=logger)
    def call_me(self, other_args: List[str]):
        """Process me command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="me",
            description="Display maps menu",
        )
        parser.add_argument(
            "-c",
            "--coordinates",
            action="store",
            dest="coordinates",
            type=str,
            default=["38.445473,-9.1065868"],
            nargs="+",
            help="List of coordinates to display",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-c")

        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser:

            try:
                coordinates = [
                    tuple(map(float, coord.split(",")))
                    for coord in ns_parser.coordinates
                ]
            except ValueError:
                console.print("[red]Invalid coordinates[/red]")
                return

            display_map_explorer(coordinates)

    @log_start_end(log=logger)
    def call_macro(self, other_args: List[str]):
        """Process macro command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="macro",
            description="Display macro indicator per country.",
        )
        parser.add_argument(
            "-i",
            "--indicator",
            action="store",
            dest="indicator",
            type=str,
            default="CPI",
            help="Indicator to display",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-i")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            display_macro(ns_parser.indicator, export=ns_parser.export)

    @log_start_end(log=logger)
    def call_openbb(self, other_args: List[str]):
        """Process openbb command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="openbb",
            description="Display openbb maintainers by country.",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            display_openbb(export=ns_parser.export)

    @log_start_end(log=logger)
    def call_stocks(self, other_args: List[str]):
        """Process openbb command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="stocks",
            description="Display openbb maintainers by country.",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            display_stocks(export=ns_parser.export)
