"""Offline-only Swing Bot US research quality gate for GitHub Actions.

No secrets, network calls, market data, price predictions or order requests.
Prints software reliability checks, never synthetic performance percentages.
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, timedelta
from math import cos, sin

from .equity_screen import DailyBar
from .massive_free import FreeMarketHistory
from .us_watchlist import US_WATCHLIST_50, rank_us_research
from .us_synthetic_lab import compare_abc_offline, SPECS, DRAWDOWN_CIRCUIT

SCENARIOS=("TREND", "RANGE", "V_SHOCK", "DECLINE")


def _synthetic_fixture(ticker: str, mode: str, *, offset: int) -> FreeMarketHistory:
    first=date(2025,1,1)
    bars=[]
    for i in range(340):
        seasonal=1.0+.007*sin((i+offset)/11)+.005*cos((i+offset)/7)
        if mode=="TREND":
            base=90.0*(1.0+.0015*i)
        elif mode=="RANGE":
            base=100+3*sin((i+offset)/18)
        elif mode=="V_SHOCK":
            base=(110+.12*i) if i<290 else (90 if i<314 else 100)
        elif mode=="DECLINE":
            base=150*(1.0-.0016*i)
        else:
            raise ValueError("Unknown artificial scenario")
        close=max(1.0,base*seasonal)
        openp=close*(1+0.002*cos((i+offset)/3))
        upper=max(openp,close)*1.015
        lower=min(openp,close)*0.985
        bars.append(DailyBar(
            first+timedelta(days=i),openp,upper,lower,close,2_000_000
        ))
    return FreeMarketHistory(
        ticker=ticker, currency="USD",
        source="SYNTHETIC_TEST_FIXTURE",
        adjustment="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED",
        bars=tuple(bars),
    )


def run_offline_quality_gate() -> dict:
    """All reported results are test outcomes, NOT any price or return."""
    all_checks=[]
    for mode in SCENARIOS:
        fixtures={
            ticker:_synthetic_fixture(ticker,mode,offset=i*7)
            for i,ticker in enumerate(US_WATCHLIST_50)
        }
        first=next(iter(fixtures.values()))
        day=first.bars[-1].day+timedelta(days=1)
        ranking=rank_us_research(fixtures,as_of=day)
        lab=compare_abc_offline(fixtures,as_of=day)
        assert ranking["received"]==50
        assert len(ranking["ranking"])<=20
        assert ranking["paper_trade_authorized"] is False
        assert lab["data_use_rights"]=="SYNTHETIC_TEST_FIXTURES_ONLY"
        assert lab["real_order_authorized"] is False
        assert lab["qualified_strategy"] is None  # <80 train sessions
        assert len(lab["variants"])==len(SPECS)==3
        assert lab["benchmark_holdout"]["fractional_shares_assumed"] is True
        for variant in lab["variants"]:
            for interval in ("training","holdout"):
                stats=variant[interval]
                assert stats["order_event_count"]==(
                    stats["buy_events"]+stats["sell_events"]
                )
                assert stats["completed_round_trips"]==stats["sell_events"]
                assert 0<=stats["max_drawdown_pct"]<=100
                assert stats["max_planned_stop_risk_pct_of_equity"]<=1.001
                assert stats["real_order_authorized"] is False
                assert stats["paper_order_authorized"] is False
        all_checks.append({"scenario":mode,"passed":True})

    # License fail-closed is part of the production-readiness gate.
    invalid=_synthetic_fixture("AAPL","TREND",offset=0)
    try:
        compare_abc_offline({
            "AAPL":replace(invalid,source="ALPACA_BASIC_IEX_ONLY_NOT_CONSOLIDATED")
        },as_of=invalid.bars[-1].day+timedelta(days=1))
    except PermissionError:
        license_guard_passed=True
    else:
        raise AssertionError("Unlicensed feed unexpectedly accepted")

    return {
        "mode":"OFFLINE_SYNTHETIC_SOFTWARE_QUALITY_ONLY",
        "scenario_checks":all_checks,
        "strategies_compiled":len(SPECS),
        "watchlist_symbols_compiled":len(US_WATCHLIST_50),
        "license_fail_closed":license_guard_passed,
        "risk_fraction_per_trade_1pct_checked":True,
        "halt_new_entries_dd_25pct_checked_by_unit_tests":True,
        "real_market_data_tested":False,
        "strategy_outperformance_proven":False,
        "orders_or_trades_enabled":False,
        "source_quotes_published":False,
    }


def main():
    print(json.dumps(run_offline_quality_gate(),ensure_ascii=False))


if __name__=="__main__":
    main()
