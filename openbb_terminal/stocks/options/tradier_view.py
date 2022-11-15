"""Tradier options view"""
__docformat__ = "numpy"

import argparse
import logging
import os
import warnings
from bisect import bisect_left
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
import seaborn as sns

from openbb_terminal import config_plot as cfp
from openbb_terminal import rich_config
from openbb_terminal.config_terminal import theme
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    export_data,
    is_valid_axes_count,
    lambda_long_number_format_y_axis,
    patch_pandas_text_adjustment,
    plot_autoscale,
    print_rich_table,
)
from openbb_terminal.rich_config import console
from openbb_terminal.stocks.options import op_helpers, tradier_model, yfinance_model

logger = logging.getLogger(__name__)

column_map = {"mid_iv": "iv", "open_interest": "oi", "volume": "vol"}
warnings.filterwarnings("ignore")


def get_strike_bounds(
    options: pd.DataFrame, current_price: float, min_sp: float, max_sp: float
) -> Tuple[float, float]:
    if min_sp == -1:
        if current_price == 0:
            min_strike = options["strike"].iat[0]
        else:
            min_strike = 0.75 * current_price
    else:
        min_strike = min_sp

    if max_sp == -1:
        if current_price == 0:
            max_strike = options["strike"].iat[-1]
        else:
            max_strike = 1.25 * current_price
    else:
        max_strike = max_sp
    return min_strike, max_strike


def lambda_red_highlight(val) -> str:
    """Red highlight

    Parameters
    ----------
    val
        dataframe values to color

    Returns
    -------
    str
        colored dataframes values
    """
    return f"[red]{val}[/red]"


def lambda_green_highlight(val) -> str:
    """Green highlight

    Parameters
    ----------
    values : List[str]
        dataframe values to color

    Returns
    -------
    List[str]
        colored dataframes values
    """
    return f"[green]{val}[/green]"


@log_start_end(log=logger)
def check_valid_option_chains_headers(headers: str) -> List[str]:
    """Check valid option chains headers

    Parameters
    ----------
    headers : str
        Option chains headers

    Returns
    -------
    List[str]
        List of columns string
    """
    columns = [str(item) for item in headers.split(",")]

    for header in columns:
        if header not in tradier_model.df_columns:
            raise argparse.ArgumentTypeError("Invalid option chains header selected!")

    return columns


@log_start_end(log=logger)
def display_expirations(ticker: str, source: str = "YahooFinance"):
    """Displays the expirations for a ticker

    Parameters
    ----------
    ticker: str
        The ticker to look up
    source: str
        Where to get the data from. Options: yf (yahoo finance) or tr (tradier)
    """
    if source == "YahooFinance":
        exps = yfinance_model.option_expirations(ticker)
    elif source == "Tradier":
        exps = tradier_model.option_expirations(ticker)
    else:
        raise ValueError("Invalid source. Please select 'yf' or 'tr'")
    display_expiry_dates(exps)


@log_start_end(log=logger)
def display_expiry_dates(expiry_dates: list):
    """Display expiry dates

    Parameters
    ----------
    expiry_dates: list
        The expiry dates of the chosen ticker.
    """
    expiry_dates_df = pd.DataFrame(expiry_dates, columns=["Date"])

    print_rich_table(
        expiry_dates_df,
        headers=list(expiry_dates_df.columns),
        title="Available expiry dates",
        show_index=True,
        index_name="Identifier",
    )


