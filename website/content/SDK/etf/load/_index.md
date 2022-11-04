## Get underlying data 
### etf.load(symbol: str, start_date: datetime.datetime = None, interval: int = 1440, end_date: datetime.datetime = None, prepost: bool = False, source: str = 'YahooFinance', iexrange: str = 'ytd', weekly: bool = False, monthly: bool = False, verbose: bool = True)

Load a symbol to perform analysis using the string above as a template.

    Optional arguments and their descriptions are listed above.

    The default source is, yFinance (https://pypi.org/project/yfinance/).
    Other sources:
            -   AlphaVantage (https://www.alphavantage.co/documentation/)
            -   IEX Cloud (https://iexcloud.io/docs/api/)
            -   Eod Historical Data (https://eodhistoricaldata.com/financial-apis/)

    Please note that certain analytical features are exclusive to the specific source.

    To load a symbol from an exchange outside of the NYSE/NASDAQ default, use yFinance as the source and
    add the corresponding exchange to the end of the symbol. i.e. `BNS.TO`.  Note this may be possible with
    other paid sources check their docs.

    BNS is a dual-listed stock, there are separate options chains and order books for each listing.
    Opportunities for arbitrage may arise from momentary pricing discrepancies between listings
    with a dynamic exchange rate as a second order opportunity in ForEx spreads.

    Find the full list of supported exchanges here:
    https://help.yahoo.com/kb/exchanges-data-providers-yahoo-finance-sln2310.html

    Certain analytical features, such as VWAP, require the ticker to be loaded as intraday
    using the `-i x` argument.  When encountering this error, simply reload the symbol using
    the interval argument. i.e. `load -t BNS -s YYYY-MM-DD -i 1 -p` loads one-minute intervals,
    including Pre/After Market data, using the default source, yFinance.

    Certain features, such as the Prediction menu, require the symbol to be loaded as daily and not intraday.

    Parameters
    ----------
    symbol: str
        Ticker to get data
    start_date: datetime
        Start date to get data from with
    interval: int
        Interval (in minutes) to get data 1, 5, 15, 30, 60 or 1440
    end_date: datetime
        End date to get data from with
    prepost: bool
        Pre and After hours data
    source: str
        Source of data extracted
    iexrange: str
        Timeframe to get IEX data.
    weekly: bool
        Flag to get weekly data
    monthly: bool
        Flag to get monthly data
    verbose: bool
        Display verbose information on what was the symbol that was loaded

    Returns
    -------
    df_stock_candidate: pd.DataFrame
        Dataframe of data
