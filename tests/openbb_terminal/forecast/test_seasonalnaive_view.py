import pytest

try:
    from openbb_terminal.forecast import seasonalnaive_view
except ImportError:
    pytest.skip(allow_module_level=True)


def test_display_seasonalnaive_forecast(tsla_csv):
    with pytest.raises(AttributeError):
        seasonalnaive_view.display_seasonalnaive_forecast(
            tsla_csv,
            target_column="close",
            seasonal_periods=3,
            n_predict=1,
            start_window=0.5,
            forecast_horizon=1,
        )
