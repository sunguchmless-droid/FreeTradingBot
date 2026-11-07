import pandas as pd
import pytest

from src.indicators import add_indicators


def sample_candles(count=100):
    close = [1.10 + (i * 0.0001) for i in range(count)]
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=count, freq="15min", tz="UTC"),
        "open": close,
        "high": [price + 0.0003 for price in close],
        "low": [price - 0.0003 for price in close],
        "close": close,
        "tick_volume": [100] * count,
    })


def test_add_indicators_creates_expected_columns():
    result = add_indicators(sample_candles())
    assert {"ema_20", "ema_50", "rsi_14", "atr_14"}.issubset(result.columns)
    assert pd.notna(result.iloc[-1]["ema_20"])
    assert pd.notna(result.iloc[-1]["ema_50"])
    assert pd.notna(result.iloc[-1]["rsi_14"])
    assert pd.notna(result.iloc[-1]["atr_14"])


def test_add_indicators_does_not_modify_input():
    candles = sample_candles()
    original_columns = list(candles.columns)
    add_indicators(candles)
    assert list(candles.columns) == original_columns


def test_add_indicators_rejects_too_few_candles():
    with pytest.raises(ValueError, match="At least 60 candles"):
        add_indicators(sample_candles(50))
