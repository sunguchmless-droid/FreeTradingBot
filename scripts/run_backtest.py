"""Run a historical-only backtest using candles downloaded from MT5.

This script reads market history and writes reports. It never places orders.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, time, timezone
from pathlib import Path

from src.backtest import run_backtest, summarize_backtest
from src.indicators import add_indicators


def parse_utc_date(value: str, *, end_of_day: bool = False) -> datetime:
    """Parse YYYY-MM-DD as a UTC date boundary."""
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    boundary = time.max if end_of_day else time.min
    return datetime.combine(parsed, boundary, tzinfo=timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MT5 candles and run a historical-only backtest.")
    parser.add_argument("--symbol", default="EURUSD", help="Exact symbol name shown by your MT5 broker.")
    parser.add_argument("--timeframe", default="M15", choices=("M1", "M5", "M15", "M30", "H1", "H4", "D1"))
    parser.add_argument("--start", required=True, help="First UTC date, YYYY-MM-DD.")
    parser.add_argument("--end", required=True, help="Last UTC date, YYYY-MM-DD.")
    parser.add_argument("--balance", type=float, default=10_000.0, help="Starting simulated balance.")
    parser.add_argument("--risk", type=float, default=1.0, help="Risk per trade as percent of equity; default 1.")
    parser.add_argument(
        "--fallback-spread",
        type=float,
        default=0.0001,
        help="Fallback spread in price units when MT5 candle spread is unavailable; default suits EURUSD roughly.",
    )
    parser.add_argument("--output", default="backtest_results", help="Folder for CSV and JSON reports.")
    args = parser.parse_args()

    start = parse_utc_date(args.start)
    end = parse_utc_date(args.end, end_of_day=True)
    if start >= end:
        parser.error("--start must be earlier than --end.")
    if args.balance <= 0 or not math.isfinite(args.balance):
        parser.error("--balance must be positive and finite.")
    if not 0 < args.risk <= 1 or not math.isfinite(args.risk):
        parser.error("--risk must be greater than 0 and no more than 1 percent.")
    if args.fallback_spread < 0 or not math.isfinite(args.fallback_spread):
        parser.error("--fallback-spread must be non-negative and finite.")

    # Import MT5 only when the local Windows script is actually run.
    import MetaTrader5 as mt5
    from src.mt5_data import connect, disconnect, get_historical_candles

    try:
        connect()
        info = mt5.symbol_info(args.symbol)
        if info is None:
            raise RuntimeError(f"MT5 does not recognise {args.symbol}. Check Market Watch for the exact symbol.")
        candles = get_historical_candles(args.symbol, args.timeframe, start, end)
        if len(candles) < 60:
            raise RuntimeError(f"Only {len(candles)} candles were returned; at least 60 are needed.")

        analysed = add_indicators(candles)
        trades = run_backtest(
            analysed,
            initial_balance=args.balance,
            risk_percent=args.risk,
            default_spread=args.fallback_spread,
            point_size=float(info.point),
        )
        report = summarize_backtest(trades, initial_balance=args.balance)
        if isinstance(report.get("profit_factor"), float) and not math.isfinite(report["profit_factor"]):
            report["profit_factor"] = "Infinity"

        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{args.symbol}_{args.timeframe}_{args.start}_{args.end}"
        trades_path = output_dir / f"trades_{stem}.csv"
        summary_path = output_dir / f"summary_{stem}.json"
        trades.to_csv(trades_path, index=False)
        summary_path.write_text(json.dumps({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "start_utc": args.start,
            "end_utc": args.end,
            "candles": int(len(candles)),
            "spread_source": "MT5 historical spread column when present; fallback otherwise",
            "fallback_spread_price_units": args.fallback_spread,
            "starting_balance": args.balance,
            "risk_percent_per_trade": args.risk,
            **report,
        }, indent=2), encoding="utf-8")

        print("\n=== HISTORICAL BACKTEST — NO ORDERS PLACED ===")
        print(f"Symbol/timeframe: {args.symbol} {args.timeframe}")
        print(f"UTC period: {args.start} to {args.end}")
        print(f"Candles analysed: {len(candles):,}")
        print(f"Trades: {report['trades']}")
        print(f"Win rate: {report['win_rate_percent']:.2f}%")
        print(f"Profit factor: {report['profit_factor']}")
        print(f"Net result: {report['net_r']:.2f} R")
        print(f"Maximum drawdown: {report['max_drawdown_percent']:.2f}%")
        print(f"Simulated ending balance: {report['ending_balance']:.2f}")
        print(f"Trade details: {trades_path}")
        print(f"Summary: {summary_path}")
        print("\nThis is a historical simulation, not evidence of future profitability.")
    finally:
        disconnect()


if __name__ == "__main__":
    main()
