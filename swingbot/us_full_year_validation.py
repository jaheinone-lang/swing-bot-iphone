"""Full-calendar-year, non-overlapping out-of-sample US swing research.

Unlike a short 65/35 split, this uses >=365 calendar-day holdouts. Strategies
are selected using only the preceding 252 *completed sessions*, with no
holdout reselection. Later folds can use previous folds as training data,
as would an actual chronological walk-forward process.

IMPORTANT: This is NOT an equity curve of a continuous live account.
Each research fold independently begins with 5,000 hypothetical USD, so
geometric chaining of fold returns is an illustration, NOT a broker statement.
The present hand-picked 50 surviving stocks cause substantial look-ahead
universe/survivorship bias; only separately licensed real SIP data is allowed.
No taxes, FX, dividends, spread measurements, delisted names or live orders.
"""
from __future__ import annotations

from datetime import date, timedelta
from math import prod
from typing import Mapping

from .massive_free import FreeMarketHistory
from .return_target import TARGET_ANNUAL_RETURN_PCT, goal_report
from .us_cost_stress import COST_CASES
from .us_synthetic_lab import (
    START_USD, SPECS, WARMUP, _prepare, _simulation,
    _equal_weight_reference,
)

TRAINING_SESSIONS = 252
MIN_HOLDOUT_DAYS = 365
MIN_TRAINING_CLOSED_TRADES = 15
SYNTHETIC = "SYNTHETIC_TEST_FIXTURE"
SIP = "ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"


