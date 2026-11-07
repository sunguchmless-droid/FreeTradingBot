from src.signals import generate_signal


def test_buy_signal_requires_uptrend_and_rsi_between_50_and_70():
    signal, _ = generate_signal({
        "ema_20": 1.12,
        "ema_50": 1.11,
        "rsi_14": 60.0,
        "close": 1.12,
    })
    assert signal == "BUY"


def test_sell_signal_requires_downtrend_and_rsi_between_30_and_50():
    signal, _ = generate_signal({
        "ema_20": 1.10,
        "ema_50": 1.11,
        "rsi_14": 40.0,
        "close": 1.10,
    })
    assert signal == "SELL"


def test_signal_is_hold_when_conditions_do_not_match():
    signal, _ = generate_signal({
        "ema_20": 1.12,
        "ema_50": 1.11,
        "rsi_14": 75.0,
        "close": 1.12,
    })
    assert signal == "HOLD"


def test_signal_is_hold_when_indicator_values_are_missing():
    signal, _ = generate_signal({
        "ema_20": None,
        "ema_50": 1.11,
        "rsi_14": 60.0,
        "close": 1.12,
    })
    assert signal == "HOLD"
