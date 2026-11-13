"""Expanding three-fold walk-forward US swing research (no orders).

This is an extension of the existing A/B/C USD lab. All strategy selection
for each fold uses *only* observations before that fold's holdout window.
Each period independently resets to the same illustrative $5,000; do not
sum or compound across folds. Training indicators may warm up from earlier
bars, but equity and positions do not carry across fold boundaries.

Synthetic outcomes prove software invariants ONLY, never trading edge.
Non-display data use must be independently authorized before a real feed
can enter the simulator. No broker access or market data download here.
"""
from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Mapping

from .massive_free import FreeMarketHistory
from .us_synthetic_lab import (
    SPECS, START_USD, WARMUP, _prepare, _simulation, _equal_weight_reference
)

FOLDS = 3
MIN_TRAIN_SESSIONS = 80
MIN_HOLDOUT_SESSIONS = 40
MIN_COMPLETED_TRAIN_TRADES = 15
SIP_SOURCE = "ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"


def _training_score(summary: dict) -> float:
    # Same fixed objective as original A/B/C study, no holdout peeking.
    return summary["return_pct"] - 1.5 * summary["max_drawdown_pct"]


def walkforward_abc_offline(
    histories: Mapping[str, FreeMarketHistory], *, as_of: date,
    licensed_non_display_use: bool = False
) -> dict:
    """Expanding-train/next-block holdout across THREE chronological folds.

    No training on later holdouts, no lookahead, no automatic optimization or
    publication. The trading lab's default fill-cost assumptions apply.
    """
    dates, aligned = _prepare(
        histories, as_of=as_of,
        licensed_non_display_use=licensed_non_display_use,
    )
    tradeable = len(dates) - WARMUP
    if tradeable < MIN_TRAIN_SESSIONS + FOLDS * MIN_HOLDOUT_SESSIONS:
        raise ValueError("Need >=200 tradable sessions for 3-fold walk-forward")
    test_span = max(MIN_HOLDOUT_SESSIONS, tradeable // 5)
    first_train_end = len(dates) - FOLDS * test_span
    if first_train_end - WARMUP < MIN_TRAIN_SESSIONS:
        raise ValueError("Insufficient first-fold training sessions")
    sources = {h.source for h in histories.values()}
    if len(sources) != 1:
        raise ValueError("Mixed historical providers are not comparable")
    synthetic_only = sources == {"SYNTHETIC_TEST_FIXTURE"}
    # SIP consolidated volume is a prerequisite for treating the existing
    # turnover filter as a complete US-market observation. Never silently
    # treat IEX-only volume or synthetic fixtures as fully qualified.
    source_qualified = licensed_non_display_use and sources == {SIP_SOURCE}
    folds = []
    for fold_index in range(FOLDS):
        train_end = first_train_end + fold_index * test_span
        test_end = train_end + test_span
        trainings = [
            _simulation(aligned, dates, cfg, WARMUP, train_end)
            for cfg in SPECS
        ]
        # Selection must NOT inspect the holdout outcomes. Ties stable.
        leader_idx = max(
            range(len(SPECS)),
            key=lambda i: (
                _training_score(trainings[i]),
                -trainings[i]["max_drawdown_pct"],
                -i
            )
        )
        holdouts = [
            _simulation(aligned, dates, cfg, train_end, test_end)
            for cfg in SPECS
        ]
        reference = _equal_weight_reference(aligned, dates, train_end, test_end)
        leader = holdouts[leader_idx]
        training_trades = trainings[leader_idx]["completed_round_trips"]
        fold_is_qualified = (
            source_qualified and
            training_trades >= MIN_COMPLETED_TRAIN_TRADES
            and train_end - WARMUP >= MIN_TRAIN_SESSIONS
        )
        folds.append({
            "fold": fold_index + 1,
            "training_start": dates[WARMUP].isoformat(),
            "training_end": dates[train_end - 1].isoformat(),
            "holdout_start": dates[train_end].isoformat(),
            "holdout_end": dates[test_end - 1].isoformat(),
            "training_sessions": train_end - WARMUP,
            "holdout_sessions": test_span,
            "selected_from_training": "ABC"[leader_idx],
            "selection_objective": "train_return_pct_minus_1.5x_max_drawdown_pct",
            "selected_training_closed_trades": training_trades,
            "qualified_historical_fold": fold_is_qualified,
            "variants": {
                "ABC"[i]: {
                    "training": trainings[i],
                    "holdout": holdouts[i],
                } for i in range(len(SPECS))
            },
            "selected_holdout_return_pct": leader["return_pct"],
            "selected_holdout_drawdown_pct": leader["max_drawdown_pct"],
            "selected_holdout_closed_trades": leader["completed_round_trips"],
            "reference_holdout_return_pct": reference["return_pct"],
            "reference_is_investable": False,
            "selected_excess_vs_reference_pct": round(
                leader["return_pct"] - reference["return_pct"], 2
            ),
            "cash_reset_between_folds": True,
        })
    # Averages summarize independent restarts. They are NOT a continuous
    # portfolio result and must not be advertised as annualized return.
    return {
        "mode": "OFFLINE_3_FOLD_EXPANDING_USD_WALKFORWARD",
        "source": next(iter(sources)),
        "synthetic_only": synthetic_only,
        "licensed_real_data_allowed": bool(
            licensed_non_display_use and not synthetic_only
        ),
        "consolidated_sip_required_for_qualified_result": True,
        "qualified_historical_comparison": all(
            fold["qualified_historical_fold"] for fold in folds
        ),
        "starting_usd_each_independent_fold": START_USD,
        "folds": folds,
        "independent_holdout_mean_return_pct_not_annualized": round(
            mean(f["selected_holdout_return_pct"] for f in folds), 2
        ),
        "independent_holdout_positive_fold_count": sum(
            f["selected_holdout_return_pct"] > 0 for f in folds
        ),
        "independent_holdout_mean_excess_vs_noninvestable_reference_pct": round(
            mean(f["selected_excess_vs_reference_pct"] for f in folds), 2
        ),
        "holdout_total_calendar_windows": FOLDS,
        "backtested_with_actual_prices": not synthetic_only,
        "strategy_profitability_proven": False,
        "lookahead_based_selection": False,
        "automatic_order_execution": False,
        "paper_order_execution": False,
        "eur_portfolio_modified": False,
        "limitations": (
            "Synthetic folds cannot establish a strategy edge. "
            "Real data may have survivorship bias (fixed 50-stock watchlist), "
            "missing delisted stocks, dividends, taxes, FX, real spreads, "
            "market impact and borrow costs. Shorting is NOT simulated. "
            "Fold restarts are independent; mean returns cannot be "
            "compounded. Compare with a real investable benchmark later."
        ),
    }
