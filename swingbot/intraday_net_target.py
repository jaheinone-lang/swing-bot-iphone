"""Intraday net-profit take-profit mathematics and conservative candle research.

READ-ONLY. No broker calls or API credentials. This module does not claim
intraday backtest validity without completed intraday OHLC input.
Net profit means after two-sided assumed fees and execution slippage, BEFORE
income tax, relative to the full original executed entry cost basis.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite


@dataclass(frozen=True)
class ExecutionCosts:
    entry_fee_bps: float = 25.0
    exit_fee_bps: float = 25.0
    entry_slippage_bps: float = 15.0
    exit_slippage_bps: float = 15.0

    def __post_init__(self):
        values = (self.entry_fee_bps, self.exit_fee_bps,
                  self.entry_slippage_bps, self.exit_slippage_bps)
        if any(not isfinite(v) or v < 0 or v >= 10000 for v in values):
            raise ValueError("Cost assumptions must be finite and 0 <= bps < 10000")


def buy_total_cost(raw_entry: float, quantity: float,
                   costs: ExecutionCosts = ExecutionCosts()) -> float:
    if not (isfinite(raw_entry) and raw_entry > 0 and
            isfinite(quantity) and quantity > 0):
        raise ValueError("Entry and quantity must be positive and finite")
    return raw_entry * (1 + costs.entry_slippage_bps/10000) * quantity * (
        1 + costs.entry_fee_bps/10000
    )


def sell_net_proceeds(raw_exit: float, quantity: float,
                      costs: ExecutionCosts = ExecutionCosts()) -> float:
    if not (isfinite(raw_exit) and raw_exit > 0 and
            isfinite(quantity) and quantity > 0):
        raise ValueError("Exit and quantity must be positive and finite")
    return raw_exit * (1 - costs.exit_slippage_bps/10000) * quantity * (
        1 - costs.exit_fee_bps/10000
    )


def net_profit_pct(raw_entry: float, raw_exit: float,
                   costs: ExecutionCosts = ExecutionCosts()) -> float:
    """Percentage net return after round-trip trading costs, before tax."""
    paid = buy_total_cost(raw_entry, 1, costs)
    received = sell_net_proceeds(raw_exit, 1, costs)
    return 100 * (received/paid - 1)


def minimum_target_price(raw_entry: float, *, net_target_pct: float = 1.0,
                         costs: ExecutionCosts = ExecutionCosts(),
                         tick_size: float = 0.01) -> float:
    """Never return a target below exact 1%-net required market price.

    Tick-round UP rather than nearest; this prevents rounding below target.
    Unknown real fills may still cause the realized gain to miss the target.
    """
    if not (isfinite(net_target_pct) and net_target_pct > 0):
        raise ValueError("Positive finite net target required")
    if not (isfinite(tick_size) and tick_size > 0):
        raise ValueError("Positive finite price tick required")
    gross_entry_unit = buy_total_cost(raw_entry, 1, costs)
    sell_unit = (1 - costs.exit_slippage_bps/10000) * (
        1 - costs.exit_fee_bps/10000
    )
    exact = gross_entry_unit * (1 + net_target_pct/100) / sell_unit
    # Tiny floating rounding guard: advance a tick if float math undershoots.
    ticks = ceil(exact / tick_size)
    result = ticks * tick_size
    while net_profit_pct(raw_entry, result, costs) + 1e-10 < net_target_pct:
        ticks += 1
        result = ticks * tick_size
    return round(result, 12)


def partial_profit_cashflow(entry: float, exit_price: float, *,
                            starting_cash_eur: float = 5000.0,
                            sold_fraction: float = .5,
                            costs: ExecutionCosts = ExecutionCosts()) -> dict:
    """Close a fraction of a spot position; do not count remaining as cash profit.

    A partial exit does not realize the unreleased half of the position.
    The remainder is marked at exit_price, not booked as received proceeds.
    """
    if not (isfinite(starting_cash_eur) and starting_cash_eur > 0):
        raise ValueError("Invalid starting cash")
    if not (isfinite(sold_fraction) and 0 < sold_fraction <= 1):
        raise ValueError("Sold fraction must be (0, 1]")
    unit_paid = buy_total_cost(entry, 1, costs)
    qty = starting_cash_eur / unit_paid
    sold_qty = qty * sold_fraction
    proceeds = sell_net_proceeds(exit_price, sold_qty, costs)
    realized_basis = starting_cash_eur * sold_fraction
    gain = proceeds - realized_basis
    remaining_quantity = qty - sold_qty
    remaining_liquidation_value = (
        sell_net_proceeds(exit_price, remaining_quantity, costs)
        if remaining_quantity > 0 else 0.
    )
    return {
        "net_realized_gain_eur_before_tax": round(gain, 4),
        "cash_returned_eur": round(proceeds, 4),
        "realized_basis_eur": round(realized_basis, 4),
        "remaining_position_quantity": round(remaining_quantity, 8),
        "remaining_estimated_liquidation_value_eur": round(
            remaining_liquidation_value, 4
        ),
        "realized_profit_on_sold_slice_pct": round(
            100*gain/realized_basis, 4
        ),
        "realized_profit_on_initial_portfolio_pct": round(
            100*gain/starting_cash_eur, 4
        ),
        "tax_included": False,
    }


def complete_bar_exit_decision(*, entry_price: float, bar_open: float,
                               bar_high: float, bar_low: float, bar_close: float,
                               target_price: float, stop_price: float) -> dict:
    """Conservative completed-bar ambiguity policy.

    If high touches profit target AND low touches stop in same bar,
    assume stop fills first. Gap down fills at worse open; gap up
    at target (not a fictitious better fill). This is only a coarse
    completed OHLC simulation and not evidence of fill quality.
    """
    values=(entry_price,bar_open,bar_high,bar_low,bar_close,target_price,stop_price)
    if any(not isfinite(v) or v <= 0 for v in values):
        raise ValueError("Prices must be finite positive")
    if bar_low > min(bar_open,bar_close) or bar_high < max(bar_open,bar_close):
        raise ValueError("Invalid OHLC candle")
    if not stop_price < entry_price < target_price:
        raise ValueError("Require stop < entry < target")
    if bar_low <= stop_price:
        return {"action":"SELL", "reason":"STOP_FIRST_CONSERVATIVE",
                "raw_exit_price": min(bar_open,stop_price)}
    if bar_high >= target_price:
        return {"action":"SELL", "reason":"TAKE_PROFIT",
                "raw_exit_price": target_price}
    return {"action":"HOLD", "reason":"NO_TOUCH", "raw_exit_price":None}
