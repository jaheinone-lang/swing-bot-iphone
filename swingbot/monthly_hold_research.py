"""Pure READ-ONLY BTC+ETH monthly holding sleeve (DCA), no exchange orders.

Separate from the EUR 5000 trading sleeve and frozen E shadow ledger.
At the first observed UTC day of each calendar month in the selected
evaluation era, hypothetical EUR 200 goes to HOLD ONLY, 50/50 BTC/ETH.
The extra EUR 200 is external cash inflow, NEVER trading profit.
Both buy and final liquidation costs included. Mark to market using
conservative estimated NET sale proceeds. Daytime next open, no future
observations when deciding contribution date.

An ambitious 100% annual return is a benchmark goal, NEVER a forecast.
TWR uses net-liquidation value with the flow at day's open. TWR can be
unstable with near-zero starting value and is not an annual performance
promise. PnL is separated from deposits, and monthly sleeve results are
not mixed into previous swing-strategy profits.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from .intraday_net_target import ExecutionCosts, buy_total_cost, sell_net_proceeds
from .daily_swing_research import PAIRS,split_eras, FEE, STRESS

MONTHLY_EUR=200.
BTC_SHARE=.50
ETH_SHARE=.50
ANNUAL_TARGET_PCT=100.
TRADING_START_EUR=5000.

def simulate(era_segments,fees=FEE,monthly=MONTHLY_EUR):
    if not(isfinite(monthly) and monthly>0):raise ValueError("Positive deposit required")
    # Use same synchronized 1d candle sections; enforce cashflow chronology.
    units={s:0. for s in PAIRS}
    total_deposited=0.
    deposit_rows=[]
    first_months=set()
    historical_values=[]
    prev_equity=None
    growth=1.
    for feed,min_ts in era_segments:
        ticks=feed["BTC-EUR"]
        for i,btc in enumerate(ticks):
            ts=btc["timestamp_ms"]
            if ts<min_ts:continue
            day=datetime.fromtimestamp(ts/1000,timezone.utc).date()
            month=day.strftime("%Y-%m")
            # This model is explicitly a NEW zero-initial-value sleeve
            # with money injected at the first UTC day in each month.
            contribution=0.
            if month not in first_months:
                first_months.add(month)
                contribution=monthly
                total_deposited+=contribution
                for symbol,weight in (("BTC-EUR",BTC_SHARE),("ETH-EUR",ETH_SHARE)):
                    raw=feed[symbol][i]["open"]
                    qty=contribution*weight/buy_total_cost(raw,1,fees)
                    units[symbol]+=qty
                deposit_rows.append({"month":month,"date":day.isoformat(),
                                     "amount_eur":round(contribution,2)})
            equity=sum(sell_net_proceeds(feed[symbol][i]["close"],
                        units[symbol],fees) for symbol in PAIRS)
            # Time-weighted daily returns strip external cash flows.
            if prev_equity is not None and prev_equity+contribution>0:
                growth*=equity/(prev_equity+contribution)
            prev_equity=equity
            historical_values.append({"day":day.isoformat(),
                                      "equity_eur":round(equity,2)})
    if not deposit_rows:raise ValueError("No valid DCA trading days")
    return {"months_funded":len(deposit_rows),
        "monthly_deposit_eur":monthly,
        "btc_weight":BTC_SHARE,"eth_weight":ETH_SHARE,
        "contributions_eur":round(total_deposited,2),
        "estimated_liquidation_eur":round(prev_equity,2),
        "net_market_pnl_eur":round(prev_equity-total_deposited,2),
        "simple_return_on_all_deposits_pct":round(100*(prev_equity/total_deposited-1),3),
        "time_weighted_growth_pct":round(100*(growth-1),3),
        "first_deposit":deposit_rows[0]["date"],
        "last_deposit":deposit_rows[-1]["date"],
        "last_valued_day":historical_values[-1]["day"],
        "deposit_schedule":deposit_rows,
        "real_orders":0,
        "warning":"Time-weighted growth is over varying full period, NOT annualized; "
                  "cashflow stripping does not make costless investments."}

def study(daily_sections):
    eras=split_eras(daily_sections)
    result={}
    for label in ("early","later"):
        result[label]={
            "normal_costs":simulate(eras[label]),
            "double_costs":simulate(eras[label],STRESS),
        }
    return {"mode":"SEPARATE_BTC_ETH_MONTHLY_EUR200_HOLD_READ_ONLY",
        "trading_sleeve_initial_eur":TRADING_START_EUR,
        "holding_sleeve_initial_eur":0.,
        "holding_sleeve_monthly_external_deposit_eur":MONTHLY_EUR,
        "allocation":{"BTC-EUR":BTC_SHARE,"ETH-EUR":ETH_SHARE},
        "annual_net_return_aspiration_pct":ANNUAL_TARGET_PCT,
        "goal_is_never_a_guaranteed_rate":True,
        "scenarios":result,
        "live_orders":0,
        "critical_caveats":[
            "Hold sleeve is separate from EUR5000 trading and existing E shadow.",
            "Monthly contributions are NOT profits or a strategy return.",
            "Historical BTC ETH concentration can lose most of its market value.",
            "Days already seen during development, no forward validation.",
            "No real buys, broker connections, taxes or accrued interest.",
        ]}
