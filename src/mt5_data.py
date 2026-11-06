"""Read market candles from the locally running MetaTrader 5 terminal."""

import MetaTrader5 as mt5
import pandas as pd

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


def connect() -> None:
    """Connect to the MT5 terminal already open on this computer."""
    if not mt5.initialize():
        code, message = mt5.last_error()
        raise RuntimeError(f"Could not connect to MetaTrader 5: {code} — {message}")


def get_candles(symbol: str, timeframe_name: str, bars: int = 300) -> pd.DataFrame:
    """Return recent candles as a DataFrame, excluding the still-forming candle."""
    if timeframe_name not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe_name}. Choose from {', '.join(TIMEFRAMES)}")
    if bars < 60:
        raise ValueError("Please request at least 60 candles for indicator calculations.")

    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}. Check the exact broker symbol in MT5 Market Watch.")

    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAMES[timeframe_name], 1, bars)
    if rates is None or len(rates) == 0:
        code, message = mt5.last_error()
        raise RuntimeError(f"No candle data returned for {symbol}: {code} — {message}")

    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame


def disconnect() -> None:
    """Shut down the MT5 connection cleanly."""
    mt5.shutdown()
