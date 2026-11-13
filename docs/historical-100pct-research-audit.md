# Swing Bot 2.0 — actual data versus 100% annual-return target

Research status: 13 November 2026. No real or PAPER orders executed.
Trading-only research capital: USD 5,000 in the US historical engine.
**+100% CAGR is an ambitious research target, not a forecast**. EUR
conversion, taxes, funding flows and actual execution are not included.

## Previously collected real historical evidence (20 October 2026)

GitHub Actions historical read-only Alpaca SIP comparison:
https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39377930968

- Source: Alpaca historical delayed SIP USD stock OHLCV, split adjustment,
  separate personal-use research consent on the user-dispatched job.
- Validated: **50/50** hand-picked US equity instrument histories.
- Common historical sessions: **583**.
- Prespecified training/holdout split in that experiment:
  training ended **2026-04-13**, untouched holdout began **2026-04-14**.
- Fees: 10 bps per entry/exit side; assumed slippage 10 bps each side.
- Actual observable summary printed by the old GitHub job:

| Strategy | Training return | Holdout return | Holdout max drawdown | Holdout completed round trips |
| --- | ---: | ---: | ---: | ---: |
| A basic | +19.02% | +0.26% | 8.21% | 49 |
| B trend | +13.43% | +2.65% | 10.20% | 42 |
| C aggressive | +8.66% | +6.75% | 5.31% | 47 |

Strategy **A** was selected using development history ONLY. Therefore
**A's +0.26%** is the valid held-out selected-model result for that
experiment. Picking C because it performed best in holdout is hindsight
selection, not a valid forward strategy evaluation.

A theoretical, non-investable equal-weight reference gained **+11.13%**
in the same holdout. The original selected A underperformed it.
This experiment did **not** establish anything close to a repeatable
+100% annual return. Do not annualize a short holdout and claim it as
one-year evidence. Longer periods and different market regimes are required.

Critical limitations: the list contains **known surviving US stocks**
rather than point-in-time tradable historical constituents; actual spreads
and fills, FX to EUR, dividends, corporate-action scope, taxes and exchange
fees were not validated. A modern 50-name survivor list can make an
historical backtest look better than reality.

## Europe: actual feed connectivity, not a performance backtest

- [SAP historical EOD connectivity](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39426033319):
  253 unadjusted daily sessions, 2026-10-19 last completed day.
- [Nokia and Elisa EOD connectivity](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39427769026):
  250 unadjusted daily sessions each.
- [Split endpoint connectivity](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39430735738):
  previous one-year request worked with zero reported events; this is
  NOT confirmation of complete historical split adjustment.
- These limited samples are insufficient for a 252-session training period
  plus a **full calendar-year** holdout. There is currently **no valid
  European historical +100%-CAGR claim**. An individually approved multi-year
  EODHD plan, verified listing IDs/ISIN and point-in-time FX are still needed.
- EODHD's official personal-use policy explicitly permits private personal
  backtesting and screening for the investor's own account; avoid
  redistributing market data or results and independently check current
  plan-specific coverage:
  https://eodhd.com/help/personal-use

## New full-year US SIP methodology

Implemented in `swingbot/us_full_year_validation.py`:
- Retrieve up to 3,000 days of actual split-adjusted SIP historical daily
  bars; no data or price guesses may be substituted.
- Exact same 50-name list as the October experiment (to avoid opportunistic
  choice after seeing returns), with the **known survivorship bias**.
- Indicator warm-up 210 sessions. Each training selection uses ONLY the
  252 completed sessions immediately before that fold.
- Following test holds out at least **365 calendar days**. Each fold ends
  and the next non-overlapping test begins after it. Later models can be
  selected from prior results, never future results.
- Frozen training-selected strategy is evaluated at three assumed execution
  costs: 10/10, 25/25, 50/75 bps (fees/slippage) per side.
- Returns, annualized return, completed trade counts, maximum drawdown,
  severe stress returns and a theoretical non-investable reference are
  presented **without ticker-specific licensed quote publication**.
- Each fold starts with **independent USD 5,000** simulated capital.
  Geometrically chained fold returns are an illustrative metric,
  **not** a verified continuously funded account's CAGR.
- The live portfolio and broker orders remain entirely untouched.

Run manually using the `US SIP 100pct CAGR full-year validation`
GitHub Action with explicit consent and existing Alpaca PAPER Secrets.
The 13-Nov user-authorized one-shot run is separately gated by its exact
merge-message marker and occurs at most once on the matching main push.

Even if one historical year exceeds +100% CAGR, that does NOT establish
sustainable future doubling. Demand multiple non-overlapping years and a
separate new forward-test period before drawing conclusions.

## Next research improvement after credible long history

Expand beyond 50 names only when historical **point-in-time** universe
membership, delisted shares, stock-class/ETF filtering, broker eligibility
and 200/250-session split-adjusted daily history for each candidate are
verified. A huge modern broker ticker catalog alone is insufficient
to produce a defensible past CAGR.

This benchmark is **not** real S&P 500 total return or an investable ETF.
Do not label it as such.
