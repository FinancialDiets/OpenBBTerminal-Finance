"""Cryptocurrency helpers"""
# pylint: disable=too-many-lines,too-many-return-statements

from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from typing import Any
import difflib
import logging

import pandas as pd
import numpy as np
import ccxt
from binance.client import Client
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, ScalarFormatter
import yfinance as yf
import mplfinance as mpf
from pycoingecko import CoinGeckoAPI

from openbb_terminal.helper_funcs import (
    lambda_long_number_format,
    plot_autoscale,
    export_data,
    print_rich_table,
    lambda_long_number_format_y_axis,
    is_valid_axes_count,
)
from openbb_terminal.config_plot import PLOT_DPI
from openbb_terminal.cryptocurrency.due_diligence import (
    pycoingecko_model,
    coinpaprika_model,
)
from openbb_terminal.cryptocurrency.discovery.pycoingecko_model import get_coin_list
from openbb_terminal.cryptocurrency.overview.coinpaprika_model import get_list_of_coins
from openbb_terminal.cryptocurrency.due_diligence.binance_model import (
    check_valid_binance_str,
    show_available_pairs_for_given_symbol,
)

from openbb_terminal.config_terminal import theme
from openbb_terminal.cryptocurrency.due_diligence import coinbase_model
import openbb_terminal.config_terminal as cfg
from openbb_terminal.rich_config import console

logger = logging.getLogger(__name__)

__docformat__ = "numpy"

INTERVALS = ["1H", "3H", "6H", "1D"]

CCXT_INTERVAL_MAP = {
    "1": "1m",
    "15": "15m",
    "30": "30m",
    "60": "1h",
    "240": "4h",
    "1440": "1d",
    "10080": "1w",
    "43200": "1M",
}

SOURCES_INTERVALS = {
    "Binance": [
        "1day",
        "3day",
        "1hour",
        "2hour",
        "4hour",
        "6hour",
        "8hour",
        "12hour",
        "1week",
        "1min",
        "3min",
        "5min",
        "15min",
        "30min",
        "1month",
    ],
    "Coinbase": [
        "1min",
        "5min",
        "15min",
        "1hour",
        "6hour",
        "24hour",
        "1day",
    ],
    "YahooFinance": [
        "1min",
        "2min",
        "5min",
        "15min",
        "30min",
        "60min",
        "90min",
        "1hour",
        "1day",
        "5day",
        "1week",
        "1month",
        "3month",
    ],
}


YF_CURRENCY = [
    "CAD",
    "CNY",
    "ETH",
    "EUR",
    "GBP",
    "INR",
    "JPY",
    "KRW",
    "RUB",
    "USD",
    "AUD",
    "BTC",
]


def check_datetime(
    ck_date: datetime | str | None = None, start: bool = True
) -> datetime:
    """Checks if given argument is string and attempts to convert to datetime.

    Parameters
    ----------
    ck_date : Optional[Union[datetime, str]], optional
        Date to check, by default None
    start : bool, optional
        If True and string is invalid, will return 1100 days ago
        If False and string is invalid, will return today, by default True

    Returns
    -------
    datetime
        Datetime object
    """
    error_catch = (datetime.now() - timedelta(days=1100)) if start else datetime.now()
    try:
        if ck_date is None:
            return error_catch
        if isinstance(ck_date, datetime):
            return ck_date
        if isinstance(ck_date, str):
            return datetime.strptime(ck_date, "%Y-%m-%d")
    except Exception:
        console.print(
            f"Invalid date format (YYYY-MM-DD), "
            f"Using {error_catch.strftime('%Y-%m-%d')} for {ck_date}"
        )
    return error_catch


def _load_coin_map(file_name: str) -> pd.DataFrame:
    if file_name.split(".")[1] != "json":
        raise TypeError("Please load json file")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "data", file_name)
    with open(path, encoding="utf8") as f:
        coins = json.load(f)

    coins_df = pd.Series(coins).reset_index()
    coins_df.columns = ["symbol", "id"]
    return coins_df


def read_data_file(file_name: str):
    if file_name.split(".")[1] != "json":
        raise TypeError("Please load json file")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "data", file_name)
    with open(path, encoding="utf8") as f:
        return json.load(f)


def load_coins_list(file_name: str, return_raw: bool = False) -> pd.DataFrame:
    if file_name.split(".")[1] != "json":
        raise TypeError("Please load json file")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "data", file_name)
    with open(path, encoding="utf8") as f:
        coins = json.load(f)
    if return_raw:
        return coins
    return pd.DataFrame(coins)


def load_binance_map():
    return _load_coin_map("binance_gecko_map.json")


def load_coinbase_map():
    return _load_coin_map("coinbase_gecko_map.json")


def prepare_all_coins_df() -> pd.DataFrame:
    """Helper method which loads coins from all sources: CoinGecko, CoinPaprika,
    Binance, Yahoo Finance and merge those coins on keys:

        CoinGecko - > name < - CoinPaprika
        CoinGecko - > id <- Binance

    Returns
    -------
    pd.DataFrame
        CoinGecko - id for coin in CoinGecko API: uniswap
        CoinPaprika - id for coin in CoinPaprika API: uni-uniswap
        Binance - symbol (baseAsset) for coin in Binance API: UNI
        Coinbase - symbol for coin in Coinbase Pro API e.g UNI
        Yahoo Finance - symbol for coin in Yahoo Finance e.g. UNI1-USD

        Symbol: uni
    """

    gecko_coins_df = load_coins_list("coingecko_coins.json")

    paprika_coins_df = load_coins_list("coinpaprika_coins.json")
    paprika_coins_df = paprika_coins_df[paprika_coins_df["is_active"]]
    paprika_coins_df = paprika_coins_df[["rank", "id", "name", "symbol", "type"]]
    yahoofinance_coins_df = load_coins_list("yahoofinance_coins.json")

    # TODO: Think about scheduled job, that once a day will update data

    binance_coins_df = load_binance_map().rename(columns={"symbol": "Binance"})
    coinbase_coins_df = load_coinbase_map().rename(columns={"symbol": "Coinbase"})
    gecko_coins_df.symbol = gecko_coins_df.symbol.str.upper()

    gecko_paprika_coins_df = pd.merge(
        gecko_coins_df, paprika_coins_df, on="symbol", how="right"
    )

    df_merged = pd.merge(
        left=gecko_paprika_coins_df,
        right=binance_coins_df,
        left_on="id_x",
        right_on="id",
        how="left",
    )
    df_merged.rename(
        columns={
            "id_x": "CoinGecko",
            "symbol": "Symbol",
            "id_y": "CoinPaprika",
        },
        inplace=True,
    )

    df_merged = pd.merge(
        left=df_merged,
        right=coinbase_coins_df,
        left_on="CoinGecko",
        right_on="id",
        how="left",
    )

    yahoofinance_coins_df.rename(
        columns={
            "symbol": "Symbol",
        },
        inplace=True,
    )

    yahoofinance_coins_df.Symbol = yahoofinance_coins_df.Symbol.str.upper()

    df_merged = pd.merge(
        left=df_merged,
        right=yahoofinance_coins_df[["Symbol", "id"]],
        on="Symbol",
        how="left",
    )

    df_merged.rename(
        columns={
            "id": "YahooFinance",
        },
        inplace=True,
    )

    return df_merged[
        ["CoinGecko", "CoinPaprika", "Binance", "Coinbase", "YahooFinance", "Symbol"]
    ]


