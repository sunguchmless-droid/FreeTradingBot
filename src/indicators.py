"""Simple, transparent technical indicator calculations."""

import pandas as pd


def add_indicators(candles: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with EMA 20, EMA 50, and RSI 14 columns added."""
    if "close" not in candles.columns:
        raise ValueError("Candle data must contain a close column.")
    if len(candles) < 60:
        raise ValueError("At least 60 candles are required.")

    data = candles.copy()
    data["ema_20"] = data["close"].ewm(span=20, adjust=False).mean()
    data["ema_50"] = data["close"].ewm(span=50, adjust=False).mean()

    change = data["close"].diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    average_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    relative_strength = average_gain / average_loss.where(average_loss != 0)
    data["rsi_14"] = 100 - (100 / (1 + relative_strength))
    data.loc[(average_loss == 0) & (average_gain > 0), "rsi_14"] = 100
    data.loc[(average_loss == 0) & (average_gain == 0), "rsi_14"] = 50
    return data
