"""Forward paper state regression: no historical fictional fills, no duplicates."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from swingbot.forward_paper import advance_paper, public_paper_summary, _sell
from swingbot.dashboard_report import refresh_snapshot_and_paper
from swingbot.market_data import MarketDataError
from swingbot.portfolio import Bar


def prices(days=64, *, start=date(2026, 7, 1)):
    bars = []
    for i in range(days):
        close = 100.0 if i < 61 else 120.0 + (i - 61)
        # For first 61 candles, constant price. The first breakout
        # after initialization is on day 62.
        bars.append(Bar(start + timedelta(days=i), close, close + 2.0,
                        close - 2.0, close))
    return bars


def one_feed(bars):
    return {"FAKE": bars}, {"FAKE": "stock"}


class PaperLedgerTests(unittest.TestCase):
    def test_initialized_account_has_no_backfilled_trades(self):
        bars = prices(62)
        data, market = one_feed(bars)
        state = advance_paper(data, market, as_of=bars[-1].day + timedelta(days=1))
        self.assertEqual(state["cash_eur"], 5000)
        self.assertEqual(state["events"], [])
        self.assertEqual(state["positions"], {})
        self.assertEqual(state["pending"], {})
        self.assertEqual(state["last_processed_day"], bars[-1].day.isoformat())

    def test_signal_then_next_candle_fill_and_no_duplicates(self):
        bars = prices(64)
        data0, markets = one_feed(bars[:61])
        state0 = advance_paper(data0, markets,
                               as_of=bars[60].day + timedelta(days=1))
        data1, _ = one_feed(bars[:62])
        state1 = advance_paper(data1, markets, state0,
                               as_of=bars[61].day + timedelta(days=1))
        self.assertEqual(state1["events"], [])
        self.assertIn("FAKE", state1["pending"])
        data2, _ = one_feed(bars[:63])
        state2 = advance_paper(data2, markets, state1,
                               as_of=bars[62].day + timedelta(days=1))
        buys = [x for x in state2["events"] if x["side"] == "BUY"]
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0]["day"], bars[62].day.isoformat())
        self.assertLessEqual(buys[0]["quantity"] * buys[0]["price_eur"], 1000.01)
        self.assertEqual(state1["events"], [])
        again = advance_paper(data2, markets, state2,
                              as_of=bars[62].day + timedelta(days=1))
        self.assertEqual(again, state2)

    def test_existing_position_gap_stop_sells_without_crash(self):
        bars = prices(64)
        data0, markets = one_feed(bars[:61])
        state = advance_paper(data0, markets,
                              as_of=bars[60].day + timedelta(days=1))
        for n in (62, 63):
            data, _ = one_feed(bars[:n])
            state = advance_paper(data, markets, state,
                                  as_of=bars[n-1].day + timedelta(days=1))
        self.assertIn("FAKE", state["positions"])
        d = bars[63].day
        gap = Bar(d, 45, 47, 43, 45)
        data, _ = one_feed(bars[:63] + [gap])
        sold = advance_paper(data, markets, state,
                             as_of=d + timedelta(days=1))
        self.assertNotIn("FAKE", sold["positions"])
        self.assertTrue(any(
            event["side"] == "SELL" and event["reason"] == "STOP"
            for event in sold["events"]
        ))
        self.assertLess(sold["cash_eur"], 5000)

    def test_profitable_exit_reserves_tax_and_removes_it_from_spending_cash(self):
        bars = prices(63)
        data, market = one_feed(bars[:61])
        state = advance_paper(data, market, as_of=bars[60].day+timedelta(days=1))
        data, _ = one_feed(bars[:62])
        state = advance_paper(data, market, state, as_of=bars[61].day+timedelta(days=1))
        data, _ = one_feed(bars[:63])
        state = advance_paper(data, market, state, as_of=bars[62].day+timedelta(days=1))
        self.assertIn("FAKE", state["positions"])
        from copy import deepcopy
        modified=deepcopy(state)
        _sell(modified,"FAKE",180,"stock",bars[62].day+timedelta(days=1),
              "TEST_PROFIT")
        self.assertGreater(modified["tax_reserved_eur"],0)
        view=public_paper_summary(modified)
        self.assertEqual(view["cash_available_for_trades_eur"],
                         round(max(0,modified["cash_eur"]-
                                   modified["tax_reserved_eur"]),2))
        self.assertGreater(view["cash_eur"],view["cash_available_for_trades_eur"])
        self.assertLess(view["equity_eur"],round(modified["cash_eur"],2))

    def test_safe_migration_without_trades_keeps_initial_balance(self):
        bars=prices(62)
        data,market=one_feed(bars)
        state=advance_paper(data,market,as_of=bars[-1].day+timedelta(days=1))
        state.pop("tax_reserved_eur")
        state.pop("disposals")
        migrated=advance_paper(data,market,state,
                               as_of=bars[-1].day+timedelta(days=1))
        self.assertEqual(migrated["tax_reserved_eur"],0)
        self.assertEqual(migrated["cash_eur"],5000)
        self.assertEqual(migrated["events"],[])
        self.assertNotIn("tax_reserved_eur",state)

    def test_tax_migration_with_legacy_trades_fails_safely(self):
        bars=prices(62)
        data,market=one_feed(bars)
        state=advance_paper(data,market,as_of=bars[-1].day+timedelta(days=1))
        state["events"].append({"side":"BUY"})
        state.pop("tax_reserved_eur")
        with self.assertRaises(ValueError):
            advance_paper(data,market,state,
                          as_of=bars[-1].day+timedelta(days=1))

    def test_corrupt_or_mismatched_state_cannot_be_reset(self):
        bars = prices(62)
        data, markets = one_feed(bars)
        state = advance_paper(data, markets,
                              as_of=bars[-1].day + timedelta(days=1))
        state["initial_eur"] = 10000
        with self.assertRaises(ValueError):
            advance_paper(data, markets, state,
                          as_of=bars[-1].day + timedelta(days=1))

    def test_stale_feed_aborts_without_changing_prior_state(self):
        bars = prices(62)
        data, markets = one_feed(bars)
        state = advance_paper(data, markets,
                              as_of=bars[-1].day + timedelta(days=1))
        snapshot = json.dumps(state, sort_keys=True)
        with self.assertRaises(ValueError):
            advance_paper(data, markets, state,
                          as_of=bars[-1].day + timedelta(days=13))
        self.assertEqual(snapshot, json.dumps(state, sort_keys=True))

    def test_summary_only_contains_forward_events(self):
        bars = prices(62)
        data, markets = one_feed(bars)
        state = advance_paper(data, markets,
                              as_of=bars[-1].day + timedelta(days=1))
        view = public_paper_summary(state)
        self.assertEqual(view["mode"], "DELAYED_FORWARD_PAPER")
        self.assertEqual(view["equity_eur"], 5000)
        self.assertEqual(view["events"], [])


class DashboardPersistenceTests(unittest.TestCase):
    def test_missing_feed_does_not_reset_existing_account(self):
        bars = prices(62)
        data, markets = one_feed(bars)
        previous = advance_paper(data, markets,
                                 as_of=bars[-1].day + timedelta(days=1))
        with tempfile.TemporaryDirectory() as folder:
            state_path = Path(folder, "state.json")
            report_path = Path(folder, "data.json")
            state_path.write_text(json.dumps(previous), encoding="utf-8")
            snapshot = {
                "schema_version": 1, "generated_at_utc": "2026-10-17T00:00:00Z",
                "instruments": [{"symbol": "FAKE", "status": "unavailable"}],
                "portfolio_backtest": None, "paper_account": None, "messages": [],
            }
            with patch("swingbot.dashboard_report.build_snapshot",
                       return_value=snapshot):
                report = refresh_snapshot_and_paper(state_path=state_path,
                                                     report_path=report_path)
            self.assertEqual(report["paper_account"]["status"], "PAUSED")
            self.assertEqual(json.loads(state_path.read_text()), previous)

    def test_complete_feed_creates_account_without_fake_history(self):
        bars = prices(62)
        with tempfile.TemporaryDirectory() as folder:
            state_path = Path(folder, "paper_state.json")
            report_path = Path(folder, "data.json")
            snap = {
                "schema_version": 1, "generated_at_utc": "2026-10-17T00:00:00Z",
                "instruments": [
                    {"symbol": "FAKE", "status": "ok", "day": bars[-1].day.isoformat(),
                     "last_completed_close_eur": bars[-1].close}
                ], "portfolio_backtest": None, "paper_account": None, "messages": [],
            }
            with patch("swingbot.dashboard_report.INSTRUMENTS",
                       {"FAKE": ("stock", lambda s: bars, "mock")}), patch(
                "swingbot.dashboard_report.build_snapshot",
                return_value=snap
            ):
                # Avoid stale data in fixture by setting UTC date internally.
                with patch("swingbot.dashboard_report.advance_paper",
                           side_effect=lambda data, markets, old:
                           advance_paper(data, markets, old,
                                         as_of=bars[-1].day + timedelta(days=1))):
                    report = refresh_snapshot_and_paper(
                        state_path=state_path, report_path=report_path
                    )
            self.assertEqual(report["paper_account"]["status"], "ACTIVE")
            self.assertEqual(report["paper_account"]["events"], [])
            self.assertEqual(report["paper_account"]["equity_eur"], 5000)
            self.assertTrue(state_path.exists())


if __name__ == "__main__":
    unittest.main()
