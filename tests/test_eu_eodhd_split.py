"""EU EODHD split safety: synthetic OHLCV and mock HTTP, no market requests."""
import json
import unittest
from datetime import date, timedelta
from urllib.error import HTTPError
from unittest.mock import patch

from swingbot.eodhd_feed import EodhdFeed, EodhdUnavailable
from swingbot.equity_screen import DailyBar
from swingbot.eu_eodhd_split import (
    fetch_eodhd_splits, parse_split_events, split_adjusted_eur_history
)

ORIGIN = date(2025, 1, 1)
TODAY = ORIGIN + timedelta(days=280)
SPLIT = ORIGIN + timedelta(days=180)


def raw_example(*, symbol="SAP.XETRA"):
    bars=[]
    for i in range(280):
        day = ORIGIN + timedelta(days=i)
        price=100.0 if i < 180 else 25.0
        # EODHD prices raw, volume pre-adjusted for historical splits.
        vol=4000.0
        bars.append(DailyBar(day, price, price+1.0, price-1.0, price, vol))
    return EodhdFeed(
        ticker=symbol, quote_currency="EUR", completed=tuple(bars),
        adjustment_status="RAW_OHLC_NOT_VERIFIED_SPLIT_OR_DIVIDEND_ADJUSTED"
    )


def prepare(raw=None, events=None, **kwargs):
    return split_adjusted_eur_history(
        raw or raw_example(),
        events if events is not None else [
            {"date":SPLIT.isoformat(),"split":"4.000000/1.000000"}
        ],
        as_of=TODAY, research_symbol="SAP.DE",
        exact_eodhd_venue_verified=True,
        broker_isin_and_listing_verified=True,
        personal_non_display_rights_verified=True,
        **kwargs
    )