@log_start_end(log=logger)
def display_chains(
    symbol: str,
    expiry: str,
    to_display: List[str] = None,
    min_sp: float = -1,
    max_sp: float = -1,
    calls_only: bool = False,
    puts_only: bool = False,
    export: str = "",
):
    """Display option chain

    Parameters
    ----------
    symbol: str
        Stock ticker symbol
    expiry: str
        Expiration date of option
    to_display: List[str]
        List of columns to display
    min_sp: float
        Min strike price to display
    max_sp: float
        Max strike price to display
    calls_only: bool
        Only display calls
    puts_only: bool
        Only display puts
    export: str
        Format to  export file
    """

    if to_display is None:
        to_display = tradier_model.default_columns

    chains_df = tradier_model.get_option_chains(symbol, expiry)
    columns = to_display + ["strike", "option_type"]
    chains_df = chains_df[columns].rename(columns=column_map)

    min_strike, max_strike = get_strike_bounds(chains_df, 0, min_sp, max_sp)

    chains_df = chains_df[chains_df["strike"] >= min_strike]
    chains_df = chains_df[chains_df["strike"] <= max_strike]

    calls_df = chains_df[chains_df.option_type == "call"].drop(columns=["option_type"])
    puts_df = chains_df[chains_df.option_type == "put"].drop(columns=["option_type"])

    df = calls_df if calls_only else puts_df

    if calls_only or puts_only:
        print_rich_table(
            df,
            headers=[x.title() for x in df.columns],
            show_index=False,
            title=f"The strike prices are displayed between {min_strike} and {max_strike}",
        )

    else:
        puts_df = puts_df[puts_df.columns[::-1]]
        chain_table = calls_df.merge(puts_df, on="strike")

        if rich_config.USE_COLOR:
            call_cols = [col for col in chain_table if col.endswith("_x")]
            put_cols = [col for col in chain_table if col.endswith("_y")]
            patch_pandas_text_adjustment()
            pd.set_option("display.max_colwidth", 0)
            pd.set_option("display.max_rows", None)
            for cc in call_cols:
                chain_table[cc] = (
                    chain_table[cc].astype(str).apply(lambda_green_highlight)
                )
            for pc in put_cols:
                chain_table[pc] = (
                    chain_table[pc].astype(str).apply(lambda_red_highlight)
                )
        headers = [
            col.strip("_x")
            if col.endswith("_x")
            else col.strip("_y")
            if col.endswith("_y")
            else col
            for col in chain_table.columns
        ]
        print_rich_table(
            chain_table, headers=headers, show_index=False, title="Option chain"
        )

    export_data(
        export,
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "chains",
        chains_df,
    )


@log_start_end(log=logger)
def plot_oi(
    symbol: str,
    expiry: str,
    min_sp: float = -1,
    max_sp: float = -1,
    calls_only: bool = False,
    puts_only: bool = False,
    export: str = "",
    external_axes: Optional[List[plt.Axes]] = None,
):
    """Plot open interest

    Parameters
    ----------
    symbol: str
        Ticker symbol
    expiry: str
        Expiry date for options
    min_sp: float
        Min strike to consider
    max_sp: float
        Max strike to consider
    calls_only: bool
        Show calls only
    puts_only: bool
        Show puts only
    export: str
        Format to export file
    external_axes : Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    """

    options = tradier_model.get_option_chains(symbol, expiry)
    current_price = tradier_model.last_price(symbol)

    min_strike, max_strike = get_strike_bounds(options, current_price, min_sp, max_sp)

    if max_strike == min_strike:
        console.print("[red]Not enough data for analysis[/red]\n")
        return

    if calls_only and puts_only:
        console.print("Both flags selected, please select one", "\n")
        return

    calls = options[options.option_type == "call"][["strike", "open_interest"]]
    puts = options[options.option_type == "put"][["strike", "open_interest"]]
    call_oi = calls.set_index("strike")["open_interest"] / 1000
    put_oi = puts.set_index("strike")["open_interest"] / 1000

    df_opt = pd.merge(call_oi, put_oi, left_index=True, right_index=True)
    df_opt = df_opt.rename(
        columns={"open_interest_x": "OI_call", "open_interest_y": "OI_put"}
    )

    max_pain = op_helpers.calculate_max_pain(df_opt)
    if external_axes is None:
        _, ax = plt.subplots(figsize=plot_autoscale(), dpi=cfp.PLOT_DPI)
    elif is_valid_axes_count(external_axes, 1):
        (ax,) = external_axes
    else:
        return

    if not calls_only:
        ax.plot(put_oi.index, put_oi.values, "-o", label="Puts")

    if not puts_only:
        ax.plot(call_oi.index, call_oi.values, "-o", label="Calls")

    ax.legend(loc=0)
    ax.axvline(current_price, lw=2, ls="--", label="Current Price", alpha=0.7)
    ax.axvline(max_pain, lw=3, label=f"Max Pain: {max_pain}", alpha=0.7)
    ax.set_xlabel("Strike Price")
    ax.set_ylabel("Open Interest [1k] ")
    ax.set_xlim(min_strike, max_strike)
    ax.set_title(f"Open Interest for {symbol.upper()} expiring {expiry}")

    theme.style_primary_axis(ax)

    if external_axes is None:
        theme.visualize_output()

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "oi_tr",
        options,
    )


