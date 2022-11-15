from datetime import datetime
import logging
from pandas import DataFrame

from openbb_terminal.decorators import log_start_end

from openbb_terminal.cryptocurrency.due_diligence.glassnode_model import get_close_price

# pylint: disable=unsupported-assignment-operation

logger = logging.getLogger(__name__)
# pylint: disable=unsupported-assignment-operation

api_url = "https://api.glassnode.com/v1/metrics/"


@log_start_end(log=logger)
def get_btc_rainbow(
    start_date: str = "2010-01-01",
    end_date: str = None,
) -> DataFrame:
    """Get bitcoin price data
    [Price data from source: https://glassnode.com]
    [Inspired by: https://blockchaincenter.net]

    Parameters
    ----------
    start_date : str
        Initial date, format YYYY-MM-DD
    end_date : str
        Final date, format YYYY-MM-DD

    Returns
    -------
    pd.DataFrame
        price over time
    """

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    df_data = get_close_price("BTC", start_date, end_date)

    return df_data
