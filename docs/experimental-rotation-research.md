# Swing Bot 2.0: exploratory return-seeking D/E stock hypotheses

Created 13 November 2026 **after** reviewing the failed-to-reach-100%
full-year A/B/C baseline. The goal remains +100% annual compounded return,
but there is no evidence it is attainable consistently. Therefore these
results are **hypothesis development** and may not be marketed as a fresh
independent test of repeatability.

## Two explicitly predeclared experimental models

- **D — 6-month 3-name momentum**: at each 21-session rebalance,
  examine the preceding 126 sessions' returns among historical active
  qualifying stocks. Require positive momentum of at least 5%, previous
  close above 200-session SMA and 50-session SMA above 200, plus observed
  traded dollar turnover >USD 5m/day. Equal-weight up to 3 top names;
  hold cash if no candidates.
- **E — 3-month 1-name breakout**: at each 5-session rebalance,
  look for preceding 63-session momentum of at least 12%, previous close
  above 200-session SMA and its 50-day average above 200, a close above
  the *prior* 20-session high and turnover >USD 5m/day.
  Concentrate in the single highest-momentum qualifying stock; cash otherwise.

Both models look at data only through the previous completed market day,
then simulate whole-share fills at today's opening price with assumed
fee/slippage on each transaction. No share is shorted and no borrowing,
margin or options are used.

**Unlike the old A/B/C:** D and E have no pre-set 1% stop-risk budget, no
20%-of-equity position cap and no 25% drawdown entry halt. 100% of the
trading account can be exposed to one stock; losses can be very large,
including most or all allocated capital.

## Comparison design

- Exactly the same 50-company US survivor list and 2555-day historical
  Alpaca delayed SIP source as the A/B/C annual test, no new names
  cherry-picked after its published performance results.
- At each fold, select A, B, C, D or E by the highest **past 252-session
  training return** after baseline transaction-cost assumptions. Freeze
  choice and assess next >=365 calendar-day period separately.
- Independently compute the historical *A/B/C-only training winner* and
  its later holdout return. This tests whether exploratory D/E materially
  improves on the previous process.
- Repeat under 10/10, 25/25 and 50/75 basis point per-side fee/slippage.
- Report year returns, calendar CAGR, max drawdown, worst day and turnover,
  and a hypothetical geometric chaining of independent $5,000 test folds.
  This stitched estimate is NOT the CAGR of a verified continuously
  funded executable account.

## Why an apparent winning result would still be insufficient

The 2021-2026 A/B/C test windows have already been seen by the researcher.
Selecting additional hypotheses after inspecting those windows leads to
**data snooping** even when individual trades themselves avoid lookahead.
These new D/E simulations must be classified as *exploratory* regardless
of how attractive the output looks.

Further obstacles remain: historical point-in-time membership for all
listed and delisted equities, exposure to today's surviving winners,
corporate actions, actual spreads/fills, dividend and tax treatment,
USD/EUR FX, Trading 212 tradability and future paper observation.
No current dataset can demonstrate a sustainable 100% annual return
merely from a few good backtest folds.

Execution is intentionally a read-only personal SIP historical research job,
never broker order placement. Only aggregate strategy-level numbers are
printed; licensed raw OHLCV and individual ticker positions are never
published. No new paid data subscription or trading transaction is created.
