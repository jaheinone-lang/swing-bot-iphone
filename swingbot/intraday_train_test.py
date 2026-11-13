"""Small preregistered training-only 5m signal grid, then frozen holdout.

READ-ONLY. Limited 1000-candle Bitvavo history (~3.5 days) is INSUFFICIENT
to validate profitability. The script exposes that fact instead of declaring
a profitable optimizer. No broker connection and no changes to paper ledger.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from statistics import mean
from .bitvavo_intraday import intraday_candles
from .intraday_research import replay
from .intraday_net_target import ExecutionCosts

@dataclass(frozen=True)
class Hypothesis:
    breakout: int
    trend: int
    vol_factor: float
    atr_min_pct: float = .12
    atr_max_pct: float = 1.8

# Six fixed hypotheses; no grid explosion or after-the-fact test tuning.
SPECS=tuple(Hypothesis(b,t,v) for b in (12,20,30) for t,v in ((40,1.0),(60,1.3)))
DOUBLE_COST=ExecutionCosts(50,50,30,30)


def signal_for(spec: Hypothesis):
    def signal(bars, i):
        n=max(spec.breakout,spec.trend,15)+1
        if i<n:
            return False
        b=bars[i]; prev=bars[i-spec.breakout:i]
        trend20=mean(x["close"] for x in bars[i-20:i])
        trend=mean(x["close"] for x in bars[i-spec.trend:i])
        if not (b["close"]>max(x["high"] for x in prev)
                and b["close"]>trend20>trend
                and b["close"]>b["open"]):
            return False
        vols=[x.get("volume") for x in bars[i-20:i]]
        v=b.get("volume")
        if v is None or any(x is None for x in vols):
            return False
        baseline=mean(vols)
        if baseline<=0 or v < baseline*spec.vol_factor:
            return False
        trs=[]
        for j in range(i-13,i+1):
            candle=bars[j]; prior=bars[j-1]["close"]
            trs.append(max(candle["high"]-candle["low"],
                           abs(candle["high"]-prior),
                           abs(candle["low"]-prior)))
        atr=mean(trs)/b["close"]*100
        return spec.atr_min_pct<=atr<=spec.atr_max_pct
    return signal


def examine(bars):
    if len(bars)<900:
        raise ValueError("Need >=900 closed, consecutive five-minute bars")
    # Separate chronological trade windows, no warmup trades allowed.
    cut=int(len(bars)*.60)
    warmup=90
    results=[]
    for spec in SPECS:
        sig=signal_for(spec)
        train_bars=bars[:cut]
        train=replay(train_bars,signal=sig,first_entry_index=warmup)
        # Stress costs in train; reject expensive, unproven patterns.
        stress=replay(train_bars,signal=sig,first_entry_index=warmup,
                      costs=DOUBLE_COST)
        results.append({
            "spec":spec.__dict__,
            "train_eur":train["estimated_pnl_eur"],
            "train_buys":train["buys"],
            "train_stress_eur":stress["estimated_pnl_eur"],
            # Ranks costs, drawdown and minimum independent completed buys.
            "qualified":train["buys"]>=5 and
                        train["estimated_pnl_eur"]>0 and
                        stress["estimated_pnl_eur"]>0,
            "score":min(train["estimated_pnl_eur"],
                        stress["estimated_pnl_eur"])
                     - 20*train["max_mark_to_market_drawdown_pct"],
        })
    candidates=[r for r in results if r["qualified"]]
    winner=max(candidates,key=lambda r:r["score"]) if candidates else None
    verification=None
    if winner:
        # Extra historical warmup is ONLY for indicators, no trades until
        # first holdout bar; training selection never sees holdout results.
        test=bars[cut-warmup:]
        selection=Hypothesis(**winner["spec"])
        h=replay(test,signal=signal_for(selection),
                 first_entry_index=warmup)
        hs=replay(test,signal=signal_for(selection),
                  first_entry_index=warmup,costs=DOUBLE_COST)
        verification={
            "period_start_ms":bars[cut]["timestamp_ms"],
            "period_end_ms":bars[-1]["timestamp_ms"],
            "normal":h,"double_cost":hs,
        }
    return {
        "mode":"READ_ONLY_TRAIN_THEN_TEST",
        "train_bars":cut,"holdout_bars":len(bars)-cut,
        "starting_eur":5000,"hypotheses":results,
        "training_selected":winner,"later_window":verification,
        "pass_for_deployment":False,
        "caveat":"3.5 days / 1000 candles too short for statistical validation. "
                 "No live trades. Even positive holdout is NOT proof of edge. "
                 "Must repeat for months of independent market cycles.",
    }


def main():
    report={}
    for symbol in ("BTC-EUR","ETH-EUR","SOL-EUR"):
        report[symbol]=examine(intraday_candles(symbol,limit=1000))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
