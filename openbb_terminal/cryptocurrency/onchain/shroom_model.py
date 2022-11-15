"""Shroom model"""
import logging
from typing import List
import json
import time
import pandas as pd
import requests

from openbb_terminal.decorators import log_start_end, check_api_key
from openbb_terminal import config_terminal as cfg

logger = logging.getLogger(__name__)


TTL_MINUTES = 15

# return up to 100,000 results per GET request on the query id
PAGE_SIZE = 100000

# return results of page 1
PAGE_NUMBER = 1


def create_query(query: str):
    r = requests.post(
        "https://node-api.flipsidecrypto.com/queries",
        data=json.dumps({"sql": query, "ttlMinutes": TTL_MINUTES}),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": cfg.API_SHROOM_KEY,
        },
    )
    if r.status_code != 200:
        raise Exception(
            f"Error creating query, got response: {r.text} with status code: {str(r.status_code)}"
        )

    return json.loads(r.text)


def get_query_results(token):
    r = requests.get(
        f"https://node-api.flipsidecrypto.com/queries/{token}?pageNumber={PAGE_NUMBER}&pageSize={PAGE_SIZE}",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": cfg.API_SHROOM_KEY,
        },
    )
    if r.status_code != 200:
        raise Exception(
            f"Error creating query, got response: {r.text} with status code: {str(r.status_code)}"
        )

    data = json.loads(r.text)
    if data["status"] == "running":
        time.sleep(10)
        return get_query_results(token)

    return data


DAPP_STATS_PLATFORM_CHOICES = ["uniswap-v3", "uniswap-v2", "sushiswap", "curve"]


def get_shroom_data(sql: str):
    """Get shroom data"""
    query = create_query(sql)
    token = query["token"]
    data = get_query_results(token)
    return data


@log_start_end(log=logger)
@check_api_key(["API_SHROOM_KEY"])
def get_dapp_stats(
    platform: str = "curve",
) -> pd.DataFrame:
    """Get dapp stats

    Parameters
    ----------
    platform: str
        platform to get stats for

    Returns
    -------
    pd.DataFrame
        dapp stats
    """
    sql = f"""select
        date_trunc('week', s.block_timestamp) as date,
        sum(t.fee_usd) as fee,
        count(distinct(s.from_address)) as n_users,
        count(distinct(s.amount_usd)) as volume
    from ethereum.dex_swaps s
    join ethereum.transactions t
        on s.tx_id = t.tx_id
    where platform = '{platform}'
    group by date
    order by date asc
    """
    data = get_shroom_data(sql)

    df = pd.DataFrame(
        data["results"], columns=["timeframe", "fees", "n_users", "volume"]
    )

    df["timeframe"] = pd.to_datetime(df["timeframe"])
    df = df.set_index("timeframe")

    return df


@log_start_end(log=logger)
@check_api_key(["API_SHROOM_KEY"])
def get_daily_transactions(symbols: List[str]) -> pd.DataFrame:
    """Get daily transactions for certain symbols in ethereum blockchain
    [Source: https://sdk.flipsidecrypto.xyz/shroomdk]

    Parameters
    ----------
    symbols : List[str]
        List of symbols to get transactions for

    Returns
    -------
    pd.DataFrame
        DataFrame with transactions for each symbol
    """
    extra_sql = ""
    for symbol in symbols:
        extra_sql += (
            f"sum(case when symbol = '{symbol}' then amount_usd end) as {symbol},"
        )
    extra_sql = extra_sql[:-1]
    sql = f"""
    select
    date_trunc('day', block_timestamp) as timeframe,
    {extra_sql}
    from  ethereum.udm_events
    where
    block_timestamp >= '2020-06-01'
    -- and amount0_usd > '0'
    group by 1
    order by timeframe desc
    """

    data = get_shroom_data(sql)

    df = pd.DataFrame(data["results"], columns=["timeframe"] + symbols)
    df["timeframe"] = pd.to_datetime(df["timeframe"])
    df.set_index("timeframe", inplace=True)

    return df


@log_start_end(log=logger)
@check_api_key(["API_SHROOM_KEY"])
def get_total_value_locked(
    user_address: str,
    address_name: str,
    symbol: str = "USDC",
    interval: int = 1,
) -> pd.DataFrame:

    """
    Get total value locked for a user/name address and symbol
    TVL measures the total amount of a token that is locked in a contract.
    [Source: https://sdk.flipsidecrypto.xyz/shroomdk]

    Parameters
    ----------
    user_address : str
        User address
    address_name : str
        Name of the address
    symbol : str
        Symbol of the token
    interval : int
        Interval in months

    Returns
    -------
    pd.DataFrame
        DataFrame with total value locked
    """

    if not (user_address or address_name):
        raise Exception("No user address or address name provided")
    if user_address:
        extra_sql = f"user_address = '{user_address}' and"
    else:
        extra_sql = f"address_name = '{address_name}' and"

    sql = f"""
    SELECT
        date_trunc('day', balance_date) as metric_date,
        symbol,
        amount_usd/1000000 as amount_usd
    FROM
        ethereum.erc20_balances
    WHERE
        {extra_sql}
        symbol = '{symbol}' AND
        balance_date >= getdate() - interval '{interval} month'
    ORDER BY
        metric_date asc
    """

    data = get_shroom_data(sql)

    df = pd.DataFrame(data["results"], columns=["metric_date", "symbol", "amount_usd"])
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    df.set_index("metric_date", inplace=True)

    return df
