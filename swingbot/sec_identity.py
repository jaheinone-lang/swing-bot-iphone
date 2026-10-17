"""Strict SEC ticker/exchange-to-CIK association; never fuzzy match.

Trading 212 instrument tickers (e.g. AAPL_US_EQ) must be mapped by a
separately verified venue and original ticker, not string guesses.
The SEC periodically updates this file; it is not a point-in-time
historical identity database or a listing confirmation.
"""
from __future__ import annotations

from collections import Counter


class SecIdentityError(ValueError):
    pass


def exact_cik_match(payload: dict, *, issuer_ticker: str,
                    exchange: str) -> dict | None:
    """An unambiguous SEC identity result, else None (no imputation)."""
    if not isinstance(payload, dict):
        raise SecIdentityError("SEC CIK map expected object")
    fields=payload.get("fields")
    data=payload.get("data")
    if not isinstance(fields, list) or not isinstance(data, list):
        raise SecIdentityError("Missing SEC ticker/exchange table")
    required={"cik","ticker","name","exchange"}
    if not required.issubset(fields):
        raise SecIdentityError("Ticker map fields are incomplete")
    indices={field:fields.index(field) for field in required}
    if not issuer_ticker or not exchange:
        raise SecIdentityError("Ticker and original listing venue required")
    matches=[]
    for row in data:
        if not isinstance(row,list) or len(row)<len(fields):
            continue
        if (str(row[indices["ticker"]]).upper()!=issuer_ticker.upper()
                or str(row[indices["exchange"]]).casefold()!=exchange.casefold()):
            continue
        try:
            cik=int(row[indices["cik"]])
            if not (0<cik<10000000000):
                continue
        except (ValueError,TypeError):
            continue
        matches.append({"cik":cik,"ticker":issuer_ticker.upper(),
                        "exchange":str(row[indices["exchange"]]),
                        "company_name":str(row[indices["name"]]),
                        "source":"SEC official exchange ticker map",
                        "identity_verified_by_isin":False,
                        "broker_mapping_status":"REQUIRES_EXACT_ISIN_AND_VENUE_REVIEW"})
    # Multiple CIKs with same ticker and exchange are ambiguous.
    if len(matches)!=1:
        return None
    return matches[0]