def _create_closest_match_df(
    coin: str, coins: pd.DataFrame, limit: int, cutoff: float
) -> pd.DataFrame:
    """Helper method. Creates a DataFrame with best matches for given coin found in given list of coins.
    Based on difflib.get_close_matches func.

    Parameters
    ----------
    coin: str
        coin you search for
    coins: list
        list of coins in which you want to find similarities
    limit: int
        limit of matches
    cutoff: float
        float between <0, 1>. Show only coins matches with score higher then cutoff.

    Returns
    -------
    pd.DataFrame
        index, id, name, symbol - > depends on source of data.
    """

    coins_list = coins["id"].to_list()
    sim = difflib.get_close_matches(coin, coins_list, limit, cutoff)
    df = pd.Series(sim).to_frame().reset_index()
    df.columns = ["index", "id"]
    return df.merge(coins, on="id")


def get_coingecko_id(symbol: str):
    client = CoinGeckoAPI()
    coin_list = client.get_coins_list()
    for coin in coin_list:
        if coin["symbol"] == symbol.lower():
            return coin["id"]
    return None


def get_coinpaprika_id(symbol: str):
    paprika_coins = get_list_of_coins()
    paprika_coins_dict = dict(zip(paprika_coins.id, paprika_coins.symbol))
    coinpaprika_id, _ = coinpaprika_model.validate_coin(
        symbol.upper(), paprika_coins_dict
    )
    return coinpaprika_id


def load_from_ccxt(
    symbol: str,
    start_date: datetime = (datetime.now() - timedelta(days=1100)),
    interval: str = "1440",
    exchange: str = "binance",
    vs_currency: str = "usdt",
) -> pd.DataFrame:
    """Load crypto currency data [Source: https://github.com/ccxt/ccxt]

    Parameters
    ----------
    symbol: str
        Coin to get
    start_date: datetime
        The datetime to start at
    interval: str
        The interval between data points in minutes.
        Choose from: 1, 15, 30, 60, 240, 1440, 10080, 43200
    exchange: str:
        The exchange to get data from.
    vs_currency: str
        Quote Currency (Defaults to usdt)

    Returns
    -------
    pd.DataFrame
        Dataframe consisting of price and volume data
    """
    df = pd.DataFrame()
    pair = f"{symbol.upper()}/{vs_currency.upper()}"

    try:
        df = fetch_ccxt_ohlc(
            exchange,
            3,
            pair,
            CCXT_INTERVAL_MAP[interval],
            int(datetime.timestamp(start_date)) * 1000,
            1000,
        )
        if df.empty:
            console.print(f"\nPair {pair} not found in {exchange}\n")
            return pd.DataFrame()
    except Exception:
        console.print(f"\nPair {pair} not found on {exchange}\n")
        return df
    return df


def load_from_coingecko(
    symbol: str,
    start_date: datetime = (datetime.now() - timedelta(days=1100)),
    vs_currency: str = "usdt",
) -> pd.DataFrame:
    """Load crypto currency data [Source: https://www.coingecko.com/]

    Parameters
    ----------
    symbol: str
        Coin to get
    start_date: datetime
        The datetime to start at
    vs_currency: str
        Quote Currency (Defaults to usdt)

    Returns
    -------
    pd.DataFrame
        Dataframe consisting of price and volume data
    """
    df = pd.DataFrame()
    delta = datetime.now() - start_date
    days = delta.days

    if days > 365:
        console.print("Coingecko free tier only allows a max of 365 days\n")
        days = 365

    coingecko_id = get_coingecko_id(symbol)
    if not coingecko_id:
        console.print(f"{symbol} not found in Coingecko\n")
        return df

    df = pycoingecko_model.get_ohlc(coingecko_id, vs_currency, days)
    df_coin = yf.download(
        f"{symbol}-{vs_currency}",
        end=datetime.now(),
        start=start_date,
        progress=False,
        interval="1d",
    ).sort_index(ascending=False)

    if not df_coin.empty:
        df = pd.merge(df, df_coin[::-1][["Volume"]], left_index=True, right_index=True)
    df.index.name = "date"
    return df


