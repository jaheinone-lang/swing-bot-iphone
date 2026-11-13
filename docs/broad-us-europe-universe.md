# Broad USA and European exchange coverage: Swing Bot 2.0

## What is implemented

- **Trading 212:** Existing daily private DEMO catalog already enumerates all account-accessible instruments. Public iPhone dashboard shows **aggregated counts only**, not the private instrument list.
- **US exchange discovery:** `swingbot/broad_market_catalog.py` can retrieve all active instruments returned by the authenticated **Alpaca PAPER `/v2/assets` endpoint**. This is US equity-class inventory, and **also includes ETFs**. It is not a guaranteed census of every US operating company, and OTC assets must not automatically become trade candidates.
- **Europe exchange discovery:** EODHD's exchange directory identifies supported exchange *venues* by country, including the EU-27, UK, Norway and Switzerland (broader geographic Europe). For each supported venue, the module can fetch provider-classified common-stock entries, in chunks. Only exchanges that the source actually covers can be discovered.
- **Scale:** `plan_batches` divides the validated listing catalog into deterministic batches (1..5000 entries). No 50-stock hard cap. The new dynamic US IEX/SIP price adapter permits a separately broker-approved list beyond the curated 50, processed in batches up to 100 symbols.
- **Fail-closed safety:** Historical USD scans require an explicit non-display research-data permission flag. A missing right results in no price requests, no invented signals and no broker orders. The old 50-stock offline lab and EU50 research model remain unchanged.

## Not yet achieved

- No validated provider snapshot proving that **every** company on **every** US/European exchange is represented, nor a complete unique-company census. A company can appear multiple times as different share classes or on different venues; a ticker is not a stable company identifier.
- Trading 212 instrument metadata does not provide the candles needed for 200-day trend, breakout, walk-forward or transaction-cost backtests.
- EODHD **EU historical prices**, point-in-time delisted inventories, dividend/split handling and EUR/GBP/CHF/NOK/SEK/DKK currency conversions are **not ready for full-market strategy simulation**.
- Alpaca IEX-only bars represent one US venue; they **do not prove total-market liquidity**. Delayed SIP and historical-data terms must be verified independently.
- No live trade authorization, no promise of future performance, and **no 100% annual-return claim**. US synthetic offline checks do not prove any edge.
- Provider terms for algorithmic/non-display use and any redistribution must be verified before processing licensed history, even when a URL technically responds.

## Optional private GitHub workflow

Run `Wide US and European equity catalog inventory` manually in GitHub Actions:
1. Choose **alpaca** to count available US equity-class instruments. Requires `ALPACA_PAPER_DATA_KEY_ID` and `ALPACA_PAPER_DATA_SECRET_KEY` stored in GitHub Actions Secrets. This is a GET-only request; no paper orders.
2. Choose **eodhd** to enumerate a small chunk of supported European exchanges. Requires `EODHD_API_TOKEN` stored as an Actions Secret. Set `start_exchange` and `max_exchanges` to iterate over the complete source-supported exchange directory within provider rate limits; different chunks are not automatically stored or aggregated. Do **not** commit raw symbol catalogs to this public repository.
3. The workflow prints safe metadata **counts only**. It does **not** perform full-universe strategy tests or save source/provider results as a private database.

For future complete scans, build an approved private datastore containing exchange/ISIN/MIC mappings with explicit data rights and point-in-time company listings; then fetch only licensed EODOHLCV for batches, validate currency/corporate actions, and test every candidate without hindsight. Publishing only safe summary statistics remains the default.

Documentation:
- <https://docs.alpaca.markets/us/reference/get-v2-assets-1>
- <https://docs.trading212.com/api/instruments>
- <https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours>
