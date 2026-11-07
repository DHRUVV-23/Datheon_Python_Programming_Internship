#!/usr/bin/env python3
"""
Investment Portfolio Tracking Utility
-------------------------------------
Allows users to enter stock ticker symbols, buy prices, and share quantities.
Stores positions in a dictionary structure, looks up current ticker prices
(from prices.csv or via live network/API fallback), computes total portfolio value,
gain/loss per holding and for the entire portfolio, and logs the summary to an
external CSV file ('portfolio_summary.csv') using Python's built-in csv module.
"""

import argparse
import csv
import datetime
import os
import sys
import urllib.request
import json
from typing import Dict, Any, List, Optional, Tuple


# ANSI Color formatting for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        if sys.stdout.isatty():
            return f"{color}{text}{cls.RESET}"
        return text


class PriceService:
    """
    Manages current stock price lookups.
    Supports reading from local CSV (e.g., prices.csv),
    live lookup via public endpoint (urllib standard library / yfinance if available),
    and interactive user prompt fallback.
    """

    def __init__(self, prices_csv: str = "prices.csv"):
        self.prices_csv = prices_csv
        self.price_cache: Dict[str, float] = {}
        self.load_prices_from_csv()

    def load_prices_from_csv(self) -> None:
        """Loads price mappings from CSV file if it exists."""
        if not os.path.exists(self.prices_csv):
            return

        try:
            with open(self.prices_csv, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Handle flexible column names
                    ticker = (row.get("Ticker") or row.get("Symbol") or "").strip().upper()
                    price_str = (
                        row.get("CurrentPrice")
                        or row.get("Price")
                        or row.get("price")
                        or row.get("current_price")
                        or ""
                    ).strip()
                    if ticker and price_str:
                        try:
                            self.price_cache[ticker] = float(price_str)
                        except ValueError:
                            continue
        except Exception as e:
            print(f"[!] Warning: Could not read prices CSV ({self.prices_csv}): {e}")

    def save_price_to_csv(self, ticker: str, price: float) -> None:
        """Updates or appends a ticker price to the local prices.csv file."""
        self.price_cache[ticker] = price
        fieldnames = ["Ticker", "CurrentPrice"]

        # If file exists, update existing or append
        existing_rows: Dict[str, str] = {}
        if os.path.exists(self.prices_csv):
            try:
                with open(self.prices_csv, mode="r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        sym = (r.get("Ticker") or r.get("Symbol") or "").strip().upper()
                        val = r.get("CurrentPrice") or r.get("Price") or ""
                        if sym:
                            existing_rows[sym] = val
            except Exception:
                pass

        existing_rows[ticker] = f"{price:.2f}"

        try:
            with open(self.prices_csv, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for sym, val in sorted(existing_rows.items()):
                    writer.writerow([sym, val])
        except Exception as e:
            print(f"[!] Warning: Could not save price to {self.prices_csv}: {e}")

    def _fetch_live_price(self, ticker: str) -> Optional[float]:
        """
        Attempts to fetch live stock price using Yahoo Finance query API
        via standard library urllib.request (zero external dependencies).
        """
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as response:
                data = json.loads(response.read().decode("utf-8"))
                meta = data["chart"]["result"][0]["meta"]
                current_price = meta.get("regularMarketPrice")
                if current_price:
                    return float(current_price)
        except Exception:
            # Network access disabled / timeout / ticker not found
            pass
        return None

    def get_price(
        self, ticker: str, default_price: Optional[float] = None, prompt_interactive: bool = False
    ) -> float:
        """
        Resolves current price for ticker:
        1. Checks cache (loaded from prices.csv)
        2. Tries live price fetch
        3. Prompts user if prompt_interactive=True
        4. Falls back to default_price or 0.0
        """
        ticker = ticker.strip().upper()

        # 1. Check local cache
        if ticker in self.price_cache:
            return self.price_cache[ticker]

        # 2. Try live price fetch
        live_price = self._fetch_live_price(ticker)
        if live_price is not None:
            self.save_price_to_csv(ticker, live_price)
            return live_price

        # 3. Interactive prompt fallback
        if prompt_interactive:
            fallback_hint = f" [Press Enter for ${default_price:.2f}]" if default_price is not None else ""
            while True:
                try:
                    val_str = input(
                        f"Enter current market price for {ticker}{fallback_hint}: $"
                    ).strip()
                    if not val_str and default_price is not None:
                        self.save_price_to_csv(ticker, default_price)
                        return default_price
                    val = float(val_str)
                    if val > 0:
                        self.save_price_to_csv(ticker, val)
                        return val
                    print("Price must be a positive number.")
                except ValueError:
                    print("Invalid input. Please enter a valid decimal number.")
                except (KeyboardInterrupt, EOFError):
                    print()
                    break

        # 4. Fallback
        if default_price is not None:
            return default_price
        return 0.0


class Portfolio:
    """
    Manages portfolio holdings stored in a dictionary data structure.

    Dictionary structure:
    {
        "AAPL": {
            "ticker": "AAPL",
            "shares": 10.0,
            "avg_buy_price": 150.00,
            "invested_capital": 1500.00,
            "transactions": [
                {"shares": 10.0, "buy_price": 150.00, "timestamp": "2026-11-07 17:00:00"}
            ]
        },
        ...
    }
    """

    def __init__(self, price_service: Optional[PriceService] = None):
        # Store positions in dictionary structure: Ticker -> Position Details
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.price_service = price_service or PriceService()

    def add_position(
        self,
        ticker: str,
        buy_price: float,
        shares: float,
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Adds or increases a stock position in the portfolio.
        Computes weighted average buy price when shares are added to an existing holding.
        """
        ticker = ticker.strip().upper()
        if not ticker:
            raise ValueError("Ticker symbol cannot be empty.")
        if buy_price <= 0:
            raise ValueError("Buy price must be greater than zero.")
        if shares <= 0:
            raise ValueError("Share quantity must be greater than zero.")

        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        transaction = {
            "shares": float(shares),
            "buy_price": float(buy_price),
            "total": float(shares * buy_price),
            "timestamp": timestamp,
        }

        if ticker in self.positions:
            pos = self.positions[ticker]
            new_total_shares = pos["shares"] + shares
            new_invested_capital = pos["invested_capital"] + (shares * buy_price)
            pos["shares"] = new_total_shares
            pos["invested_capital"] = new_invested_capital
            pos["avg_buy_price"] = new_invested_capital / new_total_shares
            pos["transactions"].append(transaction)
        else:
            self.positions[ticker] = {
                "ticker": ticker,
                "shares": float(shares),
                "avg_buy_price": float(buy_price),
                "invested_capital": float(shares * buy_price),
                "transactions": [transaction],
            }

    def remove_position(self, ticker: str) -> bool:
        """Removes a position entirely from the portfolio."""
        ticker = ticker.strip().upper()
        if ticker in self.positions:
            del self.positions[ticker]
            return True
        return False

    def clear(self) -> None:
        """Clears all positions from the portfolio."""
        self.positions.clear()

    def calculate_metrics(
        self, prompt_interactive: bool = False
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Calculates current market value, dollar gain/loss, and percentage gain/loss
        per holding and for the aggregate portfolio.

        Returns:
            holdings_metrics: List of dicts for each holding
            summary_metrics: Dictionary containing aggregate portfolio totals
        """
        holdings_metrics: List[Dict[str, Any]] = []
        total_invested = 0.0
        total_market_value = 0.0

        for ticker, pos in sorted(self.positions.items()):
            shares = pos["shares"]
            avg_buy_price = pos["avg_buy_price"]
            invested_capital = pos["invested_capital"]

            current_price = self.price_service.get_price(
                ticker,
                default_price=avg_buy_price,
                prompt_interactive=prompt_interactive,
            )

            current_value = shares * current_price
            gain_loss_dollar = current_value - invested_capital

            if invested_capital > 0:
                gain_loss_pct = (gain_loss_dollar / invested_capital) * 100.0
            else:
                gain_loss_pct = 0.0

            holdings_metrics.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "avg_buy_price": avg_buy_price,
                    "invested_capital": invested_capital,
                    "current_price": current_price,
                    "current_value": current_value,
                    "gain_loss_dollar": gain_loss_dollar,
                    "gain_loss_pct": gain_loss_pct,
                }
            )

            total_invested += invested_capital
            total_market_value += current_value

        total_gain_loss_dollar = total_market_value - total_invested
        if total_invested > 0:
            total_gain_loss_pct = (total_gain_loss_dollar / total_invested) * 100.0
        else:
            total_gain_loss_pct = 0.0

        summary_metrics = {
            "total_invested": total_invested,
            "total_market_value": total_market_value,
            "total_gain_loss_dollar": total_gain_loss_dollar,
            "total_gain_loss_pct": total_gain_loss_pct,
            "total_holdings_count": len(self.positions),
        }

        return holdings_metrics, summary_metrics

    def export_summary_to_csv(
        self,
        filepath: str = "portfolio_summary.csv",
        prompt_interactive: bool = False,
    ) -> str:
        """
        Writes portfolio evaluation results to an external CSV file using Python's
        built-in csv module.
        """
        holdings_metrics, summary = self.calculate_metrics(
            prompt_interactive=prompt_interactive
        )

        headers = [
            "Ticker",
            "Shares",
            "Buy Price ($)",
            "Invested Capital ($)",
            "Current Price ($)",
            "Current Value ($)",
            "Gain/Loss ($)",
            "Gain/Loss (%)",
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)

            for item in holdings_metrics:
                writer.writerow(
                    [
                        item["ticker"],
                        f"{item['shares']:.4f}".rstrip("0").rstrip("."),
                        f"{item['avg_buy_price']:.2f}",
                        f"{item['invested_capital']:.2f}",
                        f"{item['current_price']:.2f}",
                        f"{item['current_value']:.2f}",
                        f"{item['gain_loss_dollar']:+.2f}",
                        f"{item['gain_loss_pct']:+.2f}%",
                    ]
                )

            # Portfolio Summary / Total Row
            writer.writerow(
                [
                    "TOTAL PORTFOLIO",
                    "-",
                    "-",
                    f"{summary['total_invested']:.2f}",
                    "-",
                    f"{summary['total_market_value']:.2f}",
                    f"{summary['total_gain_loss_dollar']:+.2f}",
                    f"{summary['total_gain_loss_pct']:+.2f}%",
                ]
            )

        return filepath

    def export_transactions_to_csv(
        self, filepath: str = "transactions_log.csv"
    ) -> str:
        """
        Logs individual purchase transactions to a transaction history CSV.
        """
        headers = ["Timestamp", "Ticker", "Shares", "Buy Price ($)", "Total Invested ($)"]

        with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)

            for ticker, pos in sorted(self.positions.items()):
                for tx in pos.get("transactions", []):
                    writer.writerow(
                        [
                            tx.get("timestamp", ""),
                            ticker,
                            f"{tx['shares']:.4f}".rstrip("0").rstrip("."),
                            f"{tx['buy_price']:.2f}",
                            f"{tx['total']:.2f}",
                        ]
                    )

        return filepath

    def import_positions_from_csv(self, filepath: str) -> int:
        """
        Imports positions from an external CSV file (e.g., Ticker,BuyPrice,Shares).
        Returns number of positions imported.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File '{filepath}' not found.")

        count = 0
        with open(filepath, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = (
                    row.get("Ticker")
                    or row.get("ticker")
                    or row.get("Symbol")
                    or row.get("symbol")
                    or ""
                ).strip()
                price_str = (
                    row.get("Buy Price ($)")
                    or row.get("Buy Price")
                    or row.get("BuyPrice")
                    or row.get("buy_price")
                    or row.get("Price")
                    or row.get("price")
                    or ""
                ).strip()
                shares_str = (
                    row.get("Shares")
                    or row.get("shares")
                    or row.get("Quantity")
                    or row.get("quantity")
                    or ""
                ).strip()

                if ticker and price_str and shares_str:
                    try:
                        price = float(price_str.replace("$", "").replace(",", ""))
                        shares = float(shares_str.replace(",", ""))
                        self.add_position(ticker, price, shares)
                        count += 1
                    except ValueError:
                        continue
        return count

    def display_summary(self, prompt_interactive: bool = False) -> None:
        """
        Displays a clean, formatted terminal table with holdings,
        invested capital, market value, dollar gain/loss, and percentage gain/loss.
        """
        if not self.positions:
            print("\n" + Colors.colorize("[i] Portfolio is currently empty.", Colors.YELLOW))
            return

        holdings_metrics, summary = self.calculate_metrics(
            prompt_interactive=prompt_interactive
        )

        header_title = "INVESTMENT PORTFOLIO PERFORMANCE SUMMARY"
        border = "=" * 105
        sub_border = "-" * 105

        print("\n" + border)
        print(f"{header_title:^105}")
        print(border)
        print(
            f"{'Ticker':<8} {'Shares':>10} {'Buy Price':>13} {'Current':>13} "
            f"{'Invested':>15} {'Market Value':>15} {'Gain/Loss ($)':>14} {'Gain/Loss (%)':>14}"
        )
        print(sub_border)

        for item in holdings_metrics:
            g_dollar = item["gain_loss_dollar"]
            g_pct = item["gain_loss_pct"]

            dollar_str = f"{g_dollar:+,.2f}"
            pct_str = f"{g_pct:+.2f}%"

            if g_dollar > 0:
                colored_dollar = Colors.colorize(dollar_str, Colors.GREEN)
                colored_pct = Colors.colorize(pct_str, Colors.GREEN)
            elif g_dollar < 0:
                colored_dollar = Colors.colorize(dollar_str, Colors.RED)
                colored_pct = Colors.colorize(pct_str, Colors.RED)
            else:
                colored_dollar = dollar_str
                colored_pct = pct_str

            # Align using uncolored lengths
            raw_line = (
                f"{item['ticker']:<8} "
                f"{item['shares']:>10.4f} "
                f"${item['avg_buy_price']:>11,.2f} "
                f"${item['current_price']:>11,.2f} "
                f"${item['invested_capital']:>13,.2f} "
                f"${item['current_value']:>13,.2f} "
                f"{dollar_str:>14} "
                f"{pct_str:>14}"
            )
            # Replace with colored strings
            line = (
                f"{item['ticker']:<8} "
                f"{item['shares']:>10.4f} "
                f"${item['avg_buy_price']:>11,.2f} "
                f"${item['current_price']:>11,.2f} "
                f"${item['invested_capital']:>13,.2f} "
                f"${item['current_value']:>13,.2f} "
                f"{colored_dollar:>23} "  # extra padding for ANSI escape codes
                f"{colored_pct:>23}"
                if sys.stdout.isatty()
                else raw_line
            )
            print(line)

        print(sub_border)

        tot_invested = summary["total_invested"]
        tot_market_val = summary["total_market_value"]
        tot_gain_dollar = summary["total_gain_loss_dollar"]
        tot_gain_pct = summary["total_gain_loss_pct"]

        tot_dollar_str = f"{tot_gain_dollar:+,.2f}"
        tot_pct_str = f"{tot_gain_pct:+.2f}%"

        if tot_gain_dollar > 0:
            tot_col_dollar = Colors.colorize(tot_dollar_str, Colors.GREEN)
            tot_col_pct = Colors.colorize(tot_pct_str, Colors.GREEN)
        elif tot_gain_dollar < 0:
            tot_col_dollar = Colors.colorize(tot_dollar_str, Colors.RED)
            tot_col_pct = Colors.colorize(tot_pct_str, Colors.RED)
        else:
            tot_col_dollar = tot_dollar_str
            tot_col_pct = tot_pct_str

        total_line = (
            f"{'TOTAL':<8} {'-':>10} {'-':>13} {'-':>13} "
            f"${tot_invested:>13,.2f} "
            f"${tot_market_val:>13,.2f} "
            f"{tot_col_dollar:>23} "
            f"{tot_col_pct:>23}"
            if sys.stdout.isatty()
            else (
                f"{'TOTAL':<8} {'-':>10} {'-':>13} {'-':>13} "
                f"${tot_invested:>13,.2f} "
                f"${tot_market_val:>13,.2f} "
                f"{tot_dollar_str:>14} "
                f"{tot_pct_str:>14}"
            )
        )
        print(total_line)
        print(border)

        # Quick Highlights Card
        status = "GAIN" if tot_gain_dollar >= 0 else "LOSS"
        color = Colors.GREEN if tot_gain_dollar >= 0 else Colors.RED
        print(
            Colors.colorize(
                f"\nPortfolio Overview: {len(self.positions)} Holdings | "
                f"Total Invested: ${tot_invested:,.2f} | "
                f"Current Value: ${tot_market_val:,.2f} | "
                f"Net {status}: {tot_dollar_str} ({tot_pct_str})",
                Colors.BOLD + color,
            )
        )


def populate_demo_portfolio(portfolio: Portfolio) -> None:
    """Pre-populates a sample investment portfolio for demonstration."""
    demo_holdings = [
        ("AAPL", 150.00, 15.0),   # Apple: Buy @ $150, Current ~$225.50 (Profit)
        ("NVDA", 95.00, 20.0),    # Nvidia: Buy @ $95, Current ~$128.00 (Profit)
        ("MSFT", 430.00, 8.0),    # Microsoft: Buy @ $430, Current ~$415.00 (Loss)
        ("GOOGL", 160.00, 12.0),  # Alphabet: Buy @ $160, Current ~$175.25 (Profit)
        ("INTC", 32.50, 40.0),    # Intel: Buy @ $32.50, Current ~$22.80 (Loss)
    ]
    for ticker, buy_price, shares in demo_holdings:
        portfolio.add_position(ticker, buy_price, shares)


def interactive_add_holding(portfolio: Portfolio) -> None:
    """Prompts the user interactively to enter ticker, buy price, and share quantity."""
    print("\n--- Add Stock Position ---")
    while True:
        ticker = input("Stock Ticker Symbol (e.g. AAPL, TSLA): ").strip().upper()
        if ticker:
            break
        print("Ticker symbol cannot be empty.")

    while True:
        try:
            buy_price_input = input(f"Buy Price per share for {ticker} ($): ").strip()
            buy_price = float(buy_price_input.replace("$", "").replace(",", ""))
            if buy_price > 0:
                break
            print("Buy price must be greater than 0.")
        except ValueError:
            print("Please enter a valid numeric value.")

    while True:
        try:
            shares_input = input(f"Number of shares purchased for {ticker}: ").strip()
            shares = float(shares_input.replace(",", ""))
            if shares > 0:
                break
            print("Quantity must be greater than 0.")
        except ValueError:
            print("Please enter a valid numeric value.")

    portfolio.add_position(ticker, buy_price, shares)
    print(
        Colors.colorize(
            f"Successfully added {shares:.4f}".rstrip("0").rstrip(".")
            + f" shares of {ticker} @ ${buy_price:.2f} (Total: ${shares * buy_price:,.2f})",
            Colors.GREEN,
        )
    )

    # Check if we have a current price for it; if not, ask now
    if ticker not in portfolio.price_service.price_cache:
        portfolio.price_service.get_price(
            ticker, default_price=buy_price, prompt_interactive=True
        )


def interactive_menu(portfolio: Portfolio, output_csv: str = "portfolio_summary.csv") -> None:
    """Runs the main interactive terminal menu."""
    while True:
        print("\n" + "=" * 45)
        print("    INVESTMENT PORTFOLIO TRACKER")
        print("=" * 45)
        print("1. Add / Buy Stock Position")
        print("2. View Portfolio & Performance Summary")
        print("3. Export / Log Summary to CSV")
        print("4. Load Holdings from CSV File")
        print("5. Update / Enter Current Market Price")
        print("6. Load Sample Demo Portfolio")
        print("7. Clear All Positions")
        print("8. Exit")
        print("-" * 45)

        try:
            choice = input("Select an option (1-8): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        if choice == "1":
            interactive_add_holding(portfolio)
            # Automatically log transaction & summary
            portfolio.export_summary_to_csv(output_csv)
            portfolio.export_transactions_to_csv("transactions_log.csv")
            print(f"[✓] Summary automatically logged to '{output_csv}'")

        elif choice == "2":
            portfolio.display_summary(prompt_interactive=True)

        elif choice == "3":
            if not portfolio.positions:
                print(Colors.colorize("[!] Portfolio is empty. Nothing to export.", Colors.YELLOW))
            else:
                filename = input(f"Enter filename to save [default: {output_csv}]: ").strip()
                if not filename:
                    filename = output_csv
                portfolio.export_summary_to_csv(filename)
                portfolio.export_transactions_to_csv("transactions_log.csv")
                print(Colors.colorize(f"[✓] Successfully exported portfolio summary to '{filename}'!", Colors.GREEN))
                print(Colors.colorize("[✓] Transaction audit log updated in 'transactions_log.csv'!", Colors.GREEN))

        elif choice == "4":
            filename = input("Enter CSV filename to import (e.g. holdings.csv): ").strip()
            if not filename:
                print("[!] Filename required.")
                continue
            try:
                count = portfolio.import_positions_from_csv(filename)
                print(Colors.colorize(f"[✓] Successfully imported {count} positions from '{filename}'!", Colors.GREEN))
                portfolio.export_summary_to_csv(output_csv)
            except Exception as e:
                print(Colors.colorize(f"[!] Import failed: {e}", Colors.RED))

        elif choice == "5":
            ticker = input("Enter Stock Ticker Symbol: ").strip().upper()
            if not ticker:
                continue
            curr = portfolio.price_service.price_cache.get(ticker)
            curr_str = f" (Current cached: ${curr:.2f})" if curr else ""
            try:
                new_price_str = input(f"Enter new current price for {ticker}{curr_str}: $").strip()
                new_price = float(new_price_str.replace("$", "").replace(",", ""))
                if new_price > 0:
                    portfolio.price_service.save_price_to_csv(ticker, new_price)
                    print(Colors.colorize(f"[✓] Updated {ticker} price to ${new_price:.2f}", Colors.GREEN))
                    if portfolio.positions:
                        portfolio.export_summary_to_csv(output_csv)
                else:
                    print("[!] Price must be positive.")
            except ValueError:
                print("[!] Invalid price format.")

        elif choice == "6":
            populate_demo_portfolio(portfolio)
            print(Colors.colorize("[✓] Demo portfolio loaded with 5 sample positions (AAPL, NVDA, MSFT, GOOGL, INTC).", Colors.GREEN))
            portfolio.display_summary()
            portfolio.export_summary_to_csv(output_csv)
            portfolio.export_transactions_to_csv("transactions_log.csv")
            print(f"[✓] Summary automatically logged to '{output_csv}'")

        elif choice == "7":
            confirm = input("Are you sure you want to clear all positions? (y/N): ").strip().lower()
            if confirm == "y":
                portfolio.clear()
                portfolio.export_summary_to_csv(output_csv)
                print(Colors.colorize("[✓] Portfolio cleared.", Colors.YELLOW))

        elif choice == "8":
            print("Exiting Portfolio Tracker. Have a great day!")
            break
        else:
            print("[!] Invalid selection. Please choose an option between 1 and 8.")


def main():
    parser = argparse.ArgumentParser(
        description="Investment Portfolio Tracking Utility with CSV Logging."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Load sample demo portfolio, display performance, write portfolio_summary.csv, and exit.",
    )
    parser.add_argument(
        "--add",
        nargs=3,
        metavar=("TICKER", "BUY_PRICE", "SHARES"),
        help="Add a position directly via CLI: e.g. --add AAPL 150.0 10",
    )
    parser.add_argument(
        "--import-file",
        metavar="CSV_FILE",
        help="Import stock holdings from a CSV file.",
    )
    parser.add_argument(
        "--output",
        default="portfolio_summary.csv",
        help="Output CSV filename (default: portfolio_summary.csv).",
    )
    parser.add_argument(
        "--prices",
        default="prices.csv",
        help="CSV file containing current stock prices (default: prices.csv).",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Display portfolio performance summary and exit.",
    )

    args = parser.parse_args()

    price_service = PriceService(prices_csv=args.prices)
    portfolio = Portfolio(price_service=price_service)

    # 1. Handle Import if specified
    if args.import_file:
        try:
            count = portfolio.import_positions_from_csv(args.import_file)
            print(f"[✓] Imported {count} positions from '{args.import_file}'.")
        except Exception as e:
            print(f"[!] Error importing '{args.import_file}': {e}", file=sys.stderr)
            sys.exit(1)

    # 2. Handle CLI Add
    if args.add:
        ticker, price_str, shares_str = args.add
        try:
            price = float(price_str)
            shares = float(shares_str)
            portfolio.add_position(ticker, price, shares)
            print(f"[✓] Added {shares} shares of {ticker.upper()} @ ${price:.2f}.")
        except ValueError as e:
            print(f"[!] Invalid position arguments: {e}", file=sys.stderr)
            sys.exit(1)

    # 3. Handle Demo Mode
    if args.demo:
        populate_demo_portfolio(portfolio)
        portfolio.display_summary()
        out_path = portfolio.export_summary_to_csv(args.output)
        portfolio.export_transactions_to_csv("transactions_log.csv")
        print(f"\n[✓] Portfolio summary successfully exported to '{out_path}'")
        print("[✓] Transaction log saved to 'transactions_log.csv'")
        return

    # 4. Handle Summary only
    if args.summary:
        portfolio.display_summary()
        out_path = portfolio.export_summary_to_csv(args.output)
        print(f"\n[✓] Portfolio summary successfully exported to '{out_path}'")
        return

    # If any non-interactive flags were processed and no interactive loop was desired:
    if args.add or args.import_file:
        portfolio.display_summary()
        out_path = portfolio.export_summary_to_csv(args.output)
        print(f"\n[✓] Portfolio summary successfully exported to '{out_path}'")
        return

    # Otherwise run the full interactive menu
    interactive_menu(portfolio, output_csv=args.output)


if __name__ == "__main__":
    main()
