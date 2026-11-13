"""Exploratory returns-first USD annual research: A/B/C vs D/E.

The existing A/B/C annual periods were already inspected, so this new D/E
comparison is an exploratory historical comparison, NOT a newly independent
unseen-data validation even though selection within each fold is chronological.
Only real, permission-confirmed Alpaca SIP or purely synthetic offline bars.
No deposits, leverage, shorting, broker access, FX, taxation or trading.
"""
from __future__ import annotations

from datetime import date,timedelta
from math import prod
from typing import Mapping

from .massive_free import FreeMarketHistory
from .return_target import goal_report,TARGET_ANNUAL_RETURN_PCT
from .us_cost_stress import COST_CASES
from .us_full_year_validation import (
    TRAINING_SESSIONS,MIN_HOLDOUT_DAYS,SYNTHETIC,SIP,
)
from .us_momentum_rotation import ROTATION_SPECS,simulate_rotation
from .us_synthetic_lab import (
    START_USD,SPECS,WARMUP,_prepare,_simulation,
)


def compare_aggressive_annual(
    histories:Mapping[str,FreeMarketHistory], *,
    as_of:date,licensed_non_display_use:bool=False
)->dict:
    if not histories or not all(isinstance(h,FreeMarketHistory)
                                for h in histories.values()):
        raise ValueError("Price histories required")
    labels={h.source for h in histories.values()}
    if labels not in ({SYNTHETIC},{SIP}):
        raise PermissionError("Mixed/unverified input not permitted")
    real=labels=={SIP}
    if real!=licensed_non_display_use:
        raise PermissionError("Cannot misstate actual-data rights")
    dates,aligned=_prepare(
        histories,as_of=as_of,licensed_non_display_use=licensed_non_display_use
    )
    start=WARMUP+TRAINING_SESSIONS
    if start>=len(dates):
        raise ValueError("Full-year training or holdout not available")
    all_specs=[*SPECS,*ROTATION_SPECS]
    folds=[]
    while start<len(dates):
        one_year=dates[start]+timedelta(days=MIN_HOLDOUT_DAYS)
        last=next((i for i in range(start+1,len(dates))
                   if dates[i]>=one_year),None)
        if last is None:break
        end=last+1
        beginning=start-TRAINING_SESSIONS
        training=[]
        for spec in all_specs:
            stat=(simulate_rotation(
                aligned,dates,spec,beginning,start,
                fee_bps=COST_CASES[0][1],
                slippage_bps=COST_CASES[0][2],
            ) if spec in ROTATION_SPECS else _simulation(
                aligned,dates,spec,beginning,start,
                fee_bps=COST_CASES[0][1],
                slippage_bps=COST_CASES[0][2],
            ))
            training.append((spec,stat))
        # Choose ONLY on past, same 252-session interval for all 5 variants.
        lead=max(training,key=lambda row:(row[1]["return_pct"],
                                          row[0].name))[0]
        baseline=max(
            (it for it in training if it[0] in SPECS),
            key=lambda row:(row[1]["return_pct"],
                            row[1]["completed_round_trips"],row[0].name)
        )[0]
        reference=_simulation(
            aligned,dates,baseline,start,end,
            fee_bps=COST_CASES[0][1],
            slippage_bps=COST_CASES[0][2]
        )
        results=[]
        for scenario,fee,slip in COST_CASES:
            stat=(simulate_rotation(aligned,dates,lead,start,end,
                                    fee_bps=fee,slippage_bps=slip)
                  if lead in ROTATION_SPECS else
                  _simulation(aligned,dates,lead,start,end,
                              fee_bps=fee,slippage_bps=slip))
            goal=goal_report(
                initial_equity=START_USD,
                final_equity=stat["ending_mark_to_market_usd"],
                start=dates[start],end=dates[end-1],
                synthetic_or_unverified=not real
            )
            results.append({
                "case":scenario,
                "return_pct":stat["return_pct"],
                "cagr_pct":goal["historical_annualized_return_pct"],
                "hit_100pct_this_year":goal["target_met_on_this_sample"],
                "max_drawdown_pct":stat["max_drawdown_pct"],
                "worst_day_pct":stat["worst_day_pct"],
                "total_order_events":stat["order_event_count"],
                "estimated_fees_usd":stat["estimated_fees_usd"],
            })
        folds.append({
            "fold":len(folds)+1,
            "training_end":dates[start-1].isoformat(),
            "test_start":dates[start].isoformat(),
            "test_end":dates[end-1].isoformat(),
            "calendar_days":(dates[end-1]-dates[start]).days,
            "selected_using_training_only":lead.name,
            "winner_is_new_experimental_variant":lead in ROTATION_SPECS,
            "training_winner_return_pct":next(
                s["return_pct"] for cfg,s in training if cfg==lead),
            "baseline_abc_training_winner":baseline.name,
            "baseline_abc_holdout_return_pct":reference["return_pct"],
            "results":results,
        })
        start=end
    if not folds:
        raise ValueError("No complete year after training")
    chained=[]
    first=date.fromisoformat(folds[0]["test_start"])
    last=date.fromisoformat(folds[-1]["test_end"])
    for name,fee,slip in COST_CASES:
        stats=[next(r for r in f["results"] if r["case"]==name)
               for f in folds]
        product=prod(1+s["return_pct"]/100 for s in stats)
        goal=goal_report(initial_equity=START_USD,
                         final_equity=START_USD*product,
                         start=first,end=last,
                         synthetic_or_unverified=not real)
        chained.append({
            "case":name,
            "fee_bps_each_side":fee,
            "slippage_bps_each_side":slip,
            "historical_fold_target_hits":sum(s["hit_100pct_this_year"]
                                              for s in stats),
            "illustrative_chained_annual_pct":
                goal["historical_annualized_return_pct"],
            "illustrative_chained_total_pct":round(100*(product-1),2),
            "continuous_account_returns_verified":False,
        })
    return {
        "mode":"EXPLORATORY_ABC_VS_DE_MOMENTUM_FULL_YEAR_NO_ORDERS",
        "source":"ALPACA_DELAYED_SIP" if real else "SYNTHETIC_FIXTURE",
        "target_annual_cagr_pct":TARGET_ANNUAL_RETURN_PCT,
        "known_prior_exposure_to_baseline_holdout_periods":True,
        "untouched_independent_validation_not_yet_available":True,
        "prespecified_new_variants":[x.name for x in ROTATION_SPECS],
        "no_executed_broker_orders":True,
        "licensed_per_symbol_quotes_published":False,
        "symbol_count":len(histories),
        "folds":folds,
        "scenarios":chained,
        "survivorship_bias":True,
        "no_dividends_fx_taxes_actual_fills_or_spreads":True,
        "continuous_account_returns_verified":False,
        "paper_orders_enabled":False,
        "live_orders_enabled":False,
    }
