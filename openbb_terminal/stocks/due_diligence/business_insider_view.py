""" Business Insider View """
__docformat__ = "numpy"

import logging
import os
from datetime import datetime
from typing import List, Optional

import matplotlib.pyplot as plt
from pandas.core.frame import DataFrame
from pandas.plotting import register_matplotlib_converters

from openbb_terminal.config_terminal import theme
from openbb_terminal.config_plot import PLOT_DPI
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    export_data,
    plot_autoscale,
    print_rich_table,
    is_valid_axes_count,
)
from openbb_terminal.rich_config import console
from openbb_terminal.stocks.due_diligence import business_insider_model

logger = logging.getLogger(__name__)

register_matplotlib_converters()


@log_start_end(log=logger)
def price_target_from_analysts(
    symbol: str,
    data: DataFrame,
    start_date: str = None,
    limit: int = 10,
    raw: bool = False,
    export: str = "",
    external_axes: Optional[List[plt.Axes]] = None,
):
    """Display analysts' price targets for a given stock. [Source: Business Insider]

    Parameters
    ----------
    symbol: str
        Due diligence ticker symbol
    data: DataFrame
        Due diligence stock dataframe
    start_date : str
        Start date of the stock data, format YYYY-MM-DD
    limit : int
        Number of latest price targets from analysts to print
    raw: bool
        Display raw data only
    export: str
        Export dataframe data to csv,json,xlsx file
    external_axes: Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    """

    if start_date is None:
        start_date = datetime.now().strftime("%Y-%m-%d")

    df_analyst_data = business_insider_model.get_price_target_from_analysts(symbol)
    if df_analyst_data.empty:
        console.print("[red]Could not get data for ticker.[/red]\n")
        return

    if raw:
        df_analyst_data.index = df_analyst_data.index.strftime("%Y-%m-%d")
        print_rich_table(
            df_analyst_data.sort_index(ascending=False).head(limit),
            headers=list(df_analyst_data.columns),
            show_index=True,
            title="Analyst Price Targets",
        )

    else:

        # This plot has 1 axis
        if not external_axes:
            _, ax = plt.subplots(figsize=plot_autoscale(), dpi=PLOT_DPI)
        elif is_valid_axes_count(external_axes, 1):
            (ax,) = external_axes
        else:
            return

        # Slice start of ratings
        if start_date:
            df_analyst_data = df_analyst_data[start_date:]  # type: ignore

        plot_column = "Close"
        legend_price_label = "Close"

        ax.plot(data.index, data[plot_column].values)

        if start_date:
            ax.plot(df_analyst_data.groupby(by=["Date"]).mean(numeric_only=True)[start_date:])  # type: ignore
        else:
            ax.plot(df_analyst_data.groupby(by=["Date"]).mean(numeric_only=True))

        ax.scatter(
            df_analyst_data.index,
            df_analyst_data["Price Target"],
            color=theme.down_color,
            edgecolors=theme.up_color,
            zorder=2,
        )

        ax.legend([legend_price_label, "Average Price Target", "Price Target"])

        ax.set_title(f"{symbol} (Time Series) and Price Target")
        ax.set_xlim(data.index[0], data.index[-1])
        ax.set_ylabel("Share Price")

        theme.style_primary_axis(ax)

        if not external_axes:
            theme.visualize_output()

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "pt",
        df_analyst_data,
    )


@log_start_end(log=logger)
def estimates(symbol: str, estimate: str, export: str = ""):
    """Display analysts' estimates for a given ticker. [Source: Business Insider]

    Parameters
    ----------
    symbol : str
        Ticker to get analysts' estimates
    estimate: str
        Type of estimate to get
    export : str
        Export dataframe data to csv,json,xlsx file
    """
    (
        df_year_estimates,
        df_quarter_earnings,
        df_quarter_revenues,
    ) = business_insider_model.get_estimates(symbol)

    if estimate == "annualearnings":

        print_rich_table(
            df_year_estimates,
            headers=list(df_year_estimates.columns),
            show_index=True,
            title="Annual Earnings Estimates",
        )
        export_data(
            export,
            os.path.dirname(os.path.abspath(__file__)),
            "pt_year",
            df_year_estimates,
        )

    elif estimate == "quarterearnings":
        print_rich_table(
            df_quarter_earnings,
            headers=list(df_quarter_earnings.columns),
            show_index=True,
            title="Quarterly Earnings Estimates",
        )
        export_data(
            export,
            os.path.dirname(os.path.abspath(__file__)),
            "pt_qtr_earnings",
            df_quarter_earnings,
        )

    elif estimate == "annualrevenue":
        print_rich_table(
            df_quarter_revenues,
            headers=list(df_quarter_revenues.columns),
            show_index=True,
            title="Quarterly Revenue Estimates",
        )

        export_data(
            export,
            os.path.dirname(os.path.abspath(__file__)),
            "pt_qtr_revenues",
            df_quarter_revenues,
        )
    else:
        console.print("[red]Invalid estimate type[/red]")
