"""Cryptocurrency Discovery Controller"""
__docformat__ = "numpy"

# pylint: disable=R0904, C0302, W0622, C0201
import argparse
import logging
from typing import List

from openbb_terminal.custom_prompt_toolkit import NestedCompleter


from openbb_terminal import feature_flags as obbff
from openbb_terminal.cryptocurrency.discovery import (
    coinmarketcap_model,
    coinmarketcap_view,
    coinpaprika_model,
    coinpaprika_view,
    dappradar_model,
    dappradar_view,
    pycoingecko_model,
    pycoingecko_view,
)
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    EXPORT_ONLY_RAW_DATA_ALLOWED,
    check_positive,
)
from openbb_terminal.menu import session
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText, get_ordered_list_sources

logger = logging.getLogger(__name__)


class DiscoveryController(BaseController):
    """Discovery Controller class"""

    CHOICES_COMMANDS = [
        "search",
        "top",
        "trending",
        "gainers",
        "losers",
        "nft",
        "games",
        "dapps",
        "dex",
    ]

    PATH = "/crypto/disc/"

    ORDERED_LIST_SOURCES_TOP = get_ordered_list_sources(f"{PATH}top")

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        if session and obbff.USE_PROMPT_TOOLKIT:
            choices: dict = {c: {} for c in self.controller_choices}
            choices["gainers"] = {
                "--interval": {c: {} for c in pycoingecko_model.API_PERIODS},
                "-i": "--interval",
                "--sort": {c: {} for c in pycoingecko_model.GAINERS_LOSERS_COLUMNS},
                "-s": "--sort",
                "--limit": None,
                "-l": "--limit",
            }
            choices["losers"] = {
                "--interval": {c: {} for c in pycoingecko_model.API_PERIODS},
                "-i": "--interval",
                "--sort": {c: {} for c in pycoingecko_model.GAINERS_LOSERS_COLUMNS},
                "-s": "--sort",
                "--limit": None,
                "-l": "--limit",
            }
            choices["top"] = {
                "--sort": {c: {} for c in pycoingecko_view.COINS_COLUMNS}
                if self.ORDERED_LIST_SOURCES_TOP
                and self.ORDERED_LIST_SOURCES_TOP[0] == "CoinGecko"
                else {c: {} for c in coinmarketcap_model.FILTERS},
                "-s": "--sort",
                "--category": {c: {} for c in pycoingecko_model.get_categories_keys()},
                "-c": "--category",
                "--limit": None,
                "-l": "--limit",
                "--reverse": {},
                "-r": "--reverse",
                "--source": {c: {} for c in self.ORDERED_LIST_SOURCES_TOP},
            }
            choices["search"] = {
                "--query": None,
                "-q": "--query",
                "--sort": {c: {} for c in coinpaprika_model.FILTERS},
                "-s": "--sort",
                "--cat": {c: {} for c in coinpaprika_model.CATEGORIES},
                "-c": "--cat",
                "--limit": None,
                "-l": "--limit",
                "--reverse": {},
                "-r": "--reverse",
            }
            choices["nft"] = {
                "--sort": {c: {} for c in dappradar_model.NFT_COLUMNS},
                "-s": "--sort",
                "--limit": None,
                "-l": "--limit",
            }
            choices["games"] = {
                "--sort": {c: {} for c in dappradar_model.DEX_COLUMNS},
                "-s": "--sort",
                "--limit": None,
                "-l": "--limit",
            }
            choices["dex"] = {
                "--sort": {c: {} for c in dappradar_model.DEX_COLUMNS},
                "-s": "--sort",
                "--limit": None,
                "-l": "--limit",
            }
            choices["dapps"] = {
                "--sort": {c: {} for c in dappradar_model.DAPPS_COLUMNS},
                "-s": "--sort",
                "--limit": None,
                "-l": "--limit",
            }

            choices["support"] = self.SUPPORT_CHOICES
            choices["about"] = self.ABOUT_CHOICES

            self.completer = NestedCompleter.from_nested_dict(choices)

    def print_help(self):
        """Print help"""
        mt = MenuText("crypto/disc/")
        mt.add_cmd("top")
        mt.add_cmd("trending")
        mt.add_cmd("gainers")
        mt.add_cmd("losers")
        mt.add_cmd("search")
        mt.add_cmd("nft")
        mt.add_cmd("games")
        mt.add_cmd("dapps")
        mt.add_cmd("dex")
        console.print(text=mt.menu_text, menu="Cryptocurrency - Discovery")

    @log_start_end(log=logger)
    def call_top(self, other_args):
        """Process top command"""
        parser = argparse.ArgumentParser(
            prog="top",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""Display N coins from the data source, if the data source is CoinGecko it
            can receive a category as argument (-c decentralized-finance-defi or -c stablecoins)
            and will show only the top coins in that category.
            can also receive sort arguments (these depend on the source), e.g., --sort Volume [$]
            You can sort by {Symbol,Name,Price [$],Market Cap,Market Cap Rank,Volume [$]} with CoinGecko
            Number of coins to show: -l 10
            """,
        )

        parser.add_argument(
            "-c",
            "--category",
            default="",
            dest="category",
            help="Category (e.g., stablecoins). Empty for no category. Only works for 'CoinGecko' source.",
        )

        parser.add_argument(
            "-l",
            "--limit",
            default=10,
            dest="limit",
            help="Limit of records",
            type=check_positive,
        )
        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            nargs="+",
            help="Sort by given column. Default: Market Cap Rank",
            default="Market Cap Rank"
            if self.ORDERED_LIST_SOURCES_TOP
            and self.ORDERED_LIST_SOURCES_TOP[0] == "CoinGecko"
            else "CMC_Rank",
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
        if other_args and not other_args[0][0] == "-":
            other_args.insert(0, "-c")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if ns_parser.source == "CoinGecko":
                pycoingecko_view.display_coins(
                    sortby=" ".join(ns_parser.sortby),
                    category=ns_parser.category,
                    limit=ns_parser.limit,
                    export=ns_parser.export,
                    ascend=ns_parser.reverse,
                )
            elif ns_parser.source == "CoinMarketCap":
                coinmarketcap_view.display_cmc_top_coins(
                    limit=ns_parser.limit,
                    sortby=ns_parser.sortby,
                    ascend=ns_parser.reverse,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_dapps(self, other_args):
        """Process dapps command"""
        parser = argparse.ArgumentParser(
            prog="dapps",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""
            Shows top decentralized applications [Source: https://dappradar.com/]
            Accepts --sort {Name,Category,Protocols,Daily Users,Daily Volume [$]}
            to sort by column
            """,
        )

        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=check_positive,
            help="Number of records to display",
            default=15,
        )
        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            nargs="+",
            help="Sort by given column. Default: Daily Volume [$]",
            default="Daily Volume [$]",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            dappradar_view.display_top_dapps(
                sortby=" ".join(ns_parser.sortby),
                limit=ns_parser.limit,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_games(self, other_args):
        """Process games command"""
        parser = argparse.ArgumentParser(
            prog="games",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""
            Shows top blockchain games [Source: https://dappradar.com/]
            Accepts --sort {Name,Daily Users,Daily Volume [$]}
            to sort by column
            """,
        )

        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=check_positive,
            help="Number of records to display",
            default=15,
        )
        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            nargs="+",
            help="Sort by given column. Default: Daily Volume [$]",
            default="Daily Volume [$]",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            dappradar_view.display_top_games(
                sortby=" ".join(ns_parser.sortby),
                limit=ns_parser.limit,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_dex(self, other_args):
        """Process dex command"""
        parser = argparse.ArgumentParser(
            prog="dex",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""
            Shows top decentralized exchanges [Source: https://dappradar.com/]
            Accepts --sort {Name,Daily Users,Daily Volume [$]}
            to sort by column
            """,
        )

        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=check_positive,
            help="Number of records to display",
            default=15,
        )
        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            nargs="+",
            help="Sort by given column. Default: Daily Volume [$]",
            default="Daily Volume [$]",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            dappradar_view.display_top_dexes(
                sortby=" ".join(ns_parser.sortby),
                limit=ns_parser.limit,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_nft(self, other_args):
        """Process nft command"""
        parser = argparse.ArgumentParser(
            prog="nft",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""
            Shows top NFT collections [Source: https://dappradar.com/]
            Accepts --sort {Name,Protocols,Floor Price [$],Avg Price [$],Market Cap,Volume [$]}
            to sort by column
            """,
        )

        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=check_positive,
            help="Number of records to display",
            default=15,
        )
        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            nargs="+",
            help="Sort by given column. Default: Market Cap",
            default="Market Cap",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            dappradar_view.display_top_nfts(
                sortby=" ".join(ns_parser.sortby),
                limit=ns_parser.limit,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_gainers(self, other_args):
        """Process gainers command"""
        parser = argparse.ArgumentParser(
            prog="gainers",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""
            Shows Largest Gainers - coins which gain the most in given period.
            You can use parameter --interval to set which timeframe are you interested in: {14d,1h,1y,200d,24h,30d,7d}
            You can look on only N number of records with --limit,
            You can sort by {Symbol,Name,Price [$],Market Cap,Market Cap Rank,Volume [$]} with --sort.
            """,
        )

        parser.add_argument(
            "-i",
            "--interval",
            dest="interval",
            type=str,
            help="time period, one from {14d,1h,1y,200d,24h,30d,7d}",
            default="1h",
            choices=pycoingecko_model.API_PERIODS,
        )

        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=check_positive,
            help="Number of records to display",
            default=15,
        )

        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            nargs="+",
            help="Sort by given column. Default: Market Cap Rank",
            default=["market_cap"],
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            pycoingecko_view.display_gainers(
                interval=ns_parser.interval,
                limit=ns_parser.limit,
                export=ns_parser.export,
                sortby=" ".join(ns_parser.sortby),
            )

    @log_start_end(log=logger)
    def call_losers(self, other_args):
        """Process losers command"""
        parser = argparse.ArgumentParser(
            prog="losers",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""
           Shows Largest Losers - coins which price dropped the most in given period
           You can use parameter --interval to set which timeframe are you interested in: {14d,1h,1y,200d,24h,30d,7d}
           You can look on only N number of records with --limit,
           You can sort by {Symbol,Name,Price [$],Market Cap,Market Cap Rank,Volume [$]} with --sort.
            """,
        )

        parser.add_argument(
            "-i",
            "--interval",
            dest="interval",
            type=str,
            help="time period, one from {14d,1h,1y,200d,24h,30d,7d}",
            default="1h",
            choices=pycoingecko_model.API_PERIODS,
        )

        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=check_positive,
            help="Number of records to display",
            default=15,
        )

        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            nargs="+",
            help="Sort by given column. Default: Market Cap Rank",
            default=["Market Cap"],
        )

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            pycoingecko_view.display_losers(
                interval=ns_parser.interval,
                limit=ns_parser.limit,
                export=ns_parser.export,
                sortby=" ".join(ns_parser.sortby),
            )

    @log_start_end(log=logger)
    def call_trending(self, other_args):
        """Process trending command"""
        parser = argparse.ArgumentParser(
            prog="trending",
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="""Discover trending coins (Top-7) on CoinGecko in the last 24 hours
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            EXPORT_ONLY_RAW_DATA_ALLOWED,
        )
        if ns_parser:
            pycoingecko_view.display_trending(
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_search(self, other_args):
        """Process search command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="search",
            description="""Search over CoinPaprika API
            You can display only N number of results with --limit parameter.
            You can sort data by id, name , category --sort parameter and also with --reverse flag to sort descending.
            To choose category in which you are searching for use --cat/-c parameter. Available categories:
            currencies|exchanges|icos|people|tags|all
            Displays:
                id, name, category""",
        )
        parser.add_argument(
            "-q",
            "--query",
            help="phrase for search",
            dest="query",
            nargs="+",
            type=str,
            required="-h" not in other_args,
        )
        parser.add_argument(
            "-c",
            "--cat",
            help="Categories to search: currencies|exchanges|icos|people|tags|all. Default: all",
            dest="category",
            default="all",
            type=str,
            choices=coinpaprika_model.CATEGORIES,
        )
        parser.add_argument(
            "-l",
            "--limit",
            default=10,
            dest="limit",
            help="Limit of records",
            type=check_positive,
        )
        parser.add_argument(
            "-s",
            "--sort",
            dest="sortby",
            type=str,
            help="Sort by given column. Default: id",
            default="id",
            choices=coinpaprika_model.FILTERS,
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
        if other_args:
            if not other_args[0][0] == "-":
                other_args.insert(0, "-q")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            coinpaprika_view.display_search_results(
                limit=ns_parser.limit,
                sortby=ns_parser.sortby,
                ascend=ns_parser.reverse,
                export=ns_parser.export,
                query=" ".join(ns_parser.query),
                category=ns_parser.category,
            )