def load_from_yahoofinance(
    symbol: str,
    start_date: datetime = (datetime.now() - timedelta(days=1100)),
    interval: str = "1440",
    vs_currency: str = "usdt",
    end_date: datetime = datetime.now(),
) -> pd.DataFrame:
    """Load crypto currency data [Source: https://finance.yahoo.com/]

    Parameters
    ----------
    symbol: str
        Coin to get
    start_date: datetime
        The datetime to start at
    interval: str
        The interval between data points in minutes.
        Choose from: 1, 15, 30, 60, 240, 1440, 10080, 43200
    vs_currency: str
        Quote Currency (Defaults to usdt)
    end_date: datetime
       The datetime to end at

    Returns
    -------
    pd.DataFrame
        Dataframe consisting of price and volume data
    """
    pair = f"{symbol}-{vs_currency}"
    if int(interval) >= 1440:
        YF_INTERVAL_MAP = {
            "1440": "1d",
            "10080": "1wk",
            "43200": "1mo",
        }
        df = yf.download(
            pair,
            end=end_date,
            start=start_date,
            progress=False,
            interval=YF_INTERVAL_MAP[interval],
        ).sort_index(ascending=True)
    else:
        s_int = str(interval) + "m"
        d_granularity = {"1m": 6, "5m": 59, "15m": 59, "30m": 59, "60m": 729}
        s_start_dt = datetime.utcnow() - timedelta(days=d_granularity[s_int])
        s_date_start = s_start_dt.strftime("%Y-%m-%d")
        df = yf.download(
            pair,
            start=s_date_start
            if s_start_dt > start_date
            else start_date.strftime("%Y-%m-%d"),
            progress=False,
            interval=s_int,
        )

    open_sum = df["Open"].sum()
    if open_sum == 0:
        console.print(f"\nPair {pair} has invalid data on Yahoo Finance\n")
        return pd.DataFrame()

    if df.empty:
        console.print(f"\nPair {pair} not found in Yahoo Finance\n")
        return pd.DataFrame()
    df.index.name = "date"
    return df


def load(
    symbol: str,
    start_date: datetime | str | None = None,
    interval: str = "1440",
    exchange: str = "binance",
    vs_currency: str = "usdt",
    end_date: datetime | str | None = None,
    source: str = "CCXT",
) -> pd.DataFrame:
    """Load crypto currency to get data for

    Parameters
    ----------
    symbol: str
        Coin to get
    start_date: str or datetime, optional
        Start date to get data from with. - datetime or string format (YYYY-MM-DD)
    interval: str
        The interval between data points in minutes.
        Choose from: 1, 15, 30, 60, 240, 1440, 10080, 43200
    exchange: str:
        The exchange to get data from.
    vs_currency: str
        Quote Currency (Defaults to usdt)
    end_date: str or datetime, optional
        End date to get data from with. - datetime or string format (YYYY-MM-DD)
    source: str
        The source of the data
        Choose from: CCXT, CoinGecko, YahooFinance

    Returns
    -------
    pd.DataFrame
        Dataframe consisting of price and volume data
    """

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=1100)).strftime("%Y-%m-%d")

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    start_date = check_datetime(start_date)
    end_date = check_datetime(end_date, start=False)

    if source == "CCXT":
        return load_from_ccxt(symbol, start_date, interval, exchange, vs_currency)
    if source == "CoinGecko":
        return load_from_coingecko(symbol, start_date, vs_currency)
    if source == "YahooFinance":
        return load_from_yahoofinance(
            symbol, start_date, interval, vs_currency, end_date
        )
    console.print("[red]Invalid source sent[/red]\n")
    return pd.DataFrame()


def show_quick_performance(
    crypto_df: pd.DataFrame,
    symbol: str,
    current_currency: str,
    source: str,
    exchange: str,
    interval: str,
):
    """Show quick performance stats of crypto prices. Daily prices expected"""
    closes = crypto_df["Close"]
    volumes = crypto_df["Volume"] if "Volume" in crypto_df else pd.DataFrame()

    perfs = {}
    if interval == "1440":
        perfs = {
            "1D": 100 * closes.pct_change(2)[-1],
            "7D": 100 * closes.pct_change(7)[-1],
            "1M": 100 * closes.pct_change(30)[-1],
            "1Y": 100 * closes.pct_change(365)[-1],
        }
    first_day_current_year = str(datetime.now().date().replace(month=1, day=1))
    if first_day_current_year in closes.index:
        closes_ytd = closes[closes.index > first_day_current_year]
        perfs["YTD"] = 100 * (closes_ytd[-1] - closes_ytd[0]) / closes_ytd[0]
    else:
        perfs["Period"] = 100 * (closes[-1] - closes[0]) / closes[0]

    df = pd.DataFrame.from_dict(perfs, orient="index").dropna().T
    df = df.applymap(lambda x: str(round(x, 2)) + " %")
    df = df.applymap(lambda x: f"[red]{x}[/red]" if "-" in x else f"[green]{x}[/green]")
    if len(closes) > 365:
        df["Volatility (1Y)"] = (
            str(round(100 * np.sqrt(365) * closes[-365:].pct_change().std(), 2)) + " %"
        )
    else:
        df["Volatility (Ann)"] = (
            str(round(100 * np.sqrt(365) * closes.pct_change().std(), 2)) + " %"
        )
    if len(volumes) > 7:
        df["Volume (7D avg)"] = lambda_long_number_format(np.mean(volumes[-9:-2]), 2)

    df.insert(0, f"\nPrice ({current_currency.upper()})", closes[-1])

    try:
        coingecko_id = get_coingecko_id(symbol)

        coin_data_cg = pycoingecko_model.get_coin_tokenomics(coingecko_id)
        if not coin_data_cg.empty:
            df.insert(
                len(df.columns),
                "Circulating Supply",
                lambda_long_number_format(
                    int(
                        coin_data_cg.loc[
                            coin_data_cg["Metric"] == "Circulating Supply"
                        ]["Value"]
                    )
                ),
            )
    except Exception:
        pass

    exchange_str = f"in {exchange.capitalize()}" if source == "ccxt" else ""
    print_rich_table(
        df,
        show_index=False,
        headers=df.columns,
        title=f"{symbol.upper()}/{current_currency.upper()} Performance {exchange_str}",
    )


