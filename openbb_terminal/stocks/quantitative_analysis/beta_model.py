"""Beta model"""
__docformat__ = "numpy"

from typing import Tuple

import pandas as pd
from scipy import stats
from openbb_terminal.stocks import stocks_helper


def beta_model(
    symbol: str,
    ref_symbol: str,
    data: pd.DataFrame = None,
    ref_data: pd.DataFrame = None,
    interval: int = 1440,
) -> Tuple[pd.Series, pd.Series, float, float]:
    """Calculate beta for a ticker and a reference ticker.

    Parameters
    ----------
    symbol: str
        A ticker to calculate beta for
    ref_symbol: str
        A reference ticker symbol for the beta calculation (default in terminal is SPY)
    data: pd.DataFrame
        The selected ticker symbols price data
    ref_data: pd.DataFrame
        The reference ticker symbols price data
    interval: int
        The interval of the ref_data. This will ONLY be used if ref_data is None

    Returns
    -------
    Tuple[pd.Series, pd.Series, float, float]
        Stock ticker symbols close-to-close returns, Reference ticker symbols close-to-close returns, beta, alpha
    """
    if data is None:
        data = stocks_helper.load(symbol)
    else:
        # TODO: When loaded in the stocks menu, the stock df columns are all
        # lowercase but when loaded via stocks_helper.load(ticker) they start
        # with an uppercase char. This should be consistent.
        data = data.rename({"close": "Close"}, axis=1)
    if ref_data is None:
        ref_data = stocks_helper.load(ref_symbol, interval=interval)
        if ref_data.empty:
            raise Exception("Invalid ref_symbol ticker")
    else:
        ref_data = ref_data.rename({"close": "Close"}, axis=1)

    # join returns
    sr = 100 * data["Close"].pct_change().to_frame()
    sr = sr.rename({"Close": "Stock Pct Ret"}, axis=1)
    rr = 100 * ref_data["Close"].pct_change().to_frame()
    rr = rr.rename({"Close": "Ref Pct Ret"}, axis=1)
    df = sr.merge(rr, how="outer", left_index=True, right_index=True)
    df = df.dropna()
    sr = df["Stock Pct Ret"].tolist()
    rr = df["Ref Pct Ret"].tolist()

    # compute lin reg
    if not rr or not sr:
        return pd.Series(dtype="object"), pd.Series(dtype="object"), 0.0, 0.0
    model = stats.linregress(rr, sr)
    beta = model.slope
    alpha = model.intercept

    return sr, rr, beta, alpha
