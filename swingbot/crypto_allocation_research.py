"""Crypto 5k reinvestment study: base E60, E100 risk-capped and E100 all-in.

Strict historical simulation only. Completed EUR candles; next-bar open fills;
profits/losses compound on current net-of-reserved-tax capital. Never places
orders, changes saved forward paper state, or uses user credentials.
"""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import timedelta
from math import isfinite

from .bitvavo_data import bitvavo_eur_daily
from .crypto_alpha_research import CANDIDATES, SYMBOLS, MARKETS, aligned_crypto_data
from .crypto_validation import WARMUP_BARS
from .research_metrics import _metrics
from .strategy_lab import research_backtest

STARTING_EUR = 5000.0
DAYS_IN_MONTH = 30
E = CANDIDATES[2]

# The third model intentionally removes nominal 2%-per-trade sizing to
# investigate the exact "put all EUR 5,000 to work on each buy" request.
# It is NOT the model to automatically paper-trade or deploy.
SCENARIOS = (
    ("E60, 2% per trade, 3% aggregate nominal stop risk", E, .03),
    ("E100, 2% per trade, 3% aggregate nominal stop risk",
     replace(E, name="E100 capped", max_position=1.0), .03),
    ("E100 all-in, no stop-risk budget",
     replace(E, name="E100 all-in", max_position=1.0,
             risk_per_trade=1.0, momentum_top=1), None),
)


def _period(curve: list[dict], start_day: str, *, starting_eur: float) -> dict:
    rows = [p for p in curve if p["day"] >= start_day]
    if not rows:
        raise ValueError("Empty monthly analysis period")
    last = rows[-1]
    # A fresh run starts at 5k, not necessarily at the day's close after a fill.
    prev = {"day": ( __import__("datetime").date.fromisoformat(start_day)
                     - timedelta(days=1)).isoformat(),
            "equity_eur": starting_eur}
    stats = _metrics([prev] + rows)
    return {
        "start": start_day,
        "end": rows[-1]["day"],
        "days": len(rows),
        "starting_eur": starting_eur,
        "ending_eur": round(last["equity_eur"], 2),
        "profit_eur": round(last["equity_eur"] - starting_eur, 2),
        "return_pct": round((last["equity_eur"]/starting_eur - 1)*100, 2),
        "max_drawdown_pct": stats["max_drawdown_pct"],
        "mean_invested_share_pct": round(
            sum(row["invested_share_pct"] for row in rows) / len(rows), 2
        ),
        "days_95pct_or_more_invested": sum(
            row["invested_share_pct"] >= 95 for row in rows
        ),
        "days_not_invested": sum(
            row["invested_share_pct"] < .01 for row in rows
        ),
    }


def analyse_allocation(data: dict, *, starting_eur: float = STARTING_EUR,
                       recent_days: int = DAYS_IN_MONTH) -> dict:
    if not isfinite(starting_eur) or starting_eur <= 0:
        raise ValueError("Positive, finite starting balance required")
    if recent_days < 10:
        raise ValueError("Require at least ten calendar days")
    prices = aligned_crypto_data(data)
    dates = [bar.day for bar in prices[SYMBOLS[0]]]
    if len(dates) <= WARMUP_BARS + recent_days:
        raise ValueError("Insufficient common warmup plus comparison candles")

    first_live = dates[WARMUP_BARS]
    # Latest N COMPLETE days, reset account with that day's possible next
    # open fill. All older days are used only as trading indicator warmup.
    fresh_start = dates[-recent_days]
    results = []
    for name, spec, stop_risk in SCENARIOS:
        whole = research_backtest(
            prices, MARKETS, spec, starting_eur=starting_eur,
            entries_not_before=first_live,
            portfolio_risk_limit_fraction=stop_risk,
        )
        fresh = research_backtest(
            prices, MARKETS, spec, starting_eur=starting_eur,
            entries_not_before=fresh_start,
            portfolio_risk_limit_fraction=stop_risk,
        )
        # Reset-month fees may include only trades on/after reset date.
        recent_trades = [t for t in fresh["trade_events"]
                         if t["day"] >= fresh_start.isoformat()]
        last30 = _period(
            fresh["daily_curve"], fresh_start.isoformat(),
            starting_eur=starting_eur
        )
        active_whole = [
            d for d in whole["daily_curve"]
            if d["day"] >= first_live.isoformat()
        ]
        whole_window_means = {
            "mean_invested_share_pct": round(
                sum(d["invested_share_pct"] for d in active_whole)
                / len(active_whole), 2),
            "days_95pct_or_more_invested": sum(
                d["invested_share_pct"] >= 95 for d in active_whole
            ),
            "days_without_positions": sum(
                d["invested_share_pct"] < .01 for d in active_whole
            ),
        }
        results.append({
            "name": name,
            "parameters": asdict(spec),
            "portfolio_risk_limit_fraction": stop_risk,
            "most_recent_30d_from_fresh_5000": {
                **last30,
                "trade_events": len(recent_trades),
                "buy_events": sum(t["side"] == "BUY" for t in recent_trades),
                "sell_events": sum(t["side"] == "SELL" for t in recent_trades),
                "estimated_fees_eur": fresh["estimated_fees_eur"],
                "estimated_tax_reserve_eur": fresh["estimated_tax_reserve_eur"],
                "halted": fresh["halted"],
            },
            "full_history_compounding": {
                "first_eligible_trade_day": first_live.isoformat(),
                "final_equity_eur": whole["after_tax_equity_eur"],
                "return_pct": round(
                    (whole["after_tax_equity_eur"]/starting_eur - 1)*100, 2),
                "max_drawdown_pct": whole["stats_after_tax"]["max_drawdown_pct"],
                "estimated_fees_eur": whole["estimated_fees_eur"],
                "trade_events": len(whole["trade_events"]),
                "halted": whole["halted"],
                **whole_window_means,
            },
        })
    return {
        "mode": "READ_ONLY_CRYPTO_CAPITAL_ALLOCATION_RESEARCH",
        "history_start": dates[0].isoformat(),
        "history_end": dates[-1].isoformat(),
        "recent_days": recent_days,
        "recent_month_start": fresh_start.isoformat(),
        "starting_eur": starting_eur,
        "external_contributions": 0,
        "profits_reinvested": True,
        "compounding": (
            "Every new position uses cash and net portfolio equity "
            "AFTER realized-gain tax reserve, adjusted for prior profits/losses. "
            "No constant 5,000 EUR lot on every trade."
        ),
        "fee_model": "25 bps taker + 15 bps slippage per side",
        "scenarios": results,
        "limitations": (
            "Last 30 completed calendar days are a fresh 5000 EUR simulated account, "
            "using prior price history solely for indicator warmup. The full-history "
            "test uses compounded actual changing simulated balances. No leverage. "
            "Even E100 all-in only enters WHEN it receives a BUY signal; it does "
            "not force investment on every day or guarantee 100% at every instant. "
            "All-in removes stop-risk position sizing and can cause severe losses, "
            "despite 25% new-entry halt. Stops may gap; fees are assumptions. "
            "A historical comparison is NOT future expected returns, "
            "especially since these settings were chosen after inspecting history."
        ),
    }


def main() -> None:
    prices = {s: bitvavo_eur_daily(s) for s in SYMBOLS}
    print(json.dumps(analyse_allocation(prices), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
