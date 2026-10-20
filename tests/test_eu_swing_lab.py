"""EU A/B/C research safety tests. Offline fixtures, never broker or live data."""
import unittest
from dataclasses import replace
from datetime import date, timedelta

from swingbot.equity_screen import DailyBar
from swingbot.eu_swing_lab import (
    EUHistory, VERIFIED, compare_eu_abc_offline
)


def synthetic(symbol="SAP.DE", n=420, *, multiplier=1.0):
    start=date(2025,1,1)
    candles=[]
    for i in range(n):
        mid=(90.0+i*.16+(i % 11)*.08)*multiplier
        candles.append(DailyBar(
            start+timedelta(days=i),
            mid-.3*multiplier,
            mid+1.2*multiplier,
            mid-1.3*multiplier,
            mid,
            500_000.0
        ))
    return EUHistory(symbol, "EUR", tuple(candles))


class EUABCResearchTests(unittest.TestCase):
    def test_synthetic_eur_abc_uses_common_training_and_holdout(self):
        a=synthetic()
        b=synthetic("ASML.AS", multiplier=1.4)
        as_of=b.bars[-1].day+timedelta(days=1)
        r=compare_eu_abc_offline({"SAP.DE":a,"ASML.AS":b},as_of=as_of)
        self.assertEqual(r["source_type"],"SYNTHETIC_TEST_FIXTURES_ONLY")
        self.assertEqual(r["starting_eur"],5000)
        self.assertEqual(r["symbol_count"],2)
        self.assertEqual(len(r["variants"]),3)
        self.assertLess(r["training_end"],r["holdout_start"])
        self.assertEqual(r["qualified_strategy"],None)
        self.assertFalse(r["broker_orders_enabled"])
        self.assertFalse(r["eur_paper_portfolio_modified"])
        for v in r["variants"]:
            for period in ("training","holdout"):
                stats=v[period]
                self.assertEqual(stats["currency"],"EUR")
                self.assertEqual(stats["starting_eur"],5000)
                self.assertNotIn("starting_usd",stats)
                self.assertNotIn("ending_mark_to_market_usd",stats)
                self.assertFalse(stats["real_order_authorized"])
                self.assertFalse(stats["paper_order_authorized"])
                self.assertLessEqual(
                    stats["max_planned_stop_risk_pct_of_equity"],1.001
                )

    def test_dkk_and_sek_cannot_enter_eur_account_without_fx(self):
        n=synthetic("SAP.DE")
        as_of=n.bars[-1].day+timedelta(days=1)
        for symbol,ccy in [("NOVO-B.CO","DKK"),("VOLV-B.ST","SEK")]:
            with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                compare_eu_abc_offline(
                    {symbol:replace(n,symbol=symbol,currency=ccy)},
                    as_of=as_of
                )
            # Falsely labelling native DKK/SEK quotes as EUR also fails:
            with self.subTest(symbol=symbol+" false EUR"), self.assertRaises(ValueError):
                compare_eu_abc_offline(
                    {symbol:replace(n,symbol=symbol,currency="EUR")},
                    as_of=as_of
                )

    def test_foreign_us_unknown_and_spoofed_tickers_refused(self):
        n=synthetic()
        as_of=n.bars[-1].day+timedelta(days=1)
        for name in ["AAPL","NESN.SW","VOD.L","NOT_EU"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                compare_eu_abc_offline(
                    {name:replace(n,symbol=name)},as_of=as_of
                )
        with self.assertRaises(ValueError):
            compare_eu_abc_offline(
                {"ASML.AS":n},as_of=as_of
            )

    def test_real_non_display_data_not_autorized_by_only_one_flag(self):
        n=synthetic()
        as_of=n.bars[-1].day+timedelta(days=1)
        r=replace(n,source=VERIFIED)
        with self.assertRaises(PermissionError):
            compare_eu_abc_offline({"SAP.DE":r},as_of=as_of)
        with self.assertRaises(PermissionError):
            compare_eu_abc_offline({"SAP.DE":r},as_of=as_of,
                                   personal_non_display_use_confirmed=True)
        all_verified=replace(
            r,exchange_verified=True,
            exact_broker_instrument_verified=True,
            split_adjustment_verified=True,
            personal_non_display_rights_verified=True
        )
        with self.assertRaises(PermissionError):
            compare_eu_abc_offline({"SAP.DE":all_verified},as_of=as_of)
        report=compare_eu_abc_offline(
            {"SAP.DE":all_verified},as_of=as_of,
            personal_non_display_use_confirmed=True
        )
        self.assertEqual(report["source_type"],
                         "USER_VERIFIED_PRIVATE_NON_DISPLAY_EU_EOD")
        self.assertFalse(report["broker_orders_enabled"])
        with self.assertRaises(ValueError):
            compare_eu_abc_offline(
                {"SAP.DE":all_verified, "ASML.AS":synthetic("ASML.AS")},
                as_of=as_of,personal_non_display_use_confirmed=True
            )

    def test_changing_future_data_does_not_change_past(self):
        n=synthetic()
        today=n.bars[-1].day+timedelta(days=1)
        base=compare_eu_abc_offline({"SAP.DE":n},as_of=today)
        future=DailyBar(today,1000,1010,990,1005,999999)
        later=compare_eu_abc_offline(
            {"SAP.DE":replace(n,bars=n.bars+(future,))},
            as_of=today
        )
        self.assertEqual(base,later)

    def test_short_calendar_duplicate_and_stale_rejected(self):
        n=synthetic()
        today=n.bars[-1].day+timedelta(days=1)
        with self.assertRaises(ValueError):
            compare_eu_abc_offline(
                {"SAP.DE":replace(n,bars=n.bars[:265])},as_of=today
            )
        bad=replace(n,bars=n.bars+(n.bars[-1],))
        with self.assertRaises(ValueError):
            compare_eu_abc_offline({"SAP.DE":bad},as_of=today)
        fully=replace(n,source=VERIFIED,exchange_verified=True,
                      exact_broker_instrument_verified=True,
                      split_adjustment_verified=True,
                      personal_non_display_rights_verified=True)
        with self.assertRaises(ValueError):
            compare_eu_abc_offline(
                {"SAP.DE":fully},as_of=today+timedelta(days=20),
                personal_non_display_use_confirmed=True
            )


if __name__=="__main__":
    unittest.main()