# pylint: disable=R0912
# TODO: verify vs, interval, days, depending on source
def load_deprecated(
    coin: str,
    source: str = "CoinPaprika",
    days: int = 60,
    vs: str = "usd",
    interval: str = "1day",
    should_load_ta_data: bool = False,
):
    """Load cryptocurrency from given source. Available sources are: CoinGecko, CoinPaprika,
    Coinbase, Binance and Yahoo Finance

    Loading coin from Binance and CoinPaprika means validation if given coins exists in chosen source,
    if yes then id of the coin is returned as a string.
    In case of CoinGecko load will return Coin object, if provided coin exists. Coin object has access to different coin
    information.

    Parameters
    ----------
    coin: str
        Coin symbol or id which is checked if exists in chosen data source.
    source : str
        Source of the loaded data. CoinGecko, CoinPaprika, Yahoo Finance or Binance

    Returns
    -------
    Tuple[Union[str, pycoingecko_model.Coin], str, str]
        - str or Coin object for provided coin
        - str with source of the loaded data. CoinGecko, CoinPaprika, Yahoo Finance or Binance
        - str with symbol
        - Dataframe with coin map to different sources
    """
    if source in ("CoinGecko", "CoinPaprika"):
        if vs not in ("USD", "BTC", "usd", "btc"):
            console.print("You can only compare with usd or btc (e.g., --vs usd)\n")
            return None, None, None, None, None, None
        if interval != "1day":
            console.print(
                "Only daily data is supported for coingecko and coinpaprika (e.g., -i 1day)\n"
            )
            return None, None, None, None, None, None

    current_coin: Any | None = ""

    coins_map_df = prepare_all_coins_df().set_index("Symbol").dropna(thresh=2)

    if source == "CoinGecko":
        coingecko = pycoingecko_model.Coin(coin.lower(), False)

        if not coingecko.symbol:
            return None, None, None, None, None, None
        try:
            coin_map_df = coins_map_df.loc[coingecko.symbol].copy()
            if not isinstance(coin_map_df, pd.Series):
                pd.options.mode.chained_assignment = None
                coin_map_df["null_values"] = coin_map_df.isna().sum(axis=1)
                coin_map_df = coin_map_df[
                    coin_map_df.null_values == coin_map_df.null_values.min()
                ]
                try:
                    coin_map_df = coin_map_df.iloc[0]
                except IndexError:
                    return None, None, None, None, None, None

            coin_map_df.fillna("")
        except KeyError:
            coin_map_df = pd.Series(
                {
                    "CoinGecko": coingecko,
                    "CoinPaprika": "",
                    "Binance": "",
                    "Coinbase": "",
                    "YahooFinance": "",
                }
            )
        # if it is dataframe, it means that found more than 1 coin
        if should_load_ta_data:
            df_prices, currency = load_ta_data(
                coin_map_df=coin_map_df,
                source=source,
                currency=vs,
                days=days,
                limit=0,
                interval=interval,
            )
            return (
                coin_map_df["CoinGecko"],
                source,
                coingecko.symbol,
                coin_map_df,
                df_prices,
                currency,
            )
        return (
            str(coingecko),
            source,
            coingecko.symbol,
            coin_map_df,
            None,
            None,
        )
    if source == "CoinPaprika":
        paprika_coins = get_list_of_coins()
        paprika_coins_dict = dict(zip(paprika_coins.id, paprika_coins.symbol))
        current_coin, symbol = coinpaprika_model.validate_coin(
            coin.upper(), paprika_coins_dict
        )

        if not symbol:
            return None, None, None, None, None, None

        try:
            coin_map_df = coins_map_df.loc[
                coins_map_df.index == symbol.upper() if symbol is not None else symbol
            ]

            if not isinstance(coin_map_df, pd.Series):
                pd.options.mode.chained_assignment = None
                coin_map_df["null_values"] = coin_map_df.isnull().sum(axis=1)

                coin_map_df = coin_map_df.loc[
                    coin_map_df.null_values == coin_map_df.null_values.min()
                ]

                try:
                    coin_map_df = coin_map_df.iloc[0]
                except IndexError:
                    return None, None, None, None, None, None

            coin_map_df.fillna("")
        except KeyError:
            coin_map_df = pd.Series(
                {
                    "CoinGecko": "",
                    "CoinPaprika": symbol,
                    "Binance": "",
                    "Coinbase": "",
                    "YahooFinance": "",
                }
            )

        if should_load_ta_data:
            df_prices, currency = load_ta_data(
                coin_map_df=coin_map_df,
                source=source,
                currency=vs,
                days=days,
                limit=0,
                interval=interval,
            )

            if not df_prices.empty:
                return (current_coin, source, symbol, coin_map_df, df_prices, currency)
        return (current_coin, source, symbol, coin_map_df, None, None)
    if source == "Binance":
        if vs == "usd":
            vs = "USDT"
        if interval not in SOURCES_INTERVALS["Binance"]:
            console.print(
                "Interval not available on binance. Run command again with one supported (e.g., -i 1day):\n",
                SOURCES_INTERVALS["Binance"],
            )
            return None, None, None, None, None, None

        # TODO: convert bitcoin to btc before searching pairs
        parsed_coin = coin.upper()
        current_coin, pairs = show_available_pairs_for_given_symbol(parsed_coin)
        if len(pairs) > 0:
            if vs not in pairs:
                console.print(
                    "vs specified not supported by binance. Run command again with one supported (e.g., --vs USDT):\n",
                    pairs,
                )
                return None, None, None, None, None, None
            try:
                coin_map_df = coins_map_df.loc[parsed_coin.lower()].copy()
                if not isinstance(coin_map_df, pd.Series):
                    coin_map_df["null_values"] = coin_map_df.apply(
                        lambda x: sum(x.isnull().values), axis=1
                    )
                    coin_map_df = coin_map_df[
                        coin_map_df.null_values == coin_map_df.null_values.min()
                    ]
                    coin_map_df = coin_map_df.iloc[0]
                coin_map_df.fillna("")
            except KeyError:
                coin_map_df = pd.Series(
                    {
                        "CoinGecko": "",
                        "CoinPaprika": "",
                        "Binance": parsed_coin.lower(),
                        "Coinbase": "",
                        "YahooFinance": "",
                    }
                )
            # console.print(f"Coin found : {current_coin}\n")
            if should_load_ta_data:
                df_prices, currency = load_ta_data(
                    coin_map_df=coin_map_df,
                    source=source,
                    currency=vs,
                    days=0,
                    limit=days,
                    interval=interval,
                )
                return (
                    current_coin,
                    source,
                    parsed_coin,
                    coin_map_df,
                    df_prices,
                    currency,
                )
            return (current_coin, source, parsed_coin, coin_map_df, None, None)
        return None, None, None, None, None, None

    if source == "Coinbase":
        if vs == "usd":
            vs = "USDT"
        if interval not in SOURCES_INTERVALS["Coinbase"]:
            console.print(
                "Interval not available on coinbase. Run command again with one supported (e.g., -i 1day):\n",
                SOURCES_INTERVALS["Coinbase"],
            )
            return None, None, None, None, None, None

        # TODO: convert bitcoin to btc before searching pairs
        coinbase_coin = coin.upper()
        current_coin, pairs = coinbase_model.show_available_pairs_for_given_symbol(
            coinbase_coin
        )
        if vs not in pairs:
            if len(pairs) > 0:
                console.print(
                    "vs specified not supported by coinbase. Run command again with one supported (e.g., --vs USDT):\n",
                    pairs,
                )
            return None, None, None, None, None, None
        if len(pairs) > 0:
            # console.print(f"Coin found : {current_coin}\n")
            try:
                coin_map_df = coins_map_df.loc[coin].copy()
                if not isinstance(coin_map_df, pd.Series):
                    coin_map_df["null_values"] = coin_map_df.apply(
                        lambda x: sum(x.isnull().values), axis=1
                    )
                    coin_map_df = coin_map_df[
                        coin_map_df.null_values == coin_map_df.null_values.min()
                    ]
                    coin_map_df = coin_map_df.iloc[0]
                coin_map_df.fillna("")
            except KeyError:
                coin_map_df = pd.Series(
                    {
                        "CoinGecko": "",
                        "CoinPaprika": "",
                        "Binance": "",
                        "Coinbase": coin,
                        "YahooFinance": "",
                    }
                )
            if should_load_ta_data:
                df_prices, currency = load_ta_data(
                    coin_map_df=coin_map_df,
                    source=source,
                    currency=vs,
                    days=0,
                    limit=days,
                    interval=interval,
                )
                return (current_coin, source, coin, coin_map_df, df_prices, currency)
            return (current_coin, source, coin, coin_map_df, None, None)
        return None, None, None, None, None, None

    if source == "YahooFinance":
        if vs.upper() not in YF_CURRENCY:
            console.print(
                "vs specified not supported by Yahoo Finance. Run command again with one supported (e.g., --vs USD):\n",
                YF_CURRENCY,
            )
            return None, None, None, None, None, None

        if interval not in SOURCES_INTERVALS["YahooFinance"]:
            console.print(
                "Interval not available on YahooFinance. Run command again with one supported (e.g., -i 1day):\n",
                SOURCES_INTERVALS["YahooFinance"],
            )
            return None, None, None, None, None, None

        # Search coin using crypto symbol
        coin_map_df = coins_map_df.loc[coins_map_df.index == coin]
        # Search coin using yfinance id
        # coin_map_df_2 = coins_map_df.loc[
        #    coins_map_df.YahooFinance == f"{coin.upper()}-{vs.upper()}"
        # ]
        # Search coin using crypto full name
        # coin_map_df_3 = coins_map_df.loc[coins_map_df.CoinGecko == coin]

        # for _df in [coin_map_df_1, coin_map_df_2, coin_map_df_3]:
        #    if not _df.empty:
        #        coin_map_df = _df
        #        break

        if coin_map_df.empty or (coin_map_df["YahooFinance"]).isna().all():
            # console.print(
            #    f"Cannot find {coin} against {vs} on Yahoo finance. Try another source or currency.\n"
            # )
            return None, None, None, None, None, None

        # Filter for the currency
        try:
            coin_map_df = coin_map_df[
                coin_map_df["YahooFinance"].str.upper().str.contains(vs.upper())
            ]

            coin_map_df = (
                coin_map_df.dropna().iloc[0]
                if isinstance(coin_map_df, pd.DataFrame)
                else coin_map_df
            )
        except Exception:
            return None, None, None, None, None, None

        if should_load_ta_data:
            df_prices, currency = load_ta_data(
                coin_map_df=coin_map_df,
                source=source,
                currency=vs,
                days=days,
                limit=0,
                interval=interval,
            )

            return (
                coin_map_df["YahooFinance"],
                source,
                coin,
                coin_map_df,
                df_prices,
                currency,
            )

        return (
            coin_map_df["YahooFinance"],
            source,
            coin,
            coin_map_df,
            None,
            None,
        )

    return None, None, None, None, None, None


