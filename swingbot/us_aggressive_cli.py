"""One-shot experimental A/B/C versus aggressive D/E stock rotation.

Requires personal Alpaca SIP backtesting approval. No account/trade endpoints.
Existing 50-stock survivor set reuses previously examined historical periods:
this is an EXPLORATORY hypothesis test, not fresh independent confirmation.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date,datetime,timezone
from typing import Callable

from .alpaca_iex import AlpacaUnavailable,fetch_iex_bars
from .us_aggressive_annual import compare_aggressive_annual
from .us_watchlist import US_WATCHLIST_50


def run_aggressive_sip(*,permission_confirmed:bool=False,
                       as_of:date|None=None,
                       lookback_days:int=2555,
                       loader:Callable=fetch_iex_bars)->dict:
    if not permission_confirmed:
        return {
            "status":"NOT_RUN_WITHOUT_SIP_PERSONAL_RESEARCH_PERMISSION",
            "requests":0,"orders_enabled":False,
        }
    if type(lookback_days) is not int or not 1800<=lookback_days<=3000:
        raise ValueError("Invalid 1800..3000-day multi-year lookback")
    as_of=as_of or datetime.now(timezone.utc).date()
    if not isinstance(as_of,date):
        raise ValueError("Invalid as_of research date")
    histories={}
    failures=0
    kinds={}
    for symbol in US_WATCHLIST_50:
        try:
            feed=loader(symbol,as_of=as_of,feed="sip",
                        lookback_days=lookback_days)
            if (feed.ticker!=symbol or
                feed.source!="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"):
                raise AlpacaUnavailable("Invalid SIP source identity")
            histories[symbol]=feed
        except AlpacaUnavailable as exc:
            failures+=1
            msg=str(exc)
            if msg.startswith("Alpaca IEX request HTTP "):
                code=msg.rsplit(" ",1)[-1]
                kind="HTTP_"+code if code in (
                    "400","401","403","422","429","500","503") else "HTTP_OTHER"
            else:
                kind="INVALID_OR_INSUFFICIENT_PRICE_HISTORY"
            kinds[kind]=kinds.get(kind,0)+1
            if kind in ("HTTP_401","HTTP_403","HTTP_429"):
                break
    if failures or len(histories)!=len(US_WATCHLIST_50):
        return {
            "status":"INCOMPLETE_STOCK_HISTORY_NO_BACKTEST",
            "validated":len(histories),"failed":failures,
            "failure_types":dict(sorted(kinds.items())),
            "required":len(US_WATCHLIST_50),
            "backtest_performed":False,
            "orders_enabled":False,
        }
    result=compare_aggressive_annual(
        histories,as_of=as_of,licensed_non_display_use=True)
    summary=[]
    for fold in result["folds"]:
        base=next(x for x in fold["results"] if x["case"]=="BASE")
        severe=next(x for x in fold["results"] if x["case"]=="SEVERE")
        summary.append({
            "test_start":fold["test_start"],
            "test_end":fold["test_end"],
            "training_selected":fold["selected_using_training_only"],
            "new_momentum_variant_selected":fold[
                "winner_is_new_experimental_variant"],
            "baseline_abc_train_winner":fold["baseline_abc_training_winner"],
            "baseline_abc_test_return_pct":fold[
                "baseline_abc_holdout_return_pct"],
            "new_test_return_base_pct":base["return_pct"],
            "new_test_cagr_base_pct":base["cagr_pct"],
            "new_test_return_severe_pct":severe["return_pct"],
            "new_test_cagr_severe_pct":severe["cagr_pct"],
            "new_test_drawdown_pct":base["max_drawdown_pct"],
            "new_test_worst_day_pct":base["worst_day_pct"],
            "new_test_order_events":base["total_order_events"],
            "historical_year_reached_100pct":base["hit_100pct_this_year"],
        })
    return {
        "status":"EXPLORATORY_REAL_SIP_MOMENTUM_NOT_UNSEEN",
        "validated":len(histories),
        "as_of":as_of.isoformat(),
        "run_utc":datetime.now(timezone.utc).isoformat(),
        "target_cagr_pct":100.,
        "pre_registered_new_variants":result["prespecified_new_variants"],
        "folds":summary,
        "cost_scenarios":result["scenarios"],
        "after_review_of_abc_historical_results":True,
        "fresh_untouched_prospective_validation_missing":True,
        "stock_list_survivorship_bias":True,
        "returns_not_continuous_account_or_real_execution":True,
        "trades_placed":0,
        "orders_enabled":False,
        "no_quote_or_ticker_data_published":True,
    }


def main():
    parser=argparse.ArgumentParser(
        description="Experimental full-exposure USD SIP momentum research")
    parser.add_argument("--lookback-days",type=int,default=2555)
    args=parser.parse_args()
    allowed=os.getenv("ALPACA_PERSONAL_RESEARCH_OK","").strip().lower()=="true"
    try:
        r=run_aggressive_sip(permission_confirmed=allowed,
                             lookback_days=args.lookback_days)
        print(json.dumps(r,allow_nan=False,ensure_ascii=False))
        if r["status"]!="EXPLORATORY_REAL_SIP_MOMENTUM_NOT_UNSEEN":
            raise SystemExit(2)
    except (ValueError,PermissionError,AlpacaUnavailable):
        parser.exit(2,"Aggressive US SIP research unavailable or incomplete\n")


if __name__=="__main__":
    main()
