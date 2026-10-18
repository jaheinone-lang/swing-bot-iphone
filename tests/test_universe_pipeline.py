"""Offline, deterministic catalog-scanning tests. No API keys or network."""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from swingbot.equity_screen import DailyBar
from swingbot.universe_pipeline import (
    build_catalog_report,
    rank_verified_eur_candidates,
    refresh_catalog,
)


def items():
    return [
        {"ticker": "GOOD_DE_EQ", "shortName": "Example A", "type": "STOCK",
         "currencyCode": "EUR", "isin": "DE000001", "addedOn": "2026-10-17T08:00:00Z"},
        {"ticker": "OTHER_DE_EQ", "shortName": "Example ETF", "type": "ETF",
         "currencyCode": "EUR", "isin": "DE000002", "addedOn": "2026-08-17T08:00:00Z"},
        {"ticker": "ABC_US_EQ", "shortName": "Example USD", "type": "STOCK",
         "currencyCode": "USD", "isin": "US000003", "addedOn": "2026-10-17T08:00:00Z"},
    ]


def bars():
    result = []
    # Synthetic dates test score behavior, not actual price performance.
    for i in range(220):
        close = 100 + i*.27 + (15 if i == 219 else 0)
        result.append(DailyBar(date(2026, 2, 24)+timedelta(days=i),
                               close-1, close+1, close-2, close, 150000))
    return result


class UniversePipelineTests(unittest.TestCase):
    def test_no_price_feed_produces_counts_but_no_synthetic_top20(self):
        report = build_catalog_report(
            items(), as_of=date(2026, 10, 18),
            generated_at_utc=datetime(2026, 10, 18, 15, tzinfo=timezone.utc))
        self.assertEqual(report["instruments"]["stocks"], 2)
        self.assertEqual(report["instruments"]["etfs"], 1)
        self.assertEqual(report["instruments"]["total"], 3)
        self.assertEqual(report["instruments"]["platform_additions_last_30d"], 2)
        self.assertEqual(report["screening"]["ranking_status"],
                         "AWAITING_LICENSED_PRICE_DATA")
        self.assertEqual(report["screening"]["top_candidates"], [])
        self.assertFalse(report["catalog_is_full_market_data_scan"])
        self.assertFalse(report["recent_platform_additions_are_ipos"])
        self.assertFalse(report["auto_trading_enabled"])
        raw = json.dumps(report)
        # No full private instrument data is written to public report
        for ticker in ("GOOD_DE_EQ", "OTHER_DE_EQ", "ABC_US_EQ", "Example A"):
            self.assertNotIn(ticker, raw)

    def test_empty_broker_response_never_overwrites_old_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"report.json"
            path.write_text('{"kept":true}', encoding="utf-8")
            with patch("swingbot.universe_pipeline.load_demo_universe", return_value=[]):
                with self.assertRaises(ValueError):
                    refresh_catalog(output=path)
            self.assertEqual(path.read_text(), '{"kept":true}')

    def test_feed_requires_broker_membership_and_eur_and_adjustment(self):
        good = {"candles": bars(), "quote_currency": "EUR",
                "source": "licensed fixture",
                "adjusted_for_corporate_actions": True,
                "verified_spread_bps": 8}
        as_of = bars()[-1].day + timedelta(days=1)
        report = rank_verified_eur_candidates(items(), {
            "GOOD_DE_EQ": good,
            "ABC_US_EQ": good,  # USD instrument disallowed
            "UNKNOWN_DE_EQ": good,  # not on broker allowed list
            "OTHER_DE_EQ": {**good, "adjusted_for_corporate_actions": False},
        }, as_of=as_of)
        self.assertEqual(report["feed_matched"], 1)
        self.assertEqual(report["feed_rejected_or_unmatched"], 3)
        self.assertTrue(report["price_data_connected"])
        self.assertEqual(report["top_candidates"][0]["symbol"], "GOOD_DE_EQ")
        self.assertFalse(report["top_candidates"][0]["paper_trade_authorized"])
        self.assertFalse(report["top_candidates"][0]["live_order_authorized"])

    def test_invalid_feed_cannot_be_ranked(self):
        report = rank_verified_eur_candidates(items(), {
            "GOOD_DE_EQ": {"candles": [], "quote_currency": "EUR",
                           "source": "whatever",
                           "adjusted_for_corporate_actions": True,
                           "verified_spread_bps": 5}
        }, as_of=date(2026, 10, 18))
        self.assertFalse(report["top_candidates"])
        self.assertEqual(report["candidates_checked"], 0)

    def test_invalid_top_n_rejected(self):
        with self.assertRaises(ValueError):
            rank_verified_eur_candidates(items(), {}, as_of=date(2026,10,18), top_n=0)


if __name__ == "__main__":
    unittest.main()
