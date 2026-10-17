"""Offline checks for Trading 212 catalog, SEC filing chronology, IPO filter."""
import unittest
from datetime import date,timedelta
from unittest.mock import patch
from swingbot.trading212_universe import (
    load_demo_universe,summarize_universe,UniverseUnavailable
)
from swingbot.sec_fundamentals import analyze_companyfacts
from swingbot.ipo_watch import IpoBar,ipo_setup


def annual(year, value, filed=None):
    return {
        "form":"10-K","fp":"FY","fy":year,
        "start":f"{year}-01-01","end":f"{year}-12-31",
        "filed":filed or f"{year+1}-02-15","val":value,
        "accn":f"0000{year}"
    }


class BrokerUniverseTests(unittest.TestCase):
    def test_reads_only_stocks_etfs_and_add_date_not_ipo(self):
        rows=[
            {"ticker":"ABC_US_EQ","type":"STOCK","isin":"US1234","currencyCode":"USD",
             "shortName":"ABC","addedOn":"2026-10-15T10:00:00Z"},
            {"ticker":"XYZ_DE_EQ","type":"ETF","isin":"DE5678","currencyCode":"EUR",
             "addedOn":"2026-10-01T10:00:00Z"},
            {"ticker":"DERIV_X","type":"WARRANT","currencyCode":"USD"},
        ]
        report=summarize_universe(rows,as_of=date(2026,10,17))
        self.assertEqual(report["stock_instruments"],1)
        self.assertEqual(report["etf_instruments"],1)
        self.assertEqual(report["platform_additions_30d"],2)
        self.assertIsNone(report["ipo_discovered"])

    def test_missing_secret_fails_closed(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(UniverseUnavailable):
                load_demo_universe()


class FundamentalsTests(unittest.TestCase):
    def test_prevent_future_filing_and_restatement_leakage(self):
        facts={"cik":12345,"entityName":"FixtureCorp","facts":{"us-gaap":{
            "RevenueFromContractWithCustomerExcludingAssessedTax":{
                "units":{"USD":[annual(2024,100),annual(2025,125),
                    annual(2025,999,"2027-01-01")] }},
            "NetIncomeLoss":{"units":{"USD":[annual(2024,5),annual(2025,12)]}},
            "NetCashProvidedByUsedInOperatingActivities":{"units":{"USD":[
                annual(2024,15),annual(2025,20)]}},
            "PaymentsToAcquirePropertyPlantAndEquipment":{"units":{"USD":[
                annual(2024,4),annual(2025,6)]}},
        }}}
        no_future=analyze_companyfacts(facts,as_of=date(2025,12,31))
        self.assertEqual(no_future["fundamentals_status"],"INSUFFICIENT")
        later=analyze_companyfacts(facts,as_of=date(2026,10,17))
        self.assertEqual(later["revenue_growth_pct"],25)
        self.assertEqual(later["free_cashflow_proxy_usd"],14)
        self.assertEqual(later["points"],55)
        self.assertEqual(later["revenue_filed"],"2026-02-15")
        self.assertEqual(later["earnings_surprise_status"],"NO_ANALYST_CONSENSUS")

    def test_missing_required_filings_not_imputed(self):
        f={"facts":{"us-gaap":{}}}
        self.assertEqual(analyze_companyfacts(f,as_of=date(2026,10,17))
                         ["fundamentals_status"],"INSUFFICIENT")


def ipo_bars(n=8,breakout=True,thin=False):
    d=date(2026,10,1)
    bars=[]
    for k in range(n):
        close=24 if k==n-1 and breakout else 20
        v=1000 if thin else (1500000 if k==n-1 else 1000000)
        # The breakout is a 7.5% opening gap, inside the <12% safety limit.
        opening=(close-2.5) if (k==n-1 and breakout) else close-1
        bars.append(IpoBar(d+timedelta(days=k),opening,close+1,
                           min(opening,close)-.5,close,v))
    return bars


class IpoTests(unittest.TestCase):
    def test_platform_add_date_never_counts_as_debut(self):
        r=ipo_setup(ticker="ABC",confirmed_exchange_debut=None,
                    verified_listing_source=None,candles=ipo_bars(),
                    currency="USD",broker_available=True,spread_bps=5,
                    fx_conversion_verified=True)
        self.assertEqual(r["signal"],"NO_DATA")

    def test_wait_for_five_completed_days(self):
        r=ipo_setup(ticker="ABC",confirmed_exchange_debut=date(2026,10,1),
                    verified_listing_source="https://issuer.example/verified",
                    candles=ipo_bars(4),currency="USD",
                    broker_available=True,spread_bps=10,fx_conversion_verified=True)
        self.assertEqual(r["signal"],"WAIT_5_DAYS")

    def test_spread_fx_liquidity_and_breakout_gates(self):
        kw=dict(ticker="ABC",confirmed_exchange_debut=date(2026,10,1),
                verified_listing_source="https://issuer.example/verified",
                candles=ipo_bars(),currency="USD",broker_available=True,
                spread_bps=10,fx_conversion_verified=True)
        self.assertEqual(ipo_setup(**kw)["signal"],"IPO_BREAKOUT_WATCH")
        self.assertEqual(ipo_setup(**{**kw,"spread_bps":None})["signal"],"NO_SPREAD")
        self.assertEqual(ipo_setup(**{**kw,"fx_conversion_verified":False})["signal"],"NEEDS_FX")
        self.assertEqual(ipo_setup(**{**kw,"candles":ipo_bars(thin=True)})["signal"],"SKIP_LIQUIDITY")
        self.assertEqual(ipo_setup(**{**kw,"candles":ipo_bars(breakout=False)})["signal"],"WATCH")
        self.assertFalse(ipo_setup(**kw)["eligible_for_real_orders"])


if __name__=="__main__":
    unittest.main()
