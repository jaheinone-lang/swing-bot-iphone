# EU stock research roadmap (20 October 2026)

EU equity strategy work is currently **offline-tested, not market-data connected**.
There is no EU backtested profitability claim, no ranking based on verified EU
price history, and NO API trading.

## Implemented

- Curated 50-company EU-27 research universe in `swingbot/eu_watchlist.py`.
  Listing symbols are indicative and are *not* confirmed Trading 212 IDs or
  historical index constituents.
- 43 EUR-quoted company examples, four Danish DKK and three Swedish SEK.
  DKK/SEK names are blocked from the EUR engine until independent historical,
  date-aligned FX quotes are verified.
- Trading 212 DEMO instrument metadata is processed into safe aggregate
  *EU-ISIN-prefix* counts and shown in the iPhone dashboard. An ISIN country
  prefix does NOT prove issuer residence or exchange.
- Strict EUR-only A/B/C offline engine `swingbot/eu_swing_lab.py`, using the
  existing fixed US strategy/risk mechanics, in an independent EUR 5,000
  hypothetical research account. No real or existing paper account changes.
- Six dedicated engine safety tests, four synthetic stress regimes (trend,
  sideways, gap shock, decline), and the project's full CI suite. Synthetic
  success does NOT indicate positive trading returns.
- Strategy assessment uses a fixed development period and later holdout,
  with position cap 20%, planned risk 1%, and new entries blocked from a
  >=25% drawdown. Stop orders do NOT guarantee limiting portfolio losses.
- Spread, execution, dividend taxation, delistings, index membership bias
  and FX are not confirmed for real execution.

## EU historical split reconstruction (added 20 October 2026)

The read-only adapter `swingbot/eu_eodhd_split.py` now has an
**offline-tested price-adjustment path**:

- EODHD raw OHLC is **unadjusted**, while `adjusted_close` contains both
  dividend and split adjustment, so it cannot be reused as split-only OHLC.
- EODHD documents EOD volume as *already split-adjusted*. Never scale it
  again when reconstructing split-adjusted historical candles.
- Historical split-event dates and new/old ratios rebuild **split-only**
  open/high/low/close for earlier sessions, preserving original EOD volume.
- The selected EODHD symbol must match the entire curated listing ticker
  plus the expected provider exchange suffix, not just the exchange (for
  example, `SAP.DE` must map to `SAP.XETRA`, not `BMW.XETRA`). An independent
  accurate company/ISIN/exchange/ticker crosswalk is STILL required: symbols
  can be recycled or ambiguous and text matching alone does not prove identity.
- An ex-date needs a matching **completed EOD price bar** before adjustment.
  Duplicated, malformed, future-dated and stale records fail closed.
- The result is usable by the separate EU EUR A/B/C offline engine ONLY
  after explicit personal non-display rights, source/exchange mapping, and
  Trading 212 instrument verification. Such permissions are not inferred
  from HTTP success.
- Split history access can require an EODHD paid entitlement.
  No EODHD token has been provided or used, and **no actual EU stock
  historical strategy return has been computed**.
- The converter and end-to-end strategy integration were unit-tested with
  *synthetic fixtures only*. The 121+ tests passing reflect software
  safety, not profits.

Relevant provider documentation:
<https://eodhd.com/financial-apis/api-for-historical-data-and-volumes>
<https://eodhd.com/financial-apis/technical-indicators-api>

## Missing before EU actual-price strategy research

1. An approved personal/internal non-display data-use right for the chosen
   provider and access to >335 completed split-adjusted daily OHLCV sessions
   (preferably several market regimes and longer history) in correct native
   currencies, with correct listing venue and corporate actions.
2. A precise mapping from each exchange-listed share (preferably ISIN +
   venue/currency) to the instrument in Trading 212 DEMO metadata. A similar
   ticker or name alone is NOT enough.
3. Explicit native-currency/FX validation for DKK and SEK dates, with
   separate rate sourcing. Do not silently treat a DKK/SEK share as EUR.
4. Sample-check 50/200-day indicators, splits, day boundaries, holidays,
   halted/delisted names, quote/volume units and calendar alignment.
5. Only after independent new paper observations consider whether any
   A/B/C strategy is suitable for further development.

## Data provider research, no purchase made

- **EODHD:** as described on the provider's public EOD historical-data
  documentation on 20 Oct 2026, personal free access offers 20 API calls
  per day, about one year of history and up to 500 welcome calls.
  Paid historical-data plans advertised from US$19.99 per month.
  The existing `swingbot/eodhd_feed.py` adapter intentionally flags
  split/dividend adjustment as UNVERIFIED, therefore it is *not* an
  authorized strategy feed as-is.
  <https://eodhd.com/financial-apis/api-for-historical-data-and-volumes>
- **Twelve Data:** its free individual Basic tier primarily covers US equity
  markets and a few trial global symbols; Grow at US$79/month adds global EOD
  equities and ETFs. Provider market-specific and non-display usage rights
  should be checked *before* purchase.
  <https://twelvedata.com/pricing>
  <https://support.twelvedata.com/en/articles/12656239-european-equities-market-data>

No market-price API key for EU stock research has been supplied; none is
required for current tests. Keep any future key only in GitHub Actions
Secrets. Provider data and exact private instrument identifiers are not
published to the public repository.

### Reproducible tests

```bash
python -m unittest discover -s tests -v
python -m swingbot.eu_quality_cli
```

Live US Alpaca SIP strategy research is independent of this EU module.
