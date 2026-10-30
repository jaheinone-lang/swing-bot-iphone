import json
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from swingbot.bitvavo_intraday_history import historical_five_minute
from swingbot.market_data import MarketDataError

class HistoryTests(unittest.TestCase):
    def test_paginates_month_without_holes(self):
        now=datetime(2026,10,22,12,tzinfo=timezone.utc)
        end=int(now.timestamp()*1000)
        start=end-7*288*300000
        def request(url):
            from urllib.parse import urlparse,parse_qs
            q=parse_qs(urlparse(url).query)
            a=int(q["start"][0]);b=int(q["end"][0])
            return json.dumps([[t,100,101,99,100,30]
                               for t in range(a,b,300000)])
        with patch("swingbot.bitvavo_intraday_history._request_text",
                   side_effect=request) as mocked:
            rows=historical_five_minute("BTC-EUR",days=7,now=now)
        self.assertEqual(len(rows),2016)
        self.assertEqual(rows[0]["timestamp_ms"],start)
        self.assertEqual(mocked.call_count,3)

    def test_missing_bars_not_forward_filled(self):
        now=datetime(2026,10,22,12,tzinfo=timezone.utc)
        def request(url):
            from urllib.parse import urlparse,parse_qs
            q=parse_qs(urlparse(url).query)
            a=int(q["start"][0]);b=int(q["end"][0])
            return json.dumps([[t,100,101,99,100,30]
                               for t in range(a,b,300000) if t!=a])
        with patch("swingbot.bitvavo_intraday_history._request_text",
                   side_effect=request):
            with self.assertRaises(MarketDataError):
                historical_five_minute("ETH-EUR",days=7,now=now)

if __name__=="__main__":unittest.main()
