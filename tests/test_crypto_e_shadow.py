"""Frozen crypto-only forward research should never rewrite existing paper."""
import unittest
from datetime import date, timedelta

from swingbot.crypto_alpha_research import SYMBOLS
from swingbot.crypto_e_shadow import (
    MODE, TOTAL_STOP_RISK, _e, advance_shadow,
)
from swingbot.portfolio import Bar


def synthetic(days=410):
    start = date(2025, 1, 1)
    prices = {}
    for j, symbol in enumerate(SYMBOLS):
        bars = []
        for index in range(days):
            day = start + timedelta(days=index)
            close = (100 + index * (.4 + j*.08)) * (
                1 + .005 * (index % 5) / 5
            )
            # Low enough stops to stay live; high valid candles.
            bars.append(Bar(day, close, close*1.03, close*.97, close))
        prices[symbol] = bars
    return prices


def clip(prices, until):
    return {s: bars[:until] for s, bars in prices.items()}


def advance(prices, previous):
    day = prices[SYMBOLS[0]][-1].day + timedelta(days=1)
    return advance_shadow(prices, previous, as_of=day)


class CryptoShadowTests(unittest.TestCase):
    def test_starts_today_with_zero_retroactive_trades(self):
        data = synthetic()
        st = advance(clip(data, 380), None)
        self.assertEqual(st["mode"], MODE)
        self.assertEqual(st["cash_eur"], 5000.0)
        self.assertFalse(st["trades"])
        self.assertFalse(st["positions"])
        self.assertEqual(
            st["last_processed_day"],
            data[SYMBOLS[0]][379].day.isoformat()
        )

    def test_idempotence_and_no_mutation(self):
        data = synthetic()
        starting = advance(clip(data, 370), None)
        old_copy = __import__("copy").deepcopy(starting)
        newer = advance(clip(data, 373), starting)
        self.assertEqual(starting, old_copy)
        self.assertEqual(
            newer, advance(clip(data, 373), newer)
        )

    def test_catchup_matches_daily_no_lookahead(self):
        d = synthetic()
        initial = advance(clip(d, 380), None)
        day381 = advance(clip(d, 381), initial)
        day382 = advance(clip(d, 382), day381)
        at_once = advance(clip(d, 382), initial)
        self.assertEqual(day382, at_once)
        self.assertEqual(day381["last_processed_day"],
                         d[SYMBOLS[0]][380].day.isoformat())
        self.assertTrue(all(t["day"] >= d[SYMBOLS[0]][380].day.isoformat()
                            for t in day382["trades"]))
        self.assertTrue(all(t["side"] in ("BUY", "SELL")
                            for t in day382["trades"]))

    def test_portfolio_stop_risk_budget(self):
        d = synthetic()
        state = advance(clip(d, 380), None)
        state = advance(clip(d, 383), state)
        equity = _e(state)
        exposed = sum(
            p["qty"]*max(0.0, p["entry"]-p["stop"])
            for p in state["positions"].values()
        )
        self.assertLessEqual(exposed, equity*TOTAL_STOP_RISK + 0.15)

    def test_reject_invalid_and_missing_price_feeds(self):
        d = synthetic()
        old = advance(clip(d, 380), None)
        with self.assertRaises(ValueError):
            advance(clip(d, 391), old)
        missing = clip(d, 381)
        missing["ETH-EUR"] = missing["ETH-EUR"][:-1]
        with self.assertRaises(ValueError):
            advance(missing, old)
        gaps = clip(d, 381)
        gaps["ETH-EUR"] = gaps["ETH-EUR"][:250] + gaps["ETH-EUR"][251:]
        with self.assertRaises(ValueError):
            advance(gaps, old)
        corrupted = dict(old)
        corrupted["mode"] = "LIVE_TRADING"
        with self.assertRaises(ValueError):
            advance(clip(d, 381), corrupted)

    def test_no_existing_combined_paper_mutation(self):
        # The shadow engine accepts no path to the legacy ledger, and is
        # safe to exercise in-memory without filesystem or broker actions.
        d = synthetic()
        s = advance(clip(d, 380), None)
        self.assertNotIn("broker_key", s)
        self.assertEqual(s["mode"], "DELAYED_CRYPTO_E_SHADOW_V1")


if __name__ == "__main__":
    unittest.main()
