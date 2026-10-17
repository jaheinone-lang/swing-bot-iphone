"""Three preregistered research strategies, EUR-only, after-tax cash reservation.

STRICTLY historical research; no live or demo order endpoints.
Signals use only fully closed bars, fills use *next* available daily open.
Tax reserve excludes forecast taxes on unrealised holdings.
Positions are one FIFO lot per ticker; full exits only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import floor, isfinite
from statistics import mean
from typing import Mapping, Sequence

from .fi_tax_estimate import annual_tax_schedule
from .portfolio import Bar, COST_BPS, _atr, _validated
from .research_metrics import _metrics


@dataclass(frozen=True)
class Spec:
    name: str
    breakout: int
    trend: int
    stop_atr: float
    max_position: float
    sma200_filter: bool
    time_exit_bars: int | None
    momentum_top: int | None
    momentum_bars: int = 60
    risk_per_trade: float = 0.01


VARIANTS = (
    Spec("A - Nykyinen", 20, 50, 2.0, .20, False, None, None),
    Spec("B - Nopeampi", 15, 50, 2.5, .25, True, 20, 2),
    Spec("C - Aggressiivinen", 10, 30, 3.0, .30, True, 15, 2),
)
DEFAULT_TAX_ASSUMPTION = "Finnish-personal-tax estimate, other capital income EUR 0"


def _round(value: float) -> float:
    return round(value, 6)


def _signal(hist: Sequence[Bar], cfg: Spec) -> dict | None:
    minimum = max(cfg.breakout+1, cfg.trend, 201 if cfg.sma200_filter else 0,
                  cfg.momentum_bars+1 if cfg.momentum_top else 0, 15)
    if len(hist) < minimum:
        return None
    close = hist[-1].close
    if close <= max(x.close for x in hist[-cfg.breakout-1:-1]):
        return None
    if close <= mean(x.close for x in hist[-cfg.trend:]):
        return None
    if cfg.sma200_filter and not (close > mean(x.close for x in hist[-200:])):
        return None
    atr = _atr(hist)
    if atr <= 0:
        return None
    momentum = close/hist[-cfg.momentum_bars-1].close-1 if len(hist)>cfg.momentum_bars else 0
    return {"signal_day": hist[-1].day.isoformat(), "atr": atr,
            "momentum": momentum}


def _safe_size(available: float, equity: float, price: float,
               stop_distance: float, fee_bps: float,
               market: str, cfg: Spec) -> float:
    if available <= 0 or equity <= 0 or stop_distance <= 0:
        return 0.0
    qty = min(
        available/(price*(1+fee_bps/10000)),
        equity*cfg.max_position/price,
        equity*cfg.risk_per_trade/stop_distance,
    )
    places = 0 if market=="stock" else 8
    return floor(max(qty, 0)*10**places+1e-10)/10**places


def research_backtest(data: Mapping[str, Sequence[Bar]],
                      markets: Mapping[str, str], cfg: Spec,
                      *, starting_eur: float = 5000.0,
                      other_capital_income_eur: float = 0.0) -> dict:
    _validated(data, markets)
    if starting_eur <= 0 or not isfinite(starting_eur):
        raise ValueError("Invalid capital")
    bars_by_day = {}
    for symbol, candles in data.items():
        for bar in candles:
            bars_by_day.setdefault(bar.day, {})[symbol] = bar

    cash = starting_eur
    tax_reserved = 0.0
    peak_after_tax = starting_eur
    last_close = {}
    positions = {}
    history = {s: [] for s in data}
    pending_entries = {}
    pending_exits = set()
    disposals = []
    trades = []
    curve = []
    total_fees = 0.0
    halted = False

    def account_equity():
        gross = cash + sum(pos["qty"]*last_close.get(sym, pos["entry"])
                           for sym,pos in positions.items())
        return gross, gross-tax_reserved

    def sell(symbol, bar, day, reason, *, raw_price=None):
        nonlocal cash, tax_reserved, total_fees
        pos = positions.pop(symbol)
        fee_bps, slip_bps = COST_BPS[markets[symbol]]
        sell_price=max(0.0,(raw_price if raw_price is not None else bar.open)
                       *(1-slip_bps/10000))
        proceeds=sell_price*pos["qty"]
        fee=proceeds*fee_bps/10000
        gain=proceeds-fee-pos["basis"]
        cash += proceeds-fee
        total_fees += fee
        disposals.append({"year": day.year, "gain_eur": gain})
        tax_reserved=annual_tax_schedule(
            disposals, other_capital_income_eur=other_capital_income_eur
        )["total_estimated_tax_eur"]
        trades.append({"day":day.isoformat(),"symbol":symbol,"side":"SELL",
                       "quantity":pos["qty"],"price_eur":_round(sell_price),
                       "fee_eur":_round(fee),"realized_gain_eur":_round(gain),
                       "reason":reason})

    for day, active in sorted(bars_by_day.items()):
        stopped = set()
        for symbol, bar in sorted(active.items()):
            pos=positions.get(symbol)
            if pos and bar.low<=pos["stop"]:
                sell(symbol,bar,day,"STOP",raw_price=min(bar.open,pos["stop"]))
                stopped.add(symbol)
                pending_exits.discard(symbol)
        for symbol in sorted(pending_exits & active.keys()):
            if symbol in positions and symbol not in stopped:
                sell(symbol,active[symbol],day,"TIME_EXIT")
        pending_exits.difference_update(active.keys())

        # Only use momentum recorded at the PREVIOUS close. If multiple
        # signals compete, rank them, and limit the choice to top two.
        ready=sorted(
            [(sym,signal) for sym,signal in pending_entries.items() if sym in active],
            key=lambda x:(-x[1]["momentum"],x[0])
        )
        if cfg.momentum_top:
            ready=ready[:cfg.momentum_top]
        for symbol, entry in ready:
            if not halted and symbol not in positions and symbol not in stopped:
                bar=active[symbol]
                fee_bps,slip_bps=COST_BPS[markets[symbol]]
                price=bar.open*(1+slip_bps/10000)
                distance=cfg.stop_atr*entry["atr"]
                gross,net_equity=account_equity()
                size=_safe_size(max(0,cash-tax_reserved), net_equity, price,
                                distance,fee_bps,markets[symbol],cfg)
                if size>0 and price>distance:
                    fee=size*price*fee_bps/10000
                    cash-=size*price+fee
                    total_fees+=fee
                    positions[symbol]={
                        "qty":size,"entry":price,"basis":size*price+fee,
                        "stop":price-distance,"bars":0,"max_close":bar.close
                    }
                    trades.append({
                        "day":day.isoformat(),"symbol":symbol,"side":"BUY",
                        "quantity":size,"price_eur":_round(price),
                        "fee_eur":_round(fee),"reason":"PRIOR_CLOSE_SIGNAL"
                    })
                    # Worst-case daily stop hit on same bar as entry
                    if bar.low<=price-distance:
                        sell(symbol,bar,day,"SAME_DAY_STOP",
                             raw_price=min(bar.open,price-distance))
                        stopped.add(symbol)
        # Always discard expired unfilled entries after their next asset bar.
        for sym in active:
            pending_entries.pop(sym,None)
            last_close[sym]=active[sym].close
            history[sym].append(active[sym])

        gross,net_equity=account_equity()
        peak_after_tax=max(peak_after_tax,net_equity)
        drawdown=(peak_after_tax-net_equity)/peak_after_tax
        if drawdown>=.25:
            halted=True
            pending_entries.clear()
        curve.append({"day":day.isoformat(),"equity_eur":round(net_equity,6),
                      "gross_equity_eur":round(gross,6),
                      "tax_reserved_eur":round(tax_reserved,6),
                      "drawdown_pct":round(drawdown*100,4)})

        candidates=[]
        for symbol,bar in sorted(active.items()):
            hist=history[symbol]
            pos=positions.get(symbol)
            if pos:
                pos["bars"]+=1
                pos["max_close"]=max(pos["max_close"],bar.close)
                atr=_atr(hist)
                if atr>0:
                    pos["stop"]=max(pos["stop"],bar.close-cfg.stop_atr*atr)
                # Time-exit only after bar close; fill following available open.
                if cfg.time_exit_bars and pos["bars"]>=cfg.time_exit_bars:
                    if bar.close<pos["entry"]*1.02:
                        pending_exits.add(symbol)
            elif not halted and symbol not in stopped:
                signal=_signal(hist,cfg)
                if signal:
                    candidates.append((symbol,signal))
        if cfg.momentum_top:
            candidates=sorted(candidates,key=lambda x:(-x[1]["momentum"],x[0]))
            candidates=candidates[:cfg.momentum_top]
        for symbol,signal in candidates:
            pending_entries[symbol]=signal

    gross,net=account_equity()
    stats=_metrics(curve)
    tax_detail=annual_tax_schedule(
        disposals,other_capital_income_eur=other_capital_income_eur
    )
    return {
        "name":cfg.name,
        "parameters":{"breakout":cfg.breakout,"trend":cfg.trend,
                      "stop_atr":cfg.stop_atr,"max_position_pct":cfg.max_position*100,
                      "sma200_filter":cfg.sma200_filter,
                      "time_exit_bars":cfg.time_exit_bars,
                      "momentum_top":cfg.momentum_top,
                      "risk_per_trade_pct":cfg.risk_per_trade*100},
        "status":"RESEARCH_ONLY_NO_ORDERS",
        "starting_eur":starting_eur,
        "gross_final_equity_eur":round(gross,2),
        "estimated_tax_reserve_eur":round(tax_reserved,2),
        "after_tax_equity_eur":round(net,2),
        "estimated_fees_eur":round(total_fees,2),
        "realized_disposals":len(disposals),
        "trade_events":trades,
        "daily_curve":curve,
        "stats_after_tax":stats,
        "tax":tax_detail,
        "halted":halted,
        "open_positions":len(positions),
    }


def walkforward_research(data: Mapping[str, Sequence[Bar]],
                         markets: Mapping[str, str],
                         *, starting_eur:float=5000.0) -> dict:
    """Fixed chronological 65/35 split; NO auto-tuned or deployed winner.

    Configs are preregistered, NOT optimised by a grid search. Holdout is
    evaluated after the fact, based on each candidate's frozen rules.
    """
    _validated(data,markets)
    common_start=max(bars[0].day for bars in data.values())
    common_end=min(bars[-1].day for bars in data.values())
    aligned={
        sym:[b for b in bars if common_start<=b.day<=common_end]
        for sym,bars in data.items()
    }
    if any(len(bars)<270 for bars in aligned.values()):
        raise ValueError("At least 270 completed observations per asset required")
    calendar=sorted({b.day for bars in aligned.values() for b in bars})
    split=calendar[int(len(calendar)*.65)]
    variants=[]
    for cfg in VARIANTS:
        result=research_backtest(aligned,markets,cfg,starting_eur=starting_eur)
        curve=result["daily_curve"]
        development=[x for x in curve if x["day"]<=split.isoformat()]
        validation=[x for x in curve if x["day"]>=split.isoformat()]
        train=_metrics(development) if len(development)>1 else None
        holdout=_metrics(validation) if len(validation)>1 else None
        variants.append({
            "name":cfg.name,"parameters":result["parameters"],
            "development":train,"holdout":holdout,
            "full_period_after_tax":result["stats_after_tax"],
            "after_tax_equity_eur":result["after_tax_equity_eur"],
            "estimated_tax_reserve_eur":result["estimated_tax_reserve_eur"],
            "estimated_fees_eur":result["estimated_fees_eur"],
            "trade_count":len(result["trade_events"]),
            "realized_disposals":result["realized_disposals"],
            "halted":result["halted"],
        })
    # Apparent model "learning": choose ONLY using train returns and drawdown
    # penalty, then evaluate that selection on previously unseen holdout.
    candidates=[v for v in variants if v["development"]]
    leader=max(candidates,key=lambda v:(
        v["development"]["total_return_pct"]
        - 1.5*v["development"]["max_drawdown_pct"],
        v["name"]
    ))
    return {
        "mode":"PRE_REGISTERED_HISTORICAL_WALK_FORWARD_RESEARCH",
        "split_date":split.isoformat(),
        "development_start":common_start.isoformat(),
        "validation_end":common_end.isoformat(),
        "selection_rule":"development return percentage - 1.5 x maximum drawdown percentage",
        "training_selected_variant":leader["name"],
        "holdout_of_selected":leader["holdout"],
        "auto_trading_changes":False,
        "tax_model":"Finnish personal 30/34%, EUR only, realized gains only; simplified reserve",
        "compounding":"Each new position uses CURRENT after-tax equity and cash minus accrued tax reserve",
        "caveat":(
            "Not future-proof proof: candidates and instruments were considered using "
            "historical data. Validation split is chronological but is not a truly "
            "unseen dataset once the strategies are discussed. No dividend adjustments "
            "or actual execution. Never auto-deploy the highest historical return."
        ),
        "variants":variants,
    }
