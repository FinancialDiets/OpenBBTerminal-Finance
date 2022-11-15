""" Portfolio Optimization Controller Module """
__docformat__ = "numpy"

# pylint: disable=too-many-lines,too-many-instance-attributes

import argparse
import logging
from typing import List, Dict

from openbb_terminal.custom_prompt_toolkit import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal import parent_classes
from openbb_terminal.core.config.paths import (
    MISCELLANEOUS_DIRECTORY,
    USER_EXPORTS_DIRECTORY,
    USER_PORTFOLIO_DATA_DIRECTORY,
)
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    check_non_negative,
    get_rf,
)
from openbb_terminal.menu import session
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.portfolio.portfolio_optimization import excel_model
from openbb_terminal.portfolio.portfolio_optimization import (
    optimizer_helper,
    optimizer_model,
    optimizer_view,
)
from openbb_terminal.portfolio.portfolio_optimization import yahoo_finance_model
from openbb_terminal.portfolio.portfolio_optimization.parameters import (
    params_controller,
    params_view,
)
from openbb_terminal.rich_config import console, MenuText

logger = logging.getLogger(__name__)


def add_arguments(parser_update, parser, not_in_list):
    parser_dict = vars(parser)
    for i in parser_dict["_actions"]:
        data_dict = vars(i)
        variables = list(data_dict.keys())
        if variables[0] == "option_strings" and data_dict["dest"] not in not_in_list:
            args = [data_dict["option_strings"][0] + "-sa"]
            if len(data_dict["option_strings"]) == 2:
                args.append(data_dict["option_strings"][1] + "-sa")
            if len(data_dict["option_strings"]) in [1, 2]:
                parser_update.add_argument(
                    *args,
                    type=data_dict["type"],
                    default=data_dict["default"],
                    dest=data_dict["dest"] + "_sa",
                    choices=data_dict["choices"],
                    help=data_dict["help"],
                )


