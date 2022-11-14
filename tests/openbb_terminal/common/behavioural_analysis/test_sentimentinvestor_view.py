# IMPORTATION THIRDPARTY
import pandas as pd
import pytest

# IMPORTATION INTERNAL
from openbb_terminal.common.behavioural_analysis import sentimentinvestor_view


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_query_parameters": [
            ("token", "MOCK_TOKEN"),
        ],
    }


@pytest.mark.vcr
@pytest.mark.record_stdout
def test_display_historical(mocker):
    # MOCK VISUALIZE_OUTPUT
    mocker.patch(target="openbb_terminal.helper_classes.TerminalStyle.visualize_output")
    sentimentinvestor_view.display_historical(
        symbol="AAPL",
        start_date="2021-12-12",
        end_date="2021-12-15",
        export="",
        raw=True,
    )


@pytest.mark.vcr(record_mode="none")
@pytest.mark.record_stdout
def test_display_historical_supported_ticker(mocker):
    view = "openbb_terminal.common.behavioural_analysis.sentimentinvestor_view"
    # MOCK CHECK_SUPPORTED_TICKER
    mocker.patch(
        target=f"{view}.sentimentinvestor_model.check_supported_ticker",
        return_value=False,
    )

    sentimentinvestor_view.display_historical(
        symbol="AAPL",
        start_date="2021-12-12",
        end_date="2021-12-15",
        export="",
        raw=True,
    )


@pytest.mark.vcr(record_mode="none")
@pytest.mark.record_stdout
def test_display_historical_empty_df(mocker):
    view = "openbb_terminal.common.behavioural_analysis.sentimentinvestor_view"

    # MOCK CHECK_SUPPORTED_TICKER
    mocker.patch(
        target=f"{view}.sentimentinvestor_model.check_supported_ticker",
        return_value=True,
    )

    # MOCK GET_HISTORICAL
    mocker.patch(
        target=f"{view}.sentimentinvestor_model.get_historical",
        return_value=pd.DataFrame(),
    )

    sentimentinvestor_view.display_historical(
        symbol="AAPL",
        start_date="2021-12-12",
        end_date="2021-12-15",
        export="",
        raw=True,
    )


# This api website seems to have stop working, but I have no key to check.
@pytest.mark.skip
@pytest.mark.vcr
@pytest.mark.record_stdout
def test_display_trending():
    sentimentinvestor_view.display_trending(
        start_date="2021-12-12",
        hour=9,
        number=10,
        limit=10,
        export="",
    )


@pytest.mark.vcr(record_mode="none")
@pytest.mark.record_stdout
def test_display_trending_empty_df(mocker):
    view = "openbb_terminal.common.behavioural_analysis.sentimentinvestor_view"

    # MOCK GET_HISTORICAL
    mocker.patch(
        target=f"{view}.sentimentinvestor_model.get_trending",
        return_value=pd.DataFrame(),
    )

    sentimentinvestor_view.display_trending(
        start_date="2021-12-12",
        hour=9,
        number=10,
        limit=10,
        export="",
    )
