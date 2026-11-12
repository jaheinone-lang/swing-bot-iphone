import unittest
from datetime import datetime,timezone
from urllib.parse import urlsplit,parse_qs
import json
from swingbot.daily_swing_research import (
    history,split_eras,signal,replay,RULES,DAY,START,END,STRESS)

class DailyResearchTests(unittest.TestCase):
    def test_public_daily_download_and_gap_check(self):
        def fake(url):
            q=parse_qs(urlsplit(url).query)
            self.assertEqual(q["interval"],["1d"])
            lo=int(q["start"][0]);hi=int(q["end"][0])
            return json.dumps([[t,"100","101","99","100","5"]
                for t in range(lo,hi,DAY)])
        sections,meta=history(fetch=fake)
        self.assertEqual(len(sections),1)
        self.assertEqual(meta["both_common_days"],(END-START).days)
        self.assertTrue(meta["no_fill_of_missing_days"])
    def test_flat_market_no_phantom_trades(self):
        start=int(START.timestamp()*1000)
        b=[{"timestamp_ms":start+i*DAY,"open":100.,"high":100.5,
            "low":99.5,"close":100.,"volume":1000.} for i in range(400)]
        f={"BTC-EUR":b,"ETH-EUR":[dict(x) for x in b]}
        for name in RULES:
            self.assertFalse(signal(b,205,name))
            self.assertEqual(replay([(f,0)],name)["pnl_eur"],0)
            self.assertEqual(replay([(f,0)],name,STRESS)["trades"],0)
    def test_split_previously_known_warmup_and_no_future_in_signal(self):
        start=int(datetime(2023,4,1,tzinfo=timezone.utc).timestamp()*1000)
        b=[{"timestamp_ms":start+i*DAY,"open":100.,"high":101.,
            "low":99.,"close":100.,"volume":1000.} for i in range(700)]
        f={"BTC-EUR":b,"ETH-EUR":[dict(x) for x in b]}
        p=split_eras([f])
        self.assertTrue(p["early"])
        self.assertTrue(p["later"])
        before=[signal(b,240,name) for name in RULES]
        b[241]["high"]=500000
        self.assertEqual(before,[signal(b,240,name) for name in RULES])
    def test_bad_rule(self):
        b=[{"close":100.,"high":101.,"low":99.,"open":100.} for _ in range(300)]
        with self.assertRaises(ValueError):signal(b,205,"risk_free_profit")
if __name__=="__main__":unittest.main()
