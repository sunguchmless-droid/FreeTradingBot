"""Continuously monitor completed candles and manage demo-only trades."""

import os
import time

from dotenv import load_dotenv

from src.indicators import add_indicators
from src.mt5_data import connect, disconnect, get_candles
from src.signals import generate_signal
from src.execution import place_demo_trade, close_bot_positions_on_reverse_signal


def main() -> None:
    load_dotenv()
    symbol = os.getenv("MT5_SYMBOL", "EURUSD").strip()
    timeframe = os.getenv("MT5_TIMEFRAME", "M15").strip().upper()
    bars = int(os.getenv("MT5_BARS", "300"))
    poll_seconds = max(2, int(os.getenv("POLL_SECONDS", "5")))
    auto_demo = os.getenv("AUTO_DEMO_TRADING", "false").strip().lower() == "true"
    last_processed_candle = None

    print("=== FreeTradingBot | DEMO MODE ONLY ===")
    print(f"Monitoring {symbol} on {timeframe}; checking every {poll_seconds} seconds.")
    print("Press CTRL+C to stop. AUTO_DEMO_TRADING=" + str(auto_demo).lower())

    try:
        connect()
        while True:
            candles = get_candles(symbol, timeframe, bars)
            analysed = add_indicators(candles)
            latest = analysed.iloc[-1].to_dict()
            candle_time = latest["time"]

            # Process each completed candle once, even though we poll the terminal frequently.
            if candle_time != last_processed_candle:
                last_processed_candle = candle_time
                signal, reason = generate_signal(latest)

                print("\\n--- New completed candle ---")
                print(f"Time (UTC): {candle_time}")
                print(f"Close: {latest['close']}")
                print(f"EMA 20: {latest['ema_20']:.5f} | EMA 50: {latest['ema_50']:.5f}")
                print(f"RSI 14: {latest['rsi_14']:.2f} | ATR 14: {latest['atr_14']:.5f}")
                print(f"Signal: {signal} — {reason}")

                if auto_demo:
                    close_message = close_bot_positions_on_reverse_signal(symbol, signal)
                    print(close_message)
                    # Do not close and reopen on the same candle. A new entry can be considered
                    # on a later completed candle after MT5 confirms the close.
                    if not close_message.startswith("Closed bot position"):
                        print(place_demo_trade(symbol, signal, float(latest["atr_14"])))
                else:
                    print("AUTO_DEMO_TRADING is off; no orders will be placed or closed.")

            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("\\nBot stopped by user.")
    finally:
        disconnect()


if __name__ == "__main__":
    main()
