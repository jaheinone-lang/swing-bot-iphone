"""Small-sample uncertainty and asset/year stratification for trade audit.

Consumes the already-realized read-only BUY/EXIT ledger, NOT future candles.
Wilson 95% interval does not account for serial dependence, regime
selection, fees uncertainty, dataset gaps, or strategy overfitting.
Never select a live trading asset from this retrospective descriptive view.
"""
from __future__ import annotations
from math import sqrt
from collections import defaultdict

def wilson(k,n,z=1.96):
    if n<=0:return None
    p=k/n
    denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    radius=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return [round(max(0,(center-radius)*100),1),
            round(min(100,(center+radius)*100),1)]

def _stats(rows):
    n=len(rows)
    k=sum(x["exit"]=="FULL_TP" for x in rows)
    pnl=sum(x["net_eur"] for x in rows)
    return {
        "buys":n,"completed_one_pct_net_targets":k,
        "target_rate_pct":round(k/n*100,2) if n else None,
        "target_rate_wilson95_pct":wilson(k,n),
        "net_pnl_eur":round(pnl,2),
        "avg_pnl_per_buy_eur":round(pnl/n,2) if n else None,
    }

def summarize(ledger):
    groups={"BTC-EUR":[],"ETH-EUR":[],
            "2021-2023":[],"2024-2026":[]}
    for trade in ledger:
        s=trade["symbol"]
        if s not in ("BTC-EUR","ETH-EUR"):
            raise ValueError("Unexpected asset, SOL must remain excluded")
        day=trade["day"]
        year=int(day[:4])
        if not 2021<=year<=2026:
            raise ValueError("Outside fixed historical study")
        groups[s].append(trade)
        groups["2021-2023" if year<=2023 else "2024-2026"].append(trade)
    summary={k:_stats(v) for k,v in groups.items()}
    summary["all"]=_stats(ledger)
    summary["warnings"]=[
        "Retrospective, already-optimized historical outcomes.",
        "Wilson intervals are binomial approximations, not a causal "
        "confidence interval for forward profitable trading.",
        "Target-hit frequency alone does not imply positive expectancy.",
        "No live trading, not an auto asset-selection rule."
    ]
    return summary
