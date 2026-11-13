import unittest
from swingbot.intraday_train_test import SPECS,signal_for,examine

def synthetic(n=950):
    data=[]
    for i in range(n):
        x=100+i*.05
        data.append({"timestamp_ms":1735689600000+i*300000,
                     "open":x,"high":x+0.2,"low":x-0.25,
                     "close":x+.08,"volume":100.0+(30 if i%23==0 else 0)})
    return data

class TrainTestTests(unittest.TestCase):
    def test_fixed_predeclared_choices(self):
        self.assertEqual(len(SPECS),6)
        self.assertFalse(signal_for(SPECS[0])(synthetic(),10))

    def test_train_and_holdout_are_not_deployed(self):
        data=synthetic()
        r=examine(data)
        self.assertEqual(r["train_bars"],570)
        self.assertEqual(r["holdout_bars"],380)
        self.assertFalse(r["pass_for_deployment"])
        self.assertEqual(len(r["hypotheses"]),6)
        self.assertTrue(all("train_stress_eur" in x for x in r["hypotheses"]))
        if r["training_selected"] is None:
            self.assertIsNone(r["later_window"])

    def test_refuses_small_dataset(self):
        with self.assertRaises(ValueError):
            examine(synthetic(800))

if __name__=="__main__":
    unittest.main()
