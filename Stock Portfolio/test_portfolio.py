#!/usr/bin/env python3
"""
Unit test suite for Investment Portfolio Tracking Utility (portfolio.py).
Tests position dictionary structures, price lookup, performance calculations,
and CSV exports.
"""

import csv
import os
import tempfile
import unittest

from portfolio import Portfolio, PriceService


class TestPriceService(unittest.TestCase):
    def setUp(self):
        self.temp_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w")
        self.temp_csv.write("Ticker,CurrentPrice\nAAPL,200.00\nTSLA,250.00\n")
        self.temp_csv.close()
        self.service = PriceService(prices_csv=self.temp_csv.name)

    def tearDown(self):
        if os.path.exists(self.temp_csv.name):
            os.remove(self.temp_csv.name)

    def test_load_and_get_price(self):
        self.assertEqual(self.service.get_price("AAPL"), 200.00)
        self.assertEqual(self.service.get_price("aapl"), 200.00)  # Case insensitive
        self.assertEqual(self.service.get_price("TSLA"), 250.00)

    def test_save_and_update_price(self):
        self.service.save_price_to_csv("NVDA", 130.50)
        self.assertEqual(self.service.get_price("NVDA"), 130.50)

        # Reload from file to ensure persistence
        new_service = PriceService(prices_csv=self.temp_csv.name)
        self.assertEqual(new_service.get_price("NVDA"), 130.50)

    def test_fallback_price(self):
        self.assertEqual(self.service.get_price("UNKNOWN", default_price=55.0), 55.0)


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.temp_prices_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w")
        self.temp_prices_csv.write("Ticker,CurrentPrice\nAAPL,200.00\nMSFT,400.00\nGOOG,150.00\n")
        self.temp_prices_csv.close()

        self.price_service = PriceService(prices_csv=self.temp_prices_csv.name)
        self.portfolio = Portfolio(price_service=self.price_service)

    def tearDown(self):
        if os.path.exists(self.temp_prices_csv.name):
            os.remove(self.temp_prices_csv.name)

    def test_add_position_dictionary_structure(self):
        self.portfolio.add_position("AAPL", buy_price=150.00, shares=10.0)

        self.assertIn("AAPL", self.portfolio.positions)
        pos = self.portfolio.positions["AAPL"]
        self.assertEqual(pos["ticker"], "AAPL")
        self.assertEqual(pos["shares"], 10.0)
        self.assertEqual(pos["avg_buy_price"], 150.00)
        self.assertEqual(pos["invested_capital"], 1500.00)
        self.assertEqual(len(pos["transactions"]), 1)

    def test_dollar_cost_averaging_multiple_buys(self):
        # 10 shares @ $100 = $1,000
        self.portfolio.add_position("AAPL", buy_price=100.00, shares=10.0)
        # 10 shares @ $200 = $2,000
        self.portfolio.add_position("AAPL", buy_price=200.00, shares=10.0)

        pos = self.portfolio.positions["AAPL"]
        self.assertEqual(pos["shares"], 20.0)
        self.assertEqual(pos["invested_capital"], 3000.00)
        self.assertEqual(pos["avg_buy_price"], 150.00)
        self.assertEqual(len(pos["transactions"]), 2)

    def test_calculate_metrics_gain(self):
        # Buy 10 AAPL @ $150 (invested = 1500). Current price in CSV is $200.
        self.portfolio.add_position("AAPL", buy_price=150.00, shares=10.0)
        holdings, summary = self.portfolio.calculate_metrics()

        self.assertEqual(len(holdings), 1)
        aapl = holdings[0]
        self.assertEqual(aapl["ticker"], "AAPL")
        self.assertEqual(aapl["current_price"], 200.00)
        self.assertEqual(aapl["current_value"], 2000.00)
        self.assertEqual(aapl["gain_loss_dollar"], 500.00)
        self.assertAlmostEqual(aapl["gain_loss_pct"], 33.3333, places=2)

        self.assertEqual(summary["total_invested"], 1500.00)
        self.assertEqual(summary["total_market_value"], 2000.00)
        self.assertEqual(summary["total_gain_loss_dollar"], 500.00)
        self.assertAlmostEqual(summary["total_gain_loss_pct"], 33.3333, places=2)

    def test_calculate_metrics_loss(self):
        # Buy 10 MSFT @ $500 (invested = 5000). Current price in CSV is $400.
        self.portfolio.add_position("MSFT", buy_price=500.00, shares=10.0)
        holdings, summary = self.portfolio.calculate_metrics()

        msft = holdings[0]
        self.assertEqual(msft["current_value"], 4000.00)
        self.assertEqual(msft["gain_loss_dollar"], -1000.00)
        self.assertAlmostEqual(msft["gain_loss_pct"], -20.00, places=2)

        self.assertEqual(summary["total_invested"], 5000.00)
        self.assertEqual(summary["total_market_value"], 4000.00)
        self.assertEqual(summary["total_gain_loss_dollar"], -1000.00)
        self.assertAlmostEqual(summary["total_gain_loss_pct"], -20.00, places=2)

    def test_export_summary_to_csv(self):
        self.portfolio.add_position("AAPL", buy_price=150.00, shares=10.0)
        self.portfolio.add_position("MSFT", buy_price=400.00, shares=5.0)

        temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        temp_out.close()

        try:
            self.portfolio.export_summary_to_csv(temp_out.name)
            self.assertTrue(os.path.exists(temp_out.name))

            with open(temp_out.name, mode="r", newline="", encoding="utf-8") as f:
                reader = list(csv.reader(f))

            # Check header
            self.assertEqual(
                reader[0],
                [
                    "Ticker",
                    "Shares",
                    "Buy Price ($)",
                    "Invested Capital ($)",
                    "Current Price ($)",
                    "Current Value ($)",
                    "Gain/Loss ($)",
                    "Gain/Loss (%)",
                ],
            )
            # 2 holding rows + 1 total row + 1 header = 4 lines
            self.assertEqual(len(reader), 4)

            # Check total row
            total_row = reader[-1]
            self.assertEqual(total_row[0], "TOTAL PORTFOLIO")
            # Invested: 1500 + 2000 = 3500.00
            self.assertEqual(total_row[3], "3500.00")
            # Market value: (10 * 200) + (5 * 400) = 4000.00
            self.assertEqual(total_row[5], "4000.00")
            # Gain dollar: +500.00
            self.assertEqual(total_row[6], "+500.00")
        finally:
            if os.path.exists(temp_out.name):
                os.remove(temp_out.name)

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            self.portfolio.add_position("", 100, 5)
        with self.assertRaises(ValueError):
            self.portfolio.add_position("AAPL", -10, 5)
        with self.assertRaises(ValueError):
            self.portfolio.add_position("AAPL", 100, 0)


if __name__ == "__main__":
    unittest.main()