FIND_KEYS = ["id", "symbol", "name"]

# TODO: Find better algorithm then difflib.get_close_matches to find most similar coins


def find(
    query: str,
    source: str = "CoinGecko",
    key: str = "symbol",
    limit: int = 10,
    export: str = "",
) -> None:
    """Find similar coin by coin name,symbol or id.

    If you don't know exact name or id of the Coin at CoinGecko CoinPaprika, Binance or Coinbase
    you use this command to display coins with similar name, symbol or id to your search query.
    Example: coin name is something like "polka". So I can try: find -c polka -k name -t 25
    It will search for coin that has similar name to polka and display top 25 matches.

        -c, --coin stands for coin - you provide here your search query
        -k, --key it's a searching key. You can search by symbol, id or name of coin
        -t, --top it displays top N number of records.

    Parameters
    ----------
    query: str
        Cryptocurrency
    source: str
        Data source of coins.  CoinGecko (cg) or CoinPaprika (cp) or Binance (bin), Coinbase (cb)
    key: str
        Searching key (symbol, id, name)
    limit: int
        Number of records to display
    export : str
        Export dataframe data to csv,json,xlsx file
    """

    if source == "CoinGecko":
        coins_df = get_coin_list()
        coins_list = coins_df[key].to_list()
        if key in ["symbol", "id"]:
            query = query.lower()

        sim = difflib.get_close_matches(query, coins_list, limit)
        df = pd.Series(sim).to_frame().reset_index()
        df.columns = ["index", key]
        coins_df.drop("index", axis=1, inplace=True)
        df = df.merge(coins_df, on=key)

    elif source == "CoinPaprika":
        coins_df = get_list_of_coins()
        coins_list = coins_df[key].to_list()
        keys = {"name": "title", "symbol": "upper", "id": "lower"}

        func_key = keys[key]
        query = getattr(query, str(func_key))()

        sim = difflib.get_close_matches(query, coins_list, limit)
        df = pd.Series(sim).to_frame().reset_index()
        df.columns = ["index", key]
        df = df.merge(coins_df, on=key)

    elif source == "Binance":

        # TODO: Fix it in future. Determine if user looks for symbol like ETH or ethereum
        if len(query) > 5:
            key = "id"

        coins_df_gecko = get_coin_list()
        coins_df_bin = load_binance_map()
        coins = pd.merge(
            coins_df_bin, coins_df_gecko[["id", "name"]], how="left", on="id"
        )
        coins_list = coins[key].to_list()

        sim = difflib.get_close_matches(query, coins_list, limit)
        df = pd.Series(sim).to_frame().reset_index()
        df.columns = ["index", key]
        df = df.merge(coins, on=key)

    elif source == "Coinbase":
        if len(query) > 5:
            key = "id"

        coins_df_gecko = get_coin_list()
        coins_df_bin = load_coinbase_map()
        coins = pd.merge(
            coins_df_bin, coins_df_gecko[["id", "name"]], how="left", on="id"
        )
        coins_list = coins[key].to_list()

        sim = difflib.get_close_matches(query, coins_list, limit)
        df = pd.Series(sim).to_frame().reset_index()
        df.columns = ["index", key]
        df = df.merge(coins, on=key)

    else:
        console.print(
            "Couldn't execute find methods for CoinPaprika, Binance, Coinbase or CoinGecko\n"
        )
        df = pd.DataFrame()

    print_rich_table(
        df, headers=list(df.columns), show_index=False, title="Similar Coins"
    )

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "find",
        df,
    )


