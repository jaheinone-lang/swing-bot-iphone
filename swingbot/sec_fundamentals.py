"""SEC EDGAR point-in-time US-GAAP fundamental signals (US filers only).

Only use facts FILED before the analysis date. Annual reports (10-K/10-K/A)
may contain restatements; select the earliest available filing for each fiscal
year to avoid leaking later revisions into historic backtests. SEC facts are
NOT earnings surprises; consensus EPS requires a separately licensed source.
"""
from __future__ import annotations

from datetime import date
from math import isfinite
from typing import Any
import json
import os
import urllib.parse
import urllib.request


REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
NET_PROFIT_TAGS = ("NetIncomeLoss", "ProfitLoss")
CASH_TAGS = ("NetCashProvidedByUsedInOperatingActivities",)
CAPEX_TAGS = ("PaymentsToAcquirePropertyPlantAndEquipment",)


def _yearly_facts(facts: dict, tags: tuple[str,...], *, as_of: date) -> dict[int,dict]:
    namespace = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        values=namespace.get(tag, {}).get("units", {}).get("USD", [])
        candidates={}
        for f in values:
            if (f.get("form") not in ("10-K","10-K/A")
                    or f.get("fp") != "FY" or f.get("fy") is None
                    or not f.get("start") or not f.get("end")
                    or not f.get("filed")):
                continue
            try:
                filed=date.fromisoformat(f["filed"])
                start=date.fromisoformat(f["start"])
                end=date.fromisoformat(f["end"])
                value=float(f["val"])
                fiscal_year=int(f["fy"])
            except (ValueError, TypeError, KeyError):
                continue
            duration=(end-start).days
            if filed>as_of or not(300<=duration<=400) or not isfinite(value):
                continue
            # 'frame' may be absent for fiscal-calendar differences.
            # Prefer shortest filing-delay source (earliest filed for that FY).
            if (fiscal_year not in candidates or
                    (filed, f.get("accn","")) <
                    (candidates[fiscal_year]["filed"],candidates[fiscal_year]["accn"])):
                candidates[fiscal_year]={
                    "value":value,"filed":filed,"accn":f.get("accn",""),
                    "period_end":end,
                }
        if len(candidates)>=2:
            return candidates
    return {}


def analyze_companyfacts(payload:dict, *,as_of:date)->dict:
    if not isinstance(payload,dict) or "facts" not in payload:
        raise ValueError("SEC companyfacts payload missing")
    revenue=_yearly_facts(payload,REVENUE_TAGS,as_of=as_of)
    profit=_yearly_facts(payload,NET_PROFIT_TAGS,as_of=as_of)
    operating=_yearly_facts(payload,CASH_TAGS,as_of=as_of)
    capex=_yearly_facts(payload,CAPEX_TAGS,as_of=as_of)
    years=sorted(revenue)
    result={
        "source":"SEC EDGAR companyfacts, US GAAP (USD)",
        "as_of":as_of.isoformat(),
        "entity":payload.get("entityName"),
        "fundamentals_status":"INSUFFICIENT",
        "earnings_surprise_status":"NO_ANALYST_CONSENSUS",
        "earnings_ipo_status":"NOT_A_LISTING_DATE",
        "points":0,
        "source_url":None,
    }
    try:
        cik=int(payload.get("cik"))
        if 0<cik<10000000000:
            result["source_url"]=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    except (TypeError,ValueError):
        pass
    if len(years)<2:
        return result
    current,previous=years[-1],years[-2]
    if current-previous!=1 or revenue[previous]["value"]<=0:
        return result
    newest=revenue[current]
    # No data older than 20 months. Uses only filed fact available at as_of.
    if (as_of-newest["period_end"]).days>610:
        return result
    rev_growth=newest["value"]/revenue[previous]["value"]-1
    result.update({
        "fundamentals_status":"PARTIAL",
        "fiscal_year":current,
        "revenue_growth_pct":round(100*rev_growth,2),
        "revenue_filed":newest["filed"].isoformat(),
        "revenue_usd":round(newest["value"],2),
    })
    # A positive revenue year is not evidence of a good valuation.
    score=0
    score+=20 if rev_growth>=.15 else (10 if rev_growth>0 else -15)
    if current in profit and previous in profit:
        now_p=profit[current]["value"]
        prev_p=profit[previous]["value"]
        result["net_income_usd"]=round(now_p,2)
        result["profit_improved"]=now_p>prev_p
        score+=15 if now_p>prev_p else -10
    if current in operating:
        cash=operating[current]["value"]
        result["operating_cashflow_usd"]=round(cash,2)
        score+=10 if cash>0 else -10
        if current in capex:
            fcf=cash-capex[current]["value"]
            result["free_cashflow_proxy_usd"]=round(fcf,2)
            score+=10 if fcf>0 else -10
    result["points"]=max(-45,min(55,score))
    return result


def download_companyfacts(cik:int, *,user_agent:str|None=None)->dict:
    """Requires a truthful SEC-compliant identifying user agent.

    No SEC API requests are made when SEC_USER_AGENT is unset.
    Do not place contact email or paid market-data keys in public GitHub.
    """
    user_agent=user_agent or os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent or "@" not in user_agent or len(user_agent)>180:
        raise RuntimeError("SEC_USER_AGENT (identifying name and contact) is required")
    if not isinstance(cik,int) or cik<=0 or cik>=10000000000:
        raise ValueError("Invalid CIK")
    url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    req=urllib.request.Request(
        url,headers={"User-Agent":user_agent,"Accept":"application/json"},
        method="GET"
    )
    with urllib.request.urlopen(req,timeout=20) as res:
        raw=res.read(8_000_001)
    if len(raw)>8_000_000:
        raise RuntimeError("SEC response too large")
    result=json.loads(raw)
    if not isinstance(result,dict) or int(result.get("cik",-1))!=cik:
        raise ValueError("Invalid/mismatched SEC companyfacts response")
    return result
