"""Maps Controller Module"""
__docformat__ = "numpy"

import argparse
import logging
from typing import List
from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import EXPORT_ONLY_RAW_DATA_ALLOWED
from openbb_terminal.maps.maps_view import (
    display_bitcoin_hash,
    display_interest_rates,
)
from openbb_terminal.menu import session
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText

logger = logging.getLogger(__name__)
# pylint:disable=import-outside-toplevel


class MapsController(BaseController):
    """Maps Controller class"""

    CHOICES_COMMANDS: List[str] = []
    CHOICES_MENUS = ["bh", "ir"]
    PATH = "/maps/"

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        if session and obbff.USE_PROMPT_TOOLKIT:
            choices: dict = {c: {} for c in self.controller_choices}
            choices["support"] = self.SUPPORT_CHOICES
            choices["about"] = self.ABOUT_CHOICES

            self.completer = NestedCompleter.from_nested_dict(choices)

    def print_help(self):
        """Print help"""
        mt = MenuText("maps/")
        mt.add_cmd("bh")
        mt.add_cmd("ir")
        console.print(text=mt.menu_text, menu="Maps")

    @log_start_end(log=logger)
    def call_bh(self, other_args: List[str]):
        """Process bh command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="bh",
            description="Display a repo summary [Source: https://api.github.com]",
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
            description="Display a repo summary [Source: https://api.github.com]",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            display_interest_rates(export=ns_parser.export)
