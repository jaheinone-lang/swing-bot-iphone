"""Public SEC filings discovery for IPO WATCH candidates, US issuers only.

S-1, S-1/A, F-1, F-1/A, 424B4 etc. are listing/prospectus candidates,
NOT proof of an actual IPO, first public trade, nor a verified offering
price. Do not convert SEC filing dates to exchange debut dates.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
import urllib.error
import urllib.request

FORMS = {"S-1", "S-1/A", "F-1", "F-1/A", "424B4", "424B1"}
SEC_ENDPOINT = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


class SecFeedError(ValueError):
    pass


def extract_registration_filings(payload: dict, *, as_of: date,
                                 limit: int = 50) -> list[dict]:
    if not isinstance(payload, dict):
        raise SecFeedError("SEC submissions JSON missing")
    recent = payload.get("filings", {}).get("recent", {})
    if not isinstance(recent, dict):
        raise SecFeedError("SEC recent filing records absent")
    dates = recent.get("filingDate")
    forms = recent.get("form")
    accession = recent.get("accessionNumber")
    if (not all(isinstance(x, list) for x in (dates, forms, accession))
            or len(dates) != len(forms) or len(forms) != len(accession)
            or len(dates) > 20000):
        raise SecFeedError("SEC filing arrays invalid")
    try:
        cik = int(payload["cik"])
        if not (1 <= cik < 10_000_000_000):
            raise ValueError("Invalid CIK")
    except (KeyError, ValueError, TypeError) as exc:
        raise SecFeedError("SEC issuer CIK invalid") from exc
    out = []
    for f, day, accn in zip(forms, dates, accession):
        if f not in FORMS or not isinstance(accn, str):
            continue
        try:
            filed = date.fromisoformat(day)
        except (TypeError, ValueError):
            continue
        if filed > as_of:
            continue
        accession_no_dashes = accn.replace("-", "")
        if not accession_no_dashes.isdigit() or len(accession_no_dashes) != 18:
            continue
        out.append({
            "cik":cik, "issuer":payload.get("name", "Unknown issuer"),
            "form":f,"filing_day":filed.isoformat(),
            "accession":accn,
            "filing_index_url":(
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik}/{accession_no_dashes}/{accn}-index.html"
            ),
            "stage":"REGISTRATION_OR_PROSPECTUS_ONLY",
            "ipo_confirmed":False,
            "share_price_verified":False,
            "exchange_debut_verified":False,
        })
    return sorted(out,key=lambda x:x["filing_day"],reverse=True)[:limit]


def fetch_submissions(cik: int, *, user_agent: str | None = None) -> dict:
    user_agent=user_agent or os.getenv("SEC_USER_AGENT","").strip()
    if not user_agent or "@" not in user_agent:
        raise SecFeedError("SEC_USER_AGENT contact identifier required")
    if not isinstance(cik, int) or not 1 <= cik < 10_000_000_000:
        raise SecFeedError("Invalid issuer CIK")
    url=SEC_ENDPOINT.format(cik=cik)
    req=urllib.request.Request(url,headers={
        "User-Agent":user_agent,"Accept":"application/json"
    })
    try:
        with urllib.request.urlopen(req,timeout=22) as resp:
            raw=resp.read(8_000_001)
        if len(raw)>8_000_000:
            raise SecFeedError("SEC submissions response over limit")
        parsed=json.loads(raw)
    except (urllib.error.HTTPError,urllib.error.URLError,
            TimeoutError,ValueError,UnicodeError) as exc:
        raise SecFeedError("SEC submission feed unavailable") from None
    if not isinstance(parsed,dict) or parsed.get("cik") != cik:
        raise SecFeedError("Mismatched SEC issuer CIK")
    return parsed
