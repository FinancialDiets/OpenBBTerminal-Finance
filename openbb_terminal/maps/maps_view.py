""" Maps View """
import logging
import os
import webbrowser
import pandas as pd
import folium
from typing import List, Tuple
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import export_data
from openbb_terminal.rich_config import console

logger = logging.getLogger(__name__)

COUNTRY_SHAPES = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"

EUROZONE_COUNTRIES = [
    "Austria",
    "Belgium",
    "Cyprus",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Netherlands",
    "Portugal",
    "Slovakia",
    "Slovenia",
    "Spain",
]


def get_folium_kwargs(
    legend: str = None,
    df: pd.DataFrame = None,
    country_shapes: str = COUNTRY_SHAPES,
    scale: list = None,
) -> dict:
    kwargs = {
        "geo_data": country_shapes,
        "name": "choropleth",
        "columns": ["Country", "Value"],
        "key_on": "feature.properties.name",
        "fill_color": "YlOrRd",
        "fill_opacity": 0.7,
        "nan_fill_color": "white",
    }
    if not df.empty:
        kwargs["data"] = df
    if legend:
        kwargs["legend_name"] = legend
    if scale:
        kwargs["threshold_scale"] = scale

    return kwargs


def display_map(df: pd.DataFrame, legend: str, scale=None) -> None:
    """Display map"""

    m = folium.Map()  # zoom_control=False, scrollWheelZoom=False, dragging=False
    kwargs = get_folium_kwargs(legend=legend, df=df, scale=scale)
    folium.Choropleth(**kwargs).add_to(m)
    # save folium to html
    m.save("maps.html")
    file_path = "maps.html"
    webbrowser.open("file://" + os.path.realpath(file_path))
    console.print("")


@log_start_end(log=logger)
def display_bitcoin_hash(export: str = ""):
    """Opens Finviz map website in a browser. [Source: Finviz]

    Parameters
    ----------
    period : str
        Performance period. Available periods are 1d, 1w, 1m, 3m, 6m, 1y.
    map_filter : str
        Map filter. Available map filters are sp500, world, full, etf.
    """
    df = pd.read_csv("https://ccaf.io/cbeci/api/v1.2.0/download/mining_countries")
    df = df[df["date"] == df["date"].max()]
    df = df[["country", "monthly_hashrate_%"]]
    df["country"] = df["country"].replace("United States", "United States of America")
    df["country"] = df["country"].replace("Iran, Islamic Rep.", "Iran")
    df["country"] = df["country"].replace("Germany *", "Germany")
    df["country"] = df["country"].replace("Ireland *", "Ireland")
    df["country"] = df["country"].replace("Mainland China", "China")
    df["monthly_hashrate_%"] = df["monthly_hashrate_%"].str.rstrip("%").astype("float")
    df.columns = ["Country", "Value"]
    display_map(df, "Bitcoin Hashing Rate % per country until 2022-01-01")
    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "bh",
        df,
    )


@log_start_end(log=logger)
def display_interest_rates(export: str = ""):
    """Opens Finviz map website in a browser. [Source: Finviz]

    Parameters
    ----------
    period : str
        Performance period. Available periods are 1d, 1w, 1m, 3m, 6m, 1y.
    map_filter : str
        Map filter. Available map filters are sp500, world, full, etf.
    """
    ir_url = (
        "https://en.wikipedia.org/wiki/List_of_countries_by_central_bank_interest_rates"
    )
    df = pd.read_html(ir_url)
    df = df[0][["Country or currency union", "Central bank interest rate (%)"]]
    df.columns = ["Country", "Value"]
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "Country": country,
                        "Value": df[df["Country"] == "Eurozone"]["Value"].values[0],
                    }
                    for country in EUROZONE_COUNTRIES
                ]
            ),
        ],
    )
    df = df[df["Country"] != "Eurozone"]
    myscale = (df["Value"].quantile((0, 0.25, 0.5, 0.75, 1))).tolist()
    display_map(df, "Central Bank Interest Rates", myscale)
    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "ir",
        df,
    )


@log_start_end(log=logger)
def display_map_explorer(coordinates: List[Tuple[float, float]]):
    """
    Display map explorer

    Parameters
    ----------
    coordinates : List[Tuple[float, float]]
        List of coordinates
    """
    m = folium.Map()
    for coordinate in coordinates:
        folium.Marker(location=[coordinate[0], coordinate[1]]).add_to(m)

    # save folium to html
    m.save("maps.html")
    file_path = "maps.html"
    webbrowser.open("file://" + os.path.realpath(file_path))
    console.print("")