def load_ta_data(
    coin_map_df: pd.DataFrame, source: str, currency: str, **kwargs: Any
) -> tuple[pd.DataFrame, str]:
    """Load data for Technical Analysis

    Parameters
    ----------
    coin_map_df: pd.DataFrame
        Cryptocurrency
    source: str
        Source of data: CoinGecko, Binance, CoinPaprika, Yahoo Finance
    currency: str
        Quotes currency
    kwargs:
        days: int
            Days limit for coingecko, coinpaprika
        limit: int
            Limit for binance quotes
        interval: str
            Time interval for Binance
    Returns
    ----------
    Tuple[pd.DataFrame, str]
        df with prices
        quoted currency
    """

    limit = kwargs.get("limit", 100)
    interval = kwargs.get("interval", "1day")
    days = kwargs.get("days", 30)

    if source == "Binance":
        client = Client(cfg.API_BINANCE_KEY, cfg.API_BINANCE_SECRET)

        interval_map = {
            "1day": client.KLINE_INTERVAL_1DAY,
            "3day": client.KLINE_INTERVAL_3DAY,
            "1hour": client.KLINE_INTERVAL_1HOUR,
            "2hour": client.KLINE_INTERVAL_2HOUR,
            "4hour": client.KLINE_INTERVAL_4HOUR,
            "6hour": client.KLINE_INTERVAL_6HOUR,
            "8hour": client.KLINE_INTERVAL_8HOUR,
            "12hour": client.KLINE_INTERVAL_12HOUR,
            "1week": client.KLINE_INTERVAL_1WEEK,
            "1min": client.KLINE_INTERVAL_1MINUTE,
            "3min": client.KLINE_INTERVAL_3MINUTE,
            "5min": client.KLINE_INTERVAL_5MINUTE,
            "15min": client.KLINE_INTERVAL_15MINUTE,
            "30min": client.KLINE_INTERVAL_30MINUTE,
            "1month": client.KLINE_INTERVAL_1MONTH,
        }

        symbol_binance = coin_map_df["Binance"]

        pair = symbol_binance.upper() + currency.upper()

        if check_valid_binance_str(pair):
            # console.print(f"{symbol_binance} loaded vs {currency.upper()}")

            candles = client.get_klines(
                symbol=pair,
                interval=interval_map[interval],
                limit=limit,
            )
            candles_df = pd.DataFrame(candles).astype(float).iloc[:, :6]
            candles_df.columns = [
                "date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            ]
            df_coin = candles_df.set_index(
                pd.to_datetime(candles_df["date"], unit="ms")
            ).drop("date", axis=1)

            return df_coin, currency
        return pd.DataFrame(), currency

    if source == "CoinPaprika":
        symbol_coinpaprika = coin_map_df["CoinPaprika"]
        df = coinpaprika_model.get_ohlc_historical(
            symbol_coinpaprika, currency.upper(), days
        )

        if df.empty:
            # console.print("No data found", "\n")
            return pd.DataFrame(), ""

        df.drop(["time_close"], axis=1, inplace=True)

        if "market_cap" in df.columns:
            df.drop(["market_cap"], axis=1, inplace=True)

        df.columns = [
            "date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]
        df = df.set_index(pd.to_datetime(df["date"])).drop("date", axis=1)
        return df, currency

    if source == "CoinGecko":
        if isinstance(coin_map_df["CoinGecko"], str):
            coin_id = coin_map_df["CoinGecko"]
        else:
            coin_id = coin_map_df["CoinGecko"].coin["id"]

        # coin = pycoingecko_model.Coin(symbol_coingecko)
        df = pycoingecko_model.get_coin_market_chart(coin_id, currency, days)
        df = df["price"].resample("1D").ohlc().ffill()
        df.columns = [
            "Open",
            "High",
            "Low",
            "Close",
        ]
        df.index.name = "date"
        return df, currency

    if source == "Coinbase":
        symbol_coinbase = coin_map_df["Coinbase"]
        coin, currency = symbol_coinbase.upper(), currency.upper()
        pair = f"{coin}-{currency}"

        if coinbase_model.check_validity_of_product(pair):
            # console.print(f"{coin} loaded vs {currency}")

            df = coinbase_model.get_candles(
                symbol=pair,
                interval=interval or "24hour",
            ).head(limit)

            df_coin = df.set_index(pd.to_datetime(df["date"], unit="s")).drop(
                "date", axis=1
            )

            return df_coin[::-1], currency

    if source == "YahooFinance":

        interval_map = {
            "1min": "1m",
            "2min": "2m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "60min": "60m",
            "90min": "90m",
            "1hour": "1h",
            "1day": "1d",
            "5day": "5d",
            "1week": "1wk",
            "1month": "1mo",
            "3month": "3mo",
        }

        symbol_yf = coin_map_df["YahooFinance"]

        df_coin = yf.download(
            symbol_yf,
            end=datetime.now(),
            start=datetime.now() - timedelta(days=days),
            progress=False,
            interval=interval_map[interval],
        ).sort_index(ascending=False)

        df_coin.index.names = ["date"]

        if df_coin.empty:
            console.print(f"Could not download data for {symbol_yf} from Yahoo Finance")
            return pd.DataFrame(), currency

        return df_coin[::-1], currency

    return pd.DataFrame(), currency


def load_yf_data(symbol: str, currency: str, interval: str, days: int):
    df_coin = yf.download(
        f"{symbol.upper()}-{currency.upper()}",
        end=datetime.now(),
        start=datetime.now() - timedelta(days=days),
        progress=False,
        interval=interval,
    ).sort_index(ascending=False)

    df_coin.index.names = ["date"]
    if df_coin.empty:
        console.print(
            f"Could not download data for {symbol}-{currency} from Yahoo Finance"
        )
        return pd.DataFrame(), currency

    return df_coin[::-1], currency


def display_all_coins(
    source: str, symbol: str, limit: int, skip: int, show_all: bool, export: str
) -> None:
    """Find similar coin by coin name,symbol or id.
    If you don't remember exact name or id of the Coin at CoinGecko, CoinPaprika, Coinbase, Binance
    you can use this command to display coins with similar name, symbol or id to your search query.
    Example of usage: coin name is something like "polka". So I can try: find -c polka -k name -t 25
    It will search for coin that has similar name to polka and display top 25 matches.
        -c, --coin stands for coin - you provide here your search query
        -t, --top it displays top N number of records.

    Parameters
    ----------
    limit: int
        Number of records to display
    symbol: str
        Cryptocurrency
    source: str
        Data source of coins.  CoinGecko (cg) or CoinPaprika (cp) or Binance (bin), Coinbase (cb)
    skip: int
        Skip N number of records
    show_all: bool
        Flag to show all sources of data
    export : str
        Export dataframe data to csv,json,xlsx file
    """
    sources = ["CoinGecko", "CoinPaprika", "Binance", "Coinbase"]
    limit, cutoff = 30, 0.75
    coins_func_map = {
        "CoinGecko": get_coin_list,
        "CoinPaprika": get_list_of_coins,
        "Binance": load_binance_map,
        "Coinbase": load_coinbase_map,
    }

    if show_all:
        coins_func = coins_func_map.get(source)
        if coins_func:
            df = coins_func()
        else:
            df = prepare_all_coins_df()

    elif not source or source not in sources:
        df = prepare_all_coins_df()
        cg_coins_list = df["CoinGecko"].to_list()
        sim = difflib.get_close_matches(symbol.lower(), cg_coins_list, limit, cutoff)
        df_matched = pd.Series(sim).to_frame().reset_index()
        df_matched.columns = ["index", "CoinGecko"]
        df = df.merge(df_matched, on="CoinGecko")
        df.drop("index", axis=1, inplace=True)

    else:

        if source == "CoinGecko":
            coins_df = get_coin_list().drop("index", axis=1)
            df = _create_closest_match_df(symbol.lower(), coins_df, limit, cutoff)
            df = df[["index", "id", "name"]]

        elif source == "CoinPaprika":
            coins_df = get_list_of_coins()
            df = _create_closest_match_df(symbol.lower(), coins_df, limit, cutoff)
            df = df[["index", "id", "name"]]

        elif source == "Binance":
            coins_df_gecko = get_coin_list()
            coins_df_bin = load_binance_map()
            coins_df_bin.columns = ["symbol", "id"]
            coins_df = pd.merge(
                coins_df_bin, coins_df_gecko[["id", "name"]], how="left", on="id"
            )
            df = _create_closest_match_df(symbol.lower(), coins_df, limit, cutoff)
            df = df[["index", "symbol", "name"]]
            df.columns = ["index", "id", "name"]

        elif source == "Coinbase":
            coins_df_gecko = get_coin_list()
            coins_df_cb = load_coinbase_map()
            coins_df_cb.columns = ["symbol", "id"]
            coins_df = pd.merge(
                coins_df_cb, coins_df_gecko[["id", "name"]], how="left", on="id"
            )
            df = _create_closest_match_df(symbol.lower(), coins_df, limit, cutoff)
            df = df[["index", "symbol", "name"]]
            df.columns = ["index", "id", "name"]

        else:
            df = pd.DataFrame(columns=["index", "id", "symbol"])
            console.print("Couldn't find any coins")

    try:
        df = df[skip : skip + limit]  # noqa
    except Exception as e:
        logger.exception(str(e))
        console.print(e)

    print_rich_table(
        df.fillna("N/A"),
        headers=list(df.columns),
        show_index=False,
        title="Similar Coins",
    )

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "coins",
        df,
    )


def plot_chart(
    prices_df: pd.DataFrame,
    to_symbol: str = "",
    from_symbol: str = "",
    source: str = "",
    exchange: str = "",
    interval: str = "",
    external_axes: list[plt.Axes] | None = None,
    yscale: str = "linear",
) -> None:
    """Load data for Technical Analysis

    Parameters
    ----------
    prices_df: pd.DataFrame
        Cryptocurrency
    to_symbol: str
        Coin (only used for chart title), by default ""
    from_symbol: str
        Currency (only used for chart title), by default ""
    yscale: str
        Scale for y axis of plot Either linear or log
    """
    del interval

    if prices_df.empty:
        console.print("There is not data to plot chart\n")
        return

    exchange_str = f"/{exchange}" if source == "ccxt" else ""
    title = (
        f"{source}{exchange_str} - {to_symbol.upper()}/{from_symbol.upper()}"
        f" from {prices_df.index[0].strftime('%Y/%m/%d')} "
        f"to {prices_df.index[-1].strftime('%Y/%m/%d')}"
    )

    volume_mean = prices_df["Volume"].mean()
    if volume_mean > 1_000_000:
        prices_df["Volume"] = prices_df["Volume"] / 1_000_000

    plot_candles(
        candles_df=prices_df,
        title=title,
        volume=True,
        ylabel="Volume [1M]" if volume_mean > 1_000_000 else "Volume",
        external_axes=external_axes,
        yscale=yscale,
    )

    console.print()


def plot_candles(
    candles_df: pd.DataFrame,
    volume: bool = True,
    ylabel: str = "",
    title: str = "",
    external_axes: list[plt.Axes] | None = None,
    yscale: str = "linear",
) -> None:
    """Plot candle chart from dataframe. [Source: Binance]

    Parameters
    ----------
    candles_df: pd.DataFrame
        Dataframe containing time and OHLCV
    volume: bool
        If volume data shall be plotted, by default True
    ylabel: str
        Y-label of the graph, by default ""
    title: str
        Title of graph, by default ""
    external_axes : Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    yscale : str
        Scaling for y axis.  Either linear or log
    """
    candle_chart_kwargs = {
        "type": "candle",
        "style": theme.mpf_style,
        "volume": volume,
        "xrotation": theme.xticks_rotation,
        "ylabel_lower": ylabel,
        "scale_padding": {"left": 0.3, "right": 1, "top": 0.8, "bottom": 0.8},
        "update_width_config": {
            "candle_linewidth": 0.6,
            "candle_width": 0.8,
            "volume_linewidth": 0.8,
            "volume_width": 0.8,
        },
        "warn_too_much_data": 10000,
        "yscale": yscale,
    }

    # This plot has 2 axes
    if external_axes is None:
        candle_chart_kwargs["returnfig"] = True
        candle_chart_kwargs["figratio"] = (10, 7)
        candle_chart_kwargs["figscale"] = 1.10
        candle_chart_kwargs["figsize"] = plot_autoscale()
        fig, ax = mpf.plot(candles_df, **candle_chart_kwargs)

        fig.suptitle(
            f"\n{title}",
            horizontalalignment="left",
            verticalalignment="top",
            x=0.05,
            y=1,
        )
        lambda_long_number_format_y_axis(candles_df, "Volume", ax)
        if yscale == "log":
            ax[0].yaxis.set_major_formatter(ScalarFormatter())
            ax[0].yaxis.set_major_locator(
                LogLocator(base=100, subs=[1.0, 2.0, 5.0, 10.0])
            )
            ax[0].ticklabel_format(style="plain", axis="y")
        theme.visualize_output(force_tight_layout=False)
    else:
        nr_external_axes = 2 if volume else 1
        if not is_valid_axes_count(external_axes, nr_external_axes):
            return

        if volume:
            (ax, volume) = external_axes
            candle_chart_kwargs["volume"] = volume
        else:
            ax = external_axes[0]

        candle_chart_kwargs["ax"] = ax

        mpf.plot(candles_df, **candle_chart_kwargs)


def plot_order_book(
    bids: np.ndarray,
    asks: np.ndarray,
    coin: str,
    external_axes: list[plt.Axes] | None = None,
) -> None:
    """
    Plots Bid/Ask. Can be used for Coinbase and Binance

    Parameters
    ----------
    bids : np.array
        array of bids with columns: price, size, cumulative size
    asks : np.array
        array of asks with columns: price, size, cumulative size
    coin : str
        Coin being plotted
    external_axes : Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    """
    # This plot has 1 axis
    if external_axes is None:
        _, ax = plt.subplots(figsize=plot_autoscale(), dpi=PLOT_DPI)
    elif is_valid_axes_count(external_axes, 1):
        (ax,) = external_axes
    else:
        return

    ax.plot(bids[:, 0], bids[:, 2], color=theme.up_color, label="bids")
    ax.fill_between(bids[:, 0], bids[:, 2], color=theme.up_color, alpha=0.4)

    ax.plot(asks[:, 0], asks[:, 2], color=theme.down_color, label="asks")
    ax.fill_between(asks[:, 0], asks[:, 2], color=theme.down_color, alpha=0.4)

    ax.legend()
    ax.set_xlabel("Price")
    ax.set_ylabel("Size (Coins)")
    ax.set_title(f"Order Book for {coin}")

    theme.style_primary_axis(ax)

    if external_axes is None:
        theme.visualize_output(force_tight_layout=False)


def check_cg_id(symbol: str):
    cg_id = get_coingecko_id(symbol)
    if not cg_id:
        print(f"\n{symbol} not found on CoinGecko")
        return ""
    return symbol


def fetch_ccxt_ohlc(exchange_id, max_retries, symbol, timeframe, since, limit):
    exchange = getattr(ccxt, exchange_id)(
        {
            "enableRateLimit": True,  # required by the Manual
        }
    )
    if isinstance(since, str):
        since = exchange.parse8601(since)
    ohlcv = get_ohlcv(exchange, max_retries, symbol, timeframe, since, limit)
    df = pd.DataFrame(ohlcv, columns=["date", "Open", "High", "Low", "Close", "Volume"])
    df["date"] = pd.to_datetime(df.date, unit="ms")
    df.set_index("date", inplace=True)
    return df


def retry_fetch_ohlcv(exchange, max_retries, symbol, timeframe, since, limit):
    num_retries = 0
    try:
        num_retries += 1
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        return ohlcv
    except Exception:
        if num_retries > max_retries:
            raise
        return []


def get_ohlcv(exchange, max_retries, symbol, timeframe, since, limit):
    timeframe_duration_in_seconds = exchange.parse_timeframe(timeframe)
    timeframe_duration_in_ms = timeframe_duration_in_seconds * 1000
    timedelta_ = limit * timeframe_duration_in_ms
    now = exchange.milliseconds()
    all_ohlcv = []
    fetch_since = since
    while fetch_since < now:
        ohlcv = retry_fetch_ohlcv(
            exchange, max_retries, symbol, timeframe, fetch_since, limit
        )
        fetch_since = (ohlcv[-1][0] + 1) if len(ohlcv) else (fetch_since + timedelta_)
        all_ohlcv = all_ohlcv + ohlcv
    return exchange.filter_by_since_limit(all_ohlcv, since, None, key=0)


def get_exchanges_ohlc():
    arr = []
    for exchange in ccxt.exchanges:
        exchange_ccxt = getattr(ccxt, exchange)(
            {
                "enableRateLimit": True,
            }
        )
        if exchange_ccxt.has["fetchOHLCV"]:
            arr.append(exchange)
    return arr
