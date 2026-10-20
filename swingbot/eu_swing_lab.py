"""Private EU-27 swing strategy research engine: NO APIs, orders or publishing.

Accepts ONLY:
  (1) deliberately synthetic offline test fixtures, OR
  (2) user-supplied EUR stock candles explicitly verified for a correct EU
      exchange listing, exact broker instrument, split handling and lawful
      personal non-display investment-strategy use.

SEK/DKK bars are REFUSED, not mislabeled as EUR. A separate time-aligned
FX + native-venue source validator is required before those seven names
can join a EUR capital comparison.

Simulation shares the fixed A/B/C signal/risk engine used by US research,
but starts with a separate hypothetical 5,000 EUR research account.
Its dollar-named internal accounting fields are renamed to EUR at the
boundary; no FX conversion is implied. No real or existing paper account
is touched, even with approved historical input.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Mapping

from .equity_screen import DailyBar
from .eu_watchlist import EU_BY_SYMBOL
from .us_synthetic_lab import (
    SPECS, WARMUP, START_USD, RISK_PER_POSITION, MAX_POSITION,
    DRAWDOWN_CIRCUIT, FEE_BPS, SLIPPAGE_BPS, _simulation,
    _equal_weight_reference,
)

SYNTHETIC = "SYNTHETIC_TEST_FIXTURE"
VERIFIED = "VERIFIED_EU_PERSONAL_NON_DISPLAY_HISTORY"


@dataclass(frozen=True)
class EUHistory:
    symbol: str
    currency: str
    bars: tuple[DailyBar, ...]
    source: str = SYNTHETIC
    exchange_verified: bool = False
    exact_broker_instrument_verified: bool = False
    split_adjustment_verified: bool = False
    personal_non_display_rights_verified: bool = False


def _aligned_eur(
    histories: Mapping[str, EUHistory], *, as_of: date,
    personal_non_display_use_confirmed: bool,
) -> tuple[list[date], dict[str, tuple[DailyBar, ...]], bool]:
    if not isinstance(as_of, date) or not histories or len(histories) > 50:
        raise ValueError("EU histories and a valid as_of date are required")
    real_data = False
    selected = {}
    for symbol, history in histories.items():
        listing = EU_BY_SYMBOL.get(symbol)
        if (listing is None or not isinstance(history, EUHistory)
                or symbol != history.symbol):
            raise ValueError("Symbol not an exact curated EU exchange listing")
        if listing.currency != "EUR" or history.currency != "EUR":
            raise ValueError("Non-EUR EU listing needs verified date-aligned FX")
        if history.source == VERIFIED:
            real_data = True
            if not (
                personal_non_display_use_confirmed
                and history.exchange_verified
                and history.exact_broker_instrument_verified
                and history.split_adjustment_verified
                and history.personal_non_display_rights_verified
            ):
                raise PermissionError("EU exchange, broker, split or data-use right unverified")
        elif history.source != SYNTHETIC:
            raise PermissionError("Unexpected source; live/private rights not verified")
        completed = tuple(b for b in history.bars if b.day < as_of)
        if len(completed) < WARMUP + 50:
            raise ValueError("Need 260 completed daily stock observations")
        if any(not isinstance(b, DailyBar) for b in completed):
            raise ValueError("Unknown OHLCV record")
        if any(a.day >= b.day for a, b in zip(completed, completed[1:])):
            raise ValueError("Unsorted or duplicate OHLCV observations")
        if not all(isfinite(v) and v > 0 for b in completed
                   for v in (b.open, b.high, b.low, b.close, b.volume)):
            raise ValueError("Invalid price or volume")
        if (history.source == VERIFIED
                and not 1 <= (as_of-completed[-1].day).days <= 7):
            raise ValueError("Real EU feed stale or future-dated")
        selected[symbol] = completed

    if real_data and any(h.source == SYNTHETIC for h in histories.values()):
        raise ValueError("Do not mix synthetic and real EU prices")
    calendar = sorted(set.intersection(*(
        {b.day for b in series} for series in selected.values()
    )))
    if len(calendar) < WARMUP + 50:
        raise ValueError("Insufficient aligned EU market sessions")
    aligned = {
        symbol: tuple({b.day:b for b in series}[day] for day in calendar)
        for symbol, series in selected.items()
    }
    return calendar, aligned, real_data


def _eur_statistics(raw: dict) -> dict:
    """Avoid misreporting the unit of currency-neutral engine's bookkeeping."""
    mapped = dict(raw)
    for original, translated in (
        ("starting_usd", "starting_eur"),
        ("ending_mark_to_market_usd", "ending_mark_to_market_eur"),
        ("estimated_fees_usd", "estimated_fees_eur"),
        ("net_realized_closed_pnl_usd", "net_realized_closed_pnl_eur"),
        ("mean_closed_pnl_usd", "mean_closed_pnl_eur"),
        ("worst_closed_trade_usd", "worst_closed_trade_eur"),
    ):
        if original in mapped:
            mapped[translated] = mapped.pop(original)
    mapped["currency"] = "EUR"
    return mapped


