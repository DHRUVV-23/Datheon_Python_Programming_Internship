# Investment Portfolio Tracking Utility

An interactive Python utility to track investment portfolios, monitor stock positions, compute real-time market value and ROI (gains/losses), and automatically log portfolio snapshots and transactions to external CSV files.

---

## Features

- **Interactive & CLI Modes**: Add holdings one-by-one interactively, pass them directly via command-line arguments, or import in bulk from a CSV file.
- **Dictionary Data Structure**: Efficiently stores and aggregates positions per ticker, computing weighted average purchase price (dollar-cost averaging) across multiple transactions.
- **Current Price Lookup**:
  - Automatically reads current market prices from `prices.csv` (pre-populated with major S&P 500 stocks).
  - Integrates live quote lookup via standard library `urllib` (with fallback to `yfinance`/`requests` if installed).
  - Offers interactive user prompt fallback if a ticker price is missing or offline.
- **Comprehensive Performance Metrics**:
  - Invested Capital per holding and for the entire portfolio
  - Current Market Value per holding and total portfolio value
  - Absolute Dollar Gain/Loss (`+$ / -$`)
  - Percentage Gain/Loss (`+% / -%`)
- **Automated CSV Logging**:
  - Uses Python's built-in `csv` module (no third-party dependencies required).
  - Generates `portfolio_summary.csv` with per-holding metrics and a summary row.
  - Generates `transactions_log.csv` tracking individual buy transactions with timestamps.

---

## File Overview

| File | Description |
|---|---|
| [`portfolio.py`](file:///Users/dhruv/Documents/project%202/portfolio.py) | Main portfolio tracking utility application. |
| [`prices.csv`](file:///Users/dhruv/Documents/project%202/prices.csv) | Local CSV database of current stock prices. |
| [`portfolio_summary.csv`](file:///Users/dhruv/Documents/project%202/portfolio_summary.csv) | Output CSV file containing portfolio evaluation & summary. |
| [`transactions_log.csv`](file:///Users/dhruv/Documents/project%202/transactions_log.csv) | Output CSV logging transaction history with timestamps. |
| [`test_portfolio.py`](file:///Users/dhruv/Documents/project%202/test_portfolio.py) | Comprehensive `unittest` test suite covering calculations, storage, and CSV IO. |

---

## Getting Started

### 1. Interactive Mode
Run the program directly to launch the interactive terminal menu:
```bash
python3 portfolio.py
```

Menu options:
1. **Add / Buy Stock Position**: Prompts for ticker, buy price, and share quantity, then automatically updates `portfolio_summary.csv`.
2. **View Portfolio & Performance Summary**: Prints a formatted, color-coded tabular summary.
3. **Export / Log Summary to CSV**: Manually export to `portfolio_summary.csv` or a custom filename.
4. **Load Holdings from CSV File**: Bulk import positions from a CSV file.
5. **Update / Enter Current Market Price**: Update cached market price for any ticker.
6. **Load Sample Demo Portfolio**: Instant demo with sample holdings (AAPL, NVDA, MSFT, GOOGL, INTC).
7. **Clear All Positions**: Reset current portfolio.
8. **Exit**: Terminate utility.

---

### 2. Command-Line / Scripting Modes

- **Run Quick Demo**:
  ```bash
  python3 portfolio.py --demo
  ```

- **Add a Holding via CLI**:
  ```bash
  python3 portfolio.py --add AAPL 150.0 10
  ```

- **Import Holdings from CSV**:
  ```bash
  python3 portfolio.py --import-file my_holdings.csv
  ```

- **Specify Custom Output & Prices CSV**:
  ```bash
  python3 portfolio.py --prices my_prices.csv --output custom_summary.csv
  ```

---

## Technical Calculations

For each position:
$$\text{Invested Capital} = \text{Shares} \times \text{Average Buy Price}$$
$$\text{Current Market Value} = \text{Shares} \times \text{Current Price}$$
$$\text{Dollar Gain/Loss} = \text{Current Value} - \text{Invested Capital}$$
$$\text{Percentage Gain/Loss} = \left(\frac{\text{Current Value} - \text{Invested Capital}}{\text{Invested Capital}}\right) \times 100\%$$

For total portfolio:
$$\text{Total Invested} = \sum \text{Invested Capital}$$
$$\text{Total Market Value} = \sum \text{Current Market Value}$$
$$\text{Total Portfolio Gain/Loss} = \text{Total Market Value} - \text{Total Invested}$$
$$\text{Total Return (\%)} = \left(\frac{\text{Total Market Value} - \text{Total Invested}}{\text{Total Invested}}\right) \times 100\%$$

---

## Running Unit Tests

Run the test suite with:
```bash
python3 -m unittest test_portfolio.py -v
```
