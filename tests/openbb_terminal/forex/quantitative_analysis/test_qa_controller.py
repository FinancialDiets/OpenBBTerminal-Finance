# IMPORTATION STANDARD
import os

# IMPORTATION THIRDPARTY
import pandas as pd
import pytest

# IMPORTATION INTERNAL
from openbb_terminal.forex.quantitative_analysis import qa_controller
from tests.test_helpers import no_dfs


DF_PAIR = pd.DataFrame.from_dict(
    data={
        pd.Timestamp("2020-11-30 00:00:00"): {
            "Open": 75.69999694824219,
            "High": 76.08999633789062,
            "Low": 75.41999816894531,
            "Close": 75.75,
            "Adj Close": 71.90919494628906,
            "Volume": 5539100,
            "date_id": 1,
            "OC_High": 75.75,
            "OC_Low": 75.69999694824219,
        },
        pd.Timestamp("2020-12-01 00:00:00"): {
            "Open": 76.0199966430664,
            "High": 77.12999725341797,
            "Low": 75.69000244140625,
            "Close": 77.02999877929688,
            "Adj Close": 73.1242904663086,
            "Volume": 6791700,
            "date_id": 2,
            "OC_High": 77.02999877929688,
            "OC_Low": 76.0199966430664,
        },
    },
    orient="index",
)
EMPTY_DF = pd.DataFrame()
QA_CONTROLLER = qa_controller.QaController(
    from_symbol="MOCK_TICKER",
    to_symbol="MOCK_TICKER",
    data=DF_PAIR.copy(),
)


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [("User-Agent", None)],
        "filter_query_parameters": [
            ("period1", "MOCK_PERIOD_1"),
            ("period2", "MOCK_PERIOD_2"),
            ("date", "MOCK_DATE"),
        ],
    }


@pytest.mark.vcr(record_mode="none")
@pytest.mark.parametrize(
    "queue, expected",
    [
        (["load", "help"], ["help"]),
        (["quit", "help"], ["help"]),
    ],
)
def test_menu_with_queue(expected, mocker, queue):
    mocker.patch(
        target=(
            "openbb_terminal.forex.quantitative_analysis.qa_controller."
            "QaController.switch"
        ),
        return_value=["quit"],
    )
    result_menu = qa_controller.QaController(
        from_symbol="MOCK_TICKER",
        to_symbol="MOCK_TICKER",
        data=DF_PAIR.copy(),
        queue=queue,
    ).menu()

    assert result_menu == expected


@pytest.mark.vcr(record_mode="none")
def test_menu_without_queue_completion(mocker):
    # ENABLE AUTO-COMPLETION : HELPER_FUNCS.MENU
    mocker.patch(
        target="openbb_terminal.feature_flags.USE_PROMPT_TOOLKIT",
        new=True,
    )
    mocker.patch(
        target="openbb_terminal.parent_classes.session",
    )
    mocker.patch(
        target="openbb_terminal.parent_classes.session.prompt",
        return_value="quit",
    )

    # DISABLE AUTO-COMPLETION : CONTROLLER.COMPLETER
    mocker.patch.object(
        target=qa_controller.obbff,
        attribute="USE_PROMPT_TOOLKIT",
        new=True,
    )
    mocker.patch(
        target="openbb_terminal.forex.quantitative_analysis.qa_controller.session",
    )
    mocker.patch(
        target="openbb_terminal.forex.quantitative_analysis.qa_controller.session.prompt",
        return_value="quit",
    )

    result_menu = qa_controller.QaController(
        from_symbol="MOCK_TICKER",
        to_symbol="MOCK_TICKER",
        data=DF_PAIR.copy(),
        queue=None,
    ).menu()

    assert result_menu == ["help"]


