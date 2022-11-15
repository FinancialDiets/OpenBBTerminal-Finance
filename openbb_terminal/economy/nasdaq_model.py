"""NASDAQ Data Link Model"""
__docformat__ = "numpy"

import argparse
import logging
import os
from typing import List, Union

from datetime import datetime as dt
import pandas as pd
import requests

from openbb_terminal.config_terminal import API_KEY_QUANDL
from openbb_terminal.decorators import check_api_key, log_start_end
from openbb_terminal.rich_config import console

logger = logging.getLogger(__name__)


@log_start_end(log=logger)
def get_economic_calendar(
    countries: Union[List[str], str] = "",
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """Get economic calendar for countries between specified dates

    Parameters
    ----------
    countries : [List[str],str]
        List of countries to include in calendar.  Empty returns all
    start_date : str
        Start date for calendar
    end_date : str
        End date for calendar

    Returns
    -------
    pd.DataFrame
        Economic calendar
    """

    if start_date is None:
        start_date = dt.now().strftime("%Y-%m-%d")

    if end_date is None:
        end_date = dt.now().strftime("%Y-%m-%d")

    if countries == "":
        countries = []
    if isinstance(countries, str):
        countries = [countries]
    if start_date == end_date:
        dates = [start_date]
    else:
        dates = (
            pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()
        )
    calendar = pd.DataFrame()
    for date in dates:
        try:
            df = pd.DataFrame(
                requests.get(
                    f"https://api.nasdaq.com/api/calendar/economicevents?date={date}",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
                    },
                ).json()["data"]["rows"]
            ).replace("&nbsp;", "-")
            df.loc[:, "Date"] = date
            calendar = pd.concat([calendar, df], axis=0)
        except TypeError:
            continue

    if calendar.empty:
        console.print("[red]No data found for date range.[/red]")
        return pd.DataFrame()

    calendar = calendar.rename(
        columns={"gmt": "Time (GMT)", "country": "Country", "eventName": "Event"}
    )

    calendar = calendar.drop(columns=["description"])
    if not countries:
        return calendar

    calendar = calendar[calendar["Country"].isin(countries)].reset_index(drop=True)
    if calendar.empty:
        console.print(f"[red]No data found for {','.join(countries)}[/red]")
        return pd.DataFrame()
    return calendar


@log_start_end(log=logger)
def check_country_code_type(list_of_codes: str) -> List[str]:
    """Check that codes are valid for NASDAQ API"""
    nasdaq_codes = list(
        pd.read_csv(os.path.join(os.path.dirname(__file__), "NASDAQ_CountryCodes.csv"))[
            "Code"
        ]
    )
    valid_codes = [
        code.upper()
        for code in list_of_codes.split(",")
        if code.upper() in nasdaq_codes
    ]

    if valid_codes:
        return valid_codes
    raise argparse.ArgumentTypeError("No valid codes provided.")


@log_start_end(log=logger)
def get_country_codes() -> List[str]:
    """Get available country codes for Bigmac index

    Returns
    -------
    List[str]
        List of ISO-3 letter country codes.
    """
    file = os.path.join(os.path.dirname(__file__), "NASDAQ_CountryCodes.csv")
    codes = pd.read_csv(file, index_col=0)
    return codes


@log_start_end(log=logger)
@check_api_key(["API_KEY_QUANDL"])
def get_big_mac_index(country_code: str = "USA") -> pd.DataFrame:
    """Gets the Big Mac index calculated by the Economist

    Parameters
    ----------
    country_code : str
        ISO-3 letter country code to retrieve. Codes available through get_country_codes().

    Returns
    -------
    pd.DataFrame
        Dataframe with Big Mac index converted to USD equivalent.
    """
    URL = f"https://data.nasdaq.com/api/v3/datasets/ECONOMIST/BIGMAC_{country_code}"
    URL += f"?column_index=3&api_key={API_KEY_QUANDL}"
    try:
        r = requests.get(URL)
    except Exception:
        console.print("[red]Error connecting to NASDAQ API[/red]\n")
        return pd.DataFrame()

    df = pd.DataFrame()

    if r.status_code == 200:
        response_json = r.json()
        df = pd.DataFrame(response_json["dataset"]["data"])
        df.columns = response_json["dataset"]["column_names"]
        df["Date"] = pd.to_datetime(df["Date"])

    # Wrong API Key
    elif r.status_code == 400:
        console.print(r.text)
    # Premium Feature
    elif r.status_code == 403:
        console.print(r.text)
    # Catching other exception
    elif r.status_code != 200:
        console.print(r.text)

    return df


@log_start_end(log=logger)
@check_api_key(["API_KEY_QUANDL"])
def get_big_mac_indices(country_codes: List[str] = None) -> pd.DataFrame:
    """Display Big Mac Index for given countries

    Parameters
    ----------
    country_codes : List[str]
        List of country codes (ISO-3 letter country code). Codes available through economy.country_codes().

    Returns
    -------
    pd.DataFrame
        Dataframe with Big Mac indices converted to USD equivalent.
    """

    if country_codes is None:
        country_codes = ["USA"]

    df_cols = ["Date"]
    df_cols.extend(country_codes)
    big_mac = pd.DataFrame(columns=df_cols)
    for country in country_codes:
        df1 = get_big_mac_index(country)
        if not df1.empty:
            big_mac[country] = df1["dollar_price"]
            big_mac["Date"] = df1["Date"]
    big_mac.set_index("Date", inplace=True)

    return big_mac
