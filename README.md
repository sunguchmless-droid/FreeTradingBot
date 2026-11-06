# FreeTradingBot — Forex / MetaTrader 5

A beginner-friendly Python starter project for analysing Forex markets through MetaTrader 5 (MT5).

## Safety first

- This starter version is **signal-only**. It does not place, modify, or close trades.
- Use an MT5 demo account for testing.
- Signals and example indicator rules are educational starting points, not guaranteed profitable strategies.
- Never add your MT5 password, broker credentials, or account number to GitHub.

## What it does

- Connects to the locally installed MetaTrader 5 terminal.
- Reads recent candles for a configured symbol and timeframe.
- Calculates EMA 20, EMA 50, and RSI 14.
- Prints BUY, SELL, or HOLD with a short explanation.
- Includes a simple risk-sizing helper for later testing; it does not submit orders.

## Requirements

- Windows 10/11 (the official Python `MetaTrader5` package connects to the Windows MT5 terminal)
- Python 3.10 or 3.11 recommended
- MetaTrader 5 desktop terminal installed and logged in to a **demo** account
- A broker symbol available in Market Watch (some brokers use names such as `EURUSD.a`)

## Setup

1. Install Python and MetaTrader 5.
2. Open MT5, sign in to a demo account, and make sure the terminal is running.
3. In this repository folder, open PowerShell or Command Prompt.
4. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run:
   ```bat
   .venv\Scripts\activate.bat
   ```

5. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Copy `.env.example` to `.env` and adjust the symbol/timeframe if needed. Keep `.env` private.
7. Run:

   ```powershell
   python -m src.main
   ```

## Initial strategy (for learning and backtesting)

- BUY candidate: EMA 20 is above EMA 50 and RSI is between 50 and 70.
- SELL candidate: EMA 20 is below EMA 50 and RSI is between 30 and 50.
- Otherwise: HOLD.

This is deliberately basic. It does not account for spread, slippage, news, swaps, or broker execution conditions. Do not treat a signal as a recommendation to trade.

## Project layout

- `src/mt5_data.py` — connection and candle retrieval
- `src/indicators.py` — EMA and RSI calculations
- `src/signals.py` — transparent signal rules
- `src/risk.py` — educational position-size calculation
- `src/main.py` — runs one analysis cycle

## Next milestones

1. Confirm your broker's exact symbol names and test the MT5 connection.
2. Add historical backtesting with spread and commission assumptions.
3. Add paper/demo order execution only after reviewing backtest results.
4. Add live trading only as a separate, explicitly enabled feature with strict limits.

No profit is guaranteed. Test thoroughly before considering real funds.
