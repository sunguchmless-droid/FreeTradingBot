"""Run one automatic demo-trading analysis cycle."""

import os

from dotenv import load_dotenv

from src.indicators import add_indicators
from src.mt5_data import connect, disconnect, get_candles
from src.signals import generate_signal
from src.execution import place_demo_trade


def main() -> None:
    load_dotenv()
    symbol = os.getenv("MT5_SYMBOL", "EURUSD").strip()
    timeframe = os.getenv("MT5_TIMEFRAME", "M15").strip().upper()
    bars = int(os.getenv("MT5_BARS", "300"))
    auto_demo = os.getenv("AUTO_DEMO_TRADING", "false").strip().lower() == "true"

    try:
        connect()
        candles = get_candles(symbol, timeframe, bars)
        analysed = add_indicators(candles)
        latest = analysed.iloc[-1].to_dict()
        signal, reason = generate_signal(latest)

        print("\\n=== FreeTradingBot | DEMO MODE ONLY ===")
        print(f"Symbol: {symbol}")
        print(f"Timeframe: {timeframe}")
        print(f"Last completed candle (UTC): {latest['time']}")
        print(f"Close: {latest['close']}")
        print(f"EMA 20: {latest['ema_20']:.5f}")
        print(f"EMA 50: {latest['ema_50']:.5f}")
        print(f"RSI 14: {latest['rsi_14']:.2f}")
        print(f"ATR 14: {latest['atr_14']:.5f}")
        print(f"Signal: {signal}")
        print(f"Reason: {reason}")

        if auto_demo:
            print(place_demo_trade(symbol, signal, float(latest["atr_14"])))
        else:
            print("AUTO_DEMO_TRADING is off; no order was placed.")
        print("Real accounts are blocked by an independent safety check.")
    finally:
        disconnect()


if __name__ == "__main__":
    main()
