"""Offline-only three-fold walk-forward software safety matrix.

Uses invented OHLCV and reports *pass/fail only*. Returns are never
reported as real performance. No credentials, market-data API or orders.
"""
import json
from datetime import date, timedelta
from math import sin,cos

from .equity_screen import DailyBar
from .massive_free import FreeMarketHistory
from .us_walkforward import walkforward_abc_offline


def fixture(symbol,kind,offset):
    bars=[]
    start=date(2025,1,1)
    for i in range(570):
        if kind=="TREND_RANGE_TREND":
            core=(100+.24*i if i<230 else
                  155+3*sin(i/16) if i<410 else 155+.38*(i-410))
        elif kind=="SHOCK_AND_DECLINE":
            core=(130+.1*i if i<330 else
                  110 if i<360 else max(40,110-.19*(i-360)))
        else:
            raise AssertionError("Invalid regime")
        p=max(5,core*(1+.005*sin((i+offset)/9)))
        op=p*(1+.003*cos((i+offset)/4))
        bars.append(DailyBar(
            start+timedelta(days=i),op,
            max(op,p)*1.015,min(op,p)*.985,p,3_000_000
        ))
    return FreeMarketHistory(
        ticker=symbol,currency="USD",source="SYNTHETIC_TEST_FIXTURE",
        adjustment="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED",bars=tuple(bars))


def run():
    checks=[]
    for regime in ("TREND_RANGE_TREND","SHOCK_AND_DECLINE"):
        universe={s:fixture(s,regime,i*9)
                  for i,s in enumerate(("AAPL","MSFT","JPM","NVDA"))}
        day=next(iter(universe.values())).bars[-1].day+timedelta(days=1)
        report=walkforward_abc_offline(universe,as_of=day)
        fs=report["folds"]
        assert len(fs)==3
        assert all(f["selected_from_training"] in "ABC" for f in fs)
        assert all(not f["qualified_historical_fold"] for f in fs)
        assert all(f["cash_reset_between_folds"] for f in fs)
        assert all(f["reference_is_investable"] is False for f in fs)
        assert report["synthetic_only"]
        assert report["strategy_profitability_proven"] is False
        assert report["automatic_order_execution"] is False
        assert report["paper_order_execution"] is False
        assert report["eur_portfolio_modified"] is False
        assert fs[0]["holdout_end"]<fs[1]["holdout_start"]
        assert fs[1]["holdout_end"]<fs[2]["holdout_start"]
        checks.append({"scenario":regime,"passed":True})
    return {"status":"SYNTHETIC_WALKFORWARD_CODE_SAFETY_PASSED",
            "scenario_checks":checks,
            "folds_per_scenario":3,
            "variants_per_fold":3,
            "real_stock_prices_loaded":False,
            "actual_profitability_tested":False,
            "orders_enabled":False}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False))
