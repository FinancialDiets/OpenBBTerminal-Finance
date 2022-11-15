"""Portfolio Controller"""
__docformat__ = "numpy"

import argparse
import logging
import os
from typing import List
from datetime import date

import pandas as pd

from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    EXPORT_BOTH_RAW_DATA_AND_FIGURES,
    EXPORT_ONLY_FIGURES_ALLOWED,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
)

from openbb_terminal.menu import session
from openbb_terminal.core.config.paths import MISCELLANEOUS_DIRECTORY
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.portfolio.portfolio_model import generate_portfolio
from openbb_terminal.portfolio import statics
from openbb_terminal.portfolio import portfolio_view
from openbb_terminal.portfolio import portfolio_helper
from openbb_terminal.portfolio import attribution_model
from openbb_terminal.portfolio.portfolio_optimization import po_controller
from openbb_terminal.rich_config import console, MenuText
from openbb_terminal.common.quantitative_analysis import qa_view

# pylint: disable=R1710,E1101,C0415,W0212,too-many-function-args,C0302,too-many-instance-attributes

logger = logging.getLogger(__name__)


class PortfolioController(BaseController):
    """Portfolio Controller class"""

    CHOICES_COMMANDS = [
        "load",
        "show",
        "bench",
        "alloc",
        "attrib",
        "perf",
        "yret",
        "mret",
        "dret",
        "distr",
        "holdv",
        "holdp",
        "maxdd",
        "var",
        "es",
        "sh",
        "so",
        "om",
        "rvol",
        "rsharpe",
        "rsort",
        "rbeta",
        "metric",
        "summary",
    ]
    CHOICES_MENUS = [
        "bro",
        "po",
        "pa",
    ]
    VALID_DISTRIBUTIONS = ["laplace", "student_t", "logistic", "normal"]
    AGGREGATION_METRICS = ["assets", "sectors", "countries", "regions"]
    VALID_METRICS = [
        "volatility",
        "sharpe",
        "sortino",
        "maxdrawdown",
        "rsquare",
        "skew",
        "kurtosis",
        "gaintopain",
        "trackerr",
        "information",
        "tail",
        "commonsense",
        "jensens",
        "calmar",
        "kelly",
        "payoff",
        "profitfactor",
    ]
    PERIODS = ["3y", "5y", "10y", "all"]
    PATH = "/portfolio/"

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)
        self.file_types = ["xlsx", "csv"]

        self.DEFAULT_HOLDINGS_PATH = portfolio_helper.DEFAULT_HOLDINGS_PATH

        self.DATA_HOLDINGS_FILES = {
            filepath.name: filepath
            for file_type in self.file_types
            for filepath in self.DEFAULT_HOLDINGS_PATH.rglob(f"*.{file_type}")
        }
        self.DATA_HOLDINGS_FILES.update(
            {
                filepath.name: filepath
                for file_type in self.file_types
                for filepath in (
                    MISCELLANEOUS_DIRECTORY / "portfolio_examples" / "holdings"
                ).rglob(f"*.{file_type}")
            }
        )

        self.portfolio_df = pd.DataFrame(
            columns=[
                "Date",
                "Name",
                "Type",
                "Sector",
                "Industry",
                "Country",
                "Price",
                "Quantity",
                "Fees",
                "Premium",
                "Investment",
                "Side",
                "Currency",
            ]
        )

        self.portfolio_name: str = ""
        self.benchmark_name: str = ""
        self.original_benchmark_name = ""
        self.risk_free_rate = 0
        self.portlist: List[str] = os.listdir(self.DEFAULT_HOLDINGS_PATH)
        self.portfolio = None

        if session and obbff.USE_PROMPT_TOOLKIT:
            self.update_choices()

    def update_choices(self):

        self.DEFAULT_HOLDINGS_PATH = portfolio_helper.DEFAULT_HOLDINGS_PATH

        self.DATA_HOLDINGS_FILES.update(
            {
                filepath.name: filepath
                for file_type in self.file_types
                for filepath in self.DEFAULT_HOLDINGS_PATH.rglob(f"*.{file_type}")
            }
        )

        choices: dict = {c: {} for c in self.controller_choices}

        choices["load"] = {
            "--file": {c: {} for c in self.DATA_HOLDINGS_FILES},
            "-f": "--file",
            "--name": None,
            "-n": "--name",
            "--rfr": None,
            "-r": "--rfr",
        }
        choices["show"] = {
            "--limit": None,
            "-l": "--limit",
        }
        choices["bench"] = {c: {} for c in statics.BENCHMARK_LIST}
        choices["bench"] = {
            "--benchmark": {c: {} for c in statics.BENCHMARK_LIST},
            "-b": "--benchmark",
        }

        choices["bench"]["--full_shares"] = {}
        choices["bench"]["-s"] = "--full_shares"
        hold = {
            "--unstack": {},
            "-u": "--unstack",
            "--raw": {},
            "--limit": None,
            "-l": "--limit",
        }
        choices["holdv"] = hold
        choices["holdp"] = hold
        choices["yret"] = {
            "--period": {c: {} for c in self.PERIODS},
            "-p": "--period",
            "--raw": {},
        }
        choices["mret"] = {
            "--period": {c: {} for c in self.PERIODS},
            "-p": "--period",
            "--show": {},
            "-s": "--show",
            "--raw": {},
        }
        choices["dret"] = {
            "--period": {c: {} for c in self.PERIODS},
            "-p": "--period",
            "--limit": None,
            "-l": "--limit",
            "--raw": {},
        }
        choices["distr"] = {
            "--period": {c: {} for c in portfolio_helper.PERIODS},
            "-p": "--period",
            "--raw": {},
        }
        choices["rvol"] = {
            "--period": {c: {} for c in portfolio_helper.PERIODS},
            "-p": "--period",
        }
        r_auto_complete = {
            "--period": {c: {} for c in portfolio_helper.PERIODS},
            "-p": "--period",
            "--rfr": None,
            "-r": "--rfr",
        }
        choices["rsharpe"] = r_auto_complete
        choices["rsort"] = r_auto_complete
        choices["rbeta"] = {
            "--period": {c: {} for c in portfolio_helper.PERIODS},
            "-p": "--period",
        }
        choices["alloc"] = {c: {} for c in self.AGGREGATION_METRICS}
        choices["alloc"]["--agg"] = {c: {} for c in self.AGGREGATION_METRICS}
        choices["alloc"]["-a"] = "--agg"
        choices["alloc"]["--tables"] = {}
        choices["alloc"]["-t"] = "--tables"
        choices["alloc"]["--limit"] = None
        choices["alloc"]["-l"] = "--limit"
        choices["summary"] = r_auto_complete
        choices["metric"] = {c: {} for c in self.VALID_METRICS}
        choices["metric"]["--metric"] = {c: {} for c in self.VALID_METRICS}
        choices["metric"]["-m"] = "--metric"
        choices["metric"]["--rfr"] = None
        choices["metric"]["-r"] = "--rfr"
        choices["perf"] = {
            "--show_trades": {},
            "-t": "--show_trades",
        }
        choices["var"] = {
            "--mean": {},
            "-m": "--mean",
            "--adjusted": {},
            "-a": "--adjusted",
            "--student": {},
            "-s": "--student",
            "--percentile": None,
            "-p": "--percentile",
        }
        choices["es"] = {
            "--mean": {},
            "-m": "--mean",
            "--dist": {c: {} for c in self.VALID_DISTRIBUTIONS},
            "-d": "--dist",
            "--percentile": None,
            "-p": "--percentile",
        }
        choices["om"] = {
            "--start": None,
            "-s": "--start",
            "--end": None,
            "-e": "--end",
        }

        self.choices = choices

        choices["support"] = self.SUPPORT_CHOICES
        choices["about"] = self.ABOUT_CHOICES

        self.completer = NestedCompleter.from_nested_dict(choices)

    def print_help(self):
        """Print help"""
        mt = MenuText("portfolio/")
        mt.add_menu("bro")
        mt.add_menu("po")
        mt.add_raw("\n")

        mt.add_cmd("load")
        mt.add_cmd("show")
        mt.add_cmd("bench")
        mt.add_raw("\n")
        mt.add_param("_loaded", self.portfolio_name)
        mt.add_param("_riskfreerate", self.portfolio_name)
        mt.add_param("_benchmark", self.benchmark_name)
        mt.add_raw("\n")

        mt.add_info("_graphs_")
        mt.add_cmd("holdv", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("holdp", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("yret", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("mret", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("dret", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("distr", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("maxdd", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("rvol", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("rsharpe", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("rsort", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("rbeta", self.portfolio_name and self.benchmark_name)

        mt.add_info("_metrics_")
        mt.add_cmd("alloc", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("attrib", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("summary", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("alloc", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("attrib", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("metric", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("perf", self.portfolio_name and self.benchmark_name)

        mt.add_info("_risk_")
        mt.add_cmd("var", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("es", self.portfolio_name and self.benchmark_name)
        mt.add_cmd("os", self.portfolio_name and self.benchmark_name)

        port = bool(self.portfolio_name)
        port_bench = bool(self.portfolio_name) and bool(self.benchmark_name)

        help_text = f"""[menu]
>   bro              brokers holdings, \t\t supports: robinhood, ally, degiro, coinbase
>   po               portfolio optimization, \t optimize your portfolio weights efficiently[/menu]
[cmds]
    load             load data into the portfolio
    show             show existing transactions
    bench            define the benchmark
[/cmds]
[param]Loaded transactions file:[/param] {self.portfolio_name}
[param]Risk Free Rate:  [/param] {self.risk_free_rate:.2%}
[param]Benchmark:[/param] {self.benchmark_name}

[info]Graphs:[/info]{("[unvl]", "[cmds]")[port_bench]}
    holdv            holdings of assets (absolute value)
    holdp            portfolio holdings of assets (in percentage)
    yret             yearly returns
    mret             monthly returns
    dret             daily returns
    distr            distribution of daily returns
    maxdd            maximum drawdown
    rvol             rolling volatility
    rsharpe          rolling sharpe
    rsort            rolling sortino
    rbeta            rolling beta
{("[/unvl]", "[/cmds]")[port_bench]}
[info]Metrics:[/info]{("[unvl]", "[cmds]")[port_bench]}
    summary          all portfolio vs benchmark metrics for a certain period of choice
    alloc            allocation on an asset, sector, countries or regions basis
    attrib           display sector attribution of the portfolio compared to the S&P 500
    metric           portfolio vs benchmark metric for all different periods
    perf             performance of the portfolio versus benchmark{("[/unvl]", "[/cmds]")[port_bench]}

[info]Risk Metrics:[/info]{("[unvl]", "[cmds]")[port]}
    var              display value at risk
    es               display expected shortfall
    om               display omega ratio{("[/unvl]", "[/cmds]")[port]}
        """
        # TODO: Clean up the reports inputs
        # TODO: Edit the allocation to allow the different asset classes
        # [info]Reports:[/info]
        #    ar          annual report for performance of a given portfolio
        console.print(text=help_text, menu="Portfolio")
        self.update_choices()

    def custom_reset(self):
        """Class specific component of reset command"""
        objects_to_reload = ["portfolio"]
        if self.portfolio_name:
            objects_to_reload.append(f"load {self.portfolio_name}")
        if self.original_benchmark_name:
            objects_to_reload.append(f'bench "{self.original_benchmark_name}"')
        return objects_to_reload

    @log_start_end(log=logger)
    def call_bro(self, _):
        """Process bro command"""
        from openbb_terminal.portfolio.brokers.bro_controller import (
            BrokersController,
        )

        self.queue = self.load_class(BrokersController, self.queue)

    @log_start_end(log=logger)
    def call_po(self, _):
        """Process po command"""
        if self.portfolio is None:
            tickers = []
        else:
            tickers = self.portfolio.tickers_list
        self.queue = self.load_class(
            po_controller.PortfolioOptimizationController,
            tickers,
            None,
            None,
            self.queue,
        )

    @log_start_end(log=logger)
    def call_load(self, other_args: List[str]):
        """Process load command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="load",
            description="Load your portfolio transactions.",
        )
        parser.add_argument(
            "-f",
            "--file",
            type=str,
            dest="file",
            required="-h" not in other_args,
            help="The file to be loaded",
        )
        parser.add_argument(
            "-n",
            "--name",
            type=str,
            dest="name",
            help="The name that you wish to give to your portfolio",
        )
        parser.add_argument(
            "-r",
            "--rfr",
            type=float,
            default=0,
            dest="risk_free_rate",
            help="Set the risk free rate.",
        )

        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser and ns_parser.file:
            if ns_parser.file in self.DATA_HOLDINGS_FILES:
                file_location = self.DATA_HOLDINGS_FILES[ns_parser.file]
            else:
                file_location = ns_parser.file  # type: ignore

            self.portfolio = generate_portfolio(
                transactions_file_path=str(file_location),
                benchmark_symbol="SPY",
                risk_free_rate=ns_parser.risk_free_rate / 100,
            )

            if ns_parser.name:
                self.portfolio_name = ns_parser.name
            else:
                self.portfolio_name = ns_parser.file
            console.print(
                f"\n[bold][param]Portfolio:[/param][/bold] {self.portfolio_name}"
            )

            self.benchmark_name = "SPDR S&P 500 ETF Trust (SPY)"
            console.print(
                f"[bold][param]Risk Free Rate:[/param][/bold] {self.risk_free_rate:.2%}"
            )

            self.risk_free_rate = ns_parser.risk_free_rate / 100
            console.print(
                f"[bold][param]Benchmark:[/param][/bold] {self.benchmark_name}\n"
            )

    @log_start_end(log=logger)
    def call_show(self, other_args: List[str]):
        """Process show command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="show",
            description="Show transactions table",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            limit=10,
        )
        if ns_parser and self.portfolio is not None:
            portfolio_view.display_transactions(
                self.portfolio,
                show_index=False,
                limit=ns_parser.limit,
                export=ns_parser.export,
            )

    @log_start_end(log=logger)
    def call_bench(self, other_args: List[str]):
        """Process bench command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="bench",
            description="Load in a benchmark from a selected list or set your own based on the ticker.",
        )
        parser.add_argument(
            "-b",
            "--benchmark",
            type=str,
            default="SPY",
            nargs="+",
            dest="benchmark",
            required="-h" not in other_args,
            help="Set the benchmark for the portfolio. By default, this is SPDR S&P 500 ETF Trust (SPY).",
        )
        parser.add_argument(
            "-s",
            "--full_shares",
            action="store_true",
            default=False,
            dest="full_shares",
            help="Whether to only make a trade with the benchmark when a full share can be bought (no partial shares).",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-b")
        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser and self.portfolio is not None:
            # Needs to be checked since we want to use the start date of the portfolio when comparing with benchmark
            if self.portfolio_name:
                chosen_benchmark = " ".join(ns_parser.benchmark)

                if chosen_benchmark in statics.BENCHMARK_LIST:
                    benchmark_ticker = statics.BENCHMARK_LIST[chosen_benchmark]
                    self.original_benchmark_name = chosen_benchmark
                else:
                    benchmark_ticker = chosen_benchmark

                self.portfolio.set_benchmark(benchmark_ticker, ns_parser.full_shares)

                self.benchmark_name = chosen_benchmark

            else:
                console.print(
                    "[red]Please first load transactions file using 'load'[/red]\n"
                )
            console.print()

    @log_start_end(log=logger)
    def call_alloc(self, other_args: List[str]):
        """Process alloc command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="alloc",
            description="""
                Show your allocation to each asset or sector compared to the benchmark.
            """,
        )
        parser.add_argument(
            "-a",
            "--agg",
            default="assets",
            choices=self.AGGREGATION_METRICS,
            dest="agg",
            help="The type of allocation aggregation you wish to do",
        )
        parser.add_argument(
            "-t",
            "--tables",
            action="store_true",
            default=False,
            dest="tables",
            help="Whether to also include the assets/sectors tables of both the benchmark and the portfolio.",
        )
        if other_args:
            if other_args and "-" not in other_args[0][0]:
                other_args.insert(0, "-a")

        ns_parser = self.parse_known_args_and_warn(parser, other_args, limit=10)

        if ns_parser and self.portfolio is not None:

            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                if ns_parser.agg == "assets":
                    portfolio_view.display_assets_allocation(
                        self.portfolio,
                        ns_parser.limit,
                        ns_parser.tables,
                    )
                elif ns_parser.agg == "sectors":
                    portfolio_view.display_sectors_allocation(
                        self.portfolio,
                        ns_parser.limit,
                        ns_parser.tables,
                    )
                elif ns_parser.agg == "countries":
                    portfolio_view.display_countries_allocation(
                        self.portfolio,
                        ns_parser.limit,
                        ns_parser.tables,
                    )
                elif ns_parser.agg == "regions":
                    portfolio_view.display_regions_allocation(
                        self.portfolio,
                        ns_parser.limit,
                        ns_parser.tables,
                    )
                else:
                    console.print(
                        f"{ns_parser.agg} is not an available option. The options "
                        f"are: {', '.join(self.AGGREGATION_METRICS)}"
                    )

    @log_start_end(log=logger)
    def call_attrib(self, other_args: List[str]):
        """Process attrib command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="attrib",
            description="""
                Displays sector attribution of the portfolio compared to the S&P 500
                """,
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            choices=portfolio_helper.PERIODS,
            dest="period",
            default="all",
            help="Period in which to calculate attribution",
        )
        parser.add_argument(
            "-t",
            "--type",
            type=str,
            choices=["relative", "absolute"],
            dest="type",
            default="relative",
            help="Select between relative or absolute attribution values",
        )
        parser.add_argument(
            "--raw",
            type=bool,
            dest="raw",
            default=False,
            const=True,
            nargs="?",
            help="View raw attribution values in a table",
        )

        if other_args:
            if other_args and "-" not in other_args[0][0]:
                other_args.insert(0, "-a")

        ns_parser = self.parse_known_args_and_warn(parser, other_args, limit=10)

        if ns_parser and self.portfolio is not None:

            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                if self.benchmark_name != "SPDR S&P 500 ETF Trust (SPY)":
                    print(
                        "This feature uses S&P 500 as benchmark and will disregard selected benchmark if different."
                    )
                # sector contribution
                end_date = date.today()
                # set correct time period
                if ns_parser.period == "all":
                    start_date = self.portfolio.inception_date
                else:
                    start_date = portfolio_helper.get_start_date_from_period(
                        ns_parser.period
                    )

                # calculate benchmark and portfolio contribution values
                bench_result = attribution_model.get_spy_sector_contributions(
                    start_date, end_date
                )
                portfolio_result = attribution_model.get_portfolio_sector_contributions(
                    start_date, self.portfolio.portfolio_trades
                )

                # relative results - the proportions of return attribution
                if ns_parser.type == "relative":
                    categorisation_result = (
                        attribution_model.percentage_attrib_categorizer(
                            bench_result, portfolio_result
                        )
                    )

                    portfolio_view.display_attribution_categorisation(
                        display=categorisation_result,
                        time_period=ns_parser.period,
                        attrib_type="Contributions as % of PF",
                        plot_fields=["S&P500 [%]", "Portfolio [%]"],
                        show_table=ns_parser.raw,
                    )

                # absolute - the raw values of return attribution
                if ns_parser.type == "absolute":
                    categorisation_result = attribution_model.raw_attrib_categorizer(
                        bench_result, portfolio_result
                    )

                    portfolio_view.display_attribution_categorisation(
                        display=categorisation_result,
                        time_period=ns_parser.period,
                        attrib_type="Raw contributions (Return x PF Weight)",
                        plot_fields=["S&P500", "Portfolio"],
                        show_table=ns_parser.raw,
                    )

            console.print()

    @log_start_end(log=logger)
    def call_perf(self, other_args: List[str]):
        """Process performance command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="performance",
            description="""
                Shows performance of each trade and total performance of the portfolio versus the benchmark.
            """,
        )
        parser.add_argument(
            "-t",
            "--show_trades",
            action="store_true",
            default=False,
            dest="show_trades",
            help="Whether to show performance on all trades in comparison to the benchmark.",
        )

        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):

                portfolio_view.display_performance_vs_benchmark(
                    self.portfolio,
                    ns_parser.show_trades,
                )

    @log_start_end(log=logger)
    def call_holdv(self, other_args: List[str]):
        """Process holdv command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="holdv",
            description="Display holdings of assets (absolute value)",
        )
        parser.add_argument(
            "-u",
            "--unstack",
            action="store_true",
            default=False,
            dest="unstack",
            help="Sum all assets value over time",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
            limit=10,
        )
        if ns_parser:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_holdings_value(
                    self.portfolio,
                    ns_parser.unstack,
                    ns_parser.raw,
                    ns_parser.limit,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_holdp(self, other_args: List[str]):
        """Process holdp command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="holdp",
            description="Display holdings of assets (in percentage)",
        )
        parser.add_argument(
            "-u",
            "--unstack",
            action="store_true",
            default=False,
            dest="unstack",
            help="Sum all assets percentage over time",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
            limit=10,
        )
        if ns_parser:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_holdings_percentage(
                    self.portfolio,
                    ns_parser.unstack,
                    ns_parser.raw,
                    ns_parser.limit,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_var(self, other_args: List[str]):
        """Process var command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="var",
            description="""
                Provides value at risk (short: VaR) of the selected portfolio.
            """,
        )
        parser.add_argument(
            "-m",
            "--mean",
            action="store_true",
            default=True,
            dest="use_mean",
            help="If one should use the mean of the portfolio return",
        )
        parser.add_argument(
            "-a",
            "--adjusted",
            action="store_true",
            default=False,
            dest="adjusted",
            help="""
                If the VaR should be adjusted for skew and kurtosis (Cornish-Fisher-Expansion)
            """,
        )
        parser.add_argument(
            "-s",
            "--student",
            action="store_true",
            default=False,
            dest="student_t",
            help="""
                If one should use the student-t distribution
            """,
        )
        parser.add_argument(
            "-p",
            "--percentile",
            action="store",
            dest="percentile",
            type=float,
            default=99.9,
            help="""
                Percentile used for VaR calculations, for example input 99.9 equals a 99.9 Percent VaR
            """,
        )

        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser and self.portfolio is not None:
            if self.portfolio_name:
                if ns_parser.adjusted and ns_parser.student_t:
                    console.print(
                        "Select either the adjusted or the student_t parameter.\n"
                    )
                else:
                    portfolio_view.display_var(
                        portfolio_engine=self.portfolio,
                        use_mean=ns_parser.use_mean,
                        adjusted_var=ns_parser.adjusted,
                        student_t=ns_parser.student_t,
                        percentile=ns_parser.percentile,
                    )
            else:
                console.print(
                    "[red]Please first define the portfolio using 'load'[/red]\n"
                )

    @log_start_end(log=logger)
    def call_es(self, other_args: List[str]):
        """Process es command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="es",
            description="""
                Provides Expected Shortfall (short: ES) of the selected portfolio.
            """,
        )
        parser.add_argument(
            "-m",
            "--mean",
            action="store_true",
            default=True,
            dest="use_mean",
            help="If one should use the mean of the portfolios return",
        )
        parser.add_argument(
            "-d",
            "--dist",
            "--distributions",
            dest="distribution",
            type=str,
            choices=self.VALID_DISTRIBUTIONS,
            default="normal",
            help="Distribution used for the calculations",
        )
        parser.add_argument(
            "-p",
            "--percentile",
            action="store",
            dest="percentile",
            type=float,
            default=99.9,
            help="""
                Percentile used for ES calculations, for example input 99.9 equals a 99.9 Percent Expected Shortfall
            """,
        )

        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser and self.portfolio is not None:
            if self.portfolio_name:
                portfolio_view.display_es(
                    portfolio_engine=self.portfolio,
                    use_mean=ns_parser.use_mean,
                    distribution=ns_parser.distribution,
                    percentile=ns_parser.percentile,
                )
            else:
                console.print(
                    "[red]Please first define the portfolio using 'load'[/red]\n"
                )

    @log_start_end(log=logger)
    def call_om(self, other_args: List[str]):
        """Process om command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="om",
            description="""
                   Provides omega ratio of the selected portfolio.
               """,
        )
        parser.add_argument(
            "-s",
            "--start",
            action="store",
            dest="start",
            type=float,
            default=0,
            help="""
                   Start of the omega ratio threshold
               """,
        )
        parser.add_argument(
            "-e",
            "--end",
            action="store",
            dest="end",
            type=float,
            default=1.5,
            help="""
                   End of the omega ratio threshold
               """,
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser and self.portfolio is not None:
            if self.portfolio_name:
                data = self.portfolio.returns[1:]
                qa_view.display_omega(
                    data,
                    ns_parser.start,
                    ns_parser.end,
                )
            else:
                console.print(
                    "[red]Please first define the portfolio (via 'load')[/red]\n"
                )

    @log_start_end(log=logger)
    def call_yret(self, other_args: List[str]):
        """Process yret command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="yret",
            description="End of the year returns",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            dest="period",
            default="all",
            choices=self.PERIODS,
            help="Period to select start end of the year returns",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            raw=True,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
        )

        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_yearly_returns(
                    self.portfolio,
                    ns_parser.period,
                    ns_parser.raw,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_mret(self, other_args: List[str]):
        """Process mret command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="mret",
            description="Monthly returns",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            dest="period",
            default="all",
            choices=self.PERIODS,
            help="Period to select start end of the year returns",
        )
        parser.add_argument(
            "-s",
            "--show",
            action="store_true",
            default=False,
            dest="show_vals",
            help="Show monthly returns on heatmap",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            raw=True,
            export_allowed=EXPORT_ONLY_FIGURES_ALLOWED,
        )

        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_monthly_returns(
                    self.portfolio,
                    ns_parser.period,
                    ns_parser.raw,
                    ns_parser.show_vals,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_dret(self, other_args: List[str]):
        """Process dret command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="dret",
            description="Daily returns",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            dest="period",
            default="all",
            choices=self.PERIODS,
            help="Period to select start end of the year returns",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            raw=True,
            limit=10,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
        )

        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_daily_returns(
                    self.portfolio,
                    ns_parser.period,
                    ns_parser.raw,
                    ns_parser.limit,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_maxdd(self, other_args: List[str]):
        """Process maxdd command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="maxdd",
            description="Show portfolio maximum drawdown",
        )
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_FIGURES_ALLOWED
        )
        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_maximum_drawdown(self.portfolio)

    @log_start_end(log=logger)
    def call_rvol(self, other_args: List[str]):
        """Process rolling volatility command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="rvol",
            description="Show rolling volatility portfolio vs benchmark",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            dest="period",
            default="1y",
            choices=list(portfolio_helper.PERIODS_DAYS.keys()),
            help="Period to apply rolling window",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )
        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_rolling_volatility(
                    self.portfolio,
                    window=ns_parser.period,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_rsharpe(self, other_args: List[str]):
        """Process rolling sharpe command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="rsharpe",
            description="Show rolling sharpe portfolio vs benchmark",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            dest="period",
            default="1y",
            choices=list(portfolio_helper.PERIODS_DAYS.keys()),
            help="Period to apply rolling window",
        )
        parser.add_argument(
            "-r",
            "--rfr",
            type=float,
            dest="risk_free_rate",
            default=self.risk_free_rate,
            help="Set risk free rate for calculations.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )
        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_rolling_sharpe(
                    self.portfolio,
                    risk_free_rate=ns_parser.risk_free_rate / 100,
                    window=ns_parser.period,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_rsort(self, other_args: List[str]):
        """Process rolling sortino command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="rsort",
            description="Show rolling sortino portfolio vs benchmark",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            dest="period",
            default="1y",
            choices=list(portfolio_helper.PERIODS_DAYS.keys()),
            help="Period to apply rolling window",
        )
        parser.add_argument(
            "-r",
            "--rfr",
            type=float,
            dest="risk_free_rate",
            default=self.risk_free_rate,
            help="Set risk free rate for calculations.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )
        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_rolling_sortino(
                    portfolio_engine=self.portfolio,
                    risk_free_rate=ns_parser.risk_free_rate / 100,
                    window=ns_parser.period,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_rbeta(self, other_args: List[str]):
        """Process rolling beta command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="rbeta",
            description="Show rolling beta portfolio vs benchmark",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            dest="period",
            default="1y",
            choices=list(portfolio_helper.PERIODS_DAYS.keys()),
            help="Period to apply rolling window",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES
        )
        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_rolling_beta(
                    self.portfolio,
                    window=ns_parser.period,
                    export=ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_metric(self, other_args: List[str]):
        """Process metric command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="metric",
            description="Display metric of choice for different periods",
        )
        parser.add_argument(
            "-m",
            "--metric",
            type=str,
            dest="metric",
            default="-h" not in other_args,
            choices=self.VALID_METRICS,
            help="Set metric of choice",
        )
        parser.add_argument(
            "-r",
            "--rfr",
            type=float,
            dest="risk_free_rate",
            default=self.risk_free_rate,
            help="Set risk free rate for calculations.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-m")
        ns_parser = self.parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED
        )
        if ns_parser:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                if ns_parser.metric == "skew":
                    portfolio_view.display_skewness(self.portfolio, ns_parser.export)
                elif ns_parser.metric == "kurtosis":
                    portfolio_view.display_kurtosis(self.portfolio, ns_parser.export)
                elif ns_parser.metric == "volatility":
                    portfolio_view.display_volatility(self.portfolio, ns_parser.export)
                elif ns_parser.metric == "sharpe":
                    portfolio_view.display_sharpe_ratio(
                        self.portfolio, ns_parser.risk_free_rate, ns_parser.export
                    )
                elif ns_parser.metric == "sortino":
                    portfolio_view.display_sortino_ratio(
                        self.portfolio, ns_parser.risk_free_rate, ns_parser.export
                    )
                elif ns_parser.metric == "maxdrawdown":
                    portfolio_view.display_maximum_drawdown_ratio(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "rsquare":
                    portfolio_view.display_rsquare(self.portfolio, ns_parser.export)
                elif ns_parser.metric == "gaintopain":
                    portfolio_view.display_gaintopain_ratio(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "trackerr":
                    portfolio_view.display_tracking_error(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "information":
                    portfolio_view.display_information_ratio(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "tail":
                    portfolio_view.display_tail_ratio(self.portfolio, ns_parser.export)
                elif ns_parser.metric == "commonsense":
                    portfolio_view.display_common_sense_ratio(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "jensens":
                    portfolio_view.display_jensens_alpha(
                        self.portfolio, ns_parser.risk_free_rate, ns_parser.export
                    )
                elif ns_parser.metric == "calmar":
                    portfolio_view.display_calmar_ratio(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "kelly":
                    portfolio_view.display_kelly_criterion(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "payoff" and self.portfolio is not None:
                    portfolio_view.display_payoff_ratio(
                        self.portfolio, ns_parser.export
                    )
                elif ns_parser.metric == "profitfactor" and self.portfolio is not None:
                    portfolio_view.display_profit_factor(
                        self.portfolio, ns_parser.export
                    )

    @log_start_end(log=logger)
    def call_distr(self, other_args: List[str]):
        """Process distr command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="distr",
            description="Compute distribution of daily returns",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            choices=portfolio_helper.PERIODS,
            dest="period",
            default="all",
            help="The file to be loaded",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")

        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            raw=True,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
        )
        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_distribution_returns(
                    self.portfolio,
                    ns_parser.period,
                    ns_parser.raw,
                    ns_parser.export,
                )

    @log_start_end(log=logger)
    def call_summary(self, other_args: List[str]):
        """Process summary command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="summary",
            description="Display summary of portfolio vs benchmark",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=str,
            choices=portfolio_helper.PERIODS,
            dest="period",
            default="all",
            help="The file to be loaded",
        )
        parser.add_argument(
            "-r",
            "--rfr",
            type=float,
            dest="risk_free_rate",
            default=self.risk_free_rate,
            help="Set risk free rate for calculations.",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-p")

        ns_parser = self.parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED,
        )
        if ns_parser and self.portfolio is not None:
            if check_portfolio_benchmark_defined(
                self.portfolio_name, self.benchmark_name
            ):
                portfolio_view.display_summary(
                    self.portfolio,
                    ns_parser.period,
                    ns_parser.risk_free_rate,
                    ns_parser.export,
                )


def check_portfolio_benchmark_defined(portfolio_name: str, benchmark_name: str) -> bool:
    """Check that portfolio and benchmark have been defined

    Parameters
    ----------
    portfolio_name: str
        Portfolio name, will be empty if not defined
    benchmark_name: str
        Benchmark name, will be empty if not defined

    Returns
    -------
    bool
        If both portfolio and benchmark have been defined
    """

    if not portfolio_name:
        console.print("[red]Please first define the portfolio (via 'load')[/red]\n")
        return False

    if not benchmark_name:
        console.print("[red]Please first define the benchmark (via 'bench')[/red]\n")
        return False

    return True
