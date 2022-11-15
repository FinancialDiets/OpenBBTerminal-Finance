import logging
import os
from typing import List, Optional

from matplotlib import pyplot as plt

from openbb_terminal.config_terminal import theme
from openbb_terminal.decorators import check_api_key
from openbb_terminal import config_plot as cfgPlot
from openbb_terminal.cryptocurrency.due_diligence.santiment_model import (
    get_github_activity,
)
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    export_data,
    plot_autoscale,
    is_valid_axes_count,
)


logger = logging.getLogger(__name__)


@log_start_end(log=logger)
@check_api_key(["API_SANTIMENT_KEY"])
def display_github_activity(
    symbol: str,
    start_date: str = None,
    dev_activity: bool = False,
    end_date: str = None,
    interval: str = "1d",
    export: str = "",
    external_axes: Optional[List[plt.Axes]] = None,
) -> None:
    """Returns a list of github activity for a given coin and time interval.

    [Source: https://santiment.net/]

    Parameters
    ----------
    symbol : str
        Crypto symbol to check github activity
    dev_activity: bool
        Whether to filter only for development activity
    start_date : int
        Initial date like string (e.g., 2021-10-01)
    end_date : int
        End date like string (e.g., 2021-10-01)
    interval : str
        Interval frequency (some possible values are: 1h, 1d, 1w)
    export : str
        Export dataframe data to csv,json,xlsx file
    external_axes : Optional[List[plt.Axes]], optional
        External axes (1 axis is expected in the list), by default None
    """

    df = get_github_activity(
        symbol=symbol,
        dev_activity=dev_activity,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
    )

    if df.empty:
        return

    # This plot has 1 axis
    if not external_axes:
        _, ax = plt.subplots(figsize=plot_autoscale(), dpi=cfgPlot.PLOT_DPI)
    elif is_valid_axes_count(external_axes, 1):
        (ax,) = external_axes
    else:
        return

    ax.plot(df.index, df["value"])

    ax.set_title(f"{symbol}'s Github activity over time")
    ax.set_ylabel(f"{symbol}'s Activity count")
    ax.set_xlim(df.index[0], df.index[-1])

    theme.style_primary_axis(ax)

    if not external_axes:
        theme.visualize_output()

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "gh",
        df,
    )