class SplitTests(unittest.TestCase):
    def test_reconstructs_split_only_prices_but_not_volume_twice(self):
        history=prepare()
        self.assertEqual(history.currency, "EUR")
        self.assertTrue(history.split_adjustment_verified)
        self.assertEqual(history.source, "VERIFIED_EU_PERSONAL_NON_DISPLAY_HISTORY")
        self.assertAlmostEqual(history.bars[179].close, 25)
        self.assertAlmostEqual(history.bars[180].close, 25)
        self.assertAlmostEqual(history.bars[179].open, 25)
        self.assertEqual(history.bars[179].volume, 4000)
        self.assertEqual(history.bars[180].volume, 4000)
        self.assertEqual(history.bars[179].day, SPLIT-timedelta(days=1))
        self.assertEqual(history.bars[180].day, SPLIT)
        self.assertFalse(history.personal_non_display_rights_verified is False)

    def test_multiple_events_and_reverse_splits(self):
        evt=parse_split_events([
            {"date":"2025-03-01","split":"1/5"},
            {"date":"2025-07-01","split":"10/1"}
        ],first_day=ORIGIN,as_of=TODAY)
        self.assertEqual(evt[0][1],.2)
        self.assertEqual(evt[1][1],10)
        self.assertEqual(len(evt),2)

    def test_never_guess_split_from_adjusted_close(self):
        none=prepare(events=[])
        self.assertEqual(none.bars[179].close,100)
        self.assertEqual(none.bars[180].close,25)
        # Without events, the module explicitly does not infer or
        # back-fill splits by comparing adjusted_close to raw OHLC.

    def test_malformed_duplicate_or_out_of_range_events_fail(self):
        valid={"date":SPLIT.isoformat(),"split":"4/1"}
        cases=[
            [valid,valid],
            [{"date":SPLIT.isoformat(),"split":"0/1"}],
            [{"date":SPLIT.isoformat(),"split":"1/0"}],
            [{"date":SPLIT.isoformat(),"split":"infinity/1"}],
            [{"date":SPLIT.isoformat(),"split":"4/1;OTHER"}],
            [{"date":(TODAY+timedelta(days=1)).isoformat(),"split":"4/1"}],
            [{"date":"2020-01-01","split":"4/1"}],
            {"bars":[]},
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(EodhdUnavailable):
                parse_split_events(rows,first_day=ORIGIN,as_of=TODAY)

    def test_invalid_exchange_currency_and_rights_blocked(self):
        for variant in (
            "SAP.US", "NOVO-B.CO", "SAP.PA", "SAP.HE", "BMW.XETRA",
        ):
            with self.subTest(ticker=variant), self.assertRaises(EodhdUnavailable):
                prepare(raw_example(symbol=variant))
        for flag in (
            "exact_eodhd_venue_verified",
            "broker_isin_and_listing_verified",
            "personal_non_display_rights_verified",
        ):
            kwargs={flag:False}
            with self.subTest(flag=flag), self.assertRaises(PermissionError):
                split_adjusted_eur_history(
                    raw_example(), [{"date":SPLIT.isoformat(),"split":"4/1"}],
                    as_of=TODAY,research_symbol="SAP.DE",
                    exact_eodhd_venue_verified=kwargs.get("exact_eodhd_venue_verified",True),
                    broker_isin_and_listing_verified=kwargs.get("broker_isin_and_listing_verified",True),
                    personal_non_display_rights_verified=kwargs.get("personal_non_display_rights_verified",True)
                )
        with self.assertRaises(EodhdUnavailable):
            split_adjusted_eur_history(
                raw_example(),[],as_of=TODAY,
                research_symbol="NOVO-B.CO",
                exact_eodhd_venue_verified=True,
                broker_isin_and_listing_verified=True,
                personal_non_display_rights_verified=True
            )

    def test_split_ex_date_must_have_completed_session(self):
        # The split event alone cannot adjust bars before the first
        # completed post-split trading day; no future look-ahead.
        with self.assertRaises(EodhdUnavailable):
            prepare(events=[
                {"date":TODAY.isoformat(),"split":"4/1"}
            ])
        missing_day = raw_example()
        missing = tuple(b for b in missing_day.completed if b.day != SPLIT)
        from dataclasses import replace
        with self.assertRaises(EodhdUnavailable):
            prepare(replace(missing_day, completed=missing))

    def test_eodhd_split_to_abc_research_integration_without_network(self):
        # Deliberately synthetic prices with manually asserted permissions:
        # software integration only, NOT a real verified venue/rights proof.
        from swingbot.eu_swing_lab import compare_eu_abc_offline
        candles=[]
        for i in range(430):
            day=ORIGIN+timedelta(days=i)
            px=(95+i*.05) if i < 180 else (95+i*.05)/4
            candles.append(DailyBar(
                day,px,px*1.015,px*.985,px,200000))
        dataset=EodhdFeed(
            ticker="SAP.XETRA",quote_currency="EUR",
            completed=tuple(candles),
            adjustment_status="RAW_OHLC_NOT_VERIFIED_SPLIT_OR_DIVIDEND_ADJUSTED"
        )
        cutoff=ORIGIN+timedelta(days=430)
        feed=split_adjusted_eur_history(
            dataset,[{"date":SPLIT.isoformat(),"split":"4/1"}],
            as_of=cutoff,research_symbol="SAP.DE",
            exact_eodhd_venue_verified=True,
            broker_isin_and_listing_verified=True,
            personal_non_display_rights_verified=True
        )
        self.assertLess(abs(feed.bars[179].close/feed.bars[180].close-1),.01)
        # Permission to compare must be separately confirmed, even with
        # an injected EODHD history whose adjustment was checked.
        with self.assertRaises(PermissionError):
            compare_eu_abc_offline({"SAP.DE":feed},as_of=cutoff)
        result=compare_eu_abc_offline(
            {"SAP.DE":feed},as_of=cutoff,
            personal_non_display_use_confirmed=True
        )
        self.assertEqual(len(result["variants"]),3)
        self.assertEqual(result["symbol_count"],1)
        self.assertEqual(result["source_type"],
                         "USER_VERIFIED_PRIVATE_NON_DISPLAY_EU_EOD")
        self.assertFalse(result["broker_orders_enabled"])
        self.assertFalse(result["eur_paper_portfolio_modified"])

    def test_no_secret_or_unsafe_url_and_read_only_mock(self):
        seen=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return b'[{"date":"2025-06-30","split":"2/1"}]'
        def opener(request,timeout):
            seen.append(request)
            return Response()
        rows=fetch_eodhd_splits(
            provider_symbol="SAP.XETRA",
            first_day=ORIGIN,as_of=TODAY,
            api_token="SECRET_DO_NOT_LOG",urlopen=opener
        )
        self.assertEqual(rows[0]["split"],"2/1")
        self.assertEqual(seen[0].get_method(),"GET")
        self.assertEqual(len(seen),1)
        self.assertIn("/api/splits/SAP.XETRA?",seen[0].full_url)
        self.assertIn("api_token=",seen[0].full_url)
        with self.assertRaises(EodhdUnavailable) as raised:
            fetch_eodhd_splits(
                provider_symbol="SAP.XETRA",first_day=ORIGIN,
                as_of=TODAY,api_token="MY_PRIVATE_SECRET",
                urlopen=lambda *a,**k: (_ for _ in ()).throw(
                    HTTPError("https://eodhd.com/api/splits/a?api_token=MY_PRIVATE_SECRET",403,"denied",None,None))
            )
        self.assertNotIn("MY_PRIVATE_SECRET",str(raised.exception))
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(EodhdUnavailable):
                fetch_eodhd_splits(
                    provider_symbol="SAP.XETRA",first_day=ORIGIN,as_of=TODAY
                )


if __name__=="__main__":
    unittest.main()