def full_year_walkforward(
    histories: Mapping[str, FreeMarketHistory], *,
    as_of: date,
    licensed_non_display_use: bool = False,
) -> dict:
    """Test historical 100%-CAGR research objective on full-year holdouts.

    Fully offline and deterministic. A provider label or historical GET is
    not itself proof of rights; caller must explicitly confirm their personal
    non-display backtesting permission.
    """
    if not histories or not all(
        isinstance(h, FreeMarketHistory) for h in histories.values()
    ):
        raise ValueError("Validated USD histories required")
    labels={h.source for h in histories.values()}
    if labels not in ({SYNTHETIC},{SIP}):
        raise PermissionError("Mixed, unknown or unlicensed source is not permitted")
    actual=labels=={SIP}
    if actual and not licensed_non_display_use:
        raise PermissionError("Historical SIP strategy rights not confirmed")
    if not actual and licensed_non_display_use:
        # Synthetic fixtures should never be mistaken for validated data.
        raise ValueError("Cannot mark synthetic test candles as actual-price evidence")
    days,aligned=_prepare(histories,as_of=as_of,
                          licensed_non_display_use=licensed_non_display_use)
    first_holdout=WARMUP+TRAINING_SESSIONS
    if first_holdout>=len(days):
        raise ValueError("Not enough history for a complete one-year holdout")

    folds=[]
    start=first_holdout
    while start < len(days):
        minimum_end_day=days[start]+timedelta(days=MIN_HOLDOUT_DAYS)
        eligible_end=next((i for i in range(start+1,len(days))
                           if days[i]>=minimum_end_day),None)
        if eligible_end is None:
            break # never annualize a partial calendar year as evidence
        end=eligible_end+1
        train_start=start-TRAINING_SESSIONS
        train=[]
        for cfg in SPECS:
            stat=_simulation(aligned,days,cfg,train_start,start,
                             fee_bps=COST_CASES[0][1],
                             slippage_bps=COST_CASES[0][2])
            train.append((cfg,stat))
        # Fixed model selection: maximize net training return, not drawdown
        # score or any information from the subsequent holdout.
        leader,learned=max(train,key=lambda it:(
            it[1]["return_pct"],it[1]["completed_round_trips"],it[0].name
        ))
        results=[]
        for name,fee_bps,slip_bps in COST_CASES:
            stat=_simulation(aligned,days,leader,start,end,
                             fee_bps=fee_bps,slippage_bps=slip_bps)
            benchmark=_equal_weight_reference(
                aligned,days,start,end,
                fee_bps=fee_bps,slippage_bps=slip_bps)
            annual=goal_report(
                initial_equity=START_USD,
                final_equity=stat["ending_mark_to_market_usd"],
                start=days[start],end=days[end-1],
                synthetic_or_unverified=not actual,
            )
            results.append({
                "case":name,
                "fee_bps_each_side":fee_bps,
                "slippage_bps_each_side":slip_bps,
                "holdout_return_pct":stat["return_pct"],
                "holdout_cagr_pct":annual["historical_annualized_return_pct"],
                "target_met_in_this_historical_fold":annual["target_met_on_this_sample"],
                "holdout_max_drawdown_pct":stat["max_drawdown_pct"],
                "closed_trades":stat["completed_round_trips"],
                "holdout_profit_factor":stat["closed_trade_profit_factor"],
                "holdout_worst_day_pct":stat["worst_day_pct"],
                "halted_new_entries":stat["halted_new_entries"],
                "reference_return_pct":benchmark["return_pct"],
                "reference_is_investable":False,
                "estimated_fees_usd":stat["estimated_fees_usd"],
                "annual_evidence_status":annual["evidence_status"],
            })
        folds.append({
            "fold":len(folds)+1,
            "training_start":days[train_start].isoformat(),
            "training_end":days[start-1].isoformat(),
            "training_sessions":start-train_start,
            "training_chosen_strategy":leader.name,
            "training_chosen_return_pct":learned["return_pct"],
            "training_closed_trades":learned["completed_round_trips"],
            "holdout_start":days[start].isoformat(),
            "holdout_end":days[end-1].isoformat(),
            "holdout_calendar_days":(days[end-1]-days[start]).days,
            "holdout_sessions":end-start,
            "results":results,
        })
        start=end # independently selected, non-overlapping holdout folds

    if not folds:
        raise ValueError(
            "Insufficient completed market history: require 252-session "
            "development after 210-session warmup AND >=365-day holdout"
        )
    scenarios=[]
    first_date=date.fromisoformat(folds[0]["holdout_start"])
    last_date=date.fromisoformat(folds[-1]["holdout_end"])
    for name,fee_bps,slip_bps in COST_CASES:
        one=[next(row for row in fold["results"] if row["case"]==name)
             for fold in folds]
        # Each fold starts from fixed research capital: geometric chaining
        # is an ILLUSTRATION, not a self-financing account simulation.
        multipliers=[1+r["holdout_return_pct"]/100 for r in one]
        chained=prod(multipliers)
        combined=goal_report(
            initial_equity=START_USD,final_equity=START_USD*chained,
            start=first_date,end=last_date,
            synthetic_or_unverified=not actual,
        )
        scenarios.append({
            "case":name,
            "fee_bps_each_side":fee_bps,
            "slippage_bps_each_side":slip_bps,
            "full_year_folds":len(one),
            "historical_fold_target_hits":sum(
                r["target_met_in_this_historical_fold"] for r in one
            ),
            "illustrative_chained_oos_cagr_pct":
                combined["historical_annualized_return_pct"],
            "illustrative_chained_oos_total_return_pct":
                round(100*(chained-1),2),
            "all_folds_meet_100pct_cagr_target":all(
                r["target_met_in_this_historical_fold"] for r in one
            ),
            "continuous_account_compounding_verified":False,
            "sustainable_100pct_return_proven":False,
        })
    return {
        "mode":"FULL_YEAR_US_SIP_WALKFORWARD_RESEARCH_ONLY",
        "source":("ALPACA_DELAYED_SIP_HISTORY" if actual
                  else "SYNTHETIC_TEST_FIXTURES"),
        "research_annual_cagr_target_pct":TARGET_ANNUAL_RETURN_PCT,
        "as_of":as_of.isoformat(),
        "symbol_count":len(histories),
        "aligned_historical_sessions":len(days),
        "calendar_year_holdout_min_days":MIN_HOLDOUT_DAYS,
        "rolling_training_sessions":TRAINING_SESSIONS,
        "holdout_folds_nonoverlapping":True,
        "folds":folds,
        "cost_scenarios":scenarios,
        "no_licensed_per_symbol_prices_published":True,
        "historical_universe_survivorship_bias":True,
        "live_spreads_and_fx_and_taxes_unverified":True,
        "overall_100pct_repeatability_proven":False,
        "broker_orders_enabled":False,
        "paper_orders_enabled":False,
        "portfolio_modified":False,
        "disclaimer":(
            "This uses a curated survivor stock list, not historical tradable "
            "members. Historical full-year folds and cost assumptions cannot "
            "prove future doubling. Uninvestable equal-weight reference, no "
            "delistings, dividends, actual spreads, FX, taxes or live fills."
        ),
    }
