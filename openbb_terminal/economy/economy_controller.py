""" Econ Controller """
__docformat__ = "numpy"
# pylint:disable=too-many-lines,R1710,R0904,C0415,too-many-branches,unnecessary-dict-index-lookup

import argparse
import logging
import os
import itertools
from datetime import date, datetime as dt
from typing import List, Dict, Any

import pandas as pd

from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal.decorators import check_api_key
from openbb_terminal import feature_flags as obbff
from openbb_terminal.decorators import log_start_end
from openbb_terminal.economy import (
    alphavantage_view,
    economy_helpers,
    finviz_model,
    finviz_view,
    nasdaq_model,
    nasdaq_view,
    wsj_view,
    econdb_view,
    econdb_model,
    fred_view,
    fred_model,
    yfinance_model,
    yfinance_view,
    investingcom_model,
    investingcom_view,
    plot_view,
    commodity_view,
)
from openbb_terminal.helper_funcs import (
    EXPORT_BOTH_RAW_DATA_AND_FIGURES,
    EXPORT_ONLY_FIGURES_ALLOWED,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
    print_rich_table,
    valid_date,
    parse_and_split_input,
    list_from_str,
)
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console, MenuText
from openbb_terminal.menu import session

logger = logging.getLogger(__name__)


class EconomyController(BaseController):
    """Economy Controller class"""

    CHOICES_COMMANDS = [
        "eval",
        "overview",
        "futures",
        "macro",
        "fred",
        "index",
        "treasury",
        "plot",
        "valuation",
        "performance",
        "spectrum",
        "map",
        "rtps",
        "bigmac",
        "ycrv",
        # "spread",
        "events",
        "edebt",
    ]

    CHOICES_MENUS = [
        "qa",
    ]

    wsj_sortby_cols_dict = {c: None for c in ["ticker", "last", "change", "prevClose"]}
    map_period_list = ["1d", "1w", "1m", "3m", "6m", "1y"]
    map_filter_list = ["sp500", "world", "full", "etf"]
    macro_us_interval = [
        "annual",
        "quarter",
        "semiannual",
        "monthly",
        "weekly",
        "daily",
    ]
    macro_us_types = [
        "GDP",
        "GDPC",
        "INF",
        "CPI",
        "TYLD",
        "UNEMP",
        "gdp",
        "gpdc",
        "inf",
        "cpi",
        "tyld",
        "unemp",
    ]
    overview_options = ["indices", "usbonds", "glbonds", "currencies"]
    tyld_maturity = ["3m", "5y", "10y", "30y"]
    valuation_sort_cols = [
        "Name",
        "MarketCap",
        "P/E",
        "FwdP/E",
        "PEG",
        "P/S",
        "P/B",
        "P/C",
        "P/FCF",
        "EPSpast5Y",
        "EPSnext5Y",
        "Salespast5Y",
        "Change",
        "Volume",
    ]
    performance_sort_list = [
        "Name",
        "Week",
        "Month",
        "3Month",
        "6Month",
        "1Year",
        "YTD",
        "Recom",
        "AvgVolume",
        "RelVolume",
        "Change",
        "Volume",
    ]
    index_interval = [
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    ]
    futures_commodities = ["energy", "metals", "meats", "grains", "softs"]
    macro_show = ["parameters", "countries", "transform"]
    d_GROUPS = finviz_model.GROUPS
    PATH = "/economy/"

    stored_datasets = ""

    FILE_PATH = os.path.join(os.path.dirname(__file__), "README.md")

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        self.current_series: Dict = dict()
        self.fred_query: pd.Series = pd.Series(dtype=float)
        self.DATASETS: Dict[Any, pd.DataFrame] = dict()
        self.UNITS: Dict[Any, Dict[Any, Any]] = dict()
        self.FRED_TITLES: Dict = dict()

        self.DATASETS["macro"] = pd.DataFrame()
        self.DATASETS["treasury"] = pd.DataFrame()
        self.DATASETS["fred"] = pd.DataFrame()
        self.DATASETS["index"] = pd.DataFrame()

        if session and obbff.USE_PROMPT_TOOLKIT:
            self.choices: dict = {c: {} for c in self.controller_choices}
            self.choices["overview"] = {
                "--type": {c: None for c in self.overview_options},
                "-t": "--type",
            }
            self.choices["futures"] = {
                "--commodity": {c: {} for c in self.futures_commodities},
                "-c": "--commodity",
                "--sortby": {c: {} for c in self.wsj_sortby_cols_dict.keys()},
                "-s": "--sortby",
                "--reverse": {},
                "-r": "--reverse",
            }
            self.choices["map"] = {
                "--period": {c: {} for c in self.map_period_list},
                "-p": "--period",
                "--type": {c: {} for c in self.map_filter_list},
                "-t": "--type",
            }
            self.choices["bigmac"] = {
                "--countries": {
                    c: {} for c in nasdaq_model.get_country_codes()["Code"].values
                },
                "-c": "--countries",
                "--codes": {},
                "--raw": {},
            }
            self.choices["ycrv"] = {
                "--country": {c: {} for c in investingcom_model.BOND_COUNTRIES},
                "-c": "--country",
                "--date": None,
                "-d": "--date",
                "--raw": {},
                "--source": {
                    "FRED": {},
                },
            }
            # self.choices["spread"] = {
            #     "--group": {c: None for c in investingcom_model.MATRIX_CHOICES},
            #     "-g": "--group",
            #     "--countries": {c: None for c in investingcom_model.BOND_COUNTRIES},
            #     "-c": "--countries",
            #     "--maturity": None,
            #     "-m": "--maturity",
            #     "--change": None,
            #     "--color": {c: None for c in investingcom_view.COLORS},
            # }
            self.choices["events"] = {
                "--country": {
                    c.replace(" ", "_"): {}
                    for c in investingcom_model.CALENDAR_COUNTRIES
                },
                "-c": "--country",
                "--importance": {c: {} for c in investingcom_model.IMPORTANCES},
                "-i": "--importance",
                "--categories": {c: {} for c in investingcom_model.CATEGORIES},
                "--start": None,
                "-s": "--start",
                "--end": None,
                "-e": "--end",
                "--limit": None,
                "-l": "--limit",
                "--raw": {},
            }
            self.choices["edebt"] = {
                "--limit": None,
                "-l": "--limit",
            }
            self.choices["rtps"] = {
                "--raw": {},
            }
            self.choices["valuation"] = {
                "--group": {c: {} for c in self.d_GROUPS},
                "-g": "--group",
                "--sortby": {c: {} for c in self.valuation_sort_cols},
                "-s": "--sortby",
                "--reverse": {},
                "-r": "--reverse",
            }
            self.choices["performance"] = {
                "--group": {c: {} for c in self.d_GROUPS},
                "-g": "--group",
                "--sortby": {c: {} for c in self.performance_sort_list},
                "-s": "--sortby",
                "--reverse": {},
                "-r": "--reverse",
            }
            self.choices["spectrum"] = {
                "--group": {c: {} for c in self.d_GROUPS},
                "-g": "--group",
            }
            self.choices["macro"] = {
                "--parameters": {c: {} for c in econdb_model.PARAMETERS},
                "-p": "--parameters",
                "--countries": {c: {} for c in econdb_model.COUNTRY_CODES},
                "-c": "--countries",
                "--transform": {c: {} for c in econdb_model.TRANSFORM},
                "-t": "--transform",
                "--convert": {c: {} for c in econdb_model.COUNTRY_CURRENCIES},
                "--show": {c: {} for c in self.macro_show},
                "--start": None,
                "-s": "--start",
                "--end": None,
                "-e": "--end",
                "--raw": {},
            }
            self.choices["treasury"] = {
                "--maturity": None,
                "-m": "--maturity",
                "--freq": {c: {} for c in econdb_model.TREASURIES["frequencies"]},
                "--type": {c: {} for c in econdb_model.TREASURIES["instruments"]},
                "-t": "--type",
                "--show": {},
                "--start": None,
                "-s": "--start",
                "--end": None,
                "-e": "--end",
                "--limit": None,
                "-l": "--limit",
                "--raw": {},
            }
            self.choices["fred"] = {
                "--parameter": {c: {} for c in self.fred_query},
                "-p": "--parameter",
                "--start": None,
                "-s": "--start",
                "--end": None,
                "-e": "--end",
                "--query": None,
                "-q": "--query",
                "--raw": {},
            }
            self.choices["index"] = {
                "--indices": {c: {} for c in yfinance_model.INDICES},
                "-i": "--indices",
                "--interval": {c: {} for c in self.index_interval},
                "--show": {},
                "--start": None,
                "-s": "--start",
                "--end": None,
                "-e": "--end",
                "--query": None,
                "-q": "--query",
                "--limit": None,
                "-l": "--limit",
                "--returns": {},
                "-r": "--returns",
                "--raw": {},
            }
            self.choices["plot"] = {
                "--y1": None,
                "--y2": None,
                "--raw": {},
                "--limit": None,
                "-l": "--limit",
            }

            self.choices["support"] = self.SUPPORT_CHOICES
            self.choices["about"] = self.ABOUT_CHOICES

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

    def update_runtime_choices(self):
        if session and obbff.USE_PROMPT_TOOLKIT:
            if not self.fred_query.empty:
                self.choices["fred"]["--parameter"] = {c: None for c in self.fred_query}

            if self.DATASETS:
                options = [
                    option
                    for _, values in self.DATASETS.items()
                    for option in values.keys()
                ]

                # help users to select multiple timeseries for one axis
                economicdata = list()
                for L in [1, 2]:
                    for subset in itertools.combinations(options, L):
                        economicdata.append(",".join(subset))
                        if len(subset) > 1:
                            economicdata.append(",".join(subset[::-1]))

                for argument in [
                    "--y1",
                    "--y2",
                ]:
                    self.choices["plot"][argument] = {
                        option: None for option in economicdata
                    }
        self.completer = NestedCompleter.from_nested_dict(self.choices)

    def print_help(self):
        """Print help"""
        mt = MenuText("economy/")
        mt.add_cmd("overview")
        mt.add_cmd("futures")
        mt.add_cmd("map")
        mt.add_cmd("bigmac")
        mt.add_cmd("ycrv")
        # Comment out spread while investpy is donw :()
        # mt.add_cmd("spread")
        mt.add_cmd("events")
        mt.add_cmd("edebt")
        mt.add_raw("\n")
        mt.add_cmd("rtps")
        mt.add_cmd("valuation")
        mt.add_cmd("performance")
        mt.add_cmd("spectrum")
        mt.add_raw("\n")
        mt.add_info("_database_")
        mt.add_cmd("macro")
        mt.add_cmd("treasury")
        mt.add_cmd("fred")
        mt.add_cmd("index")
        mt.add_raw("\n")
        mt.add_param("_stored", self.stored_datasets)
        mt.add_raw("\n")
        mt.add_cmd("eval")
        mt.add_cmd("plot")
        mt.add_raw("\n")
        mt.add_menu("qa")
        console.print(text=mt.menu_text, menu="Economy")

    @log_start_end(log=logger)
    def call_overview(self, other_args: List[str]):
        """Process overview command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="overview",
            description="""
            Provide a market overview of a variety of options. This can be a general overview,
            indices, bonds and currencies. [Source: Wall St. Journal]
            """,
        )

        parser.add_argument(
            "-t",
            "--type",
            dest="type",
            help="Obtain either US indices, US Bonds, Global Bonds or Currencies",
            type=str,
            choices=self.overview_options,
            default="",
        )

        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-t")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if not ns_parser.type:
                wsj_view.display_overview(
                    export=ns_parser.export,
                )
            elif ns_parser.type == "indices":
                wsj_view.display_indices(
                    export=ns_parser.export,
                )
            if ns_parser.type == "usbonds":
                wsj_view.display_usbonds(
                    export=ns_parser.export,
                )
            if ns_parser.type == "glbonds":
                wsj_view.display_glbonds(
                    export=ns_parser.export,
                )
            if ns_parser.type == "currencies":
                wsj_view.display_currencies(
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_futures(self, other_args: List[str]):
        """Process futures command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="futures",
            description="Futures/Commodities from Wall St. Journal and FinViz.",
        )

        parser.add_argument(
            "-c",
            "--commodity",
            dest="commodity",
            help="Obtain commodity futures from FinViz",
            type=str,
            choices=self.futures_commodities,
            default="",
        )

        parser.add_argument(
            "-s",
            "--sortby",
            dest="sortby",
            type=str,
            choices=self.wsj_sortby_cols_dict.keys(),
            default="ticker",
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
            other_args.insert(0, "-c")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )

        if ns_parser:
            if ns_parser.source == "Finviz":
                if ns_parser.commodity:
                    finviz_view.display_future(
                        future_type=ns_parser.commodity.capitalize(),
                        sortby=ns_parser.sortby,
                        ascend=ns_parser.reverse,
                        export=ns_parser.export,
                    )
                else:
                    console.print(
                        "[red]Commodity group must be specified on Finviz.[/red]"
                    )
            elif ns_parser.source == "WallStreetJournal":
                if ns_parser.commodity:
                    console.print("[red]Commodity flag valid with Finviz only.[/red]")
                wsj_view.display_futures(
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_map(self, other_args: List[str]):
        """Process map command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="map",
            description="""
                Performance index stocks map categorized by sectors and industries.
                Size represents market cap. Opens web-browser. [Source: Finviz]
            """,
        )
        parser.add_argument(
            "-p",
            "--period",
            action="store",
            dest="s_period",
            type=str,
            default="1d",
            choices=self.map_period_list,
            help="Performance period.",
        )
        parser.add_argument(
            "-t",
            "--type",
            action="store",
            dest="s_type",
            type=str,
            default="sp500",
            choices=self.map_filter_list,
            help="Map filter type.",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            finviz_view.display_performance_map(
                period=ns_parser.s_period,
                map_filter=ns_parser.s_type,
            )

    @log_start_end(log=logger)
    def call_bigmac(self, other_args: List[str]):
        """Process bigmac command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="bigmac",
            description="""
                 Get historical Big Mac Index [Nasdaq Data Link]
             """,
        )
        parser.add_argument(
            "--codes",
            help="Flag to show all country codes",
            dest="codes",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "-c",
            "--countries",
            help="Country codes to get data for.",
            dest="countries",
            default="USA",
            type=nasdaq_model.check_country_code_type,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
        )
        if ns_parser:
            if ns_parser.codes:
                console.print(
                    nasdaq_model.get_country_codes().to_string(index=False), "\n"
                )
            else:
                nasdaq_view.display_big_mac_index(
                    country_codes=ns_parser.countries,
                    raw=ns_parser.raw,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_macro(self, other_args: List[str]):
        """Process macro command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="macro",
            description="Get a broad selection of macro data from one or multiple countries. This includes Gross "
            "Domestic Product (RGDP & GDP) and the underlying components, Treasury Yields (Y10YD & M3YD), "
            "Employment figures (URATE, EMP, AC0I0 and EMRATIO), Government components (e.g. GBAL & GREV), "
            "Consumer and Producer Indices (CPI & PPI) and a variety of other indicators. [Source: EconDB]",
        )
        parser.add_argument(
            "-p",
            "--parameters",
            type=str,
            dest="parameters",
            help="Abbreviation(s) of the Macro Economic data",
            default="CPI",
        )
        parser.add_argument(
            "-c",
            "--countries",
            type=str,
            dest="countries",
            help="The country or countries you wish to show data for",
            default="united_states",
        )
        parser.add_argument(
            "-t",
            "--transform",
            dest="transform",
            help="The transformation to apply to the data",
            default="",
            choices=econdb_model.TRANSFORM,
        )
        parser.add_argument(
            "--show",
            dest="show",
            help="Show parameters and what they represent using 'parameters'"
            " or countries and their currencies using 'countries'",
            choices=self.macro_show,
            default=None,
        )
        parser.add_argument(
            "-s",
            "--start",
            dest="start_date",
            help="The start date of the data (format: YEAR-MONTH-DAY, i.e. 2010-12-31)",
            default=None,
        )
        parser.add_argument(
            "-e",
            "--end",
            dest="end_date",
            help="The end date of the data (format: YEAR-MONTH-DAY, i.e. 2021-06-20)",
            default=None,
        )
        parser.add_argument(
            "--convert",
            dest="currency",
            help="Convert the currency of the chosen country to a specified currency. To find the "
            "currency symbols use '--show countries'",
            default=False,
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            parameters = list_from_str(ns_parser.parameters.upper())
            countries = list_from_str(ns_parser.countries.lower())
            if ns_parser.show:
                if ns_parser.show == "parameters":
                    print_rich_table(
                        pd.DataFrame.from_dict(econdb_model.PARAMETERS, orient="index"),
                        show_index=True,
                        index_name="Parameter",
                        headers=["Name", "Period", "Description"],
                    )
                elif ns_parser.show == "countries":
                    print_rich_table(
                        pd.DataFrame(econdb_model.COUNTRY_CURRENCIES.items()),
                        show_index=False,
                        headers=["Country", "Currency"],
                    )
                elif ns_parser.show == "transform":
                    print_rich_table(
                        pd.DataFrame(econdb_model.TRANSFORM.items()),
                        show_index=False,
                        headers=["Code", "Transform"],
                    )
                return self.queue

            if ns_parser.parameters and ns_parser.countries:

                # Store data
                (df, units, _) = econdb_model.get_aggregated_macro_data(
                    parameters=parameters,
                    countries=countries,
                    transform=ns_parser.transform,
                    start_date=ns_parser.start_date,
                    end_date=ns_parser.end_date,
                    symbol=ns_parser.currency,
                )

                if not df.empty:
                    df.columns = ["_".join(column) for column in df.columns]

                    if ns_parser.transform:
                        df.columns = [df.columns[0] + f"_{ns_parser.transform}"]

                    self.DATASETS["macro"] = pd.concat([self.DATASETS["macro"], df])

                    # update units dict
                    for country, data in units.items():
                        if country not in self.UNITS:
                            self.UNITS[country] = {}

                        for key, value in data.items():
                            self.UNITS[country][key] = value

                    self.stored_datasets = (
                        economy_helpers.update_stored_datasets_string(self.DATASETS)
                    )

                    # Display data just loaded
                    econdb_view.show_macro_data(
                        parameters=parameters,
                        countries=countries,
                        transform=ns_parser.transform,
                        start_date=ns_parser.start_date,
                        end_date=ns_parser.end_date,
                        symbol=ns_parser.currency,
                        raw=ns_parser.raw,
                        export=ns_parser.export,
                    )

                    self.update_runtime_choices()
                    if obbff.ENABLE_EXIT_AUTO_HELP:
                        self.print_help()

    @check_api_key(["API_FRED_KEY"])
    def call_fred(self, other_args: List[str]):
        """Process fred command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="fred",
            description="Query the FRED database and plot data based on the Series ID. [Source: FRED]",
        )
        parser.add_argument(
            "-p",
            "--parameter",
            type=str,
            dest="parameter",
            default="",
            help="Series ID of the Macro Economic data from FRED",
        )
        parser.add_argument(
            "-s",
            "--start",
            dest="start_date",
            type=valid_date,
            help="Starting date (YYYY-MM-DD) of data",
            default=None,
        )
        parser.add_argument(
            "-e",
            "--end",
            dest="end_date",
            type=valid_date,
            help="Ending date (YYYY-MM-DD) of data",
            default=None,
        )
        parser.add_argument(
            "-q",
            "--query",
            type=str,
            action="store",
            dest="query",
            help="Query the FRED database to obtain Series IDs given the query search term.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
            limit=100,
        )
        if ns_parser:
            parameters = list_from_str(ns_parser.parameter.upper())

            if ns_parser.query:
                query = ns_parser.query.replace(",", " ")
                df_search = fred_model.get_series_notes(search_query=query)

                if not df_search.empty:
                    fred_view.notes(search_query=query, limit=ns_parser.limit)

                    self.fred_query = df_search["id"].head(ns_parser.limit)
                    self.update_runtime_choices()

                if parameters:
                    console.print(
                        "\nWarning: -p/--parameter is ignored when using -q/--query."
                    )

                return self.queue

            if parameters:
                series_dict = {}
                for series in parameters:
                    information = fred_model.check_series_id(series)

                    if "seriess" in information:
                        series_dict[series] = {
                            "title": information["seriess"][0]["title"],
                            "units": information["seriess"][0]["units_short"],
                        }

                        self.current_series = {series: series_dict[series]}

                if not series_dict:
                    return self.queue

                df, detail = fred_view.display_fred_series(
                    series_ids=parameters,
                    start_date=ns_parser.start_date,
                    end_date=ns_parser.end_date,
                    limit=ns_parser.limit,
                    raw=ns_parser.raw,
                    export=ns_parser.export,
                    get_data=True,
                )

                if not df.empty:

                    for series_id, data in detail.items():
                        self.FRED_TITLES[
                            series_id
                        ] = f"{data['title']} ({data['units']})"

                        # Making data available at the class level
                        self.DATASETS["fred"][series_id] = df[series_id]

                    self.stored_datasets = (
                        economy_helpers.update_stored_datasets_string(self.DATASETS)
                    )

                    self.update_runtime_choices()
                    if obbff.ENABLE_EXIT_AUTO_HELP:
                        self.print_help()

                else:
                    console.print("[red]No data found for the given Series ID[/red]")

            elif not parameters and ns_parser.raw:
                console.print(
                    "Warning: -r/--raw should be combined with -p/--parameter."
                )

    @log_start_end(log=logger)
    def call_index(self, other_args: List[str]):
        """Process index command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="index",
            description="Obtain any set of indices and plot them together. With the -si argument the major indices are "
            "shown. By using the arguments (for example 'nasdaq' and 'sp500') you can collect data and "
            "plot the graphs together. [Source: Yahoo finance / FinanceDatabase]",
        )
        parser.add_argument(
            "-i",
            "--indices",
            type=str,
            dest="indices",
            help="One or multiple indices",
        )
        parser.add_argument(
            "--show",
            dest="show_indices",
            help="Show the major indices, their arguments and ticker",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--interval",
            type=str,
            dest="interval",
            help="The preferred interval data is shown at. This can be 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, "
            "1d, 5d, 1wk, 1mo or 3mo",
            choices=self.index_interval,
            default="1d",
        )
        parser.add_argument(
            "-s",
            "--start",
            dest="start_date",
            help="The start date of the data (format: YEAR-MONTH-DAY, i.e. 2010-12-31)",
            default="2000-01-01",
        )
        parser.add_argument(
            "-e",
            "--end",
            dest="end_date",
            help="The end date of the data (format: YEAR-MONTH-DAY, i.e. 2021-06-20)",
            default=None,
        )
        parser.add_argument(
            "-c",
            "--column",
            type=str,
            dest="column",
            help="The column you wish to load in, by default this is the Adjusted Close column",
            default="Adj Close",
        )
        parser.add_argument(
            "-q",
            "--query",
            type=str,
            dest="query",
            help="Search for indices with given keyword",
        )
        parser.add_argument(
            "-r",
            "--returns",
            help="Flag to show compounded returns over interval.",
            dest="returns",
            action="store_true",
            default=False,
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-i")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
            raw=True,
            limit=10,
        )
        if ns_parser:
            indices = list_from_str(ns_parser.indices)
            if ns_parser.query and ns_parser.limit:
                yfinance_view.search_indices(ns_parser.query, ns_parser.limit)
                return self.queue

            if ns_parser.show_indices:
                print_rich_table(
                    pd.DataFrame.from_dict(yfinance_model.INDICES, orient="index"),
                    show_index=True,
                    index_name="Argument",
                    headers=["Name", "Ticker"],
                    title="Major Indices",
                )
                return self.queue

            if indices:
                for i, index in enumerate(indices):
                    df = yfinance_model.get_index(
                        index,
                        interval=ns_parser.interval,
                        start_date=ns_parser.start_date,
                        end_date=ns_parser.end_date,
                        column=ns_parser.column,
                    )

                    if not df.empty:
                        self.DATASETS["index"][index] = df

                        self.stored_datasets = (
                            economy_helpers.update_stored_datasets_string(self.DATASETS)
                        )

                        # display only once in the last iteration
                        if i == len(indices) - 1:
                            yfinance_view.show_indices(
                                indices=indices,
                                interval=ns_parser.interval,
                                start_date=ns_parser.start_date,
                                end_date=ns_parser.end_date,
                                column=ns_parser.column,
                                raw=ns_parser.raw,
                                export=ns_parser.export,
                                returns=ns_parser.returns,
                            )

                            self.update_runtime_choices()
                            if obbff.ENABLE_EXIT_AUTO_HELP:
                                self.print_help()

    @log_start_end(log=logger)
    def call_treasury(self, other_args: List[str]):
        """Process treasury command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="treasury",
            description="Obtain any set of U.S. treasuries and plot them together. These can be a range of maturities "
            "for nominal, inflation-adjusted (on long term average of inflation adjusted) and secondary "
            "markets over a lengthy period. Note: 3-month and 10-year treasury yields for other countries "
            "are available via the command 'macro' and parameter 'M3YD' and 'Y10YD'. [Source: EconDB / FED]",
        )
        parser.add_argument(
            "-m",
            "--maturity",
            type=str,
            dest="maturity",
            help="The preferred maturity which is dependent on the type of the treasury",
            default="10y",
        )
        parser.add_argument(
            "--show",
            dest="show_maturities",
            help="Show the maturities available for every instrument.",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--freq",
            type=str,
            dest="frequency",
            choices=econdb_model.TREASURIES["frequencies"],
            help="The frequency, this can be annually, monthly, weekly or daily",
            default="monthly",
        )
        parser.add_argument(
            "-t",
            "--type",
            type=str,
            dest="type",
            help="Choose from: nominal, inflation, average, secondary",
            default="nominal",
        )
        parser.add_argument(
            "-s",
            "--start",
            dest="start_date",
            help="The start date of the data (format: YEAR-MONTH-DAY, i.e. 2010-12-31)",
            default="1934-01-31",
        )
        parser.add_argument(
            "-e",
            "--end",
            dest="end_date",
            help="The end date of the data (format: YEAR-DAY-MONTH, i.e. 2021-06-02)",
            default=date.today(),
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-m")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
            raw=True,
            limit=10,
        )
        if ns_parser:
            maturities = list_from_str(ns_parser.maturity)
            types = list_from_str(ns_parser.type)
            for item in types:
                if item not in econdb_model.TREASURIES["instruments"]:
                    print(f"{item} is not a valid instrument type.\n")
                    return self.queue
            if ns_parser.show_maturities:
                econdb_view.show_treasury_maturities()
                return self.queue

            if ns_parser.maturity and ns_parser.type:
                df = econdb_model.get_treasuries(
                    instruments=types,
                    maturities=maturities,
                    frequency=ns_parser.frequency,
                    start_date=ns_parser.start_date,
                    end_date=ns_parser.end_date,
                )

                if not df.empty:
                    self.DATASETS["treasury"] = pd.concat(
                        [
                            self.DATASETS["treasury"],
                            df,
                        ]
                    )

                    cols = []
                    for column in self.DATASETS["treasury"].columns:
                        if isinstance(column, tuple):
                            cols.append("_".join(column))
                        else:
                            cols.append(column)
                    self.DATASETS["treasury"].columns = cols

                    self.stored_datasets = (
                        economy_helpers.update_stored_datasets_string(self.DATASETS)
                    )

                    econdb_view.show_treasuries(
                        instruments=types,
                        maturities=maturities,
                        frequency=ns_parser.frequency,
                        start_date=ns_parser.start_date,
                        end_date=ns_parser.end_date,
                        raw=ns_parser.raw,
                        export=ns_parser.export,
                    )

                    self.update_runtime_choices()
                    if obbff.ENABLE_EXIT_AUTO_HELP:
                        self.print_help()

    @log_start_end(log=logger)
    def call_ycrv(self, other_args: List[str]):
        """Process ycrv command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="ycrv",
            description="Generate country yield curve. The yield curve shows the bond rates"
            " at different maturities.",
        )
        parser.add_argument(
            "-c",
            "--country",
            action="store",
            dest="country",
            default="united_states",
            help="Yield curve for a country. Ex: united_states",
        )

        parser.add_argument(
            "-d",
            "--date",
            type=valid_date,
            help="Date to get data from FRED. If not supplied, the most recent entry will be used.",
            dest="date",
            default=None,
        )
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
            raw=True,
        )
        if ns_parser:
            country = ns_parser.country.lower().replace("_", " ")

            if country == "united states":
                fred_view.display_yield_curve(
                    ns_parser.date,
                    raw=ns_parser.raw,
                    export=ns_parser.export,
                )
            else:
                console.print("Source FRED is only available for united states.\n")

            # TODO: Add `Investing` to sources again when `investpy` is fixed

    @log_start_end(log=logger)
    def call_spread(self, other_args: List[str]):
        """Process spread command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="spread",
            description="Generate bond spread matrix.",
        )
        parser.add_argument(
            "-g",
            "--group",
            action="store",
            dest="group",
            choices=investingcom_model.MATRIX_CHOICES,
            default="G7",
            help="Show bond spread matrix for group of countries.",
        )
        parser.add_argument(
            "-c",
            "--countries",
            action="store",
            dest="countries",
            type=str,
            help="Show bond spread matrix for explicit list of countries.",
        )
        parser.add_argument(
            "-m",
            "--maturity",
            action="store",
            dest="maturity",
            type=str,
            default="10Y",
            help="Specify maturity to compare rates.",
        )
        parser.add_argument(
            "--change",
            action="store",
            dest="change",
            type=bool,
            default=False,
            help="Get matrix of 1 day change in rates or spreads.",
        )
        parser.add_argument(
            "--color",
            action="store",
            dest="color",
            type=str,
            choices=investingcom_view.COLORS,
            default="openbb",
            help="Set color palette on heatmap.",
        )

        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
            raw=True,
        )
        if ns_parser:
            if ns_parser.countries:
                countries_string = ns_parser.countries.replace("_", " ")
                countries_list = investingcom_model.countries_string_to_list(
                    countries_string
                )

                investingcom_view.display_spread_matrix(
                    countries=countries_list,
                    maturity=ns_parser.maturity.upper(),
                    change=ns_parser.change,
                    color=ns_parser.color,
                    raw=ns_parser.raw,
                    export=ns_parser.export,
                )
            elif ns_parser.group:
                investingcom_view.display_spread_matrix(
                    countries=ns_parser.group,
                    maturity=ns_parser.maturity.upper(),
                    change=ns_parser.change,
                    color=ns_parser.color,
                    raw=ns_parser.raw,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_events(self, other_args: List[str]):
        """Process events command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="events",
            description="Economic calendar. If no start or end dates, default is the current day high importance events.",
        )
        parser.add_argument(
            "-c",
            "--country",
            action="store",
            dest="country",
            type=str,
            default="",
            help="Display calendar for specific country.",
        )
        parser.add_argument(
            "-s",
            "--start",
            dest="start_date",
            type=valid_date,
            help="The start date of the data (format: YEAR-MONTH-DAY, i.e. 2010-12-31)",
            default=dt.now().strftime("%Y-%m-%d"),
        )
        parser.add_argument(
            "-e",
            "--end",
            dest="end_date",
            type=valid_date,
            help="The start date of the data (format: YEAR-MONTH-DAY, i.e. 2010-12-31)",
            default=dt.now().strftime("%Y-%m-%d"),
        )
        parser.add_argument(
            "-d",
            "--date",
            dest="spec_date",
            type=valid_date,
            help="Get a specific date for events. Overrides start and end dates.",
            default=None,
        )
        parser.add_argument(
            "-i",
            "--importance",
            action="store",
            dest="importance",
            choices=investingcom_model.IMPORTANCES,
            help="Event importance classified as high, medium, low or all.",
        )
        parser.add_argument(
            "--categories",
            action="store",
            dest="category",
            choices=investingcom_model.CATEGORIES,
            default=None,
            help="[INVESTING source only] Event category.",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
            raw=True,
            limit=100,
        )

        if ns_parser:

            if ns_parser.start_date:
                start_date = ns_parser.start_date.strftime("%Y-%m-%d")
            else:
                start_date = None

            if ns_parser.end_date:
                end_date = ns_parser.end_date.strftime("%Y-%m-%d")
            else:
                end_date = None

            # TODO: Add `Investing` to sources again when `investpy` is fixed

            countries = (
                ns_parser.country.replace("_", " ").title().split(",")
                if ns_parser.country
                else []
            )

            if ns_parser.spec_date:
                start_date = ns_parser.spec_date.strftime("%Y-%m-%d")
                end_date = ns_parser.spec_date.strftime("%Y-%m-%d")

            else:
                start_date, end_date = sorted([start_date, end_date])
            nasdaq_view.display_economic_calendar(
                country=countries,
                start_date=start_date,
                end_date=end_date,
                limit=ns_parser.limit,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_plot(self, other_args: List[str]):
        """Process plot command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="plot",
            description="This command can plot any data on two y-axes obtained from the macro, fred, index and "
            "treasury commands. To be able to use this data, just load the available series from the previous "
            "commands. For example 'macro -p GDP -c Germany Netherlands' will store the data for usage "
            "in this command. Therefore, it allows you to plot different time series in one graph. "
            "The example above could be plotted the following way: 'plot --y1 Germany_GDP --y2 Netherlands_GDP' "
            "or 'plot --y1 Germany_GDP Netherlands_GDP'",
        )
        parser.add_argument(
            "--y1",
            type=str,
            dest="yaxis1",
            help="Select the data you wish to plot on the first y-axis. You can select multiple variables here.",
            default="",
        )
        parser.add_argument(
            "--y2",
            type=str,
            dest="yaxis2",
            help="Select the data you wish to plot on the second y-axis. You can select multiple variables here.",
            default="",
        )

        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "--y1")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
            limit=10,
        )

        if ns_parser:
            y1s = list_from_str(ns_parser.yaxis1)
            y2s = list_from_str(ns_parser.yaxis2)
            if not self.DATASETS:
                console.print(
                    "There is no data stored yet. Please use either the 'macro', 'fred', 'index' and/or "
                    "'treasury' command."
                )
            else:
                dataset_yaxis1 = pd.DataFrame()
                dataset_yaxis2 = pd.DataFrame()

                if y1s:
                    for variable in y1s:
                        for key, data in self.DATASETS.items():
                            if variable in data.columns:
                                if key == "macro":
                                    split = variable.split("_")
                                    transform = ""
                                    if (
                                        len(split) == 3
                                        and split[2] in econdb_model.TRANSFORM
                                    ):
                                        (
                                            country,
                                            parameter_abbreviation,
                                            transform,
                                        ) = split
                                    elif len(split) == 2:
                                        country, parameter_abbreviation = split
                                    else:
                                        country = f"{split[0]} {split[1]}"
                                        parameter_abbreviation = split[2]

                                    parameter = econdb_model.PARAMETERS[
                                        parameter_abbreviation
                                    ]["name"]
                                    units = self.UNITS[country.replace(" ", "_")][
                                        parameter_abbreviation
                                    ]
                                    if transform:
                                        transformtype = (
                                            f" ({econdb_model.TRANSFORM[transform]}) "
                                        )
                                    else:
                                        transformtype = " "
                                    dataset_yaxis1[
                                        f"{country}{transformtype}[{parameter}, Units: {units}]"
                                    ] = data[variable]
                                elif key == "fred":
                                    compound_detail = self.FRED_TITLES[variable]
                                    detail = {
                                        "units": compound_detail.split("(")[-1].split(
                                            ")"
                                        )[0],
                                        "title": compound_detail.split("(")[0].strip(),
                                    }
                                    data_to_plot, title = fred_view.format_data_to_plot(
                                        data[variable], detail
                                    )
                                    dataset_yaxis1[title] = data_to_plot
                                elif (
                                    key == "index"
                                    and variable in yfinance_model.INDICES
                                ):
                                    dataset_yaxis1[
                                        yfinance_model.INDICES[variable]["name"]
                                    ] = data[variable]
                                elif key == "treasury":
                                    parameter, maturity = variable.split("_")
                                    dataset_yaxis1[f"{parameter} [{maturity}]"] = data[
                                        variable
                                    ]
                                else:
                                    dataset_yaxis1[variable] = data[variable]
                                break
                    if dataset_yaxis1.empty:
                        console.print(
                            f"[red]Not able to find any data for the --y1 argument. The currently available "
                            f"options are: {', '.join(self.choices['plot']['--y1'])}[/red]\n"
                        )

                if y2s:
                    for variable in y2s:
                        for key, data in self.DATASETS.items():
                            if variable in data.columns:
                                if key == "macro":
                                    split = variable.split("_")
                                    transform = ""
                                    if (
                                        len(split) == 3
                                        and split[2] in econdb_model.TRANSFORM
                                    ):
                                        (
                                            country,
                                            parameter_abbreviation,
                                            transform,
                                        ) = split
                                    elif len(split) == 2:
                                        country, parameter_abbreviation = split
                                    else:
                                        country = f"{split[0]} {split[1]}"
                                        parameter_abbreviation = split[2]

                                    parameter = econdb_model.PARAMETERS[
                                        parameter_abbreviation
                                    ]["name"]
                                    units = self.UNITS[country.replace(" ", "_")][
                                        parameter_abbreviation
                                    ]
                                    if transform:
                                        transformtype = (
                                            f" ({econdb_model.TRANSFORM[transform]}) "
                                        )
                                    else:
                                        transformtype = " "
                                    dataset_yaxis2[
                                        f"{country}{transformtype}[{parameter}, Units: {units}]"
                                    ] = data[variable]
                                elif key == "fred":
                                    compound_detail = self.FRED_TITLES[variable]
                                    detail = {
                                        "units": compound_detail.split("(")[-1].split(
                                            ")"
                                        )[0],
                                        "title": compound_detail.split("(")[0].strip(),
                                    }
                                    data_to_plot, title = fred_view.format_data_to_plot(
                                        data[variable], detail
                                    )
                                    dataset_yaxis2[title] = data_to_plot
                                elif (
                                    key == "index"
                                    and variable in yfinance_model.INDICES
                                ):
                                    dataset_yaxis2[
                                        yfinance_model.INDICES[variable]["name"]
                                    ] = data[variable]
                                elif key == "treasury":
                                    parameter, maturity = variable.split("_")
                                    dataset_yaxis2[f"{parameter} [{maturity}]"] = data[
                                        variable
                                    ]
                                else:
                                    dataset_yaxis2[variable] = data[variable]
                                break
                    if dataset_yaxis2.empty:
                        console.print(
                            f"[red]Not able to find any data for the --y2 argument. The currently available "
                            f"options are: {', '.join(self.choices['plot']['--y2'])}[/red]\n"
                        )

                if y1s or y2s:
                    plot_view.show_plot(
                        dataset_yaxis_1=dataset_yaxis1,
                        dataset_yaxis_2=dataset_yaxis2,
                        export=ns_parser.export,
                    )

    @log_start_end(log=logger)
    def call_rtps(self, other_args: List[str]):
        """Process rtps command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="rtps",
            description="""
                Real-time and historical sector performances calculated from
                S&P500 incumbents. Pops plot in terminal. [Source: Alpha Vantage]
            """,
        )

        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
        )
        if ns_parser:
            alphavantage_view.realtime_performance_sector(
                raw=ns_parser.raw,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_valuation(self, other_args: List[str]):
        """Process valuation command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="valuation",
            description="""
                View group (sectors, industry or country) valuation data. [Source: Finviz]
            """,
        )
        parser.add_argument(
            "-g",
            "--group",
            type=str,
            choices=list(self.d_GROUPS.keys()),
            default="sector",
            dest="group",
            help="Data group (sectors, industry or country)",
        )
        parser.add_argument(
            "-s",
            "--sortby",
            dest="sortby",
            type=str,
            choices=self.valuation_sort_cols,
            default="Name",
            help="Column to sort by",
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
            other_args.insert(0, "-g")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            ns_group = (
                " ".join(ns_parser.group)
                if isinstance(ns_parser.group, list)
                else ns_parser.group
            )
            finviz_view.display_valuation(
                group=ns_group,
                sortby=ns_parser.sortby,
                ascend=ns_parser.reverse,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_performance(self, other_args: List[str]):
        """Process performance command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="performance",
            description="""
                View group (sectors, industry or country) performance data. [Source: Finviz]
            """,
        )
        parser.add_argument(
            "-g",
            "--group",
            type=str,
            choices=list(self.d_GROUPS.keys()),
            default="sector",
            dest="group",
            help="Data group (sector, industry or country)",
        )
        parser.add_argument(
            "-s",
            "--sortby",
            dest="sortby",
            choices=self.performance_sort_list,
            default="Name",
            help="Column to sort by",
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
            other_args.insert(0, "-g")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            ns_group = (
                " ".join(ns_parser.group)
                if isinstance(ns_parser.group, list)
                else ns_parser.group
            )
            finviz_view.display_performance(
                group=ns_group,
                sortby=ns_parser.sortby,
                ascend=ns_parser.reverse,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_edebt(self, other_args: List[str]):
        """Process edebt command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="edebt",
            description="""
                National debt statistics for various countries. [Source: Wikipedia]
            """,
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, limit=20
        )
        if ns_parser:
            commodity_view.display_debt(export=ns_parser.export, limit=ns_parser.limit)

    @log_start_end(log=logger)
    def call_spectrum(self, other_args: List[str]):
        """Process spectrum command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="spectrum",
            description="""
                View group (sectors, industry or country) spectrum data. [Source: Finviz]
            """,
        )
        parser.add_argument(
            "-g",
            "--group",
            type=str,
            choices=list(self.d_GROUPS.keys()),
            default="sector",
            dest="group",
            help="Data group (sector, industry or country)",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-g")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_FIGURES_ALLOWED
        )
        if ns_parser:
            ns_group = (
                " ".join(ns_parser.group)
                if isinstance(ns_parser.group, list)
                else ns_parser.group
            )
            finviz_view.display_spectrum(group=ns_group)

            # # Due to Finviz implementation of Spectrum, we delete the generated spectrum figure
            # # after saving it and displaying it to the user
            os.remove(self.d_GROUPS[ns_group] + ".jpg")

    @log_start_end(log=logger)
    def call_eval(self, other_args):
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="eval",
            description="""Create custom data column from loaded datasets.  Can be mathematical expressions supported
            by pandas.eval() function.

            Example.  If I have loaded `fred DGS2,DGS5` and I want to create a new column that is the difference
            between these two, I can create a new column by doing `eval spread = DGS2 - DGS5`.
            Notice that the command is case sensitive, i.e., `DGS2` is not the same as `dgs2`.
            """,
        )
        parser.add_argument(
            "-q",
            "--query",
            type=str,
            nargs="+",
            dest="query",
            help="Query to evaluate on loaded datasets",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-q")

        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            self.DATASETS = economy_helpers.create_new_entry(
                self.DATASETS, " ".join(ns_parser.query)
            )

            self.stored_datasets = economy_helpers.update_stored_datasets_string(
                self.DATASETS
            )
        console.print()

    @log_start_end(log=logger)
    def call_qa(self, _):
        """Process qa command"""
        if not any(True for x in self.DATASETS.values() if not x.empty):
            console.print(
                "There is no data stored. Please use either the 'macro', 'fred', 'index' and/or "
                "'treasury' command in combination with the -st argument to plot data.\n"
            )
            return

        from openbb_terminal.economy.quantitative_analysis.qa_controller import (
            QaController,
        )

        data: Dict = {}
        for source, _ in self.DATASETS.items():
            if not self.DATASETS[source].empty:
                if len(self.DATASETS[source].columns) == 1:
                    data[self.DATASETS[source].columns[0]] = self.DATASETS[source]
                else:
                    for col in list(self.DATASETS[source].columns):
                        data[col] = self.DATASETS[source][col].to_frame()

        if data:
            self.queue = self.load_class(QaController, data, self.queue)
        else:
            console.print(
                "[red]Please load a dataset before moving to the qa menu[/red]\n"
            )
