.. role:: python(code)
    :language: python
    :class: highlight

|

To obtain charts, make sure to add :python:`chart = True` as the last parameter.

.. raw:: html

    <h3>
    > Getting data
    </h3>

{{< highlight python >}}
crypto.dd.eb(
    symbol: str,
    exchange: str = 'binance',
    start_date: int = 1262304000,
    end_date: int = 1668077823,
    chart: bool = False,
) -> pandas.core.frame.DataFrame
{{< /highlight >}}

.. raw:: html

    <p>
    Returns the total amount of coins held on exchange addresses in units and percentage.
    [Source: https://glassnode.com]
    </p>

* **Parameters**

    symbol : str
        Asset to search active addresses (e.g., BTC)
    exchange : str
        Exchange to check net position change (e.g., binance)
    start_date : int
        Initial date timestamp (e.g., 1_614_556_800)
    end_date : int
        End date timestamp (e.g., 1_614_556_800)
    chart: bool
       Flag to display chart


* **Returns**

    pd.DataFrame
        total amount of coins in units/percentage and symbol price over time

|

.. raw:: html

    <h3>
    > Getting charts
    </h3>

{{< highlight python >}}
crypto.dd.eb(
    symbol: str,
    exchange: str = 'binance',
    start_date: int = 1577836800,
    end_date: int = 1609459200,
    percentage: bool = False,
    export: str = '',
    external_axes: Optional[List[matplotlib.axes._axes.Axes]] = None,
    chart: bool = False,
) -> None
{{< /highlight >}}

.. raw:: html

    <p>
    Display total amount of coins held on exchange addresses in units and percentage.
    [Source: https://glassnode.org]
    </p>

* **Parameters**

    symbol : str
        Asset to search active addresses (e.g., BTC)
    exchange : str
        Exchange to check net position change (possible values are: aggregated, binance, bittrex,
        coinex, gate.io, gemini, huobi, kucoin, poloniex, bibox, bigone, bitfinex, hitbtc, kraken,
        okex, bithumb, zb.com, cobinhood, bitmex, bitstamp, coinbase, coincheck, luno)
    start_date : int
        Initial date timestamp (e.g., 1_614_556_800)
    end_date : int
        End date timestamp (e.g., 1_614_556_800)
    percentage : bool
        Show percentage instead of stacked value.
    export : str
        Export dataframe data to csv,json,xlsx file
    external_axes : Optional[List[plt.Axes]], optional
        External axes (2 axes are expected in the list), by default None
    chart: bool
       Flag to display chart

