"""BTC + ETH single-entry Finnish daytime strategy (READ-ONLY).

One REAL shared EUR cash balance. At most one entry per Helsinki calendar
day, across BOTH assets. On a confirmed completed 5m bar, buy at NEXT bar
open, take profit on 100% at >=1% net of estimated ROUNDTRIP costs, stop
conservatively, or close at 21:55 local market-time. No holding overnight.

OHLC simulation cannot establish exchange-native order execution order,
actual limit fills, or seconds-level reaction times. NEVER sends orders.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from math import isfinite
from statistics import mean
from zoneinfo import ZoneInfo

from .btc_eth_quality_gate import quality_buy_signal
from .intraday_net_target import (
    ExecutionCosts, buy_total_cost, minimum_target_price,
    net_profit_pct, sell_net_proceeds)
from .intraday_risk_regime import max_affordable_units

PAIRS = ("BTC-EUR", "ETH-EUR")
HELSINKI = ZoneInfo("Europe/Helsinki")
ENTRY_START = time(9, 0)
ENTRY_CUTOFF = time(20, 0)
FORCED_FLAT = time(21, 55)
START_CAPITAL = 5000.
MAX_POSITION_PCT = 20.
RISK_PER_TRADE_PCT = .25


def local_time(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).astimezone(
        HELSINKI)


def confirmed_upward_move(bars, i):
    """More selective alternative: buy only a confirmed rising 15m impulse.

    The quality gate already checks 20/50/100 trend, volume, volatility
    and breakout. 3 consecutive closes and modest 15m rise reduce noise.
    All decisions use FINISHED bars only, never a future candle price.
    """
    if i < 160 or not quality_buy_signal(bars, i):
        return False
    last = [b["close"] for b in bars[i-3:i+1]]
    if not (last[0] < last[1] < last[2] < last[3]):
        return False
    rise_pct = (last[-1] / last[0] - 1) * 100
    return .12 <= rise_pct <= .90


def replay_one_per_day(
    feeds, *, capital=START_CAPITAL, costs=ExecutionCosts(),
    signal=confirmed_upward_move, net_target_pct=1.,
    stop_pct=1.5, first_entry_index=160,
    previously_traded_days=(), exit_guard=None
):
    """One shared account, max ONE trade per FI local calendar day.

    Candle starting at 21:55 Finland time triggers flat-at-OPEN.
    Missing data must be handled externally by splitting contiguous
    segments and assuming last-close liquidation when a segment ends.
    """
    if set(feeds) != set(PAIRS):
        raise ValueError("BTC/ETH exactly, no SOL")
    if not (isfinite(capital) and capital > 0 and
            isfinite(stop_pct) and .5 <= stop_pct <= 5 and
            isfinite(net_target_pct) and 1 <= net_target_pct <= 5):
        raise ValueError("Invalid capital or exit constraints")
    lengths = {len(b) for b in feeds.values()}
    if len(lengths) != 1 or min(lengths) < first_entry_index + 2:
        raise ValueError("Not enough aligned complete candles")
    timestamps = [[b["timestamp_ms"] for b in feeds[s]] for s in PAIRS]
    if timestamps[0] != timestamps[1] or any(
        b-a != 300000 for a,b in zip(timestamps[0],timestamps[0][1:])
    ):
        raise ValueError("Both instruments must have aligned, gap-free 5m candles")
    count = lengths.pop()
    cash = float(capital)
    position = None
    pending = None
    trade_dates = set(previously_traded_days)
    executed = []
    equity_curve = []
    pending_rejected = 0

    def close_position(symbol, i, price, reason):
        nonlocal position, cash
        p = position
        received = sell_net_proceeds(price, p["qty"], costs)
        cash += received
        pnl = received - p["basis"]
        executed.append({
            "bar": i, "symbol": symbol, "type": reason,
            "day_local": p["day"], "entry_raw": round(p["entry_raw"], 6),
            "exit_raw": round(price, 6),
            "net_eur_before_tax": round(pnl, 4),
            "net_return_pct_on_position": round(
                100 * pnl / p["basis"], 4),
            "position_cost_eur": round(p["basis"], 4),
            "holding_minutes": (i-p["entry_bar"])*5,
        })
        position = None

    for i in range(count):
        stamp = timestamps[0][i]
        local = local_time(stamp)
        today = local.date().isoformat()
        clock = local.time().replace(tzinfo=None)

        # No end-of-day open risk. At 21:55 local close using next bar's
        # observed OPEN (no unobserved end-of-candle close fill).
        if position is not None:
            symbol = position["symbol"]
            candle = feeds[symbol][i]
            if today != position["day"] or clock >= FORCED_FLAT:
                close_position(symbol, i, candle["open"], "DAY_FLAT")
            elif exit_guard is not None and exit_guard(
                    feeds[symbol], i, position):
                # Guard uses ONLY completed bars through i-1;
                # close at current OPEN, before observing candle extremes.
                close_position(symbol, i, candle["open"], "EARLY_EXIT")
            elif candle["low"] <= position["stop"]:
                close_position(
                    symbol, i, min(candle["open"], position["stop"]),
                    "STOP",
                )
            elif candle["high"] >= position["target"]:
                # Conservative: if stop and target touch one candle, stop
                # above gets priority. Target filled exactly, no best-price
                # benefit for favorable gaps, estimated fees and slip used.
                close_position(symbol, i, position["target"], "FULL_TP")

        # Pending order is based on bar i-1's completed signal and may only
        # be attempted at NEXT bar's open inside permitted Finland hours.
        if pending is not None:
            symbol, enter_at = pending
            pending = None
            if (enter_at == i and position is None and
                today not in trade_dates and
                ENTRY_START <= clock < ENTRY_CUTOFF):
                price = feeds[symbol][i]["open"]
                stop = price * (1-stop_pct/100)
                qty = max_affordable_units(
                    cash, cash, price, risk_budget_pct=RISK_PER_TRADE_PCT,
                    max_position_pct=MAX_POSITION_PCT,
                    stop_raw_price=stop, costs=costs)
                if qty > 0:
                    basis = buy_total_cost(price, qty, costs)
                    if basis > cash + 1e-6:
                        raise ArithmeticError("Spent more cash than available")
                    cash -= basis
                    position = {
                        "symbol": symbol, "day": today, "entry_raw": price,
                        "entry_bar": i, "qty": qty, "basis": basis,
                        "stop": stop,
                        "target": minimum_target_price(
                            price, net_target_pct=net_target_pct,
                            costs=costs),
                    }
                    trade_dates.add(today)
                    executed.append({
                        "bar":i,"symbol":symbol,"type":"BUY",
                        "day_local":today,"basis_eur":round(basis,4),
                        "raw_entry":round(price,6),
                        "raw_target":position["target"],
                    })
                    # Entry bar can contain stop and target; honor STOP
                    # first, and allow full TP on the SAME 5m candle.
                    candle = feeds[symbol][i]
                    if candle["low"] <= stop:
                        close_position(
                            symbol, i, min(candle["open"],stop),
                            "ENTRY_BAR_STOP")
                    elif candle["high"] >= position["target"]:
                        close_position(symbol, i, position["target"],
                                       "FULL_TP")
                else:
                    pending_rejected += 1

        # Candles are considered complete when the loop evaluates signals.
        # Only schedule a potential NEXT-OPEN trade if that opening time
        # is within daytime (using timestamp, not future candle price).
        if (position is None and pending is None and i >= first_entry_index
                and i+1 < count and today not in trade_dates):
            next_local = local_time(timestamps[0][i+1])
            next_day = next_local.date().isoformat()
            next_clock = next_local.time().replace(tzinfo=None)
            if (next_day == today
                    and ENTRY_START <= next_clock < ENTRY_CUTOFF):
                possible = [s for s in PAIRS if signal(feeds[s],i)]
                if possible:
                    # Relative 20-candle return uses completed candles only.
                    chosen = sorted(possible, key=lambda s:(
                        -feeds[s][i]["close"]/feeds[s][i-20]["close"],s
                    ))[0]
                    pending = (chosen,i+1)
        # Closing mark to reported account equity excludes potential exit
        # costs except on actual exits. End-of-test liquidation charges them.
        marked = cash + (
            position["qty"]*feeds[position["symbol"]][i]["close"]
            if position else 0.)
        equity_curve.append(marked)

    # Data gaps are segmented externally. Force last-observed CLOSE with
    # simulated exit costs for any open inventory, and disclose in result.
    if position is not None:
        symbol = position["symbol"]
        close_position(symbol,count-1,feeds[symbol][-1]["close"],
                       "END_OF_OBSERVED_SEGMENT")

    peak = capital
    max_dd = 0.
    for value in equity_curve:
        peak = max(peak,value)
        max_dd = max(max_dd,(peak-value)/peak*100)
    buys = [e for e in executed if e["type"] == "BUY"]
    if len(set(e["day_local"] for e in buys)) != len(buys):
        raise AssertionError("One-trade-per-Finnish-day invariant broken")
    return {
        "mode":"READ_ONLY_FINNISH_DAYTRADE",
        "starting_eur":round(capital,2),
        "end_eur":round(cash,2),
        "pnl_eur":round(cash-capital,2),
        "max_marked_drawdown_pct":round(max_dd,3),
        "buys":len(buys),
        "full_take_profits":sum(
            e["type"]=="FULL_TP" for e in executed),
        "stop_exits":sum(
            e["type"] in ("STOP","ENTRY_BAR_STOP") for e in executed),
        "session_end_exits":sum(
            e["type"]=="DAY_FLAT" for e in executed),
        "early_exits":sum(e["type"]=="EARLY_EXIT" for e in executed),
        "end_segment_forced_exits":sum(
            e["type"]=="END_OF_OBSERVED_SEGMENT" for e in executed),
        "daily_trade_dates":sorted(trade_dates),
        "events":executed,
        "open_positions":0,
        "no_live_orders":True,
        "taxes_included":False,
        "warning":"5m OHLC retrospective simulation, not guaranteed immediate "
                  "limit fill. Fees/slippage are estimates. Stop gap losses "
                  "may exceed risk target. No orders submitted.",
        "size_rejects":pending_rejected,
    }
