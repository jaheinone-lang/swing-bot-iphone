"""Finnish individual capital-gains tax ESTIMATE for research simulations.

Not tax advice and not a filing engine. EUR disposals only, no crypto swaps.
Assumes all positions are taxable personal holdings, no other capital income,
no dividends, no deemed acquisition costs, no €1000 disposal exemption,
no tax-account wrappers and deductible realised losses under the simplified
five-following-tax-years carry-forward rule.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite

RATE_BASE = 0.30
RATE_HIGH = 0.34
CAPITAL_BRACKET_EUR = 30_000.0


def annual_tax_schedule(disposals: list[dict], *,
                        other_capital_income_eur: float = 0.0) -> dict:
    """Return per-year estimates; tax charged on net realised gains, not equity.

    Each disposal is {year: YYYY, gain_eur: net sales - full cost basis}.
    Losses can offset other capital income and may carry to five later
    years. We only model losses against simulated capital gains. The
    caller's OTHER income is a threshold parameter, not represented as
    simulated portfolio income (so not taxed here).
    """
    if not isfinite(other_capital_income_eur) or other_capital_income_eur < 0:
        raise ValueError("Other capital income must be nonnegative and finite")
    net = defaultdict(float)
    for d in disposals:
        year = d.get("year")
        gain = float(d.get("gain_eur"))
        if not isinstance(year, int) or year < 1900 or year > 2100 or not isfinite(gain):
            raise ValueError("Invalid gain record")
        net[year] += gain
    if not net:
        return {"by_year": [], "total_estimated_tax_eur": 0.0,
                "unclaimed_losses_eur": 0.0}
    loss_lots = []
    schedule = []
    for year in range(min(net), max(net)+1):
        # Losses expire after the FIFTH following tax year.
        loss_lots = [[loss_year, amount] for loss_year, amount in loss_lots
                     if amount > 1e-8 and 0 <= year-loss_year <= 5]
        gain = net[year]
        used_losses = 0.0
        if gain < 0:
            loss_lots.append([year, -gain])
            taxable = 0.0
        else:
            remaining = gain
            for lot in loss_lots:
                applied = min(remaining, lot[1])
                remaining -= applied
                lot[1] -= applied
                used_losses += applied
                if remaining <= 1e-10:
                    break
            taxable = max(0.0, remaining)
        # Other capital income is ONLY used to determine the 30/34 bracket.
        # Actual personal taxation depends on real-world gains, losses and
        # other deductions unknown to this application.
        lower_band = max(0.0, CAPITAL_BRACKET_EUR-other_capital_income_eur)
        first = min(taxable, lower_band)
        due = first * RATE_BASE + (taxable-first) * RATE_HIGH
        schedule.append({
            "year": year, "net_realized_gain_eur": round(gain, 4),
            "losses_used_eur": round(used_losses, 4),
            "estimated_tax_eur": round(due, 4),
            "taxable_gain_eur": round(taxable, 4),
        })
    return {
        "by_year": schedule,
        "total_estimated_tax_eur": round(sum(x["estimated_tax_eur"] for x in schedule), 4),
        "unclaimed_losses_eur": round(sum(x[1] for x in loss_lots), 4),
    }
