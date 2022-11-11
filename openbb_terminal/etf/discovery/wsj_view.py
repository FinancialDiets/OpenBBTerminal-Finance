"""WSJ view"""
__docformat__ = "numpy"

import logging
import os

from openbb_terminal.decorators import log_start_end
from openbb_terminal.etf.discovery import wsj_model
from openbb_terminal.helper_funcs import export_data, print_rich_table
from openbb_terminal.rich_config import console

logger = logging.getLogger(__name__)


@log_start_end(log=logger)
def show_top_mover(sort_type: str = "gainers", limit: int = 10, export=""):
    """
    Show top ETF movers from wsj.com

    Parameters
    ----------
    sort_type: str
        What to show. Either Gainers, Decliners or Activity
    limit: int
        Number of etfs to show
    export: str
        Format to export data
    """
    data = wsj_model.etf_movers(sort_type)
    if data.empty:
        console.print("No data available\n")
        return

    print_rich_table(
        data.iloc[:limit],
        show_index=False,
        headers=list(data.columns),
        title="ETF Movers",
    )

    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        sort_type,
        data,
    )
