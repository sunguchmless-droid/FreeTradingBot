"""A basic educational EMA/RSI signal rule. Not a proven trading strategy."""


def generate_signal(latest: dict) -> tuple[str, str]:
    """Return (BUY/SELL/HOLD, explanation) from the latest indicator row."""
    required = ("ema_20", "ema_50", "rsi_14", "close")
    if any(key not in latest for key in required):
        raise ValueError(f"Latest candle must include: {', '.join(required)}")

    values = [latest[key] for key in required]
    if any(value is None for value in values):
        return "HOLD", "Indicator values are incomplete."

    ema_fast = float(latest["ema_20"])
    ema_slow = float(latest["ema_50"])
    rsi = float(latest["rsi_14"])

    if ema_fast > ema_slow and 50 <= rsi <= 70:
        return "BUY", f"EMA 20 is above EMA 50 and RSI is {rsi:.1f} (50–70)."
    if ema_fast < ema_slow and 30 <= rsi <= 50:
        return "SELL", f"EMA 20 is below EMA 50 and RSI is {rsi:.1f} (30–50)."
    return "HOLD", f"No setup: EMA 20={ema_fast:.5f}, EMA 50={ema_slow:.5f}, RSI={rsi:.1f}."