def compare_eu_abc_offline(
    histories: Mapping[str, EUHistory], *, as_of: date,
    personal_non_display_use_confirmed: bool = False,
) -> dict:
    """Fixed A/B/C strategies; selection on training only, holdout untouched."""
    days, aligned, real_data = _aligned_eur(
        histories, as_of=as_of,
        personal_non_display_use_confirmed=personal_non_display_use_confirmed,
    )
    tradable = len(days) - WARMUP
    split = WARMUP + int(tradable * .65)
    if split-WARMUP < 80 or len(days)-split < 15:
        raise ValueError("Insufficient separated training and holdout observations")
    variants = []
    for cfg in SPECS:
        training = _eur_statistics(
            _simulation(aligned, days, cfg, WARMUP, split)
        )
        holdout = _eur_statistics(
            _simulation(aligned, days, cfg, split, len(days))
        )
        variants.append({"strategy":cfg.name, "training":training,
                         "holdout":holdout})

    leader = max(variants, key=lambda v:(
        v["training"]["return_pct"]-
        1.5*v["training"]["max_drawdown_pct"],
        -v["training"]["max_drawdown_pct"], v["strategy"]
    ))
    baseline_train = _eur_statistics(
        _equal_weight_reference(aligned, days, WARMUP, split)
    )
    baseline_holdout = _eur_statistics(
        _equal_weight_reference(aligned, days, split, len(days))
    )
    training_threshold_met = (
        real_data and leader["training"]["completed_round_trips"] >= 15
        and split-WARMUP >= 80
    )
    return {
        "mode": "EU_EUR_OFFLINE_HISTORICAL_RESEARCH_NO_ORDERS",
        "source_type": (
            "USER_VERIFIED_PRIVATE_NON_DISPLAY_EU_EOD" if real_data
            else "SYNTHETIC_TEST_FIXTURES_ONLY"
        ),
        "starting_eur": START_USD,
        "symbol_count": len(histories),
        "aligned_sessions": len(days),
        "training_end":days[split-1].isoformat(),
        "holdout_start":days[split].isoformat(),
        "variants":variants,
        "chosen_on_training_only":leader["strategy"],
        "qualified_strategy": None,
        "training_trade_threshold_met":training_threshold_met,
        "benchmark_training":baseline_train,
        "benchmark_holdout":baseline_holdout,
        "risk_per_trade_pct": RISK_PER_POSITION*100,
        "max_position_pct":MAX_POSITION*100,
        "halt_new_entries_at_drawdown_pct":DRAWDOWN_CIRCUIT*100,
        "fee_bps_each_side":FEE_BPS,
        "slippage_bps_each_side":SLIPPAGE_BPS,
        "warnings": (
            "Curated EU survivors and selected venues create historical "
            "selection bias. Reference is equal-weight theoretical, not "
            "investable. Not tax/dividend/spread/FX-adjusted. Calendar is "
            "intersection of available stock sessions. Historical performance "
            "is NOT future evidence; strategy choice is not automatic."
        ),
        "market_data_redistributed": False,
        "eur_paper_portfolio_modified": False,
        "broker_orders_enabled": False,
    }
