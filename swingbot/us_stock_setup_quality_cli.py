"""Deterministic stock setup gate matrix, synthetic data ONLY.

Reports observed/rejected signals and integrity safeguards, NEVER ROI.
No web/API data, broker authentication, buys, shorts or fill simulations.
"""
from __future__ import annotations
from datetime import date,timedelta
import json
from .equity_screen import DailyBar
from .us_stock_setup_research import scan,FAMILIES

def fixture(last,*,volume=1_000_000):
    first=date(2025,1,1)
    bars=[]
    for i in range(219):
        p=10+i*.01
        bars.append(DailyBar(first+timedelta(days=i),
                             p,p*1.01,p*.99,p,volume))
    bars.append(DailyBar(first+timedelta(days=219),*last))
    return bars

def report():
    cases={
      "liquid_smallcap_momentum":{
        "last":(13.7,15.2,13.6,14.7,4_000_000),
        "cap":800_000_000,"expected":"small_cap_momentum"},
      "failed_gap_up_bearish_watch":{
        "last":(13.6,14.2,11.3,11.5,4_000_000),
        "cap":800_000_000,"expected":"failed_gap_up"},
      "largecap_20day_breakout":{
        "last":(14.8,16.0,14.7,15.8,4_000_000),
        "cap":20_000_000_000,"expected":"large_cap_breakout"},
      "flat_market_no_signal":{
        "last":(12.19,12.3,12.1,12.19,1_000_000),
        "cap":800_000_000,"expected":None},
    }
    rows=[]
    for label,case in cases.items():
        bars=fixture(case["last"])
        s=scan("SYNTHETIC",bars,as_of=date(2025,8,9),
            market_cap_usd=case["cap"],consolidated_volume=True,
            split_adjusted=True,verified_spread_bps=12)
        selected=[name for name,v in s["family_signals"].items() if v]
        if selected != ([] if case["expected"] is None else [case["expected"]]):
            raise AssertionError(label+": incorrect signal gate result")
        if s["paper_order_authorized"] or s["live_order_authorized"] or s["short_order_authorized"]:
            raise AssertionError("Broker permission accidentally enabled")
        rows.append({"scenario":label,"signals":selected,"passed":True})
    # Explicit fail-closed tests on same positive candidate.
    b=fixture(cases["liquid_smallcap_momentum"]["last"])
    for label,kw in {
        "iex_partial_volume":{"consolidated_volume":False},
        "unknown_historical_market_cap":{"market_cap_usd":None},
        "missing_verified_spread":{"verified_spread_bps":None},
        "unadjusted_split_history":{"split_adjusted":False},
        "future_data_as_of":{"as_of":b[-1].day},
    }.items():
        args={"market_cap_usd":800_000_000,
            "consolidated_volume":True,"split_adjusted":True,
            "verified_spread_bps":12,"as_of":date(2025,8,9)}
        args.update(kw)
        r=scan("SYNTHETIC",b,**args)
        if r["status"]!="REJECTED" or any(r["family_signals"].values()):
            raise AssertionError(label+": failed to reject unreliable input")
        rows.append({"scenario":label,"signals":[],"passed":True})
    return {"mode":"SYNTHETIC_STOCK_SIGNAL_SAFETY_MATRIX",
      "cases":rows,"tests_passed":len(rows),
      "signal_families":list(FAMILIES),
      "real_market_data_tested":False,
      "historical_return_computed":False,
      "real_trade_orders":0,
      "real_money_enabled":False,
      "requires_historical_sip_and_point_in_time_marketcap":True,
      "warning":"These are synthetic software correctness tests, not profitable backtests."}

if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False))