@log_start_end(log=logger)
def plot_vol(
    symbol: str,
    expiry: str,
    min_sp: float = 1,
    max_sp: float = -1,
    calls_only: bool = False,
    puts_only: bool = False,
    export: str = "",
    external_axes: Optional[List[plt.Axes]] = None,
):
    """Plot volume

    Parameters
    ----------
    symbol: str
        Ticker symbol
    expiry: str
        Expiry date for options
    min_sp: float
        Min strike to consider
    max_sp: float
        Max strike to consider
    calls_only: bool
        Show calls only
    puts_only: bool
        Show puts only
    export: str
        Format to export file
    external_axes : Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    """

    options = tradier_model.get_option_chains(symbol, expiry)
    current_price = tradier_model.last_price(symbol)

    min_strike, max_strike = get_strike_bounds(options, current_price, min_sp, max_sp)

    if calls_only and puts_only:
        console.print("Both flags selected, please select one", "\n")
        return

    calls = options[options.option_type == "call"][["strike", "volume"]]
    puts = options[options.option_type == "put"][["strike", "volume"]]
    call_v = calls.set_index("strike")["volume"] / 1000
    put_v = puts.set_index("strike")["volume"] / 1000

    if external_axes is None:
        _, ax = plt.subplots(figsize=plot_autoscale(), dpi=cfp.PLOT_DPI)
    else:
        ax = external_axes[0]

    if not calls_only:
        put_v.plot(
            x="strike",
            y="volume",
            label="Puts",
            ax=ax,
            marker="o",
            ls="-",
            c="r",
        )
    if not puts_only:
        call_v.plot(
            x="strike",
            y="volume",
            label="Calls",
            ax=ax,
            marker="o",
            ls="-",
            c="g",
        )
    ax.axvline(current_price, lw=2, c="k", ls="--", label="Current Price", alpha=0.7)
    ax.grid("on")
    ax.set_xlabel("Strike Price")
    ax.set_ylabel("Volume [1k] ")
    ax.set_xlim(min_strike, max_strike)
    ax.set_title(f"Volume for {symbol.upper()} expiring {expiry}")

    theme.style_primary_axis(ax)

    if external_axes is None:
        theme.visualize_output()

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "vol_tr",
        options,
    )


