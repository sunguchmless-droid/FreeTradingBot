import pandas as pd
import pytest

from src.backtest import run_backtest, summarize_backtest


def make_candles(rows):
    return pd.DataFrame(rows)


def base_row(**updates):
    row = {
        "open": 1.1000, "high": 1.1010, "low": 1.0990, "close": 1.1000,
        "ema_20": 1.101, "ema_50": 1.100, "rsi_14": 60, "atr_14": 0.0010,
    }
    row.update(updates)
    return row


def test_enters_on_next_candle_and_hits_take_profit():
    candles = make_candles([
        base_row(),
        base_row(high=1.1040, low=1.0995, close=1.1030),
    ])
    trades = run_backtest(candles, default_spread=0)
    assert len(trades) == 1
    assert trades.iloc[0]["exit_reason"] == "take_profit"
    assert trades.iloc[0]["r_multiple"] == pytest.approx(2.0)


def test_stop_loss_wins_if_stop_and_target_hit_same_candle():
    candles = make_candles([
        base_row(),
        base_row(high=1.1040, low=1.0970, close=1.1010),
    ])
    trades = run_backtest(candles, default_spread=0)
    assert trades.iloc[0]["exit_reason"] == "stop_loss"
    assert trades.iloc[0]["r_multiple"] == pytest.approx(-1.0)


def test_hold_signal_creates_no_trade():
    candles = make_candles([
        base_row(rsi_14=75),
        base_row(rsi_14=75),
    ])
    assert run_backtest(candles, default_spread=0).empty


def test_buy_pays_full_spread_on_entry_and_exits_at_bid():
    candles = make_candles([
        base_row(),
        base_row(open=1.1000, high=1.1010, low=1.0990, close=1.1000),
    ])
    trades = run_backtest(candles, default_spread=0.0002)
    trade = trades.iloc[0]
    assert trade["entry_price"] == pytest.approx(1.1002)
    assert trade["exit_price"] == pytest.approx(1.1000)
    assert trade["r_multiple"] < 0


def test_sell_pays_spread_on_exit_and_uses_ask_for_stop():
    candles = make_candles([
        base_row(ema_20=1.099, ema_50=1.100, rsi_14=40),
        base_row(open=1.1000, high=1.1010, low=1.0990, close=1.1000,
                 ema_20=1.099, ema_50=1.100, rsi_14=40),
    ])
    trades = run_backtest(candles, default_spread=0.0002)
    trade = trades.iloc[0]
    assert trade["entry_price"] == pytest.approx(1.1000)
    assert trade["exit_price"] == pytest.approx(1.1002)
    assert trade["r_multiple"] < 0


def test_summary_returns_expected_metrics_and_compounds_risk():
    trades = pd.DataFrame({
        "r_multiple": [2.0, -1.0],
        "risk_percent": [1.0, 1.0],
    })
    report = summarize_backtest(trades)
    assert report["trades"] == 2
    assert report["win_rate_percent"] == 50
    assert report["profit_factor"] == 2
    assert report["net_r"] == 1
    assert report["ending_balance"] == pytest.approx(10_098.0)
    assert report["max_drawdown_percent"] == pytest.approx(1.0)


def test_summary_rejects_missing_risk_metadata():
    trades = pd.DataFrame({"r_multiple": [1.0]})
    with pytest.raises(ValueError, match="risk_percent"):
        summarize_backtest(trades)


def test_empty_summary_preserves_balance():
    report = summarize_backtest(pd.DataFrame(), initial_balance=5000)
    assert report["ending_balance"] == 5000
