"""Conservative, candle-based historical backtesting for the EMA/RSI strategy.

This module never connects to MT5 and never places orders. Input candles must be
chronological OHLC data with indicator columns added by src.indicators.
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
    """Simulate one position at a time; returns one row per completed trade.

    Signals use a completed candle and entries occur at the following candle's
    open. Spread is modeled as half-spread on each side of entry and exit.
    If SL and TP are both touched within one candle, SL is assumed first.
    PnL is expressed in R-multiples, not account currency.
    """
    required = {"open", "high", "low", "close", "ema_20", "ema_50", "rsi_14", "atr_14"}
    missing = required.difference(candles.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if len(candles) < 2:
        raise ValueError("At least 2 candles are required.")
    if initial_balance <= 0 or not 0 < risk_percent <= 1:
        raise ValueError("initial_balance must be positive and risk_percent must be in (0, 1].")
    if default_spread < 0 or point_size <= 0:
        raise ValueError("Spread must be non-negative and point_size must be positive.")

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
        half_spread = _half_spread(entry_bar, default_spread, point_size)
        raw_entry = float(entry_bar["open"])
        entry = raw_entry + half_spread if direction == 1 else raw_entry - half_spread
        stop = entry - direction * stop_distance
        target = entry + direction * stop_distance * REWARD_RISK_RATIO

        exit_price = None
        exit_reason = None
        exit_i = entry_i

        for j in range(entry_i, len(data)):
            bar = data.iloc[j]
            bar_half_spread = _half_spread(bar, default_spread, point_size)
            high = float(bar["high"])
            low = float(bar["low"])

            if direction == 1:
                stop_hit = low <= stop
                target_hit = high >= target
            else:
                # Short exits pay the ask, so add half-spread to OHLC.
                stop_hit = high + 2 * bar_half_spread >= stop
                target_hit = low + 2 * bar_half_spread <= target

            if stop_hit:
                raw_exit = float(bar["open"])
                if direction == 1:
                    exit_price = min(stop, raw_exit) - bar_half_spread if raw_exit < stop else stop - bar_half_spread
                else:
                    ask_open = raw_exit + 2 * bar_half_spread
                    exit_price = max(stop, ask_open)
                exit_reason = "stop_loss"
                exit_i = j
                break
            if target_hit:
                exit_price = target - bar_half_spread if direction == 1 else target
                exit_reason = "take_profit"
                exit_i = j
                break

        if exit_price is None:
            last = data.iloc[-1]
            last_half_spread = _half_spread(last, default_spread, point_size)
            exit_price = float(last["close"]) - direction * last_half_spread
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
            "return_percent_of_risk": r_multiple * risk_percent,
            "signal_reason": reason,
        })
        i = exit_i + 1

    return pd.DataFrame(trades)


def _half_spread(bar: pd.Series, default_spread: float, point_size: float) -> float:
    spread_points = bar.get("spread")
    if spread_points is not None and pd.notna(spread_points):
        spread = max(0.0, float(spread_points) * point_size)
    else:
        spread = default_spread
    return spread / 2.0


def summarize_backtest(trades: pd.DataFrame, *, initial_balance: float = 10_000.0) -> dict:
    """Return headline metrics from run_backtest output."""
    if trades.empty:
        return {
            "trades": 0, "win_rate_percent": 0.0, "profit_factor": 0.0,
            "net_r": 0.0, "max_drawdown_r": 0.0,
            "ending_balance": initial_balance,
        }

    results = trades["r_multiple"].astype(float)
    wins = results[results > 0]
    losses = results[results < 0]
    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
    equity_r = results.cumsum()
    peak_r = equity_r.cummax().clip(lower=0)
    drawdown_r = peak_r - equity_r
    risk_percent = float(trades["return_percent_of_risk"].iloc[0]) / float(results.iloc[0]) if results.iloc[0] != 0 else 0.01
    ending_balance = initial_balance * (1 + risk_percent) ** 0  # replaced below with sequential compounding
    balance = initial_balance
    for r_value in results:
        balance *= 1 + (risk_percent * float(r_value))
    return {
        "trades": int(len(trades)),
        "win_rate_percent": float((results > 0).mean() * 100),
        "profit_factor": profit_factor,
        "net_r": float(results.sum()),
        "max_drawdown_r": float(drawdown_r.max()),
        "ending_balance": float(balance),
    }