@pytest.mark.vcr(record_mode="none")
@pytest.mark.parametrize(
    "mock_input",
    ["help", "homee help", "home help", "mock"],
)
def test_menu_without_queue_sys_exit(mock_input, mocker):
    # DISABLE AUTO-COMPLETION
    mocker.patch.object(
        target=qa_controller.obbff,
        attribute="USE_PROMPT_TOOLKIT",
        new=False,
    )
    mocker.patch(
        target="openbb_terminal.forex.quantitative_analysis.qa_controller.session",
        return_value=None,
    )

    # MOCK USER INPUT
    mocker.patch("builtins.input", return_value=mock_input)

    # MOCK SWITCH
    class SystemExitSideEffect:
        def __init__(self):
            self.first_call = True

        def __call__(self, *args, **kwargs):
            if self.first_call:
                self.first_call = False
                raise SystemExit()
            return ["quit"]

    mock_switch = mocker.Mock(side_effect=SystemExitSideEffect())
    mocker.patch(
        target=(
            "openbb_terminal.forex.quantitative_analysis.qa_controller."
            "QaController.switch"
        ),
        new=mock_switch,
    )

    result_menu = qa_controller.QaController(
        from_symbol="MOCK_TICKER",
        to_symbol="MOCK_TICKER",
        data=DF_PAIR.copy(),
        queue=None,
    ).menu()

    assert result_menu == ["help"]


@pytest.mark.vcr(record_mode="none")
@pytest.mark.record_stdout
def test_print_help():
    controller = qa_controller.QaController(
        from_symbol="MOCK_TICKER",
        to_symbol="MOCK_TICKER",
        data=DF_PAIR.copy(),
    )
    controller.print_help()


@pytest.mark.vcr(record_mode="none")
@pytest.mark.parametrize(
    "an_input, expected_queue",
    [
        ("", []),
        ("/help", ["home", "help"]),
        ("help/help", ["help", "help"]),
        ("q", ["quit"]),
        ("h", []),
        (
            "r",
            [
                "quit",
                "quit",
                "reset",
                "forex",
                "from MOCK_TICKER",
                "to MOCK_TICKER",
                "load",
                "qa",
            ],
        ),
    ],
)
def test_switch(an_input, expected_queue):
    controller = qa_controller.QaController(
        from_symbol="MOCK_TICKER",
        to_symbol="MOCK_TICKER",
        data=DF_PAIR.copy(),
        queue=None,
    )
    queue = controller.switch(an_input=an_input)

    assert queue == expected_queue


@pytest.mark.vcr(record_mode="none")
def test_call_cls(mocker):
    mocker.patch("os.system")
    controller = qa_controller.QaController(
        from_symbol="MOCK_TICKER",
        to_symbol="MOCK_TICKER",
        data=DF_PAIR.copy(),
    )
    controller.call_cls([])

    assert controller.queue == []
    os.system.assert_called_once_with("cls||clear")


@pytest.mark.vcr(record_mode="none")
@pytest.mark.parametrize(
    "func, queue, expected_queue",
    [
        (
            "call_exit",
            [],
            [
                "quit",
                "quit",
                "quit",
            ],
        ),
        ("call_exit", ["help"], ["quit", "quit", "quit", "help"]),
        ("call_home", [], ["quit", "quit"]),
        ("call_help", [], []),
        ("call_quit", [], ["quit"]),
        ("call_quit", ["help"], ["quit", "help"]),
        (
            "call_reset",
            [],
            [
                "quit",
                "quit",
                "reset",
                "forex",
                "from MOCK_TICKER",
                "to MOCK_TICKER",
                "load",
                "qa",
            ],
        ),
        (
            "call_reset",
            ["help"],
            [
                "quit",
                "quit",
                "reset",
                "forex",
                "from MOCK_TICKER",
                "to MOCK_TICKER",
                "load",
                "qa",
                "help",
            ],
        ),
    ],
)
def test_call_func_expect_queue(expected_queue, queue, func):
    controller = qa_controller.QaController(
        from_symbol="MOCK_TICKER",
        to_symbol="MOCK_TICKER",
        data=DF_PAIR.copy(),
        queue=queue,
    )
    result = getattr(controller, func)([])

    assert result is None
    assert controller.queue == expected_queue


