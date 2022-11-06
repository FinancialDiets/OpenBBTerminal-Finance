# IMPORTATION STANDARD
from datetime import datetime
import os

# IMPORTATION THIRDPARTY
import pytest

# IMPORTATION INTERNAL
from openbb_terminal.stocks import stocks_helper
from openbb_terminal.stocks import stocks_views
from openbb_terminal import helper_funcs


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_query_parameters": [
            ("period1", "MOCK_PERIOD_1"),
            ("period2", "MOCK_PERIOD_2"),
            ("date", "MOCK_DATE"),
            ("token", "MOCK_TOKEN"),
            ("apikey", "MOCK_API_KEY"),
            ("apiKey", "MOCK_API_KEY2"),
        ]
    }


@pytest.mark.vcr
def test_quote():
    stocks_views.display_quote("GME")


@pytest.mark.default_cassette("test_search")
@pytest.mark.vcr
@pytest.mark.record_stdout
@pytest.mark.parametrize(
    "use_tab",
    [True, False],
)
def test_search(mocker, use_tab):
    mocker.patch.object(
        target=helper_funcs.obbff, attribute="USE_TABULATE_DF", new=use_tab
    )
    stocks_helper.search(
        query="sonae",
        country="Portugal",
        sector="",
        industry="",
        exchange_country="",
        limit=5,
        export="",
    )


@pytest.mark.vcr
@pytest.mark.parametrize(
    "interval, source",
    [
        (1440, "AlphaVantage"),
        (1440, "IEXCloud"),
        (1440, "YahooFinance"),
        (60, "YahooFinance"),
        # (1440, "Polygon"),
        # (60, "Polygon"),
    ],
)
def test_load(interval, recorder, source):
    ticker = "GME"
    start = datetime.strptime("2021-12-01", "%Y-%m-%d")
    end = datetime.strptime("2021-12-02", "%Y-%m-%d")
    prepost = False
    result_df = stocks_helper.load(
        symbol=ticker,
        start_date=start,
        interval=interval,
        end_date=end,
        prepost=prepost,
        source=source,
    )
    recorder.capture(result_df)


@pytest.mark.vcr
@pytest.mark.parametrize(
    "weekly, monthly",
    [(True, True), (True, False), (False, True)],
)
def test_load_week_or_month(recorder, weekly, monthly):
    ticker = "AAPL"
    start = datetime.strptime("2019-12-01", "%Y-%m-%d")
    end = datetime.strptime("2021-12-02", "%Y-%m-%d")
    prepost = False
    result_df = stocks_helper.load(
        symbol=ticker,
        start_date=start,
        interval=1440,
        end_date=end,
        prepost=prepost,
        source="YahooFinance",
        weekly=weekly,
        monthly=monthly,
    )
    recorder.capture(result_df)


@pytest.mark.vcr
@pytest.mark.record_stdout
@pytest.mark.parametrize(
    "path",
    [os.path.join(os.path.join("random_folder", "test69.csv"))],
)
def test_load_custom_output_wrong_path(path):
    stocks_helper.load_custom(path)


@pytest.mark.default_cassette("test_display_candle")
@pytest.mark.vcr
@pytest.mark.parametrize(
    "use_matplotlib",
    [True, False],
)
def test_display_candle(mocker, use_matplotlib):
    # MOCK VISUALIZE_OUTPUT
    mocker.patch(target="openbb_terminal.helper_classes.TerminalStyle.visualize_output")

    mocker.patch("plotly.basedatatypes.BaseFigure.show")

    # LOAD DATA
    ticker = "GME"
    start = datetime.strptime("2020-12-01", "%Y-%m-%d")
    interval = 1440
    end = datetime.strptime("2020-12-08", "%Y-%m-%d")
    prepost = False
    source = "YahooFinance"
    df_stock = stocks_helper.load(
        symbol=ticker,
        start_date=start,
        interval=interval,
        end_date=end,
        prepost=prepost,
        source=source,
    )

    # PROCESS DATA
    df_stock = stocks_helper.process_candle(data=df_stock)

    # DISPLAY CANDLE
    s_ticker = "GME"
    intraday = False
    stocks_helper.display_candle(
        symbol=s_ticker,
        data=df_stock,
        use_matplotlib=use_matplotlib,
        intraday=intraday,
    )


@pytest.mark.vcr
def test_load_ticker(recorder):
    ticker = "PM"
    start = datetime.strptime("2020-12-01", "%Y-%m-%d")
    end = datetime.strptime("2020-12-02", "%Y-%m-%d")
    result_df = stocks_helper.load_ticker(ticker=ticker, start_date=start, end_date=end)
    recorder.capture(result_df)
