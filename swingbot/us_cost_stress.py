"""Deterministic US equity cost sensitivity research; never routes orders.

Compare frozen A/B/C strategies at three explicit assumptions for fees and
slippage. The strategy selected on BASE *training* is held fixed across every
holdout scenario, preventing convenient reselection after viewing results.

A pass is only a preliminary research screen, not a trading authorisation.
Curated fixed 50-stock membership and synthetic fixtures have selection bias;
real tick history, rights, execution quality and forward paper validation
are independent requirements.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Mapping

from .massive_free import FreeMarketHistory
from .us_synthetic_lab import compare_abc_offline, START_USD
from .return_target import TARGET_ANNUAL_RETURN_PCT, goal_report

COST_CASES = (
    ("BASE", 10.0, 10.0),
    ("WORSE", 25.0, 25.0),
    ("SEVERE", 50.0, 75.0),
)
MIN_TRAINING_CLOSED_TRADES = 15
MIN_HOLDOUT_CLOSED_TRADES = 10


def run_us_cost_stress(
    histories: Mapping[str, FreeMarketHistory], *,
    as_of: date,
    licensed_non_display_use: bool = False,
) -> dict:
    """Run locked-selection fee/slippage sensitivity without any broker API.

    Returns explicit diagnostics, not a market-data performance claim.
    Never changes portfolio state, touches EUR holdings or submits orders.
    """
    if not histories:
        raise ValueError("Missing price histories")
    synthetic = all(
        isinstance(hist, FreeMarketHistory)
        and hist.source == "SYNTHETIC_TEST_FIXTURE"
        for hist in histories.values()
    )
    results = []
    locked_strategy = None
    for name, fee_bps, slippage_bps in COST_CASES:
        comparison = compare_abc_offline(
            histories, as_of=as_of,
            licensed_non_display_use=licensed_non_display_use,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        if locked_strategy is None:
            locked_strategy = comparison["training_selected_strategy"]
        # The fixed BASE train winner is evaluated in every subsequent
        # stress holdout. Never pick the most flattering holdout result.
        selected = next(
            row for row in comparison["variants"]
            if row["strategy"] == locked_strategy
        )
        train, holdout = selected["training"], selected["holdout"]
        reference = comparison["benchmark_holdout"]
        annual_goal = goal_report(
            initial_equity=START_USD,
            final_equity=holdout["ending_mark_to_market_usd"],
            start=date.fromisoformat(holdout["start"]),
            end=date.fromisoformat(holdout["end"]),
            synthetic_or_unverified=synthetic or not licensed_non_display_use,
        )
        # Optimize for the stated annual return goal instead of using
        # a pre-chosen drawdown percentage as an eligibility cutoff.
        passed = (
            train["completed_round_trips"] >= MIN_TRAINING_CLOSED_TRADES
            and holdout["completed_round_trips"] >= MIN_HOLDOUT_CLOSED_TRADES
            and annual_goal["target_met_on_this_sample"]
            and holdout["return_pct"] > reference["return_pct"]
        )
        results.append({
            "case": name,
            "fee_bps_per_side": fee_bps,
            "slippage_bps_per_side": slippage_bps,
            "frozen_strategy": locked_strategy,
            "training_completed_trades": train["completed_round_trips"],
            "holdout_completed_trades": holdout["completed_round_trips"],
            "holdout_return_pct": holdout["return_pct"],
            "holdout_max_drawdown_pct": holdout["max_drawdown_pct"],
            "holdout_reference_return_pct": reference["return_pct"],
            "holdout_reference_is_investable": False,
            "holdout_halted_new_entries": holdout["halted_new_entries"],
            "holdout_annual_goal": annual_goal,
            "hypothetical_case_passed": passed,
        })
    preliminary_screen_passed = all(
        row["hypothetical_case_passed"] for row in results
    )
    return {
        "mode": "US_EQUITY_RESEARCH_COST_STRESS_NO_ORDERS",
        "selected_using": "BASE_TRAINING_ONLY",
        "frozen_strategy": locked_strategy,
        "source_is_entirely_synthetic": synthetic,
        "licensed_non_display_use_asserted": licensed_non_display_use,
        "cost_cases": results,
        "minimum_training_completed_trades": MIN_TRAINING_CLOSED_TRADES,
        "minimum_holdout_completed_trades": MIN_HOLDOUT_CLOSED_TRADES,
        "research_annual_return_target_pct": TARGET_ANNUAL_RETURN_PCT,
        "selection_objective": "HIGHEST_TRAINING_RETURN_NO_DRAWDOWN_PENALTY",
        "hypothetical_screen_passed": preliminary_screen_passed,
        "real_data_research_evidence": (
            preliminary_screen_passed and licensed_non_display_use
            and not synthetic
        ),
        "real_data_history_required": True,
        "broker_and_execution_validation_required": True,
        "forward_paper_observation_required": True,
        "strategy_outperformance_proven": False,
        "paper_order_authorized": False,
        "real_order_authorized": False,
        "eur_paper_modified": False,
        "warning": (
            "Synthetic fixtures cannot validate returns. Fixed historical "
            "watchlists have survivorship bias. No FX, real spreads, taxes, "
            "dividends, delistings or fully investable reference is verified. "
            "This screen never authorizes any real or paper broker order."
        ),
    }


def main() -> None:
    """Run a self-contained offline smoke check; print no synthetic P/L."""
    from .us_quality_cli import _synthetic_fixture
    from .us_watchlist import US_WATCHLIST_50

    histories = {
        ticker: _synthetic_fixture(ticker, "V_SHOCK", offset=i * 7)
        for i, ticker in enumerate(US_WATCHLIST_50[:10])
    }
    as_of = next(iter(histories.values())).bars[-1].day + timedelta(days=1)
    report = run_us_cost_stress(histories, as_of=as_of)
    assert len(report["cost_cases"]) == len(COST_CASES)
    assert report["source_is_entirely_synthetic"]
    assert not report["real_data_research_evidence"]
    assert not report["paper_order_authorized"]
    assert not report["real_order_authorized"]
    print(json.dumps({
        "mode": report["mode"],
        "case_checks": [row["case"] for row in report["cost_cases"]],
        "locked_strategy_consistent": len(set(
            row["frozen_strategy"] for row in report["cost_cases"]
        )) == 1,
        "real_data_research_evidence": False,
        "order_authorized": False,
    }))


if __name__ == "__main__":
    main()