class PortfolioOptimizationController(BaseController):
    """Portfolio Optimization Controller class"""

    CHOICES_COMMANDS = [
        "select",
        "show",
        "rpf",
        "load",
        "plot",
        "equal",
        "mktcap",
        "dividend",
        "property",
        "maxsharpe",
        "minrisk",
        "maxutil",
        "maxret",
        "maxdiv",
        "maxdecorr",
        "blacklitterman",
        "riskparity",
        "relriskparity",
        "hrp",
        "herc",
        "nco",
        "ef",
        "yolo",
        "file",
        "params",
    ]

    PERIOD_CHOICES = [
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    ]

    MEAN_RISK_CHOICES = [
        "MV",
        "MAD",
        "MSV",
        "FLPM",
        "SLPM",
        "CVaR",
        "EVaR",
        "WR",
        "ADD",
        "UCI",
        "CDaR",
        "EDaR",
        "MDD",
    ]

    RISK_PARITY_CHOICES = [
        "MV",
        "MAD",
        "MSV",
        "FLPM",
        "SLPM",
        "CVaR",
        "EVaR",
        "CDaR",
        "EDaR",
        "UCI",
    ]

    REL_RISK_PARITY_CHOICES = [
        "A",
        "B",
        "C",
    ]

    HCP_CHOICES = [
        "MV",
        "MAD",
        "GMD",
        "MSV",
        "VaR",
        "CVaR",
        "TG",
        "EVaR",
        "RG",
        "CVRG",
        "TGRG",
        "WR",
        "FLPM",
        "SLPM",
        "MDD",
        "ADD",
        "DaR",
        "CDaR",
        "EDaR",
        "UCI",
        "MDD_Rel",
        "ADD_Rel",
        "DaR_Rel",
        "CDaR_Rel",
        "EDaR_Rel",
        "UCI_Rel",
    ]

    RISK_CHOICES = {
        "mv": "MV",
        "mad": "MAD",
        "gmd": "GMD",
        "msv": "MSV",
        "var": "VaR",
        "cvar": "CVaR",
        "tg": "TG",
        "evar": "EVaR",
        "rg": "RG",
        "cvrg": "CVRG",
        "tgrg": "TGRG",
        "wr": "WR",
        "flpm": "FLPM",
        "slpm": "SLPM",
        "mdd": "MDD",
        "add": "ADD",
        "dar": "DaR",
        "cdar": "CDaR",
        "edar": "EDaR",
        "uci": "UCI",
        "mdd_rel": "MDD_Rel",
        "add_rel": "ADD_Rel",
        "dar_rel": "DaR_Rel",
        "cdar_rel": "CDaR_Rel",
        "edar_rel": "EDaR_Rel",
        "uci_rel": "UCI_Rel",
    }
    MEAN_CHOICES = [
        "hist",
        "ewma1",
        "ewma2",
    ]

    CODEPENDENCE_CHOICES = [
        "pearson",
        "spearman",
        "abs_pearson",
        "abs_spearman",
        "distance",
        "mutual_info",
        "tail",
    ]

    COVARIANCE_CHOICES = [
        "hist",
        "ewma1",
        "ewma2",
        "ledoit",
        "oas",
        "shrunk",
        "gl",
        "jlogo",
        "fixed",
        "spectral",
        "shrink",
    ]

    OBJECTIVE_CHOICES = [
        "MinRisk",
        "Utility",
        "Sharpe",
        "MaxRet",
    ]

    NCO_OBJECTIVE_CHOICES = [
        "MinRisk",
        "Utility",
        "Sharpe",
        "ERC",
    ]

    LINKAGE_CHOICES = [
        "single",
        "complete",
        "average",
        "weighted",
        "centroid",
        "median",
        "ward",
        "dbht",
    ]

    BINS_CHOICES = [
        "KN",
        "FD",
        "SC",
        "HGR",
    ]

    FREQ_CHOICES = [
        "d",
        "w",
        "m",
    ]

    METHOD_CHOICES = [
        "linear",
        "time",
        "nearest",
        "zero",
        "slinear",
        "quadratic",
        "cubic",
        "barycentric",
    ]

    PATH = "/portfolio/po/"

    files_available: List = list()

    def __init__(
        self,
        tickers: List[str] = None,
        portfolios: Dict = None,
        categories: Dict = None,
        queue: List[str] = None,
    ):
        """Constructor"""
        super().__init__(queue)
        self.current_model = None

        if tickers:
            self.tickers = list(set(tickers))
            self.tickers.sort()
        else:
            self.tickers = list()

        if portfolios:
            self.portfolios = dict(portfolios)
        else:
            self.portfolios = dict()

        if categories:
            self.categories = dict(categories)
        else:
            self.categories = dict()

        self.count = 0
        self.current_portfolio = ""

        models = [
            "maxsharpe",
            "minrisk",
            "maxutil",
            "maxret",
            "maxdiv",
            "maxdecorr",
            "blacklitterman",
            "ef",
            "riskparity",
            "relriskparity",
            "hrp",
            "herc",
            "nco",
            "equal",
            "mktcap",
            "dividend",
            "property",
        ]
        self.file_types = ["xlsx", "ini"]
        self.DEFAULT_ALLOCATION_PATH = USER_PORTFOLIO_DATA_DIRECTORY / "allocation"

        self.DATA_ALLOCATION_FILES = {
            filepath.name: filepath
            for file_type in self.file_types
            for filepath in self.DEFAULT_ALLOCATION_PATH.rglob(f"*.{file_type}")
        }

        self.DATA_ALLOCATION_FILES.update(
            {
                filepath.name: filepath
                for file_type in self.file_types
                for filepath in (
                    MISCELLANEOUS_DIRECTORY / "portfolio_examples" / "allocation"
                ).rglob(f"*.{file_type}")
            }
        )

        self.current_file = ""
        self.DEFAULT_OPTIMIZATION_PATH = USER_PORTFOLIO_DATA_DIRECTORY / "optimization"

        self.DATA_OPTIMIZATION_FILES = {
            filepath.name: filepath
            for file_type in self.file_types
            for filepath in self.DEFAULT_OPTIMIZATION_PATH.rglob(f"*.{file_type}")
        }

        self.DATA_OPTIMIZATION_FILES.update(
            {
                filepath.name: filepath
                for file_type in self.file_types
                for filepath in (
                    MISCELLANEOUS_DIRECTORY / "portfolio_examples" / "optimization"
                ).rglob(f"*.{file_type}")
            }
        )

        self.params: Dict = {}

        if session and obbff.USE_PROMPT_TOOLKIT:
            self.choices: dict = {c: {} for c in self.controller_choices}
            self.choices["property"]["-p"] = {
                c: None for c in yahoo_finance_model.yf_info_choices
            }
            self.choices["property"]["--property"] = {
                c: None for c in yahoo_finance_model.yf_info_choices
            }
            self.choices["file"]["--file"] = {
                c: {} for c in self.DATA_OPTIMIZATION_FILES
            }
            self.choices["file"]["-f"] = "--file"
            self.choices["load"] = {c: {} for c in self.DATA_ALLOCATION_FILES}
            self.choices["load"]["--file"] = {c: {} for c in self.DATA_ALLOCATION_FILES}
            self.choices["load"]["-f"] = "--file"
            self.choices["plot"]["--portfolios"] = None
            self.choices["plot"]["-pf"] = "--portfolios"
            self.choices["plot"]["--pie"] = None
            self.choices["plot"]["-pi"] = "--pie"
            self.choices["plot"]["--hist"] = None
            self.choices["plot"]["-hi"] = "--hist"
            self.choices["plot"]["--drawdown"] = None
            self.choices["plot"]["-dd"] = "--drawdown"
            self.choices["plot"]["--rc-chart"] = None
            self.choices["plot"]["-rc"] = "--rc-chart"
            self.choices["plot"]["--heat"] = None
            self.choices["plot"]["-he"] = "--heat"
            self.choices["plot"]["--risk-measure"] = {
                c: {} for c in self.MEAN_RISK_CHOICES
            }
            self.choices["plot"]["-rm"] = "--risk-measure"
            self.choices["plot"]["--method"] = {c: {} for c in self.METHOD_CHOICES}
            self.choices["plot"]["-mt"] = "--method"
            self.choices["plot"]["--categories"] = None
            self.choices["plot"]["-ct"] = "--categories"
            self.choices["plot"]["--period"] = {c: {} for c in self.PERIOD_CHOICES}
            self.choices["plot"]["-p"] = "--period"
            self.choices["plot"]["--start"] = None
            self.choices["plot"]["-s"] = "--start"
            self.choices["plot"]["--end"] = None
            self.choices["plot"]["-e"] = "--end"
            self.choices["plot"]["--log-returns"] = None
            self.choices["plot"]["-lr"] = "--log-returns"
            self.choices["plot"]["--freq"] = {c: {} for c in ["d", "w", "m"]}
            self.choices["plot"]["--maxnan"] = None
            self.choices["plot"]["-mn"] = "--maxnan"
            self.choices["plot"]["--threshold"] = None
            self.choices["plot"]["-th"] = "--threshold"
            self.choices["plot"]["--risk-free-rate"] = None
            self.choices["plot"]["-r"] = "--risk-free-rate"
            self.choices["plot"]["--alpha"] = None
            self.choices["plot"]["-a"] = "--alpha"
            self.choices["plot"]["--value"] = None
            self.choices["plot"]["-v"] = "--value"
            self.choices["rpf"]["--portfolios"] = None
            self.choices["rpf"]["--pf"] = "--portfolios"
            for fn in models:
                self.choices[fn]["-p"] = {c: {} for c in self.PERIOD_CHOICES}
                self.choices[fn]["--period"] = {c: {} for c in self.PERIOD_CHOICES}
                self.choices[fn]["--freq"] = {c: {} for c in self.FREQ_CHOICES}
                self.choices[fn]["-mt"] = {c: {} for c in self.METHOD_CHOICES}
                self.choices[fn]["--method"] = {c: {} for c in self.METHOD_CHOICES}
                self.choices[fn]["--name"] = None
                self.choices[fn]["--start"] = None
                self.choices[fn]["-s"] = "--start"
                self.choices[fn]["--end"] = None
                self.choices[fn]["-e"] = "--end"

            for fn in ["maxsharpe", "minrisk", "maxutil", "maxret", "nco", "ef"]:
                self.choices[fn]["-rm"] = {c: {} for c in self.MEAN_RISK_CHOICES}
                self.choices[fn]["--risk-measure"] = {
                    c: {} for c in self.MEAN_RISK_CHOICES
                }

            self.choices["riskparity"]["-rm"] = {
                c: {} for c in self.RISK_PARITY_CHOICES
            }
            self.choices["riskparity"]["--risk-measure"] = {
                c: {} for c in self.RISK_PARITY_CHOICES
            }
            self.choices["relriskparity"]["-ve"] = {
                c: {} for c in self.RISK_PARITY_CHOICES
            }
            self.choices["relriskparity"]["--version"] = {
                c: {} for c in self.RISK_PARITY_CHOICES
            }

            for fn in [
                "maxsharpe",
                "minrisk",
                "maxutil",
                "maxret",
                "riskparity",
                "relriskparity",
            ]:
                self.choices[fn]["-m"] = {c: {} for c in self.MEAN_CHOICES}
                self.choices[fn]["--mean"] = {c: {} for c in self.MEAN_CHOICES}
                self.choices[fn]["-cv"] = {c: {} for c in self.COVARIANCE_CHOICES}
                self.choices[fn]["--covariance"] = {
                    c: {} for c in self.COVARIANCE_CHOICES
                }

            for fn in ["maxdiv", "maxdecorr"]:
                self.choices[fn]["-cv"] = {c: {} for c in self.COVARIANCE_CHOICES}
                self.choices[fn]["--covariance"] = {
                    c: {} for c in self.COVARIANCE_CHOICES
                }

            for fn in ["hrp", "herc"]:
                self.choices[fn]["-rm"] = {c: {} for c in self.HCP_CHOICES}
                self.choices[fn]["--risk-measure"] = {c: {} for c in self.HCP_CHOICES}

            for fn in ["hrp", "herc", "nco"]:
                self.choices[fn]["-cd"] = {c: {} for c in self.CODEPENDENCE_CHOICES}
                self.choices[fn]["--codependence"] = {
                    c: {} for c in self.CODEPENDENCE_CHOICES
                }
                self.choices[fn]["-cv"] = {c: {} for c in self.COVARIANCE_CHOICES}
                self.choices[fn]["--covariance"] = {
                    c: {} for c in self.COVARIANCE_CHOICES
                }
                self.choices[fn]["-lk"] = {c: {} for c in self.LINKAGE_CHOICES}
                self.choices[fn]["--linkage"] = {c: {} for c in self.LINKAGE_CHOICES}
                self.choices[fn]["-bi"] = {c: {} for c in self.BINS_CHOICES}
                self.choices[fn]["--bins-info"] = {c: {} for c in self.BINS_CHOICES}

            self.choices["blacklitterman"]["-o"] = {
                c: {} for c in self.OBJECTIVE_CHOICES
            }
            self.choices["blacklitterman"]["--objective"] = {
                c: {} for c in self.OBJECTIVE_CHOICES
            }
            self.choices["nco"]["-o"] = {c: {} for c in self.NCO_OBJECTIVE_CHOICES}
            self.choices["nco"]["--objective"] = {
                c: {} for c in self.NCO_OBJECTIVE_CHOICES
            }
            self.completer = NestedCompleter.from_nested_dict(self.choices)

    def update_runtime_choices(self):
        if session and obbff.USE_PROMPT_TOOLKIT:
            if self.portfolios:
                self.choices["show"] = {c: {} for c in list(self.portfolios.keys())}

                self.choices = {**self.choices, **self.SUPPORT_CHOICES}
                self.completer = NestedCompleter.from_nested_dict(self.choices)

    def print_help(self):
        """Print help"""
        mt = MenuText("portfolio/po/")
        mt.add_cmd("load")
        mt.add_raw("\n")
        mt.add_param("_loaded", self.current_portfolio or "")
        mt.add_raw("\n")
        mt.add_param("_tickers", ", ".join(self.tickers))
        mt.add_param("_categories", ", ".join(self.categories.keys()))
        mt.add_raw("\n")
        mt.add_cmd("file")
        mt.add_menu("params")
        mt.add_raw("\n")
        mt.add_param("_parameter", self.current_file)
        mt.add_raw("\n")
        mt.add_info("_mean_risk_optimization_")
        mt.add_cmd("maxsharpe", self.tickers)
        mt.add_cmd("minrisk", self.tickers)
        mt.add_cmd("maxutil", self.tickers)
        mt.add_cmd("maxret", self.tickers)
        mt.add_cmd("maxdiv", self.tickers)
        mt.add_cmd("maxdecorr", self.tickers)
        mt.add_cmd("blacklitterman", self.tickers)
        mt.add_cmd("ef", self.tickers)

        mt.add_info("_risk_parity_optimization_")
        mt.add_cmd("riskparity", self.tickers)
        mt.add_cmd("relriskparity", self.tickers)

        mt.add_info("_hierarchical_clustering_models_")
        mt.add_cmd("hrp", self.tickers)
        mt.add_cmd("herc", self.tickers)
        mt.add_cmd("nco", self.tickers)

        mt.add_info("_other_optimization_techniques_")
        mt.add_cmd("equal", self.tickers)
        mt.add_cmd("mktcap", self.tickers)
        mt.add_cmd("dividend", self.tickers)
        mt.add_cmd("property", self.tickers)

        mt.add_raw("\n")
        mt.add_param("_optimized_portfolio", ", ".join(self.portfolios.keys()))
        mt.add_raw("\n")

        mt.add_cmd("rpf", bool(self.portfolios.keys()))
        mt.add_cmd("show", bool(self.portfolios.keys()))
        mt.add_cmd("plot", bool(self.portfolios.keys()))

        console.print(text=mt.menu_text, menu="Portfolio - Portfolio Optimization")

    # pylint: disable=too-many-arguments
    def po_parser(
        self,
        parser,
        rm: bool = False,
        mt: bool = False,
        ct: bool = False,
        p: bool = False,
        s: bool = False,
        e: bool = False,
        lr: bool = False,
        freq: bool = False,
        mn: bool = False,
        th: bool = False,
        r: bool = False,
        a: bool = False,
        v: bool = True,
        name: str = "",
    ):
        """Holds common parser arguments to eliminate repetition"""
        if rm:
            parser.add_argument(
                "-rm",
                "--risk-measure",
                default=self.params["risk_measure"]
                if "risk_measure" in self.params
                else "MV",
                dest="risk_measure",
                help="""Risk measure used to optimize the portfolio. Possible values are:
                        'MV' : Variance
                        'MAD' : Mean Absolute Deviation
                        'MSV' : Semi Variance (Variance of negative returns)
                        'FLPM' : First Lower Partial Moment
                        'SLPM' : Second Lower Partial Moment
                        'CVaR' : Conditional Value at Risk
                        'EVaR' : Entropic Value at Risk
                        'WR' : Worst Realization
                        'ADD' : Average Drawdown of uncompounded returns
                        'UCI' : Ulcer Index of uncompounded returns
                        'CDaR' : Conditional Drawdown at Risk of uncompounded returns
                        'EDaR' : Entropic Drawdown at Risk of uncompounded returns
                        'MDD' : Maximum Drawdown of uncompounded returns
                        """,
                choices=self.MEAN_RISK_CHOICES,
            )
        if mt:
            parser.add_argument(
                "-mt",
                "--method",
                default=self.params["nan_fill_method"]
                if "nan_fill_method" in self.params
                else "time",
                dest="nan_fill_method",
                help="""Method used to fill nan values in time series, by default time.
                        Possible values are:
                        'linear': linear interpolation
                        'time': linear interpolation based on time index
                        'nearest': use nearest value to replace nan values
                        'zero': spline of zeroth order
                        'slinear': spline of first order
                        'quadratic': spline of second order
                        'cubic': spline of third order
                        'barycentric': builds a polynomial that pass for all points""",
            )
        if ct:
            parser.add_argument(
                "-ct",
                "--categories",
                dest="categories",
                type=lambda s: [str(item).upper() for item in s.split(",")],
                default=[],
                help="Show selected categories",
            )
        if p:
            parser.add_argument(
                "-p",
                "--period",
                default=self.params["historic_period"]
                if "historic_period" in self.params
                else "3y",
                dest="historic_period",
                help="""Period to get yfinance data from.
                        Possible frequency strings are:
                        'd': means days, for example '252d' means 252 days
                        'w': means weeks, for example '52w' means 52 weeks
                        'mo': means months, for example '12mo' means 12 months
                        'y': means years, for example '1y' means 1 year
                        'ytd': downloads data from beginning of year to today
                        'max': downloads all data available for each asset""",
            )
        if s:
            parser.add_argument(
                "-s",
                "--start",
                default=self.params["start_period"]
                if "start_period" in self.params
                else "",
                dest="start_period",
                help="""Start date to get yfinance data from. Must be in
                        'YYYY-MM-DD' format""",
            )
        if e:
            parser.add_argument(
                "-e",
                "--end",
                default=self.params["end_period"]
                if "end_period" in self.params
                else "",
                dest="end_period",
                help="""End date to get yfinance data from. Must be in
                        'YYYY-MM-DD' format""",
            )
        if lr:
            parser.add_argument(
                "-lr",
                "--log-returns",
                action="store_true",
                default=self.params["log_returns"]
                if "log_returns" in self.params
                else False,
                dest="log_returns",
                help="If use logarithmic or arithmetic returns to calculate returns",
            )
        if freq:
            parser.add_argument(
                "--freq",
                default=self.params["return_frequency"]
                if "return_frequency" in self.params
                else "d",
                dest="return_frequency",
                help="""Frequency used to calculate returns. Possible values are:
                        'd': for daily returns
                        'w': for weekly returns
                        'm': for monthly returns
                        """,
                choices=self.FREQ_CHOICES,
            )
        if mn:
            parser.add_argument(
                "-mn",
                "--maxnan",
                type=float,
                default=self.params["max_nan"] if "max_nan" in self.params else 0.05,
                dest="max_nan",
                help="""Max percentage of nan values accepted per asset to be
                    considered in the optimization process""",
            )
        if th:
            parser.add_argument(
                "-th",
                "--threshold",
                type=float,
                default=self.params["threshold_value"]
                if "threshold_value" in self.params
                else 0.30,
                dest="threshold_value",
                help="""Value used to replace outliers that are higher to threshold
                        in absolute value""",
            )
        if r:
            parser.add_argument(
                "-r",
                "--risk-free-rate",
                type=float,
                dest="risk_free",
                default=self.params["risk_free"]
                if "risk_free" in self.params
                else get_rf(),
                help="""Risk-free rate of borrowing/lending. The period of the
                    risk-free rate must be annual""",
            )
        if a:
            parser.add_argument(
                "-a",
                "--alpha",
                type=float,
                default=self.params["significance_level"]
                if "significance_level" in self.params
                else 0.05,
                dest="significance_level",
                help="Significance level of CVaR, EVaR, CDaR and EDaR",
            )
        if v:
            parser.add_argument(
                "-v",
                "--value",
                default=self.params["long_allocation"]
                if "long_allocation" in self.params
                else 1,
                type=float,
                dest="long_allocation",
                help="Amount to allocate to portfolio",
            )
        if name:
            parser.add_argument(
                "--name",
                type=str,
                dest="name",
                default=name + str(self.count),
                help="Save portfolio with personalized or default name",
            )
        return parser

    def custom_reset(self):
        """Class specific component of reset command"""
        objects_to_reload = ["portfolio", "po"]
        if self.current_portfolio:
            objects_to_reload.append(f"load {self.current_portfolio}")
        if self.current_file:
            objects_to_reload.append(f"file {self.current_file}")
        return objects_to_reload

    @log_start_end(log=logger)
    def call_file(self, other_args: List[str]):
        """Process file command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="file",
            description="Select parameter file to use",
        )

        parser.add_argument(
            "-f",
            "--file",
            required="-h" not in other_args,
            nargs="+",
            dest="file",
            help="Parameter file to be used",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "--file")

        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser:
            self.current_file = " ".join(ns_parser.file)

            if self.current_file in self.DATA_OPTIMIZATION_FILES:
                file_location = self.DATA_OPTIMIZATION_FILES[self.current_file]
            else:
                file_location = self.current_file  # type: ignore

            self.params, self.current_model = params_view.load_file(file_location)

    @log_start_end(log=logger)
    def call_params(self, _):
        """Process params command"""
        self.queue = self.load_class(
            params_controller.ParametersController,
            self.current_file,
            self.queue,
            self.params,
            self.current_model,
        )
        self.current_file = parent_classes.controllers[
            "/portfolio/po/params/"
        ].current_file
        self.current_model = parent_classes.controllers[
            "/portfolio/po/params/"
        ].current_model
        self.params = parent_classes.controllers["/portfolio/po/params/"].params

    @log_start_end(log=logger)
    def call_show(self, other_args: List[str]):
        """Show saved portfolios"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="show",
            description="""Show selected saved portfolios""",
        )
        parser.add_argument(
            "-pf",
            "--portfolios",
            dest="portfolios",
            type=lambda s: [str(item).upper() for item in s.split(",")],
            default=[],
            help="Show selected saved portfolios",
        )
        if other_args:
            if "-" not in other_args[0]:
                other_args.insert(0, "-pf")

        parser = self.po_parser(parser, ct=True)
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            portfolios = set(self.portfolios.keys())
            if not ns_parser.categories:
                categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
            else:
                categories = ns_parser.categories

            flag = True
            for portfolio in ns_parser.portfolios:
                if portfolio in portfolios:
                    console.print("")
                    console.print("Portfolio - " + portfolio)
                    optimizer_view.display_weights(self.portfolios[portfolio])

                    for category in categories:
                        console.print("")
                        optimizer_view.display_categories(
                            weights=self.portfolios[portfolio],
                            categories=self.categories,
                            column=category,
                            title="Category - " + category.title(),
                        )
                    flag = False

            if flag:
                console.print(
                    f"Current Portfolios: {('None', ', '.join(portfolios))[bool(portfolios)]}"
                )
                console.print(
                    f"\nCurrent Categories: {('None', ', '.join(categories))[bool(categories)]}"
                )

    @log_start_end(log=logger)
    def call_rpf(self, other_args: List[str]):
        """Remove one portfolio"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="rpf",
            description="""Remove one of the portfolios""",
        )
        parser.add_argument(
            "-pf",
            "--portfolios",
            dest="portfolios",
            type=lambda s: [str(item).upper() for item in s.split(",")],
            default=[],
            help="portfolios to be removed from the saved portfolios",
        )
        if other_args:
            if "-" not in other_args[0]:
                other_args.insert(0, "-pf")

        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            portfolios = set(self.portfolios.keys())
            for portfolio in ns_parser.portfolios:
                if portfolio in portfolios:
                    self.portfolios.pop(portfolio)
                    portfolios.remove(portfolio)

            if self.portfolios:
                console.print(
                    f"\nCurrent Portfolios: {('None', ', '.join(portfolios))[bool(portfolios)]}"
                )

            self.update_runtime_choices()

    @log_start_end(log=logger)
    def call_load(self, other_args: List[str]):
        """Load file with stocks tickers and categories"""
        parser = argparse.ArgumentParser(
            add_help=False,
            prog="load",
            description="""Load file of stocks tickers with optional categories""",
        )
        parser.add_argument(
            "-f",
            "--file",
            required="-h" not in other_args,
            nargs="+",
            dest="file",
            help="Allocation file to be used",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "--file")
        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser:
            filename = " ".join(ns_parser.file)

            if filename in self.DATA_ALLOCATION_FILES:
                file_location = self.DATA_ALLOCATION_FILES[filename]
            else:
                file_location = filename  # type: ignore

            self.tickers, self.categories = excel_model.load_allocation(file_location)
            self.portfolios = dict()
            self.update_runtime_choices()
            self.current_portfolio = filename

    @log_start_end(log=logger)
    def call_plot(self, other_args: List[str]):
        """Process plot command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="plot",
            description="Plot selected charts for portfolios",
        )
        parser.add_argument(
            "-pf",
            "--portfolios",
            type=lambda s: [str(item).upper() for item in s.split(",")],
            default=[],
            dest="portfolios",
            help="Selected portfolios that will be plotted",
        )
        parser.add_argument(
            "-pi",
            "--pie",
            action="store_true",
            dest="pie",
            default=False,
            help="Display a pie chart for weights",
        )
        parser.add_argument(
            "-hi",
            "--hist",
            action="store_true",
            dest="hist",
            default=False,
            help="Display a histogram with risk measures",
        )
        parser.add_argument(
            "-dd",
            "--drawdown",
            action="store_true",
            dest="dd",
            default=False,
            help="Display a drawdown chart with risk measures",
        )
        parser.add_argument(
            "-rc",
            "--rc-chart",
            action="store_true",
            dest="rc_chart",
            default=False,
            help="Display a risk contribution chart for assets",
        )
        parser.add_argument(
            "-he",
            "--heat",
            action="store_true",
            dest="heat",
            default=False,
            help="Display a heatmap of correlation matrix with dendrogram",
        )
        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
        )
        if other_args:
            if "-" not in other_args[0]:
                other_args.insert(0, "-pf")

        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            portfolios = ns_parser.portfolios
            stocks = []
            for i in portfolios:
                stocks += list(self.portfolios[i].keys())
            stocks = list(set(stocks))
            stocks.sort()

            _, stock_returns = optimizer_model.get_equal_weights(
                symbols=stocks,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                value=1,
            )

            categories = ns_parser.categories

            for i in portfolios:
                weights = self.portfolios[i]
                weights = dict(
                    sorted(weights.items(), key=lambda x: x[1], reverse=True)
                )
                stocks = list(weights.keys())
                optimizer_view.additional_plots(
                    weights=weights,
                    data=stock_returns[stocks],
                    category=None,
                    title_opt=i,
                    freq=ns_parser.return_frequency,
                    risk_measure=ns_parser.risk_measure.lower(),
                    risk_free_rate=ns_parser.risk_free,
                    alpha=ns_parser.significance_level,
                    a_sim=100,
                    beta=ns_parser.significance_level,
                    b_sim=100,
                    pie=ns_parser.pie,
                    hist=ns_parser.hist,
                    dd=ns_parser.dd,
                    rc_chart=ns_parser.rc_chart,
                    heat=ns_parser.heat,
                    external_axes=None,
                )
                if ns_parser.pie or ns_parser.heat or ns_parser.rc_chart:
                    for category in categories:
                        filtered_categories = dict(
                            filter(
                                lambda elem: elem[0] in stocks,
                                self.categories[category].items(),
                            )
                        )
                        optimizer_view.additional_plots(
                            weights=weights,
                            data=stock_returns[stocks],
                            category=filtered_categories,
                            title_opt=category + " - " + i,
                            freq=ns_parser.return_frequency,
                            risk_measure=ns_parser.risk_measure.lower(),
                            risk_free_rate=ns_parser.risk_free,
                            alpha=ns_parser.significance_level,
                            a_sim=100,
                            beta=ns_parser.significance_level,
                            b_sim=100,
                            pie=ns_parser.pie,
                            hist=ns_parser.hist,
                            dd=ns_parser.dd,
                            rc_chart=ns_parser.rc_chart,
                            heat=ns_parser.heat,
                            external_axes=None,
                        )

    @log_start_end(log=logger)
    def call_equal(self, other_args: List[str]):
        """Process equal command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="equal",
            description="Returns an equally weighted portfolio",
        )
        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="NAME_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            weights = optimizer_view.display_equal_weight(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                value=ns_parser.long_allocation,
                table=True,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

    @log_start_end(log=logger)
    def call_mktcap(self, other_args: List[str]):
        """Process mktcap command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="mktcap",
            description="Returns a portfolio that is weighted based on Market Cap.",
        )
        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="MKTCAP_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 stocks selected to perform calculations."
                )
                return

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_property_weighting(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                s_property="marketCap",
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                value=ns_parser.long_allocation,
                table=True,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

    @log_start_end(log=logger)
    def call_dividend(self, other_args: List[str]):
        """Process dividend command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="dividend",
            description="Returns a portfolio that is weighted based dividend yield.",
        )
        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="DIVIDEND_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 stocks selected to perform calculations."
                )
                return

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_property_weighting(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                s_property="dividendYield",
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                value=ns_parser.long_allocation,
                table=True,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

    @log_start_end(log=logger)
    def call_property(self, other_args: List[str]):
        """Process property command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="property",
            description="Returns a portfolio that is weighted based on selected property.",
        )
        parser.add_argument(
            "-pr",
            "--property",
            required=bool("-h" not in other_args),
            type=optimizer_helper.check_valid_property_type,
            dest="s_property",
            choices=yahoo_finance_model.yf_info_choices,
            help="""Property info to weight. Use one of yfinance info options.""",
        )
        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="PROPERTY_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 stocks selected to perform calculations."
                )
                return

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_property_weighting(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                s_property=ns_parser.s_property,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                value=ns_parser.long_allocation,
                table=True,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

    @log_start_end(log=logger)
    def call_maxsharpe(self, other_args: List[str]):
        """Process maxsharpe command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="maxsharpe",
            description="Maximizes the portfolio's return/risk ratio",
        )
        parser.add_argument(
            "-tr",
            "--target-return",
            dest="target_return",
            default=self.params["target_return"]
            if "target_return" in self.params
            else -1,
            type=int,
            help="Constraint on minimum level of portfolio's return",
        )
        parser.add_argument(
            "-tk",
            "--target-risk",
            dest="target_risk",
            default=self.params["target_risk"] if "target_risk" in self.params else -1,
            help="Constraint on maximum level of portfolio's risk",
        )
        parser.add_argument(
            "-m",
            "--mean",
            default=self.params["expected_return"]
            if "expected_return" in self.params
            else "hist",
            dest="expected_return",
            help="Method used to estimate the expected return vector",
            choices=self.MEAN_CHOICES,
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["expected_return"]
            if "expected_return" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="MAXSHARPE_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_max_sharpe(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                target_return=ns_parser.target_return,
                target_risk=ns_parser.target_risk,
                mean=ns_parser.expected_return.lower(),
                covariance=ns_parser.covariance.lower(),
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_max_sharpe(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    alpha=ns_parser.significance_level_sa,
                    target_return=ns_parser.target_return_sa,
                    target_risk=ns_parser.target_risk_sa,
                    mean=ns_parser.expected_return_sa.lower(),
                    covariance=ns_parser.covariance_sa.lower(),
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    value_short=ns_parser.short_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_minrisk(self, other_args: List[str]):
        """Process minrisk command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="minrisk",
            description="Minimizes portfolio's risk",
        )
        parser.add_argument(
            "-tr",
            "--target-return",
            dest="target_return",
            default=self.params["target_return"]
            if "target_return" in self.params
            else -1,
            help="Constraint on minimum level of portfolio's return",
        )
        parser.add_argument(
            "-tk",
            "--target-risk",
            dest="target_risk",
            default=self.params["target_risk"] if "target_risk" in self.params else -1,
            help="Constraint on maximum level of portfolio's risk",
        )
        parser.add_argument(
            "-m",
            "--mean",
            default=self.params["expected_return"]
            if "expected_return" in self.params
            else "hist",
            dest="expected_return",
            help="Method used to estimate expected returns vector",
            choices=self.MEAN_CHOICES,
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"] if "mean_ewma" in self.params else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="MINRISK_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_min_risk(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                target_return=ns_parser.target_return,
                target_risk=ns_parser.target_risk,
                mean=ns_parser.expected_return.lower(),
                covariance=ns_parser.covariance.lower(),
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_min_risk(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    alpha=ns_parser.significance_level_sa,
                    target_return=ns_parser.target_return_sa,
                    target_risk=ns_parser.target_risk_sa,
                    mean=ns_parser.expected_return_sa.lower(),
                    covariance=ns_parser.covariance_sa.lower(),
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    value_short=ns_parser.short_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_maxutil(self, other_args: List[str]):
        """Process maxutil command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="maxutil",
            description="Maximizes a risk averse utility function",
        )
        parser.add_argument(
            "-ra",
            "--risk-aversion",
            type=float,
            dest="risk_aversion",
            default=self.params["long_allocation"]
            if "long_allocation" in self.params
            else 1,
            help="Risk aversion parameter",
        )
        parser.add_argument(
            "-tr",
            "--target-return",
            dest="target_return",
            default=self.params["target_return"]
            if "target_return" in self.params
            else -1,
            help="Constraint on minimum level of portfolio's return",
        )
        parser.add_argument(
            "-tk",
            "--target-risk",
            dest="target_risk",
            default=self.params["target_risk"] if "target_risk" in self.params else -1,
            help="Constraint on maximum level of portfolio's risk",
        )
        parser.add_argument(
            "-m",
            "--mean",
            default=self.params["expected_return"]
            if "expected_return" in self.params
            else "hist",
            dest="expected_return",
            help="Method used to estimate the expected return vector",
            choices=self.MEAN_CHOICES,
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"]
            if "covariance" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="MAXUTIL_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_max_util(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                risk_aversion=ns_parser.risk_aversion,
                alpha=ns_parser.significance_level,
                target_return=ns_parser.target_return,
                target_risk=ns_parser.target_risk,
                mean=ns_parser.expected_return.lower(),
                covariance=ns_parser.covariance.lower(),
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_max_util(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    risk_aversion=ns_parser.risk_aversion_sa,
                    alpha=ns_parser.significance_level_sa,
                    target_return=ns_parser.target_return_sa,
                    target_risk=ns_parser.target_risk_sa,
                    mean=ns_parser.expected_return_sa.lower(),
                    covariance=ns_parser.covariance_sa.lower(),
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    value_short=ns_parser.short_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_maxret(self, other_args: List[str]):
        """Process maxret command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="maxret",
            description="Maximizes the portfolio's return ",
        )
        parser.add_argument(
            "-tr",
            "--target-return",
            dest="target_return",
            default=self.params["target_return"]
            if "target_return" in self.params
            else -1,
            help="Constraint on minimum level of portfolio's return",
        )
        parser.add_argument(
            "-tk",
            "--target-risk",
            dest="target_risk",
            default=self.params["target_risk"] if "target_risk" in self.params else -1,
            help="Constraint on maximum level of portfolio's risk",
        )
        parser.add_argument(
            "-m",
            "--mean",
            default=self.params["expected_return"]
            if "expected_return" in self.params
            else "hist",
            dest="expected_return",
            help="Method used to estimate the expected return vector",
            choices=self.MEAN_CHOICES,
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"]
            if "covariance" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="MAXRET_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_max_ret(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                target_return=ns_parser.target_return,
                target_risk=ns_parser.target_risk,
                mean=ns_parser.expected_return.lower(),
                covariance=ns_parser.covariance.lower(),
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_max_ret(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    alpha=ns_parser.significance_level_sa,
                    target_return=ns_parser.target_return_sa,
                    target_risk=ns_parser.target_risk_sa,
                    mean=ns_parser.expected_return_sa.lower(),
                    covariance=ns_parser.covariance_sa.lower(),
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    value_short=ns_parser.short_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_maxdiv(self, other_args: List[str]):
        """Process maxdiv command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="maxdiv",
            description="Maximizes the portfolio's diversification ratio",
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"]
            if "covariance" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            v=True,
            name="MAXDIV_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_max_div(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                covariance=ns_parser.covariance.lower(),
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_max_div(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    covariance=ns_parser.covariance_sa.lower(),
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    value_short=ns_parser.short_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_maxdecorr(self, other_args: List[str]):
        """Process maxdecorr command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="maxdecorr",
            description="Maximizes the portfolio's decorrelation",
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"]
            if "covariance" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            v=True,
            name="MAXDECORR_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_max_decorr(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                covariance=ns_parser.covariance.lower(),
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_max_decorr(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    covariance=ns_parser.covariance_sa.lower(),
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    value_short=ns_parser.short_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_blacklitterman(self, other_args: List[str]):
        """Process blacklitterman command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="blacklitterman",
            description="Optimize portfolio using Black Litterman estimates",
        )
        parser.add_argument(
            "-bm",
            "--benchmark",
            type=str,
            default=None,
            dest="benchmark",
            help="portfolio name from current portfolio list",
        )
        parser.add_argument(
            "-o",
            "--objective",
            default=self.params["objective"]
            if "objective" in self.params
            else "Sharpe",
            dest="objective",
            help="Objective function used to optimize the portfolio",
            choices=self.OBJECTIVE_CHOICES,
        )
        parser.add_argument(
            "-pv",
            "--p-views",
            type=lambda s: [
                [float(item) for item in row.split(",")] for row in s.split(";")
            ],
            default=self.params["p_views"] if "p_views" in self.params else None,
            dest="p_views",
            help="matrix P of analyst views",
        )
        parser.add_argument(
            "-qv",
            "--q-views",
            type=lambda s: [float(item) for item in s.split(",")],
            default=self.params["q_views"] if "q_views" in self.params else None,
            dest="q_views",
            help="matrix Q of analyst views",
        )
        parser.add_argument(
            "-ra",
            "--risk-aversion",
            type=float,
            dest="risk_aversion",
            default=self.params["long_allocation"]
            if "long_allocation" in self.params
            else 1,
            help="Risk aversion parameter",
        )
        parser.add_argument(
            "-d",
            "--delta",
            default=self.params["delta"] if "delta" in self.params else None,
            dest="delta",
            help="Risk aversion factor of Black Litterman model",
        )
        parser.add_argument(
            "-eq",
            "--equilibrium",
            action="store_true",
            default=self.params["equilibrium"]
            if "equilibrium" in self.params
            else True,
            dest="equilibrium",
            help="""If True excess returns are based on equilibrium market portfolio, if False
                excess returns are calculated as historical returns minus risk free rate.
                """,
        )
        parser.add_argument(
            "-op",
            "--optimize",
            action="store_false",
            default=self.params["optimize"] if "optimize" in self.params else True,
            dest="optimize",
            help="""If True Black Litterman estimates are used as inputs of mean variance model,
                if False returns equilibrium weights from Black Litterman model
                """,
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
        )
        parser.add_argument(
            "--file",
            type=lambda s: s if s.endswith(".xlsx") or len(s) == 0 else s + ".xlsx",
            dest="file",
            default="",
            help="Upload an Excel file with views for Black Litterman model",
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name", "benchmark"])

        parser.add_argument(
            "--download",
            type=lambda s: s if s.endswith(".xlsx") or len(s) == 0 else s + ".xlsx",
            dest="download",
            default="",
            help="Create a template to design Black Litterman model views",
        )
        parser = self.po_parser(
            parser,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            v=True,
            name="BL_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            if len(ns_parser.download) > 0:
                file = (
                    USER_EXPORTS_DIRECTORY / "portfolio" / "views" / ns_parser.download
                )

                excel_model.excel_bl_views(file=file, stocks=self.tickers, n=1)
                return

            if ns_parser.file:
                excel_file = USER_PORTFOLIO_DATA_DIRECTORY / "views" / ns_parser.file
                p_views, q_views = excel_model.load_bl_views(excel_file=excel_file)
            else:
                p_views = ns_parser.p_views
                q_views = ns_parser.q_views

            if ns_parser.benchmark is None:
                benchmark = None
            else:
                benchmark = self.portfolios[ns_parser.benchmark.upper()]

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_black_litterman(
                symbols=self.tickers,
                p_views=p_views,
                q_views=q_views,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                benchmark=benchmark,
                objective=ns_parser.objective.lower(),
                risk_free_rate=ns_parser.risk_free,
                risk_aversion=ns_parser.risk_aversion,
                delta=ns_parser.delta,
                equilibrium=ns_parser.equilibrium,
                optimize=ns_parser.optimize,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                if ns_parser.file_sa:
                    excel_file = (
                        USER_PORTFOLIO_DATA_DIRECTORY / "views" / ns_parser.file_sa
                    )
                    p_views_sa, q_views_sa = excel_model.load_bl_views(
                        excel_file=excel_file
                    )
                else:
                    p_views_sa = ns_parser.p_views_sa
                    q_views_sa = ns_parser.q_views_sa

                weights_sa = optimizer_view.display_black_litterman(
                    symbols=self.tickers,
                    p_views=p_views_sa,
                    q_views=q_views_sa,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    benchmark=benchmark,
                    objective=ns_parser.objective_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    risk_aversion=ns_parser.risk_aversion_sa,
                    delta=ns_parser.delta_sa,
                    equilibrium=ns_parser.equilibrium_sa,
                    optimize=ns_parser.optimize_sa,
                    value=ns_parser.long_allocation_sa,
                    value_short=ns_parser.short_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_ef(self, other_args):
        """Process ef command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="ef",
            description="""This function plots random portfolios based on their
                risk and returns and shows the efficient frontier.""",
        )
        parser.add_argument(
            "-vs",
            "--value-short",
            dest="short_allocation",
            help="Amount to allocate to portfolio in short positions",
            type=float,
            default=self.params["short_allocation"]
            if "short_allocation" in self.params
            else 0.0,
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-n")
        parser.add_argument(
            "-n",
            "--number-portfolios",
            default=self.params["amount_portfolios"]
            if "amount_portfolios" in self.params
            else 100,
            type=check_non_negative,
            dest="amount_portfolios",
            help="Number of portfolios to simulate",
        )
        parser.add_argument(
            "-se",
            "--seed",
            default=self.params["random_seed"] if "random_seed" in self.params else 123,
            type=check_non_negative,
            dest="random_seed",
            help="Seed used to generate random portfolios",
        )
        parser.add_argument(
            "-t",
            "--tangency",
            action="store_true",
            dest="tangency",
            default=self.params["tangency"] if "tangency" in self.params else False,
            help="Adds the optimal line with the risk-free asset",
        )
        parser.add_argument(
            "--no_plot",
            action="store_false",
            dest="plot_tickers",
            default=True,
            help="Whether or not to plot the tickers for the assets provided",
        )
        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)

        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            optimizer_view.display_ef(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                value=ns_parser.long_allocation,
                value_short=ns_parser.short_allocation,
                n_portfolios=ns_parser.amount_portfolios,
                seed=ns_parser.random_seed,
                tangency=ns_parser.tangency,
                plot_tickers=ns_parser.plot_tickers,
            )

    @log_start_end(log=logger)
    def call_riskparity(self, other_args: List[str]):
        """Process riskparity command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="riskparity",
            description="""Build a risk parity portfolio based on risk
                budgeting approach""",
        )
        parser.add_argument(
            "-rm",
            "--risk-measure",
            default=self.params["risk_measure"]
            if "risk_measure" in self.params
            else "MV",
            dest="risk_measure",
            help="""Risk measure used to optimize the portfolio. Possible values are:
                    'MV' : Variance
                    'MAD' : Mean Absolute Deviation
                    'MSV' : Semi Variance (Variance of negative returns)
                    'FLPM' : First Lower Partial Moment
                    'SLPM' : Second Lower Partial Moment
                    'CVaR' : Conditional Value at Risk
                    'EVaR' : Entropic Value at Risk
                    'UCI' : Ulcer Index of uncompounded returns
                    'CDaR' : Conditional Drawdown at Risk of uncompounded returns
                    'EDaR' : Entropic Drawdown at Risk of uncompounded returns
                    """,
            choices=self.RISK_PARITY_CHOICES,
        )
        parser.add_argument(
            "-rc",
            "--risk-cont",
            type=lambda s: [float(item) for item in s.split(",")],
            default=self.params["risk_contribution"]
            if "risk_contribution" in self.params
            else None,
            dest="risk_contribution",
            help="vector of risk contribution constraint",
        )
        parser.add_argument(
            "-tr",
            "--target-return",
            dest="target_return",
            default=self.params["target_return"]
            if "target_return" in self.params
            else -1,
            help="Constraint on minimum level of portfolio's return",
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="RP_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_risk_parity(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                risk_measure=ns_parser.risk_measure.lower(),
                risk_cont=ns_parser.risk_contribution,
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                target_return=ns_parser.target_return,
                value=ns_parser.long_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_risk_parity(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_cont=ns_parser.risk_contribution_sa,
                    risk_free_rate=ns_parser.risk_free_sa,
                    alpha=ns_parser.significance_level_sa,
                    target_return=ns_parser.target_return_sa,
                    value=ns_parser.long_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_relriskparity(self, other_args: List[str]):
        """Process relriskparity command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="relriskparity",
            description="""Build a relaxed risk parity portfolio based on
                least squares approach""",
        )
        parser.add_argument(
            "-ve",
            "--version",
            default=self.params["risk_parity_model"]
            if "risk_parity_model" in self.params
            else "A",
            dest="risk_parity_model",
            help="""version of relaxed risk parity model: Possible values are:
                'A': risk parity without regularization and penalization constraints
                'B': with regularization constraint but without penalization constraint
                'C': with regularization and penalization constraints""",
            choices=self.REL_RISK_PARITY_CHOICES,
        )
        parser.add_argument(
            "-rc",
            "--risk-cont",
            type=lambda s: [float(item) for item in s.split(",")],
            default=self.params["risk_contribution"]
            if "risk_contribution" in self.params
            else None,
            dest="risk_contribution",
            help="Vector of risk contribution constraints",
        )
        parser.add_argument(
            "-pf",
            "--penal-factor",
            type=float,
            dest="penal_factor",
            default=self.params["penal_factor"] if "penal_factor" in self.params else 1,
            help="""The penalization factor of penalization constraints. Only
            used with version 'C'.""",
        )
        parser.add_argument(
            "-tr",
            "--target-return",
            dest="target_return",
            default=self.params["target_return"]
            if "target_return" in self.params
            else -1,
            help="Constraint on minimum level of portfolio's return",
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            v=True,
            name="RRP_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_rel_risk_parity(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                version=ns_parser.risk_parity_model,
                risk_cont=ns_parser.risk_contribution,
                penal_factor=ns_parser.penal_factor,
                target_return=ns_parser.target_return,
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_rel_risk_parity(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    version=ns_parser.risk_parity_model_sa,
                    risk_cont=ns_parser.risk_contribution_sa,
                    penal_factor=ns_parser.penal_factor_sa,
                    target_return=ns_parser.target_return_sa,
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_hrp(self, other_args: List[str]):
        """Process hierarchical risk parity command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="hrp",
            description="Builds a hierarchical risk parity portfolio",
        )
        parser.add_argument(
            "-cd",
            "--codependence",
            default=self.params["co_dependence"]
            if "co_dependence" in self.params
            else "pearson",
            dest="co_dependence",
            help="""The codependence or similarity matrix used to build the
                distance metric and clusters. Possible values are:
                'pearson': pearson correlation matrix
                'spearman': spearman correlation matrix
                'abs_pearson': absolute value of pearson correlation matrix
                'abs_spearman': absolute value of spearman correlation matrix
                'distance': distance correlation matrix
                'mutual_info': mutual information codependence matrix
                'tail': tail index codependence matrix""",
            choices=self.CODEPENDENCE_CHOICES,
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"]
            if "covariance" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-rm",
            "--risk-measure",
            default=self.params["risk_measure"]
            if "risk_measure" in self.params
            else "MV",
            dest="risk_measure",
            help="""Risk measure used to optimize the portfolio. Possible values are:
                    'MV' : Variance
                    'MAD' : Mean Absolute Deviation
                    'GMD' : Gini Mean Difference
                    'MSV' : Semi Variance (Variance of negative returns)
                    'FLPM' : First Lower Partial Moment
                    'SLPM' : Second Lower Partial Moment
                    'VaR' : Value at Risk
                    'CVaR' : Conditional Value at Risk
                    'TG' : Tail Gini
                    'EVaR' : Entropic Value at Risk
                    'WR' : Worst Realization
                    'RG' : Range
                    'CVRG' : CVaR Range
                    'TGRG' : Tail Gini Range
                    'ADD' : Average Drawdown of uncompounded returns
                    'UCI' : Ulcer Index of uncompounded returns
                    'DaR' : Drawdown at Risk of uncompounded returns
                    'CDaR' : Conditional Drawdown at Risk of uncompounded returns
                    'EDaR' : Entropic Drawdown at Risk of uncompounded returns
                    'MDD' : Maximum Drawdown of uncompounded returns
                    'ADD_Rel' : Average Drawdown of compounded returns
                    'UCI_Rel' : Ulcer Index of compounded returns
                    'DaR_Rel' : Drawdown at Risk of compounded returns
                    'CDaR_Rel' : Conditional Drawdown at Risk of compounded returns
                    'EDaR_Rel' : Entropic Drawdown at Risk of compounded returns
                    'MDD_Rel' : Maximum Drawdown of compounded returns
                    """,
            choices=self.HCP_CHOICES,
        )
        parser.add_argument(
            "-as",
            "--a-sim",
            type=int,
            default=self.params["cvar_simulations_losses"]
            if "cvar_simulations_losses" in self.params
            else 100,
            dest="cvar_simulations_losses",
            help="""Number of CVaRs used to approximate Tail Gini of losses.
                The default is 100""",
        )
        parser.add_argument(
            "-b",
            "--beta",
            type=float,
            default=self.params["cvar_significance"]
            if "cvar_significance" in self.params
            else None,
            dest="cvar_significance",
            help="""Significance level of CVaR and Tail Gini of gains. If
                empty it duplicates alpha""",
        )
        parser.add_argument(
            "-bs",
            "--b-sim",
            type=int,
            default=self.params["cvar_simulations_gains"]
            if "cvar_simulations_gains" in self.params
            else None,
            dest="cvar_simulations_gains",
            help="""Number of CVaRs used to approximate Tail Gini of gains.
                If empty it duplicates a_sim value""",
        )
        parser.add_argument(
            "-lk",
            "--linkage",
            default=self.params["linkage"] if "linkage" in self.params else "single",
            dest="linkage",
            help="Linkage method of hierarchical clustering",
            choices=self.LINKAGE_CHOICES,
        )
        parser.add_argument(
            "-k",
            type=int,
            default=self.params["amount_clusters"]
            if "amount_clusters" in self.params
            else None,
            dest="amount_clusters",
            help="Number of clusters specified in advance",
        )
        parser.add_argument(
            "-mk",
            "--max-k",
            type=int,
            default=self.params["max_clusters"]
            if "max_clusters" in self.params
            else 10,
            dest="max_clusters",
            help="""Max number of clusters used by the two difference gap
            statistic to find the optimal number of clusters. If k is
            empty this value is used""",
        )
        parser.add_argument(
            "-bi",
            "--bins-info",
            default=self.params["amount_bins"]
            if "amount_bins" in self.params
            else "KN",
            dest="amount_bins",
            help="Number of bins used to calculate the variation of information",
        )
        parser.add_argument(
            "-at",
            "--alpha-tail",
            type=float,
            default=self.params["alpha_tail"] if "alpha_tail" in self.params else 0.05,
            dest="alpha_tail",
            help="""Significance level for lower tail dependence index, only
            used when when codependence value is 'tail' """,
        )
        parser.add_argument(
            "-lo",
            "--leaf-order",
            default=self.params["leaf_order"] if "leaf_order" in self.params else True,
            dest="leaf_order",
            help="""Indicates if the cluster are ordered so that the distance
                between successive leaves is minimal""",
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="_HRP",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_hrp(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                codependence=ns_parser.co_dependence.lower(),
                covariance=ns_parser.covariance.lower(),
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                a_sim=ns_parser.cvar_simulations_losses,
                beta=ns_parser.cvar_significance,
                b_sim=ns_parser.cvar_simulations_gains,
                linkage=ns_parser.linkage.lower(),
                k=ns_parser.amount_clusters,
                max_k=ns_parser.max_clusters,
                bins_info=ns_parser.amount_bins.upper(),
                alpha_tail=ns_parser.alpha_tail,
                leaf_order=ns_parser.leaf_order,
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_hrp(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    codependence=ns_parser.co_dependence_sa.lower(),
                    covariance=ns_parser.covariance_sa.lower(),
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    alpha=ns_parser.significance_level_sa,
                    a_sim=ns_parser.cvar_simulations_losses_sa,
                    beta=ns_parser.cvar_significance_sa,
                    b_sim=ns_parser.cvar_simulations_gains_sa,
                    linkage=ns_parser.linkage_sa.lower(),
                    k=ns_parser.amount_clusters_sa,
                    max_k=ns_parser.max_clusters_sa,
                    bins_info=ns_parser.amount_bins_sa.upper(),
                    alpha_tail=ns_parser.alpha_tail_sa,
                    leaf_order=ns_parser.leaf_order_sa,
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_herc(self, other_args: List[str]):
        """Process hierarchical equal risk contribution command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="herc",
            description="Builds a hierarchical equal risk contribution portfolio",
        )
        parser.add_argument(
            "-cd",
            "--codependence",
            default="pearson",
            dest="co_dependence",
            help="""The codependence or similarity matrix used to build the
                distance metric and clusters. Possible values are:
                'pearson': pearson correlation matrix
                'spearman': spearman correlation matrix
                'abs_pearson': absolute value of pearson correlation matrix
                'abs_spearman': absolute value of spearman correlation matrix
                'distance': distance correlation matrix
                'mutual_info': mutual information codependence matrix
                'tail': tail index codependence matrix""",
            choices=self.CODEPENDENCE_CHOICES,
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"]
            if "covariance" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-rm",
            "--risk-measure",
            default=self.params["risk_measure"]
            if "risk_measure" in self.params
            else "MV",
            dest="risk_measure",
            help="""Risk measure used to optimize the portfolio. Possible values are:
                    'MV' : Variance
                    'MAD' : Mean Absolute Deviation
                    'GMD' : Gini Mean Difference
                    'MSV' : Semi Variance (Variance of negative returns)
                    'FLPM' : First Lower Partial Moment
                    'SLPM' : Second Lower Partial Moment
                    'VaR' : Value at Risk
                    'CVaR' : Conditional Value at Risk
                    'TG' : Tail Gini
                    'EVaR' : Entropic Value at Risk
                    'WR' : Worst Realization
                    'RG' : Range
                    'CVRG' : CVaR Range
                    'TGRG' : Tail Gini Range
                    'ADD' : Average Drawdown of uncompounded returns
                    'UCI' : Ulcer Index of uncompounded returns
                    'DaR' : Drawdown at Risk of uncompounded returns
                    'CDaR' : Conditional Drawdown at Risk of uncompounded returns
                    'EDaR' : Entropic Drawdown at Risk of uncompounded returns
                    'MDD' : Maximum Drawdown of uncompounded returns
                    'ADD_Rel' : Average Drawdown of compounded returns
                    'UCI_Rel' : Ulcer Index of compounded returns
                    'DaR_Rel' : Drawdown at Risk of compounded returns
                    'CDaR_Rel' : Conditional Drawdown at Risk of compounded returns
                    'EDaR_Rel' : Entropic Drawdown at Risk of compounded returns
                    'MDD_Rel' : Maximum Drawdown of compounded returns
                    """,
            choices=self.HCP_CHOICES,
        )
        parser.add_argument(
            "-as",
            "--a-sim",
            type=int,
            default=self.params["cvar_simulations_losses"]
            if "cvar_simulations_losses" in self.params
            else 100,
            dest="cvar_simulations_losses",
            help="""Number of CVaRs used to approximate Tail Gini of losses.
                The default is 100""",
        )
        parser.add_argument(
            "-b",
            "--beta",
            type=float,
            default=self.params["cvar_significance"]
            if "cvar_significance" in self.params
            else None,
            dest="cvar_significance",
            help="""Significance level of CVaR and Tail Gini of gains. If
                empty it duplicates alpha""",
        )
        parser.add_argument(
            "-bs",
            "--b-sim",
            type=int,
            default=self.params["cvar_simulations_gains"]
            if "cvar_simulations_gains" in self.params
            else None,
            dest="cvar_simulations_gains",
            help="""Number of CVaRs used to approximate Tail Gini of gains.
                If empty it duplicates a_sim value""",
        )
        parser.add_argument(
            "-lk",
            "--linkage",
            default=self.params["linkage"] if "linkage" in self.params else "single",
            dest="linkage",
            help="Linkage method of hierarchical clustering",
            choices=self.LINKAGE_CHOICES,
        )
        parser.add_argument(
            "-k",
            type=int,
            default=self.params["amount_clusters"]
            if "amount_clusters" in self.params
            else None,
            dest="amount_clusters",
            help="Number of clusters specified in advance",
        )
        parser.add_argument(
            "-mk",
            "--max-k",
            type=int,
            default=self.params["max_clusters"]
            if "max_clusters" in self.params
            else 10,
            dest="max_clusters",
            help="""Max number of clusters used by the two difference gap
            statistic to find the optimal number of clusters. If k is
            empty this value is used""",
        )
        parser.add_argument(
            "-bi",
            "--bins-info",
            default=self.params["amount_bins"]
            if "amount_bins" in self.params
            else "KN",
            dest="amount_bins",
            help="Number of bins used to calculate the variation of information",
        )
        parser.add_argument(
            "-at",
            "--alpha-tail",
            type=float,
            default=self.params["alpha_tail"] if "alpha_tail" in self.params else 0.05,
            dest="alpha_tail",
            help="""Significance level for lower tail dependence index, only
            used when when codependence value is 'tail' """,
        )
        parser.add_argument(
            "-lo",
            "--leaf-order",
            default=self.params["leaf_order"] if "leaf_order" in self.params else True,
            dest="leaf_order",
            help="""Indicates if the cluster are ordered so that the distance
                between successive leaves is minimal""",
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="HERC_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_herc(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                codependence=ns_parser.co_dependence.lower(),
                covariance=ns_parser.covariance.lower(),
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                alpha=ns_parser.significance_level,
                a_sim=ns_parser.cvar_simulations_losses,
                beta=ns_parser.cvar_significance,
                b_sim=ns_parser.cvar_simulations_gains,
                linkage=ns_parser.linkage.lower(),
                k=ns_parser.amount_clusters,
                max_k=ns_parser.max_clusters,
                bins_info=ns_parser.amount_bins.upper(),
                alpha_tail=ns_parser.alpha_tail,
                leaf_order=ns_parser.leaf_order,
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_herc(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    codependence=ns_parser.co_dependence_sa.lower(),
                    covariance=ns_parser.covariance_sa.lower(),
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    alpha=ns_parser.significance_level_sa,
                    a_sim=ns_parser.cvar_simulations_losses_sa,
                    beta=ns_parser.cvar_significance_sa,
                    b_sim=ns_parser.cvar_simulations_gains_sa,
                    linkage=ns_parser.linkage_sa.lower(),
                    k=ns_parser.amount_clusters_sa,
                    max_k=ns_parser.max_clusters_sa,
                    bins_info=ns_parser.amount_bins_sa.upper(),
                    alpha_tail=ns_parser.alpha_tail_sa,
                    leaf_order=ns_parser.leaf_order_sa,
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )

    @log_start_end(log=logger)
    def call_nco(self, other_args: List[str]):
        """Process nested clustered optimization command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="nco",
            description="Builds a nested clustered optimization portfolio",
        )
        parser.add_argument(
            "-cd",
            "--codependence",
            default=self.params["co_dependence"]
            if "co_dependence" in self.params
            else "pearson",
            dest="co_dependence",
            help="""The codependence or similarity matrix used to build the
                distance metric and clusters. Possible values are:
                'pearson': pearson correlation matrix
                'spearman': spearman correlation matrix
                'abs_pearson': absolute value of pearson correlation matrix
                'abs_spearman': absolute value of spearman correlation matrix
                'distance': distance correlation matrix
                'mutual_info': mutual information codependence matrix
                'tail': tail index codependence matrix""",
            choices=self.CODEPENDENCE_CHOICES,
        )
        parser.add_argument(
            "-cv",
            "--covariance",
            default=self.params["covariance"]
            if "covariance" in self.params
            else "hist",
            dest="covariance",
            help="""Method used to estimate covariance matrix. Possible values are
                    'hist': historical method
                    'ewma1': exponential weighted moving average with adjust=True
                    'ewma2': exponential weighted moving average with adjust=False
                    'ledoit': Ledoit and Wolf shrinkage method
                    'oas': oracle shrinkage method
                    'shrunk': scikit-learn shrunk method
                    'gl': graphical lasso method
                    'jlogo': j-logo covariance
                    'fixed': takes average of eigenvalues above max Marchenko Pastour limit
                    'spectral':  makes zero eigenvalues above max Marchenko Pastour limit
                    'shrink': Lopez de Prado's book shrinkage method
                    """,
            choices=self.COVARIANCE_CHOICES,
        )
        parser.add_argument(
            "-o",
            "--objective",
            default=self.params["objective"]
            if "objective" in self.params
            else "MinRisk",
            dest="objective",
            help="Objective function used to optimize the portfolio",
            choices=self.NCO_OBJECTIVE_CHOICES,
        )
        parser.add_argument(
            "-ra",
            "--risk-aversion",
            type=float,
            dest="risk_aversion",
            default=self.params["long_allocation"]
            if "long_allocation" in self.params
            else 1,
            help="Risk aversion parameter",
        )
        parser.add_argument(
            "-lk",
            "--linkage",
            default=self.params["linkage"] if "linkage" in self.params else "single",
            dest="linkage",
            help="Linkage method of hierarchical clustering",
            choices=self.LINKAGE_CHOICES,
        )
        parser.add_argument(
            "-k",
            type=int,
            default=self.params["amount_clusters"]
            if "amount_clusters" in self.params
            else None,
            dest="amount_clusters",
            help="Number of clusters specified in advance",
        )
        parser.add_argument(
            "-mk",
            "--max-k",
            type=int,
            default=self.params["max_clusters"]
            if "max_clusters" in self.params
            else 10,
            dest="max_clusters",
            help="""Max number of clusters used by the two difference gap
            statistic to find the optimal number of clusters. If k is
            empty this value is used""",
        )
        parser.add_argument(
            "-bi",
            "--bins-info",
            default=self.params["amount_bins"]
            if "amount_bins" in self.params
            else "KN",
            dest="amount_bins",
            help="Number of bins used to calculate the variation of information",
        )
        parser.add_argument(
            "-at",
            "--alpha-tail",
            type=float,
            default=self.params["alpha_tail"] if "alpha_tail" in self.params else 0.05,
            dest="alpha_tail",
            help="""Significance level for lower tail dependence index, only
            used when when codependence value is 'tail' """,
        )
        parser.add_argument(
            "-lo",
            "--leaf-order",
            action="store_true",
            default=self.params["leaf_order"] if "leaf_order" in self.params else True,
            dest="leaf_order",
            help="""indicates if the cluster are ordered so that the distance
                between successive leaves is minimal""",
        )
        parser.add_argument(
            "-de",
            "--d-ewma",
            type=float,
            default=self.params["smoothing_factor_ewma"]
            if "smoothing_factor_ewma" in self.params
            else 0.94,
            dest="smoothing_factor_ewma",
            help="Smoothing factor for ewma estimators",
        )
        subparsers = parser.add_subparsers(
            title="sensitivity analysis command", help="sensitivity analysis"
        )
        parser_update = subparsers.add_parser("sa", help="sensitivity analysis command")

        add_arguments(parser_update, parser, ["name"])

        parser = self.po_parser(
            parser,
            rm=True,
            mt=True,
            ct=True,
            p=True,
            s=True,
            e=True,
            lr=True,
            freq=True,
            mn=True,
            th=True,
            r=True,
            a=True,
            v=True,
            name="NCO_",
        )
        ns_parser = self.parse_known_args_and_warn(parser, other_args)
        if ns_parser:
            if len(self.tickers) < 2:
                console.print(
                    "Please have at least 2 loaded tickers to calculate weights.\n"
                )
                return

            table = True
            if "historic_period_sa" in vars(ns_parser):
                table = False

            console.print(
                "[yellow]Optimization can take time. Please be patient...\n[/yellow]"
            )

            weights = optimizer_view.display_nco(
                symbols=self.tickers,
                interval=ns_parser.historic_period,
                start_date=ns_parser.start_period,
                end_date=ns_parser.end_period,
                log_returns=ns_parser.log_returns,
                freq=ns_parser.return_frequency,
                maxnan=ns_parser.max_nan,
                threshold=ns_parser.threshold_value,
                method=ns_parser.nan_fill_method,
                codependence=ns_parser.co_dependence.lower(),
                covariance=ns_parser.covariance.lower(),
                objective=ns_parser.objective.lower(),
                risk_measure=ns_parser.risk_measure.lower(),
                risk_free_rate=ns_parser.risk_free,
                risk_aversion=ns_parser.risk_aversion,
                alpha=ns_parser.significance_level,
                linkage=ns_parser.linkage.lower(),
                k=ns_parser.amount_clusters,
                max_k=ns_parser.max_clusters,
                bins_info=ns_parser.amount_bins.upper(),
                alpha_tail=ns_parser.alpha_tail,
                leaf_order=ns_parser.leaf_order,
                d_ewma=ns_parser.smoothing_factor_ewma,
                value=ns_parser.long_allocation,
                table=table,
            )

            self.portfolios[ns_parser.name.upper()] = weights
            self.count += 1
            self.update_runtime_choices()

            if table is False:
                weights_sa = optimizer_view.display_nco(
                    symbols=self.tickers,
                    interval=ns_parser.historic_period_sa,
                    start_date=ns_parser.start_period_sa,
                    end_date=ns_parser.end_period_sa,
                    log_returns=ns_parser.log_returns_sa,
                    freq=ns_parser.return_frequency_sa,
                    maxnan=ns_parser.max_nan_sa,
                    threshold=ns_parser.threshold_value_sa,
                    method=ns_parser.nan_fill_method_sa,
                    codependence=ns_parser.co_dependence_sa.lower(),
                    covariance=ns_parser.covariance_sa.lower(),
                    objective=ns_parser.objective_sa.lower(),
                    risk_measure=ns_parser.risk_measure_sa.lower(),
                    risk_free_rate=ns_parser.risk_free_sa,
                    risk_aversion=ns_parser.risk_aversion_sa,
                    alpha=ns_parser.significance_level_sa,
                    linkage=ns_parser.linkage_sa.lower(),
                    k=ns_parser.amount_clusters_sa,
                    max_k=ns_parser.max_clusters_sa,
                    bins_info=ns_parser.amount_bins_sa.upper(),
                    alpha_tail=ns_parser.alpha_tail_sa,
                    leaf_order=ns_parser.leaf_order_sa,
                    d_ewma=ns_parser.smoothing_factor_ewma_sa,
                    value=ns_parser.long_allocation_sa,
                    table=table,
                )

                console.print("")
                optimizer_view.display_weights_sa(
                    weights=weights, weights_sa=weights_sa
                )

                if not ns_parser.categories:
                    categories = ["ASSET_CLASS", "COUNTRY", "SECTOR", "INDUSTRY"]
                else:
                    categories = ns_parser.categories

                for category in categories:
                    optimizer_view.display_categories_sa(
                        weights=weights,
                        weights_sa=weights_sa,
                        categories=self.categories,
                        column=category,
                        title="Category - " + category.title(),
                    )
