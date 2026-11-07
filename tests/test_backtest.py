import pandas as pd
import pytest

from src.backtest import run_backtest, summarize_backtest


def make_candles(rows):
    return pd.DataFrame(rows)


def test_enters_on_next_candle_and_hits_take_profit():
    candles = make_candles([
        {"open": 1.1000, "high": 1.1010, "low": 1.0990, "close": 1.1000, "ema_20": 1.101, "ema_50": 1.100, "rsi_14": 60, "atr_14": 0.0010},
        {"open": 1.1000, "high": 1.1040, "low": 1.0995, "close": 1.1030, "ema_20": 1.101, "ema_50": 1.100, "rsi_14": 60, "atr_14": 0.0010},
    ])
    trades = run_backtest(candles, default_spread=0)
    assert len(trades) == 1
    assert trades.iloc[0]["exit_reason"] == "take_profit"
    assert trades.iloc[0]["r_multiple"] == pytest.approx(2.0)


def test_stop_loss_wins_if_stop_and_target_hit_same_candle():
    candles = make_candles([
        {"open": 1.1000, "high": 1.1010, "low": 1.0990, "close": 1.1000, "ema_20": 1.101, "ema_50": 1.100, "rsi_14": 60, "atr_14": 0.0010},
        {"open": 1.1000, "high": 1.1040, "low": 1.0970, "close": 1.1010, "ema_20": 1.101, "ema_50": 1.100, "rsi_14": 60, "atr_14": 0.0010},
    ])
    trades = run_backtest(candles, default_spread=0)
    assert trades.iloc[0]["exit_reason"] == "stop_loss"
    assert trades.iloc[0]["r_multiple"] == pytest.approx(-1.0)


def test_hold_signal_creates_no_trade():
    candles = make_candles([
        {"open": 1.1, "high": 1.101, "low": 1.099, "close": 1.1, "ema_20": 1.101, "ema_50": 1.100, "rsi_14": 75, "atr_14": 0.001},
        {"open": 1.1, "high": 1.101, "low": 1.099, "close": 1.1, "ema_20": 1.101, "ema_50": 1.100, "rsi_14": 75, "atr_14": 0.001},
    ])
    assert run_backtest(candles, default_spread=0).empty


def test_summary_returns_expected_metrics():
    trades = pd.DataFrame({"r_multiple": [2.0, -1.0], "return_percent_of_risk": [2.0, -1.0]})
    report = summarize_backtest(trades)
    assert report["trades"] == 2
    assert report["win_rate_percent"] == 50
    assert report["profit_factor"] == 2
    assert report["net_r"] == 1
