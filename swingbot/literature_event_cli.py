"""Consent-gated market history fetch for four literature-inspired patterns.

GET-only from already configured Alpaca PAPER historical market-data secrets.
A report contains aggregate event counts and forward interval percentages
ONLY; no raw licensed prices, provider symbols, user account information,
trade orders, individual ranking, or full event date lists.
"""
from __future__ import annotations

import json
import os
from datetime import date,datetime,timezone
from typing import Callable

from .alpaca_iex import AlpacaUnavailable,fetch_iex_bars
from .literature_event_study import study_pattern_events,SIP
from .us_watchlist import US_WATCHLIST_50


def run_private_literature_patterns(*, approved:bool=False,
    as_of:date|None=None, lookback_days:int=2555,
    loader:Callable=fetch_iex_bars) -> dict:
    """No access without explicit confirmed personal data rights."""
    if not approved:
        return {
            "status":"NOT_RUN_NEEDS_PAPER_ONLY_NONDISPLAY_DATA_USE_APPROVAL",
            "requested":0,"study_executed":False,"orders_enabled":False,
        }
    if type(lookback_days) is not int or not 1800<=lookback_days<=3000:
        raise ValueError("History window must be 1800..3000 calendar days")
    as_of=as_of or datetime.now(timezone.utc).date()
    if not isinstance(as_of,date):
        raise ValueError("Invalid evaluation date")
    collected={}
    error_categories={}
    attempted=0
    failed=0
    for ticker in (*US_WATCHLIST_50,"SPY"):
        attempted+=1
        try:
            if ticker=="SPY":
                hist=loader("SPY",as_of=as_of,feed="sip",
                            lookback_days=lookback_days,
                            allowed_symbols=frozenset({"SPY"}))
            else:
                hist=loader(ticker,as_of=as_of,feed="sip",
                            lookback_days=lookback_days)
            if hist.ticker!=ticker or hist.source!=SIP:
                raise AlpacaUnavailable("Price source mismatch")
            collected[ticker]=hist
        except AlpacaUnavailable as exc:
            failed+=1
            message=str(exc)
            if message.startswith("Alpaca IEX request HTTP "):
                code=message.rsplit(" ",1)[-1]
                reason="HTTP_"+code if code in (
                    "400","401","403","422","429","500","503"
                ) else "HTTP_OTHER"
            elif "stale" in message.lower():
                reason="STALE_HISTORY"
            else:
                reason="OHLCV_VALIDATION"
            error_categories[reason]=error_categories.get(reason,0)+1
            if reason in ("HTTP_401","HTTP_403","HTTP_429"):
                break
    if failed or len(collected)!=len(US_WATCHLIST_50)+1:
        return {
            "status":"BLOCKED_INCOMPLETE_SIP_STOCK_OR_SPY_DATA",
            "requested":attempted,
            "validated":len(collected),
            "failed":failed,
            "error_categories":dict(sorted(error_categories.items())),
            "study_executed":False,
            "price_data_published":False,
            "orders_enabled":False,
        }
    benchmark=collected.pop("SPY")
    report=study_pattern_events(
        collected,as_of=as_of,licensed_non_display_use=True,
        benchmark=benchmark
    )
    report.update({
        "status":"COMPLETED_LITERATURE_PATTERN_SIP_DISCOVERY",
        "lookback_days":lookback_days,
        "validated_stock_histories":len(collected),
        "spy_history_verified":True,
        "research_method":"NON_EXCLUSIVE_EVENT_WINDOWS_NOT_PORTFOLIO",
    })
    return report


def main():
    from argparse import ArgumentParser
    parser=ArgumentParser(description="Historical read-only literature study")
    parser.add_argument("--lookback-days",type=int,default=2555)
    args=parser.parse_args()
    consent=os.getenv("ALPACA_PERSONAL_RESEARCH_OK","").lower()=="true"
    try:
        report=run_private_literature_patterns(
            approved=consent,lookback_days=args.lookback_days
        )
        print(json.dumps(report,ensure_ascii=False,allow_nan=False))
        if report["status"]!="COMPLETED_LITERATURE_PATTERN_SIP_DISCOVERY":
            raise SystemExit(2)
    except (AlpacaUnavailable,ValueError,PermissionError) as exc:
        # Sanitized diagnostic only; URL and token never included.
        parser.exit(2,"SIP literature research unavailable: "+
                    type(exc).__name__+"\n")


if __name__=="__main__":
    main()
