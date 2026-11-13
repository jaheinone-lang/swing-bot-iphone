"""Annual return *research target* only, never a guarantee or an order signal.

The business objective is compounding the trading-only research capital at a
hypothetical 100% CAGR. The model must NOT optimize against a drawdown penalty
or declare success from synthetic, unlicensed, short or in-sample history.
Cash additions and withdrawals are intentionally unsupported in this simple
endpoint-based CAGR; use time-weighted return for external cash flows.
"""
from __future__ import annotations

from datetime import date
from math import isfinite

TARGET_ANNUAL_RETURN_PCT = 100.0
MIN_EVIDENCE_CALENDAR_DAYS = 365


def goal_report(*, initial_equity: float, final_equity: float,
                start: date, end: date,
                synthetic_or_unverified: bool = True) -> dict:
    """Return historical CAGR and explicit level of evidence.

    Never confuse a short annualized backtest, or synthetic fixture data,
    with a predictable real-world 100%-per-year return. Negative or zero
    final equity is treated as a full loss, not an exponent error.
    """
    if (not isinstance(start, date) or not isinstance(end, date)
            or end <= start):
        raise ValueError("Need a positive historical date interval")
    if (not all(isinstance(v, (int, float)) and isfinite(v)
                for v in (initial_equity, final_equity))
            or initial_equity <= 0 or final_equity < 0):
        raise ValueError("Invalid equity values")
    days = (end-start).days
    if final_equity == 0:
        cagr = -100.0
    else:
        try:
            cagr = 100 * ((final_equity / initial_equity)**(365.25 / days)-1)
        except OverflowError:
            cagr = float("inf")
    # Extreme samples are allowed to be flagged, but never serialized as
    # Infinity/NaN; use None when numerical overflow prevents comparison.
    cagr = round(cagr, 2) if isfinite(cagr) else None
    short = days < MIN_EVIDENCE_CALENDAR_DAYS
    sample_hit = cagr is not None and cagr >= TARGET_ANNUAL_RETURN_PCT
    if synthetic_or_unverified:
        evidence = "UNVERIFIED_OR_SYNTHETIC_DATA_NOT_PROOF"
    elif short:
        evidence = "SHORT_WINDOW_ANNUALIZED_NOT_PROOF"
    else:
        evidence = "HISTORICAL_SAMPLE_ONLY_NOT_PREDICTION"
    return {
        "target_annual_return_pct": TARGET_ANNUAL_RETURN_PCT,
        "historical_annualized_return_pct": cagr,
        "target_gap_percentage_points": (
            round(cagr-TARGET_ANNUAL_RETURN_PCT,2) if cagr is not None else None
        ),
        "calendar_days": days,
        "observation_at_least_one_year": not short,
        "target_met_on_this_sample": sample_hit,
        "evidence_status": evidence,
        "sustainable_100pct_return_proven": False,
        "real_orders_authorized": False,
        "cash_flows_supported": False,
    }
