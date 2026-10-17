"""Tests for optional, not-yet-connected external market-data adapters."""
import unittest
from datetime import date,timedelta
from unittest.mock import patch

from swingbot.ecb_fx import (
    FxUnavailable, parse_ecb_rate, eur_value, ecb_rate_for_day
)
from swingbot.eodhd_feed import (
    EodhdUnavailable, validate_eodhd_rows, fetch_eodhd_eod
)
from swingbot.sec_ipo_filings import (
    SecFeedError, extract_registration_filings, fetch_submissions
)


class FxTests(unittest.TestCase):
    def test_real_ecb_reference_currency_direction(self):
        record=parse_ecb_rate({"date":"2026-10-16","base":"EUR",
                               "quote":"USD","rate":1.20},
                              expected_quote="USD",trading_day=date(2026,10,17))
        self.assertAlmostEqual(eur_value(120,record),100)
        self.assertEqual(record["age_days"],1)

    def test_no_future_wrong_currency_or_stale_rates(self):
        base={"date":"2026-10-16","base":"EUR","quote":"USD","rate":1.20}
        for payload,day in [
            (base,date(2026,10,15)),
            (base,date(2026,10,30)),
            ({**base,"base":"USD"},date(2026,10,17)),
            ({**base,"rate":0},date(2026,10,17)),
        ]:
            with self.assertRaises(FxUnavailable):
                parse_ecb_rate(payload,expected_quote="USD",trading_day=day)

    def test_ecb_endpoint_uses_single_provider_and_historical_date(self):
        class FakeResponse:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):
                return b'{"date":"2026-10-16","base":"EUR","quote":"USD","rate":1.2}'
        with patch("swingbot.ecb_fx.urlopen",return_value=FakeResponse()) as mocked:
            result=ecb_rate_for_day("USD",date(2026,10,17))
            url=mocked.call_args.args[0].full_url
        self.assertIn("/providers/ecb/rate/eur/usd",url)
        self.assertIn("date=2026-10-17",url)
        self.assertEqual(result["date"],"2026-10-16")


def prices(n=210):
    start=date(2025,1,1)
    return [
        {"date":(start+timedelta(days=i)).isoformat(),
         "open":100+i*.1-1,"high":100+i*.1+1,
         "low":100+i*.1-2,"close":100+i*.1,"volume":100000}
        for i in range(n)
    ]


class EodTests(unittest.TestCase):
    def test_data_is_unadjusted_and_never_order_ready(self):
        rows=prices()
        feed=validate_eodhd_rows(rows,ticker="SAP.XETRA",quote_currency="EUR",
                                 as_of=date(2025,8,1))
        self.assertEqual(len(feed.completed),210)
        self.assertFalse(feed.order_ready)
        self.assertIn("NOT_VERIFIED",feed.adjustment_status)

    def test_future_data_and_wrong_currency_blocked(self):
        rows=prices()
        with self.assertRaises(EodhdUnavailable):
            validate_eodhd_rows(rows,ticker="AAPL.US",quote_currency="INVALID",
                                as_of=date(2025,8,1))
        with self.assertRaises(EodhdUnavailable):
            validate_eodhd_rows(rows+[{**rows[-1],"date":rows[-1]["date"]}],
                                ticker="AAPL.US",quote_currency="USD",
                                as_of=date(2025,8,1))
        with self.assertRaises(EodhdUnavailable):
            validate_eodhd_rows(rows,ticker="AAPL.US",quote_currency="USD",
                                as_of=date(2025,10,1))

    def test_requires_private_eodhd_token(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(EodhdUnavailable):
                fetch_eodhd_eod("AAPL.US",quote_currency="USD")


class SecIpoTests(unittest.TestCase):
    def test_filing_does_not_prove_exchange_ipo(self):
        payload={"cik":123456,"name":"Test Corp",
                 "filings":{"recent":{
                     "form":["S-1","F-1","10-K","424B4"],
                     "filingDate":["2026-10-01","2026-10-18",
                                   "2026-01-01","2026-10-10"],
                     "accessionNumber":["0001234567-26-000001"]*4,
                 }}}
        signals=extract_registration_filings(payload,as_of=date(2026,10,17))
        self.assertEqual(len(signals),2)
        self.assertEqual(signals[0]["form"],"424B4")
        self.assertFalse(signals[0]["ipo_confirmed"])
        self.assertFalse(signals[0]["exchange_debut_verified"])

    def test_requires_identifying_sec_user_agent(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(SecFeedError):
                fetch_submissions(12345)


if __name__=="__main__":
    unittest.main()
