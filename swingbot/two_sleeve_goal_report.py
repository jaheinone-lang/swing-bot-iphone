"""Swing Bot 2.0: accounting report for two legally separate paper sleeves.

Reports a 100% annual RETURN target as a hurdle, NEVER as an estimate.
Combines mark-to-market portfolio reporting only; contributions are not
performance. PnL is measured relative to the actual external cash flows.
No trading APIs, funds, deposits, predictions or E-shadow changes.
"""
from __future__ import annotations
from datetime import date
from math import isfinite

INITIAL_TRADE_EUR=5000.0
MONTHLY_HOLD_EUR=200.0
ANNUAL_GOAL_PCT=100.0
MAX_DRAWDOWN_LIMIT_PCT=25.0


def _amount(x,name):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not isfinite(x) or x<0:
        raise ValueError(name+" must be a finite nonnegative amount")
    return float(x)


def _month(d):
    return date.fromisoformat(d[:10]).isoformat()[:7]


def report(*,as_of,trading_equity_eur,holding_liquidation_eur,
           holding_contributions,starting_trade_eur=INITIAL_TRADE_EUR,
           trading_external_flows_eur=0,trade_peak_eur=None):
    """Produce cash-flow-explicit snapshot from trusted paper ledger values.

    holding_contributions: externally funded positive cashflows, with fields
      {"month":"YYYY-MM","eur":200}; no inferred or scheduled deposits.
    Requires a unique month, dated on/before as_of.
    Trading equity is mark to market; no contributions unless explicitly
    supplied via trading_external_flows_eur. Overall 'simple_profit' is NOT
    annualized / TWR / realized return.
    """
    today=date.fromisoformat(as_of)
    trade=_amount(trading_equity_eur,"trading_equity")
    hold=_amount(holding_liquidation_eur,"holding_value")
    initial=_amount(starting_trade_eur,"initial")
    flows=_amount(trading_external_flows_eur,"trade_flows")
    if initial<=0:raise ValueError("Trading initial equity must be positive")
    if not isinstance(holding_contributions,list):
        raise ValueError("Holding contributions must be a list")
    seen=set()
    deposited=0.
    normalized=[]
    for item in holding_contributions:
        if not isinstance(item,dict) or set(item)!={"month","eur"}:
            raise ValueError("Unknown holding deposit shape")
        month=item["month"]
        if not isinstance(month,str) or len(month)!=7 or month[4]!="-":
            raise ValueError("Invalid month")
        # Gregorian month validity, and no planned/future deposits.
        date.fromisoformat(month+"-01")
        if month>today.isoformat()[:7] or month in seen:
            raise ValueError("Duplicate or future holding deposit")
        value=_amount(item["eur"],"holding deposit")
        if value<=0:raise ValueError("Only actual positive deposits")
        deposited+=value
        seen.add(month)
        normalized.append({"month":month,"eur":round(value,2)})
    trading_profit=trade-initial-flows
    holding_profit=hold-deposited
    combined=trade+hold
    combined_deposited=initial+flows+deposited
    drawdown_pct=None
    if trade_peak_eur is not None:
        peak=_amount(trade_peak_eur,"peak")
        if peak<trade or peak==0:
            raise ValueError("Peak cannot be below present equity")
        drawdown_pct=round((1-trade/peak)*100,3)
    return {
        "mode":"PAPER_TWO_SLEEVE_CASHFLOW_SEPARATED_V1",
        "as_of":today.isoformat(),
        "trading":{
            "initial_eur":round(initial,2),
            "external_flows_eur":round(flows,2),
            "equity_eur":round(trade,2),
            "profit_eur":round(trading_profit,2),
            "simple_profit_over_initial_pct":round(100*trading_profit/initial,3),
            "peak_drawdown_pct":drawdown_pct,
            "drawdown_halt_threshold_pct":MAX_DRAWDOWN_LIMIT_PCT,
            "drawdown_threshold_breached":(
                drawdown_pct is not None and drawdown_pct>=MAX_DRAWDOWN_LIMIT_PCT),
            "one_year_100pct_goal_eur_if_no_external_flows":
                round(initial*2,2),
            "annual_goal_pct":ANNUAL_GOAL_PCT,
            "annual_goal_is_not_forecast":True,
        },
        "holding":{
            "monthly_target_contribution_eur":MONTHLY_HOLD_EUR,
            "contributed_eur":round(deposited,2),
            "liquidation_eur":round(hold,2),
            "profit_eur":round(holding_profit,2),
            "cashflows":sorted(normalized,key=lambda x:x["month"]),
        },
        "combined":{
            "equity_eur":round(combined,2),
            "external_capital_eur":round(combined_deposited,2),
            "profit_eur":round(combined-combined_deposited,2),
        },
        "warning":"Simple profit is NOT time-weighted/annual return. "
          "Separate actual external deposits, paper market PnL and estimated "
          "liquidation fees. No autonomous purchases or live funds."
    }