@pytest.mark.vcr(record_mode="none")
@pytest.mark.parametrize(
    "tested_func, other_args, mocked_func, called_args, called_kwargs",
    [
        (
            "call_pick",
            [QA_CONTROLLER.target],
            "",
            [],
            dict(),
        ),
        (
            "call_raw",
            ["--limit=1", "--reverse", "--export=csv"],
            "qa_view.display_raw",
            [],
            dict(
                data=QA_CONTROLLER.data,
                limit=1,
                sortby="",
                ascend=True,
                export="csv",
            ),
        ),
        (
            "call_summary",
            ["--export=csv"],
            "qa_view.display_summary",
            [],
            dict(
                data=QA_CONTROLLER.data,
                export="csv",
            ),
        ),
        (
            "call_hist",
            ["--bins=1"],
            "qa_view.display_hist",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                bins=1,
            ),
        ),
        (
            "call_cdf",
            ["--export=csv"],
            "qa_view.display_cdf",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                export="csv",
            ),
        ),
        (
            "call_bw",
            ["--yearly"],
            "qa_view.display_bw",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                yearly=True,
            ),
        ),
        (
            "call_rolling",
            ["--window=1", "--export=csv"],
            "rolling_view.display_mean_std",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                window=1,
                export="csv",
            ),
        ),
        (
            "call_decompose",
            ["--multiplicative", "--export=csv"],
            "qa_view.display_seasonal",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                multiplicative=True,
                export="csv",
            ),
        ),
        (
            "call_cusum",
            ["--threshold=1", "--drift=2"],
            "qa_view.display_cusum",
            [],
            dict(
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                threshold=1,
                drift=2,
            ),
        ),
        (
            "call_acf",
            ["--lags=1"],
            "qa_view.display_acf",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                lags=1,
            ),
        ),
        (
            "call_spread",
            ["--window=1", "--export=csv"],
            "rolling_view.display_spread",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                window=1,
                export="csv",
            ),
        ),
        (
            "call_quantile",
            ["--window=1", "--quantile=0.1", "--export=csv"],
            "rolling_view.display_quantile",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                window=1,
                quantile=0.1,
                export="csv",
            ),
        ),
        (
            "call_skew",
            ["--window=1", "--export=csv"],
            "rolling_view.display_skew",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                window=1,
                export="csv",
            ),
        ),
        (
            "call_kurtosis",
            ["--window=1", "--export=csv"],
            "rolling_view.display_kurtosis",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                window=1,
                export="csv",
            ),
        ),
        (
            "call_normality",
            ["--export=csv"],
            "qa_view.display_normality",
            [],
            dict(
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                export="csv",
            ),
        ),
        (
            "call_qqplot",
            [],
            "qa_view.display_qqplot",
            [],
            dict(
                symbol=QA_CONTROLLER.ticker,
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
            ),
        ),
        (
            "call_unitroot",
            ["--fuller_reg=ctt", "--kps_reg=ct", "--export=csv"],
            "qa_view.display_unitroot",
            [],
            dict(
                data=QA_CONTROLLER.data,
                target=QA_CONTROLLER.target,
                fuller_reg="ctt",
                kpss_reg="ct",
                export="csv",
            ),
        ),
    ],
)
def test_call_func(
    tested_func, mocked_func, other_args, called_args, called_kwargs, mocker
):
    if mocked_func:
        mock = mocker.Mock()
        mocker.patch(
            "openbb_terminal.forex.quantitative_analysis.qa_controller." + mocked_func,
            new=mock,
        )

        getattr(QA_CONTROLLER, tested_func)(other_args=other_args)

        if called_args or called_kwargs and no_dfs(called_args, called_kwargs):
            mock.assert_called_once_with(*called_args, **called_kwargs)
        else:
            mock.assert_called_once()
    else:
        getattr(QA_CONTROLLER, tested_func)(other_args=other_args)


@pytest.mark.vcr(record_mode="none")
@pytest.mark.parametrize(
    "from_symbol, to_symbol, expected",
    [
        (None, None, ["forex", "from None", "to None", "load", "qa"]),
        ("MOCK_FROM", None, ["forex", "from MOCK_FROM", "to None", "load", "qa"]),
        (None, "MOCK_TO", ["forex", "from None", "to MOCK_TO", "load", "qa"]),
        (
            "MOCK_FROM",
            "MOCK_TO",
            ["forex", "from MOCK_FROM", "to MOCK_TO", "load", "qa"],
        ),
    ],
)
def test_custom_reset(expected, from_symbol, to_symbol):
    controller = qa_controller.QaController(
        from_symbol=None,
        to_symbol=None,
        data=DF_PAIR.copy(),
    )
    controller.from_symbol = from_symbol
    controller.to_symbol = to_symbol

    result = controller.custom_reset()

    assert result == expected
