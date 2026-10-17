"""Build a public, read-only snapshot for the iPhone dashboard.

Uses historical, completed candles; this is *not* an execution engine.
No account balances, secrets, or personally identifying data are processed.
Failure of one market does not silently substitute synthetic prices.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .forward_paper import advance_paper, public_paper_summary

from .bitvavo_data import bitvavo_eur_daily
from .market_data import MarketDataError, stooq_eur_daily
from .yahoo_data import yahoo_eur_daily
from .portfolio import backtest
from .strategy import evaluate_signal

# Keep price provenance attached to every displayed instrument.
INSTRUMENTS = {
    "BTC-EUR": ("crypto", bitvavo_eur_daily, "Bitvavo public OHLC"),
    "ETH-EUR": ("crypto", bitvavo_eur_daily, "Bitvavo public OHLC"),
    "SOL-EUR": ("crypto", bitvavo_eur_daily, "Bitvavo public OHLC"),
    "SAP.DE": ("stock", yahoo_eur_daily, "Yahoo Finance unofficial historical OHLC"),
}
PAPER_CAPITAL_EUR = 5000.0


def build_snapshot() -> dict:
    snapshot = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "READ_ONLY_RESEARCH",
        "initial_eur": PAPER_CAPITAL_EUR,
        "max_new_entry_drawdown_pct": 25,
        "instruments": [],
        "portfolio_backtest": None,
        "paper_account": None,
        "messages": [
            "Oikeaa rahaa ei käytetä. Ei välittäjätiliyhteyttä eikä toimeksiantoja.",
            "Päiväkynttilät ovat valmistuneita historiallisen datan havaintoja; signaalit eivät ole intraday-hälytyksiä.",
            "Pörssikulut, verot, toimeksiannon toteutuvuus ja mallin tuottavuus vaativat erillisen vahvistuksen.",
        ],
    }
    full_data = {}
    market_types = {}
    for symbol, (market, loader, source) in INSTRUMENTS.items():
        entry = {
            "symbol": symbol, "market": market, "currency": "EUR",
            "source": source,
        }
        try:
            bars = loader(symbol if market == "crypto" else symbol.lower())
            closes = [bar.close for bar in bars]
            highs = [bar.high for bar in bars]
            lows = [bar.low for bar in bars]
            signal = evaluate_signal(closes, highs, lows)
            entry.update({
                "status": "ok", "day": bars[-1].day.isoformat(),
                "last_completed_close_eur": bars[-1].close,
                "signal": signal["action"], "reason": signal["reason"],
                "bars": len(bars)
            })
            full_data[symbol] = bars
            market_types[symbol] = market
        except (MarketDataError, ValueError) as exc:
            entry.update({
                "status": "unavailable", "signal": "NO_DATA",
                "reason": str(exc)[:160]
            })
        snapshot["instruments"].append(entry)

    # Require ALL requested feeds and a common start/end window. Never
    # present partial-market P&L as a combined market performance result.
    if len(full_data) == len(INSTRUMENTS):
        first_day = max(bars[0].day for bars in full_data.values())
        last_day = min(bars[-1].day for bars in full_data.values())
        aligned = {
            symbol: [bar for bar in bars if first_day <= bar.day <= last_day]
            for symbol, bars in full_data.items()
        }
        if all(len(bars) >= 61 for bars in aligned.values()):
            result = backtest(aligned, market_types, PAPER_CAPITAL_EUR)
            snapshot["portfolio_backtest"] = {
                "start": first_day.isoformat(), "end": last_day.isoformat(),
                "starting_eur": result["starting_eur"],
                "final_equity_eur": result["final_equity_eur"],
                "return_pct": result["return_pct"],
                "max_drawdown_pct": result["max_drawdown_pct"],
                "estimated_fees_eur": result["estimated_fees_eur"],
                "halted_new_entries": result["halted_new_entries"],
                "trade_count": len(result["trade_events"]),
            }
    else:
        snapshot["messages"].append(
            "Yhdistettyä tuottoa ei lasketa ennen kuin KAIKKIEN markkinoiden EUR-hintadata toimii."
        )
    return snapshot


def refresh_snapshot_and_paper(
    *,
    state_path: Path = Path("paper/state.json"),
    report_path: Path = Path("docs/data.json"),
) -> dict:
    """Atomic-ish local write before GitHub commits both files together.

    A missing or failed asset feed leaves the prior ledger unchanged.
    Dashboard may show the previous validated ledger with a PAUSED marker.
    Backtest remains separate from new forward paper account.
    """
    snapshot = build_snapshot()
    previous = None
    if state_path.exists():
        # Invalid state MUST raise; never silently start a fresh €5k account.
        previous = json.loads(state_path.read_text(encoding="utf-8"))
    valid_feed = all(i["status"] == "ok" for i in snapshot["instruments"])
    if valid_feed:
        # Fetch the same canonical data for forward trading; if this fails,
        # retain the previous account and report the pause. Duplicated reads
        # intentionally give a consistency check on feed day and closing quote.
        data = {}
        markets = {}
        try:
            for symbol, (market, loader, _source) in INSTRUMENTS.items():
                bars = loader(symbol if market == "crypto" else symbol.lower())
                first = next(x for x in snapshot["instruments"]
                             if x["symbol"] == symbol)
                if bars[-1].day.isoformat() != first["day"] or abs(
                    bars[-1].close - first["last_completed_close_eur"]
                ) > 0.000001:
                    raise ValueError("Feed changed during refresh; retry next run")
                data[symbol] = bars
                markets[symbol] = market
            next_state = advance_paper(data, markets, previous)
        except (ValueError, MarketDataError) as error:
            next_state = None
            reason = f"Paper update paused: {str(error)[:140]}"
    else:
        next_state = None
        reason = "Paper update paused: one or more price feeds unavailable"

    if next_state is not None:
        snapshot["paper_account"] = public_paper_summary(next_state)
        # This ledger is public and contains only a fictional paper account.
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = state_path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(next_state, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temp.replace(state_path)
    elif previous is not None:
        snapshot["paper_account"] = public_paper_summary(
            previous, status="PAUSED", reason=reason
        )
        snapshot["messages"].append(reason)
    else:
        snapshot["messages"].append(reason + "; paper account not started")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temp = report_path.with_suffix(".json.tmp")
    temp.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(report_path)
    return snapshot


def main():
    snapshot = refresh_snapshot_and_paper()
    print(json.dumps({
        "output": "docs/data.json",
        "generated_at_utc": snapshot["generated_at_utc"],
        "statuses": {x["symbol"]: x["status"] for x in snapshot["instruments"]},
        "backtest_complete": snapshot["portfolio_backtest"] is not None,
        "forward_paper_status": (
            snapshot["paper_account"]["status"]
            if snapshot["paper_account"] is not None else "NOT_STARTED"
        ),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
