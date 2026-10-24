import unittest
from swingbot.intraday_entry_filters import filtered_buy_signal, compare
from swingbot.intraday_research import replay

def bars(n=150):
    arr=[]
    for i in range(n):
        p=100+i*.05
        arr.append({"timestamp_ms":1700000100000+i*300000,
                    "open":p-.04,"high":p+.15,"low":p-.16,
                    "close":p+.07,"volume":100})
    return arr

class EntryFilterTests(unittest.TestCase):
    def test_rejects_absent_volume(self):
        data=bars()
        for bar in data:
            bar.pop("volume")
        self.assertFalse(filtered_buy_signal(data,100))

    def test_rejects_no_volume_confirmation(self):
        data=bars()
        self.assertFalse(filtered_buy_signal(data,100))

    def test_replay_is_backward_compatible(self):
        data=bars()
        base=replay(data)
        custom=replay(data,signal=lambda candles,i: False)
        self.assertEqual(custom["buys"],0)
        self.assertEqual(custom["estimated_pnl_eur"],0)
        self.assertIn("estimated_pnl_eur",base)

    def test_comparison_separate_models(self):
        data=bars()
        r=compare(data)
        self.assertIn("baseline",r)
        self.assertIn("filtered",r)
        self.assertEqual(r["bars"],len(data))

if __name__=="__main__": unittest.main()
