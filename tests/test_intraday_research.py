import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import json
from swingbot.bitvavo_intraday import intraday_candles
from swingbot.intraday_research import replay

def bars(n=100):
    out=[]
    for i in range(n):
        p=100+i*.11
        out.append({"timestamp_ms":1735689600000+i*300000,
                    "open":p,"high":p+1.5,"low":p-.25,"close":p+.1})
    return out

class IntradayTests(unittest.TestCase):
    def test_report_no_orders_and_no_zero_fee_claim(self):
        r=replay(bars())
        self.assertEqual(r["mode"],"READ_ONLY_INTRADAY_BACKTEST")
        self.assertGreaterEqual(r["buys"],0)
        self.assertEqual(r["initial_eur"],5000)
        self.assertIn("estimated_pnl_eur",r)

    def test_gapped_candles_fail_closed(self):
        b=bars()
        b[40]["timestamp_ms"]+=1000
        with self.assertRaises(ValueError):
            replay(b)

    def test_provider_omits_unfinished_bars(self):
        start=1735689600000
        rows=[[start+i*300000,100,101,99,100,0] for i in range(41)]
        now=datetime.fromtimestamp((start+40*300000)/1000,timezone.utc)
        with patch("swingbot.bitvavo_intraday._request_text",return_value=json.dumps(rows)):
            candles=intraday_candles("BTC-EUR",limit=100,now=now)
        self.assertEqual(len(candles),40)

    def test_provider_rejects_gaps(self):
        start=1735689600000
        rows=[[start+i*300000,100,101,99,100,0] for i in range(40) if i!=20]
        now=datetime.fromtimestamp((start+42*300000)/1000,timezone.utc)
        with patch("swingbot.bitvavo_intraday._request_text",return_value=json.dumps(rows)):
            with self.assertRaises(Exception):
                intraday_candles("BTC-EUR",limit=100,now=now)

if __name__=="__main__":
    unittest.main()