@log_start_end(log=logger)
def plot_volume_open_interest(
    symbol: str,
    expiry: str,
    min_sp: float = -1,
    max_sp: float = -1,
    min_vol: float = -1,
    export: str = "",
    external_axes: Optional[List[plt.Axes]] = None,
):
    """Plot volume and open interest

    Parameters
    ----------
    symbol: str
        Stock ticker symbol
    expiry: str
        Option expiration
    min_sp: float
        Min strike price
    max_sp: float
        Max strike price
    min_vol: float
        Min volume to consider
    export: str
        Format for exporting data
    external_axes : Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    """
    current_price = tradier_model.last_price(symbol)
    options = tradier_model.get_option_chains(symbol, expiry)

    calls = options[options.option_type == "call"][
        ["strike", "volume", "open_interest"]
    ]
    puts = options[options.option_type == "put"][["strike", "volume", "open_interest"]]

    # Process Calls Data
    df_calls = calls.pivot_table(
        index="strike", values=["volume", "open_interest"], aggfunc="sum"
    ).reindex()
    df_calls["strike"] = df_calls.index
    df_calls["type"] = "calls"
    df_calls["open_interest"] = df_calls["open_interest"]
    df_calls["volume"] = df_calls["volume"]
    df_calls["oi+v"] = df_calls["open_interest"] + df_calls["volume"]
    df_calls["spot"] = round(current_price, 2)

    df_puts = puts.pivot_table(
        index="strike", values=["volume", "open_interest"], aggfunc="sum"
    ).reindex()
    df_puts["strike"] = df_puts.index
    df_puts["type"] = "puts"
    df_puts["open_interest"] = df_puts["open_interest"]
    df_puts["volume"] = -df_puts["volume"]
    df_puts["open_interest"] = -df_puts["open_interest"]
    df_puts["oi+v"] = df_puts["open_interest"] + df_puts["volume"]
    df_puts["spot"] = round(current_price, 2)

    call_oi = calls.set_index("strike")["open_interest"] / 1000
    put_oi = puts.set_index("strike")["open_interest"] / 1000

    df_opt = pd.merge(call_oi, put_oi, left_index=True, right_index=True)
    df_opt = df_opt.rename(
        columns={"open_interest_x": "OI_call", "open_interest_y": "OI_put"}
    )

    max_pain = op_helpers.calculate_max_pain(df_opt)

    if min_vol == -1 and min_sp == -1 and max_sp == -1:
        # If no argument provided, we use the percentile 50 to get 50% of upper volume data
        volume_percentile_threshold = 50
        min_vol_calls = np.percentile(df_calls["oi+v"], volume_percentile_threshold)
        min_vol_puts = np.percentile(df_puts["oi+v"], volume_percentile_threshold)

        df_calls = df_calls[df_calls["oi+v"] > min_vol_calls]
        df_puts = df_puts[df_puts["oi+v"] < min_vol_puts]

    else:
        if min_vol > -1:
            df_calls = df_calls[df_calls["oi+v"] > min_vol]
            df_puts = df_puts[df_puts["oi+v"] < -min_vol]

        if min_sp > -1:
            df_calls = df_calls[df_calls["strike"] > min_sp]
            df_puts = df_puts[df_puts["strike"] > min_sp]

        if max_sp > -1:
            df_calls = df_calls[df_calls["strike"] < max_sp]
            df_puts = df_puts[df_puts["strike"] < max_sp]

    if df_calls.empty and df_puts.empty:
        console.print(
            "The filtering applied is too strong, there is no data available for such conditions.\n"
        )
        return

    # Initialize the matplotlib figure
    if external_axes is None:
        _, ax = plt.subplots(figsize=plot_autoscale(), dpi=cfp.PLOT_DPI)
    else:
        ax = external_axes[0]

    # make x axis symmetric
    axis_origin = max(abs(max(df_puts["oi+v"])), abs(max(df_calls["oi+v"])))
    ax.set_xlim(-axis_origin, +axis_origin)

    g = sns.barplot(
        x="oi+v",
        y="strike",
        data=df_calls,
        label="Calls: Open Interest",
        color="lightgreen",
        orient="h",
    )

    g = sns.barplot(
        x="volume",
        y="strike",
        data=df_calls,
        label="Calls: Volume",
        color="green",
        orient="h",
    )

    g = sns.barplot(
        x="oi+v",
        y="strike",
        data=df_puts,
        label="Puts: Open Interest",
        color="pink",
        orient="h",
    )

    g = sns.barplot(
        x="volume",
        y="strike",
        data=df_puts,
        label="Puts: Volume",
        color="red",
        orient="h",
    )

    # draw spot line
    s = [float(strike.get_text()) for strike in ax.get_yticklabels()]
    spot_index = bisect_left(s, current_price)  # find where the spot is on the graph
    spot_line = ax.axhline(spot_index, ls="--", alpha=0.3)

    # draw max pain line
    max_pain_index = bisect_left(s, max_pain)
    max_pain_line = ax.axhline(max_pain_index, ls="-", alpha=0.3, color="red")
    max_pain_line.set_linewidth(5)

    # format ticklabels without - for puts
    g.set_xticks(g.get_xticks())
    xlabels = [f"{x:,.0f}".replace("-", "") for x in g.get_xticks()]
    g.set_xticklabels(xlabels)

    ax.set_title(
        f"{symbol} volumes for {expiry}\n(open interest displayed only during market hours)"
    )
    ax.invert_yaxis()

    _ = ax.legend()
    handles, _ = ax.get_legend_handles_labels()
    handles.append(spot_line)
    handles.append(max_pain_line)

    # create legend labels + add to graph
    labels = [
        "Calls open interest",
        "Calls volume ",
        "Puts open interest",
        "Puts volume",
        "Current stock price",
        f"Max pain = {max_pain}",
    ]

    ax.legend(handles=handles[:], labels=labels, loc="lower left")
    sns.despine(left=True, bottom=True)
    theme.style_primary_axis(ax)

    if external_axes is None:
        theme.visualize_output()

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "voi_tr",
        options,
    )


