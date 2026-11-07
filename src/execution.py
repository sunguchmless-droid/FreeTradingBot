"""Strictly demo-only MT5 order execution with fixed risk controls."""

import math
import MetaTrader5 as mt5

MAGIC = 261107
MAX_RISK_PERCENT = 1.0
ATR_STOP_MULTIPLIER = 1.5
REWARD_RISK_RATIO = 2.0
DEVIATION_POINTS = 20


def _volume_for_risk(symbol_info, order_type: int, entry: float, stop: float, balance: float) -> float:
    risk_cash = balance * (MAX_RISK_PERCENT / 100.0)
    one_lot_pnl = mt5.order_calc_profit(order_type, symbol_info.name, 1.0, entry, stop)
    if one_lot_pnl is None or one_lot_pnl >= 0:
        raise RuntimeError(f"Could not calculate stop-loss risk: {mt5.last_error()}")
    raw_volume = risk_cash / abs(one_lot_pnl)
    step = symbol_info.volume_step
    volume = math.floor(raw_volume / step) * step
    volume = round(volume, 8)
    if volume < symbol_info.volume_min:
        raise RuntimeError(
            f"Calculated volume {volume} is below broker minimum {symbol_info.volume_min}; trade skipped."
        )
    return min(volume, symbol_info.volume_max)


def place_demo_trade(symbol: str, signal: str, atr: float) -> str:
    """Place one market order only after verifying the connected account is a demo account."""
    if signal not in ("BUY", "SELL"):
        return "No order: signal is HOLD."

    account = mt5.account_info()
    terminal = mt5.terminal_info()
    if account is None or terminal is None:
        raise RuntimeError("MT5 account or terminal information is unavailable.")
    if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise RuntimeError("SAFETY BLOCK: this bot only permits DEMO accounts.")
    if not terminal.trade_allowed or not account.trade_allowed:
        raise RuntimeError("Trading is disabled in the MT5 terminal or account.")
    if not math.isfinite(atr) or atr <= 0:
        raise RuntimeError("Invalid ATR; trade skipped.")

    existing = mt5.positions_get(symbol=symbol)
    if existing is None:
        raise RuntimeError(f"Could not check existing positions: {mt5.last_error()}")
    if len(existing) > 0:
        return f"No order: {len(existing)} open position(s) already exist for {symbol}."

    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None or info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        raise RuntimeError(f"{symbol} is unavailable for trading.")

    is_buy = signal == "BUY"
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    entry = tick.ask if is_buy else tick.bid
    stop_distance = atr * ATR_STOP_MULTIPLIER
    stop = entry - stop_distance if is_buy else entry + stop_distance
    target = entry + stop_distance * REWARD_RISK_RATIO if is_buy else entry - stop_distance * REWARD_RISK_RATIO
    entry, stop, target = (round(v, info.digits) for v in (entry, stop, target))

    min_stop = max(info.trade_stops_level, 0) * info.point
    if abs(entry - stop) < min_stop or abs(target - entry) < min_stop:
        raise RuntimeError("Broker minimum stop distance is too large; trade skipped.")

    volume = _volume_for_risk(info, order_type, entry, stop, account.balance)
    filling = mt5.ORDER_FILLING_IOC
    if info.filling_mode & 1:
        filling = mt5.ORDER_FILLING_FOK

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": entry,
        "sl": stop,
        "tp": target,
        "deviation": DEVIATION_POINTS,
        "magic": MAGIC,
        "comment": "FreeTradingBot DEMO",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }
    check = mt5.order_check(request)
    if check is None or check.retcode != 0:
        detail = "No response" if check is None else f"retcode={check.retcode}, comment={check.comment}"
        raise RuntimeError(f"Order pre-check failed; no order sent: {detail}")

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"Order send failed: {mt5.last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Order was not confirmed: retcode={result.retcode}, comment={result.comment}")
    return (
        f"DEMO ORDER PLACED: {signal} {symbol}, volume={volume}, "
        f"entry={entry}, SL={stop}, TP={target}, order={result.order}"
    )


def close_bot_positions_on_reverse_signal(symbol: str, signal: str) -> str:
    """Close only this bot's own demo position when an opposite signal appears."""
    if signal not in ("BUY", "SELL"):
        return "No closing action: signal is HOLD."

    account = mt5.account_info()
    if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise RuntimeError("SAFETY BLOCK: position management is permitted only on a DEMO account.")

    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        raise RuntimeError(f"Could not check positions: {mt5.last_error()}")

    messages = []
    for position in positions:
        if position.magic != MAGIC:
            continue

        opposite = (
            (position.type == mt5.POSITION_TYPE_BUY and signal == "SELL")
            or (position.type == mt5.POSITION_TYPE_SELL and signal == "BUY")
        )
        if not opposite:
            continue

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Could not get a fresh quote to close position {position.ticket}.")

        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        close_price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "position": position.ticket,
            "volume": position.volume,
            "type": close_type,
            "price": close_price,
            "deviation": DEVIATION_POINTS,
            "magic": MAGIC,
            "comment": "FreeTradingBot reverse-signal exit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        check = mt5.order_check(request)
        if check is None or check.retcode != 0:
            detail = "No response" if check is None else f"retcode={check.retcode}, comment={check.comment}"
            raise RuntimeError(f"Close pre-check failed for {position.ticket}: {detail}")

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            detail = mt5.last_error() if result is None else f"retcode={result.retcode}, comment={result.comment}"
            raise RuntimeError(f"Could not confirm close for position {position.ticket}: {detail}")
        messages.append(f"Closed bot position {position.ticket} after opposite {signal} signal.")

    return " ".join(messages) if messages else "No bot position required closing."
