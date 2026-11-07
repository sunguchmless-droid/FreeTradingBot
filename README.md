# FreeTradingBot — Forex / MetaTrader 5

A beginner-friendly Python prototype for monitoring Forex through the locally installed MetaTrader 5 terminal.

## Safety first

- **Keep `AUTO_DEMO_TRADING=false` until the monitoring loop has been tested.**
- Order execution and reverse-signal exits are restricted in code to MT5 demo accounts.
- Demo execution uses a maximum planned risk of 1% of balance per trade, an ATR-based stop-loss, and a 2:1 target.
- The bot does not guarantee profit. The EMA/RSI rules are educational and are not a proven strategy.
- Test on a demo account only. Never add MT5 passwords or account details to GitHub.

## What it does

- Connects to the locally running MT5 desktop terminal.
- Reads completed candles for the configured symbol/timeframe.
- Calculates EMA 20, EMA 50, RSI 14, and ATR 14.
- Monitors continuously and processes each newly completed candle once.
- With demo execution explicitly enabled, may place a BUY/SELL demo order with a stop-loss and take-profit.
- Closes only positions opened with this bot's magic number when an opposite signal appears.
- Does not close manually opened trades. Existing positions on the same symbol prevent a new entry.

**Important limitations:** This is an early prototype. It does not trail stops, guarantee broker execution, handle every broker's filling policy, or protect against gaps/slippage. Reverse-signal exits are checked only when a new candle completes; the attached SL/TP remain the primary protective orders. Do not use real funds.

## Requirements

- Windows 10/11
- Python version supported by the official MetaTrader5 Python package (the tested setup here uses Python 3.14)
- MetaTrader 5 desktop terminal installed and logged in to a DEMO account

## Setup

1. Open MT5 and log in to your demo account. Keep it running.
2. Open this project folder in Command Prompt.
3. Create and activate a virtual environment:
   `py -3.14 -m venv .venv`
   `.venv\\Scripts\\activate`
4. Install dependencies:
   `python -m pip install --upgrade pip`
   `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`.
6. First run with `AUTO_DEMO_TRADING=false`:
   `python -m src.main`
7. The program keeps running. Press **CTRL+C** to stop it.

## Configuration

- `MT5_SYMBOL=EURUSD`
- `MT5_TIMEFRAME=M15`
- `MT5_BARS=300`
- `POLL_SECONDS=5` (how often the terminal is checked; signals are still processed only once per completed candle)
- `AUTO_DEMO_TRADING=false` (safe default; do not change until the loop is reviewed and tested)

## Signal rules

- BUY candidate: EMA 20 above EMA 50 and RSI between 50 and 70.
- SELL candidate: EMA 20 below EMA 50 and RSI between 30 and 50.
- Otherwise: HOLD.

These simple rules do not account for all market conditions, spread, slippage, news, swaps, or broker execution differences.
