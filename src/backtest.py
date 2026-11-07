"""Conservative, candle-based historical backtesting for the EMA/RSI strategy.

This module never connects to MT5 and never places orders. Input candles must
be chronological OHLC data with indicator columns added by src.indicators.

Price convention: OHLC values are BID prices (as in typical MT5 Forex rates).
Spread is added to BUY entries and SELL exits; it is not split in half.
"""
from __future__ import annotations

import math
import pandas as pd

from src.signals import generate_signal

ATR_STOP_MULTIPLIER = 1.5
REWARD_RISK_RATIO = 2.0


def run_backtest(
    candles: pd.DataFrame,
    *,
    initial_balance: float = 10_000.0,
    risk_percent: float = 1.0,
    default_spread: float = 0.0001,
    point_size: float = 0.00001,
) -> pd.DataFrame:
    """Simulate one position at a time; return one row per completed trade.

    Signals use a completed candle and entries occur at the following candle's
    open. OHLC is assumed to be BID data. BUY entries pay the ask (bid + spread);
    SELL exits pay the ask. SL is assumed first when SL and TP are both touched
    in one candle. A gap through a stop is filled at the worse opening price.
    """
    required = {"open", "high", "low", "close", "ema_20", "ema_50", "rsi_14", "atr_14"}
    missing = required.difference(candles.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if len(candles) < 2:
        raise ValueError("At least 2 candles are required.")
    if not math.isfinite(initial_balance) or initial_balance <= 0:
        raise ValueError("initial_balance must be positive and finite.")
    if not math.isfinite(risk_percent) or not 0 < risk_percent <= 1:
        raise ValueError("risk_percent must be in (0, 1] percent.")
    if not math.isfinite(default_spread) or default_spread < 0:
        raise ValueError("default_spread must be non-negative and finite.")
    if not math.isfinite(point_size) or point_size <= 0:
        raise ValueError("point_size must be positive and finite.")

    data = candles.reset_index(drop=True).copy()
    trades: list[dict] = []
    i = 0

    while i < len(data) - 1:
        signal, reason = generate_signal(data.iloc[i].to_dict())
        if signal not in ("BUY", "SELL"):
            i += 1
            continue

        entry_i = i + 1
        entry_bar = data.iloc[entry_i]
        atr = float(data.iloc[i]["atr_14"])
        if not math.isfinite(atr) or atr <= 0:
            i += 1
            continue

        direction = 1 if signal == "BUY" else -1
        stop_distance = atr * ATR_STOP_MULTIPLIER
        entry_spread = _spread(entry_bar, default_spread, point_size)
        raw_entry_bid = float(entry_bar["open"])
        # BID OHLC: a BUY pays ask; a SELL enters at bid.
        entry = raw_entry_bid + entry_spread if direction == 1 else raw_entry_bid
        stop = entry - direction * stop_distance
        target = entry + direction * stop_distance * REWARD_RISK_RATIO

        exit_price = None
        exit_reason = None
        exit_i = entry_i

        for j in range(entry_i, len(data)):
            bar = data.iloc[j]
            spread = _spread(bar, default_spread, point_size)
            raw_open = float(bar["open"])
            high_bid = float(bar["high"])
            low_bid = float(bar["low"])

            if direction == 1:
                stop_hit = low_bid <= stop
                target_hit = high_bid >= target
            else:
                high_ask = high_bid + spread
                low_ask = low_bid + spread
                stop_hit = high_ask >= stop
                target_hit = low_ask <= target

            if stop_hit:
                if direction == 1:
                    exit_price = min(stop, raw_open)
                else:
                    exit_price = max(stop, raw_open + spread)
                exit_reason = "stop_loss"
                exit_i = j
                break

            if target_hit:
                if direction == 1:
                    exit_price = max(target, raw_open) if raw_open > target else target
                else:
                    ask_open = raw_open + spread
                    exit_price = min(target, ask_open) if ask_open < target else target
                exit_reason = "take_profit"
                exit_i = j
                break

        if exit_price is None:
            last = data.iloc[-1]
            last_bid = float(last["close"])
            last_spread = _spread(last, default_spread, point_size)
            exit_price = last_bid if direction == 1 else last_bid + last_spread
            exit_reason = "end_of_data"
            exit_i = len(data) - 1

        pnl_price = direction * (exit_price - entry)
        r_multiple = pnl_price / stop_distance
        trades.append({
            "signal": signal,
            "signal_time": data.iloc[i]["time"] if "time" in data.columns else i,
            "entry_time": entry_bar["time"] if "time" in data.columns else entry_i,
            "exit_time": data.iloc[exit_i]["time"] if "time" in data.columns else exit_i,
            "entry_price": entry,
            "exit_price": exit_price,
            "stop_loss": stop,
            "take_profit": target,
            "exit_reason": exit_reason,
            "pnl_price": pnl_price,
            "r_multiple": r_multiple,
            "risk_percent": risk_percent,
            "return_percent_of_risk": r_multiple * risk_percent,
            "signal_reason": reason,
        })
        i = exit_i + 1

    return pd.DataFrame(trades)


def _spread(bar: pd.Series, default_spread: float, point_size: float) -> float:
    spread_points = bar.get("spread")
    if spread_points is not None and pd.notna(spread_points):
        return max(0.0, float(spread_points) * point_size)
    return default_spread


def summarize_backtest(trades: pd.DataFrame, *, initial_balance: float = 10_000.0) -> dict:
    """Return trade statistics and compounded equity metrics."""
    if initial_balance <= 0 or not math.isfinite(initial_balance):
        raise ValueError("initial_balance must be positive and finite.")
    if trades.empty:
        return {
            "trades": 0, "win_rate_percent": 0.0, "profit_factor": 0.0,
            "net_r": 0.0, "max_drawdown_r": 0.0, "max_drawdown_percent": 0.0,
            "ending_balance": initial_balance,
        }
    if "r_multiple" not in trades.columns or "risk_percent" not in trades.columns:
        raise ValueError("trades must contain r_multiple and risk_percent columns.")

    results = trades["r_multiple"].astype(float)
    risk_rates = trades["risk_percent"].astype(float)
    if not results.map(math.isfinite).all():
        raise ValueError("r_multiple values must be finite.")
    if not risk_rates.map(lambda value: math.isfinite(value) and 0 < value <= 1).all():
        raise ValueError("risk_percent values must be in (0, 1] percent.")

    wins = results[results > 0]
    losses = results[results < 0]
    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)

    equity = initial_balance
    peak_equity = initial_balance
    max_drawdown_percent = 0.0
    equity_r = 0.0
    peak_r = 0.0
    max_drawdown_r = 0.0
    for r_value, risk_rate in zip(results, risk_rates):
        equity *= 1.0 + (float(r_value) * float(risk_rate) / 100.0)
        peak_equity = max(peak_equity, equity)
        if peak_equity > 0:
            max_drawdown_percent = max(max_drawdown_percent, (peak_equity - equity) / peak_equity * 100.0)
        equity_r += float(r_value)
        peak_r = max(peak_r, equity_r)
        max_drawdown_r = max(max_drawdown_r, peak_r - equity_r)

    return {
        "trades": int(len(trades)),
        "win_rate_percent": float((results > 0).mean() * 100),
        "profit_factor": profit_factor,
        "net_r": float(results.sum()),
        "max_drawdown_r": float(max_drawdown_r),
        "max_drawdown_percent": float(max_drawdown_percent),
        "ending_balance": float(equity),
    }
