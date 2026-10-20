"""EU EUR swing engine reliability scenarios, synthetic OHLCV ONLY.

Prints safety checks, never synthetic return numbers or investment signals.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from math import cos, sin

from .equity_screen import DailyBar
from .eu_watchlist import EU_WATCHLIST_50
from .eu_swing_lab import EUHistory, compare_eu_abc_offline

REGIMES = ("TREND", "SIDEWAYS", "GAP_SHOCK", "DECLINE")


def synthetic_eu(symbol: str, regime: str, *, offset: int) -> EUHistory:
    candles=[]
    origin=date(2025,1,1)
    for idx in range(430):
        noise = 1+.009*sin((idx+offset)/11)+.007*cos((idx+offset)/19)
        if regime=="TREND":
            level=100*(1+.0014*idx)
        elif regime=="SIDEWAYS":
            level=115+5*sin((idx+offset)/18)
        elif regime=="GAP_SHOCK":
            level=110+.16*idx if idx<335 else 78+.03*(idx-335)
        elif regime=="DECLINE":
            level=160*(1-.0013*idx)
        else:
            raise ValueError("Unknown offline synthetic stress regime")
        mid=max(1,level*noise)
        opening=mid*(1+.004*cos((idx+offset)/7))
        candles.append(DailyBar(
            origin+timedelta(days=idx),opening,
            max(opening,mid)*1.018,
            min(opening,mid)*.98,mid,500_000
        ))
    return EUHistory(symbol,"EUR",tuple(candles))


def run_eu_quality_checks() -> dict:
    # 12 eurozone companies are sufficient for deterministic risk mechanics.
    symbols=tuple(x.symbol for x in EU_WATCHLIST_50 if x.currency=="EUR")[:12]
    checked=[]
    for regime in REGIMES:
        inputs={
            sym:synthetic_eu(sym,regime,offset=k*5)
            for k,sym in enumerate(symbols)
        }
        as_of=next(iter(inputs.values())).bars[-1].day+timedelta(days=1)
        result=compare_eu_abc_offline(inputs,as_of=as_of)
        assert result["source_type"]=="SYNTHETIC_TEST_FIXTURES_ONLY"
        assert result["qualified_strategy"] is None
        assert result["symbol_count"]==len(symbols)
        assert result["starting_eur"]==5000
        assert result["risk_per_trade_pct"]==1
        assert result["max_position_pct"]==20
        assert result["halt_new_entries_at_drawdown_pct"]==25
        assert not result["market_data_redistributed"]
        assert not result["broker_orders_enabled"]
        assert not result["eur_paper_portfolio_modified"]
        for v in result["variants"]:
            for phase in ("training","holdout"):
                values=v[phase]
                assert values["currency"]=="EUR"
                assert 0<=values["max_drawdown_pct"]<=100
                assert values["max_planned_stop_risk_pct_of_equity"]<=1.001
                assert not values["real_order_authorized"]
                assert not values["paper_order_authorized"]
        checked.append({"regime":regime,"passed":True})
    return {
        "mode":"OFFLINE_EU_SYNTHETIC_QUALITY_CHECKS",
        "stress_regimes":checked,
        "eur_stocks_fixture_count":len(symbols),
        "eu_eod_real_data_tested":False,
        "historic_profitability_proven":False,
        "fx_not_assumed":True,
        "orders_or_public_price_signals_enabled":False,
    }


def main():
    print(json.dumps(run_eu_quality_checks(),ensure_ascii=False))


if __name__=="__main__":
    main()
