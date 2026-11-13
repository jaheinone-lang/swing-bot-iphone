# Swing Bot 2.0: research from books, blogs, podcasts and academic studies

Date authored: **2026-11-13**. All new historical studies of these
hypotheses are **exploratory** because we have already inspected A/B/C/D/E
historical performance. A newly measured old sample cannot become an
independent prospective holdout by being called "out of sample".

## Actual source reading / how rules translate

### 1. Kristjan Kullamägi: original public blog
- Original article (2021):
  https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/
- Podcast interview, Chat With Traders, episode 212 (2021):
  https://chatwithtraders.com/episode/212-kristjan-kullamagi-breakouts-home-runs-exponential-returns
- Original breakout concept: leader stock with strong preceding +30..100%
  advance, relatively orderly 2–8 week consolidation, renewed price/volume
  expansion. Original execution may use intraday opening-range levels.
- Our **LEADER_BASE_BREAK** DAILY PROXY (code, frozen before data run):
  over prior 60 completed sessions to 15 sessions before the signal,
  advance >=25%; previous 15-session price range high/low <=1.20 and latest
  5-session intraday ranges not more than 15% wider than the first 10;
  signal-day close > prior 15 highs, >=1.5× prior 20-session volume,
  close in upper 30% of day's range, adequate trailing dollar turnover.
- **GAP_VOLUME_PROXY**: after-close information shows day opened at least
  10% above prior close, day volume >=2× previous 20-session mean, close
  >=open in high 30% of today's range and adequate liquidity.
  This is **NOT** verified "Episodic Pivot" because we lack earnings/news
  cause and intraday opening-range data. We must not infer EPS surprise
  from a price gap or imply a feasible intraday fill.

### 2. Academic evidence: 52-week highs and momentum
- Thomas J. George and Chuan-Yang Hwang (2004),
  *The 52-Week High and Momentum Investing*, Journal of Finance.
  https://doi.org/10.1111/j.1540-6261.2004.00695.x
- Finding: distance to annual high can explain parts of cross-sectional
  momentum. Not a validated +100% yearly trading strategy.
- **52W_HIGH** daily event proxy: close within 2% of highest high in
  252 historical sessions, close above 50-day above 200-day simple means,
  63-day stock price advance >=10%, trailing dollar turnover >=USD 5m/day.
  Same-name event cooldown 20 trading sessions.

### 3. Andreas Clenow: Stocks on the Move
- Book *Stocks on the Move* (2015), catalog:
  https://search.worldcat.org/title/stocks-on-the-move-beating-the-market-with-hedge-fund-momentum-strategies/oclc/920465742
- Independent implementation description:
  https://www.turingtrader.com/portfolios/clenow-stocks-on-the-move/?v=1
- Describes 90-day log-price regression slope × R², weekly rebalancing,
  MA100 stock eligibility and MA200 index regime filter on a historical
  investable S&P 500 constituent universe.
- Our **90D_SMOOTH_TREND** is NOT the book's whole portfolio rule:
  positive 90-session log slope, regression R² >=0.75, last 90 sessions
  >=15% price increase, above MA100, no single 90-day daily close jump
  exceeding ±15%, dollar turnover >=USD 5m/day.
  Absolute event threshold is a provisional test proxy; selection by
  cross-sectional ranked momentum and proper historical membership is
  later work. The book has NOT been copied or reproduced in full.

### 4. Evidence against overconfident claims
- Lesmond, Schill and Zhou (2004), *The illusory nature of momentum
  profits*, Journal of Financial Economics:
  https://www.sciencedirect.com/science/article/pii/S0304405X0300206X
  Frequent trading of costly securities can wipe out apparent momentum
  outperformance. We therefore explicitly apply entry + exit friction.
- Fink, Palan and Theissen (2024), *Earnings Autocorrelation and the
  Post-Earnings-Announcement Drift: Experimental Evidence*:
  https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/earnings-autocorrelation-and-the-postearningsannouncement-drift-experimental-evidence/61CD6A2065A4686418A3C47DEF3AC24B
  A genuine earnings-event strategy would require verified publication
  timestamps, surprises and intraday fills. SIP daily bars alone cannot
  validate it.

## What the new event study actually measures

`swingbot/literature_event_study.py` takes validated split-adjusted USD
daily bars. End-of-day patterns do NOT enter on the same closing price.
Every triggered event hypothetically buys at next trading-session OPEN
and sells at the OPEN after 5 or 20 additional completed sessions.
Charging 10 basis points fee and 10 basis points slippage **per side**,
with no stops or margin. This is a pair of fixed-horizon academic-style
event-return experiments, NOT a fully executable trading system.

Optional verified historical SIP **SPY** data form a same-date
next-open-to-exit-open benchmark. This price-only reference EXCLUDES
dividends, borrow/financing costs and FX to EUR. Matched dates are
mandatory; missing SPY bars are not silently filled.

Results (public aggregate only) include event counts, number of distinct
stocks, year-by-year counts, average and median 5/20-session NET returns,
percentage positive, matched SPY interval return and mean excess, and
sample-size warning at fewer than 30 events per hypothesis.

There is an intentional 20-session same-ticker event cooldown, but trades
from different tickers **overlap in calendar time**. These event returns
are NOT independent observations, a fair confidence interval, a
self-financing portfolio equity curve, or proof of recurring +100% CAGR.

## Current architecture constraints

- Original 50-stock US hand-picked survivor set is biased and very unlike
  the full market momentum leader set. Strong speculative growth leaders,
  IPOs and failed/delisted names are underrepresented.
- EOD prices cannot reproduce Qullamägi's true intraday entry, nor verify
  whether a gap was actually caused by earnings guidance.
- Securities may be absent from Trading 212; no verified margin, spread,
  currency conversion, commissions, tax or real order liquidity.
- Only research feeds with separately confirmed personal non-display rights
  are allowed; no redistributable per-ticker quotes or symbol lists.
- We need a historical **point-in-time company universe** including the
  delisted and a separate event timestamp source before any broad-market
  historical claim can be trusted.

## Practical continuation

A transparent failure (no high-volume gap events among 50 large caps)
is valuable information. It means expand to historically eligible liquid
smaller-cap and true growth leaders with proper listing rights, not lower
all thresholds until a backtest suddenly claims +100%.

If one event type has a positive historical event-return statistic, do
not declare victory. Formal future testing requires preregistered rules,
genuine new data after 2026-11-13, transaction cost and spread checks,
execution feasibility and a continuous-cash equity curve using only data
available at the decision time.

The existing aggressive momentum D/E experiment (GitHub run
43493593751) reported an **illustrative** +19.68% 5-fold chained
annualized result and none of the five folds exceeded +100%. It is still
exploratory, not a validated live edge or new truly unseen test.
