"""One-shot opt-in real historical SIP research, never orders.

This orchestrator runs only when GitHub Actions manual authorization confirms
paper-only API keys and applicable personal algorithmic/data license rights.
It never writes OHLCV, provider symbols, keys, executions or positions to
public artifacts. Only a compact, source-attributed aggregate report is
printed. Non-empty missing feeds block comparison rather than silently
selecting the best surviving stocks.
"""
from __future__ import annotations

import json
import os
from datetime import date,datetime,timezone
from typing import Callable

from .alpaca_iex import AlpacaUnavailable, fetch_iex_bars
from .us_full_year_validation import full_year_walkforward
from .us_watchlist import US_WATCHLIST_50


def run_private_full_year_sip(*,
    research_permission_confirmed: bool=False,
    as_of: date | None=None,
    lookback_days: int=2555,
    loader: Callable=fetch_iex_bars,
) -> dict:
    """Manual SIP GETs only; each symbol must pass source/date validation."""
    if not research_permission_confirmed:
        return {
            "status":"NOT_RUN_NEEDS_PERSONAL_SIP_BACKTEST_APPROVAL",
            "requested":0,"validated":0,"orders_enabled":False,
            "no_price_data_published":True,
        }
    if type(lookback_days) is not int or not 1800<=lookback_days<=3000:
        raise ValueError("Full-year validation requires 1800..3000 days of history")
    if as_of is not None and not isinstance(as_of,date):
        raise ValueError("Invalid research evaluation date")
    as_of=as_of or datetime.now(timezone.utc).date()
    # No account lookup or trade endpoint: all credentials belong to the
    # paper-data adapter and remain only in GitHub Secrets.
    verified={}
    failed=0
    failures={}
    for symbol in US_WATCHLIST_50:
        try:
            value=loader(symbol,as_of=as_of,feed="sip",
                         lookback_days=lookback_days)
            if (value.ticker!=symbol or
                value.source!="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"):
                raise AlpacaUnavailable("Unexpected historical feed")
            verified[symbol]=value
        except AlpacaUnavailable as exc:
            failed+=1
            message=str(exc)
            if message.startswith("Alpaca IEX request HTTP "):
                code=message.rsplit(" ",1)[-1]
                tag="HTTP_"+code if code in (
                    "400","401","403","422","429","500","503") else "HTTP_OTHER"
            elif "stale" in message.lower():
                tag="STALE_HISTORY"
            elif "260" in message:
                tag="INSUFFICIENT_SESSIONS"
            else:
                tag="PRICE_VALIDATION_ERROR"
            failures[tag]=failures.get(tag,0)+1
            if tag in ("HTTP_401","HTTP_403","HTTP_429"):
                break
    if failed or len(verified)!=len(US_WATCHLIST_50):
        return {
            "status":"BLOCKED_INCOMPLETE_SIP_INPUT",
            "requested":len(verified)+failed,
            "validated":len(verified),
            "failed":failed,
            "error_categories":dict(sorted(failures.items())),
            "required_symbols":len(US_WATCHLIST_50),
            "annual_comparison_performed":False,
            "orders_enabled":False,
            "no_price_data_published":True,
        }
    report=full_year_walkforward(verified,as_of=as_of,
                                  licensed_non_display_use=True)
    compact=[]
    for fold in report["folds"]:
        base=next(r for r in fold["results"] if r["case"]=="BASE")
        severe=next(r for r in fold["results"] if r["case"]=="SEVERE")
        compact.append({
            "train_end":fold["training_end"],
            "test_start":fold["holdout_start"],
            "test_end":fold["holdout_end"],
            "full_year_days":fold["holdout_calendar_days"],
            "selected_by_training_only":fold["training_chosen_strategy"],
            "test_return_after_base_friction_pct":base["holdout_return_pct"],
            "test_cagr_base_pct":base["holdout_cagr_pct"],
            "test_return_after_severe_friction_pct":severe["holdout_return_pct"],
            "test_cagr_severe_pct":severe["holdout_cagr_pct"],
            "test_max_drawdown_pct":base["holdout_max_drawdown_pct"],
            "test_completed_trades":base["closed_trades"],
            "test_profit_factor":base["holdout_profit_factor"],
            "test_theoretical_reference_return_pct":base["reference_return_pct"],
            "test_excess_vs_reference_percentage_points":round(
                base["holdout_return_pct"]-base["reference_return_pct"],2
            ),
            "gap_to_100pct_cagr_percentage_points":(
                round(base["holdout_cagr_pct"]-100.0,2)
                if base["holdout_cagr_pct"] is not None else None
            ),
            "benchmark_not_investable":True,
            "target_met_in_this_fold":base["target_met_in_this_historical_fold"],
        })
    return {
        "status":"HISTORICAL_SIP_FULL_YEAR_RESEARCH_ONLY",
        "source":"ALPACA_DELAYED_SIP",
        "requested":len(US_WATCHLIST_50),
        "validated":len(verified),
        "lookback_days":lookback_days,
        "as_of":as_of.isoformat(),
        "target_annual_cagr_pct":100.0,
        "folds":compact,
        "friction_scenarios":report["cost_scenarios"],
        "universe_survivorship_bias":True,
        "no_fx_taxes_real_spreads_dividends_or_broker_fills":True,
        "continuous_account_returns_verified":False,
        "profit_goal_proven_repeatable":False,
        "no_price_data_published":True,
        "orders_enabled":False,
        "paper_orders_enabled":False,
    }


def main():
    from argparse import ArgumentParser
    parser=ArgumentParser(description="Manual SIP full-calendar-year research")
    parser.add_argument("--lookback-days",type=int,default=2555)
    args=parser.parse_args()
    allowed=os.getenv("ALPACA_PERSONAL_RESEARCH_OK","").strip().lower()=="true"
    try:
        report=run_private_full_year_sip(
            research_permission_confirmed=allowed,
            lookback_days=args.lookback_days,
        )
        print(json.dumps(report,allow_nan=False,ensure_ascii=False))
        if report["status"]!="HISTORICAL_SIP_FULL_YEAR_RESEARCH_ONLY":
            raise SystemExit(2)
    except (ValueError,PermissionError,AlpacaUnavailable) as exc:
        # No URL, token, raw historical prices or source payload in errors.
        parser.exit(2,"Full-year SIP research unavailable: "+
                    type(exc).__name__+"\n")


if __name__=="__main__":
    main()