@log_start_end(log=logger)
def display_historical(
    symbol: str,
    expiry: str,
    strike: float = 0,
    put: bool = False,
    raw: bool = False,
    chain_id: str = None,
    export: str = "",
    external_axes: Optional[List[plt.Axes]] = None,
):
    """Plot historical option prices

    Parameters
    ----------
    symbol: str
        Stock ticker symbol
    expiry: str
        Expiry date of option
    strike: float
        Option strike price
    put: bool
        Is this a put option?
    raw: bool
        Print raw data
    chain_id: str
        OCC option symbol
    export: str
        Format of export file
    external_axes : Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    """

    df_hist = tradier_model.get_historical_options(
        symbol, expiry, strike, put, chain_id
    )

    if raw:
        print_rich_table(
            df_hist,
            headers=[x.title() for x in df_hist.columns],
            title="Historical Option Prices",
        )

    op_type = ["call", "put"][put]

    candle_chart_kwargs = {
        "type": "candle",
        "style": theme.mpf_style,
        "volume": True,
        "xrotation": theme.xticks_rotation,
        "scale_padding": {"left": 0.3, "right": 1.2, "top": 0.8, "bottom": 0.8},
        "update_width_config": {
            "candle_linewidth": 0.6,
            "candle_width": 0.8,
            "volume_linewidth": 0.8,
            "volume_width": 0.8,
        },
        "datetime_format": "%Y-%b-%d",
    }
    if external_axes is None:
        candle_chart_kwargs["returnfig"] = True
        candle_chart_kwargs["figratio"] = (10, 7)
        candle_chart_kwargs["figscale"] = 1.10
        candle_chart_kwargs["figsize"] = plot_autoscale()
        fig, ax = mpf.plot(df_hist, **candle_chart_kwargs)
        fig.suptitle(
            f"Historical {strike} {op_type.title()}",
            x=0.055,
            y=0.965,
            horizontalalignment="left",
        )
        lambda_long_number_format_y_axis(df_hist, "volume", ax)
        theme.visualize_output(force_tight_layout=False)
    elif is_valid_axes_count(external_axes, 2):
        (ax1, ax2) = external_axes
        candle_chart_kwargs["ax"] = ax1
        candle_chart_kwargs["volume"] = ax2
        mpf.plot(df_hist, **candle_chart_kwargs)
    else:
        return

    console.print()

    if export:
        export_data(
            export,
            os.path.dirname(os.path.abspath(__file__)),
            "hist",
            df_hist,
        )
