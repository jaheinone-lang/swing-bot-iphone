"""EU-27 listed-company swing research universe (50 hand-picked examples).

A listing's venue/currency is a research assumption to verify against the
selected price-data provider and broker; Yahoo-style symbols are NOT
Trading 212 identifiers or EODHD exchange identifiers. This module performs
NO requests and authorizes NO real, demo or paper orders.

EU membership is NOT the same as the euro area: Danish and Swedish stock
prices need a date-aligned DKK/SEK -> EUR conversion before EUR portfolio
performance can be calculated. United Kingdom, Switzerland and Norway are
NOT EU member states, and are deliberately excluded.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass

EU27 = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})
MARKET_QUOTE = {
    "DE": ("XETRA", "EUR", ".DE"),
    "FR": ("EURONEXT_PARIS", "EUR", ".PA"),
    "NL": ("EURONEXT_AMSTERDAM", "EUR", ".AS"),
    "FI": ("NASDAQ_HELSINKI", "EUR", ".HE"),
    "ES": ("BME_MADRID", "EUR", ".MC"),
    "IT": ("BORSA_ITALIANA", "EUR", ".MI"),
    "BE": ("EURONEXT_BRUSSELS", "EUR", ".BR"),
    "DK": ("NASDAQ_COPENHAGEN", "DKK", ".CO"),
    "SE": ("NASDAQ_STOCKHOLM", "SEK", ".ST"),
}


@dataclass(frozen=True)
class EUListing:
    company: str
    symbol: str  # illustrative venue-qualified research ticker, NOT T212 ID
    country: str
    exchange: str
    currency: str


# Symbols require independent per-provider verification BEFORE any price fetch,
# comparison, mapping to an ISIN or trade simulation. This curated set has
# survivorship/selection bias; historical index membership is NOT asserted.
_RAW_LISTINGS = (
    ("SAP", "SAP.DE", "DE"), ("Siemens", "SIE.DE", "DE"),
    ("Allianz", "ALV.DE", "DE"), ("Deutsche Telekom", "DTE.DE", "DE"),
    ("BASF", "BAS.DE", "DE"), ("BMW", "BMW.DE", "DE"),
    ("Mercedes-Benz Group", "MBG.DE", "DE"),
    ("adidas", "ADS.DE", "DE"), ("Infineon", "IFX.DE", "DE"),
    ("Munich Re", "MUV2.DE", "DE"),
    ("LVMH", "MC.PA", "FR"), ("L'Oreal", "OR.PA", "FR"),
    ("Sanofi", "SAN.PA", "FR"), ("Airbus", "AIR.PA", "FR"),
    ("Schneider Electric", "SU.PA", "FR"), ("Danone", "BN.PA", "FR"),
    ("Vinci", "DG.PA", "FR"), ("TotalEnergies", "TTE.PA", "FR"),
    ("EssilorLuxottica", "EL.PA", "FR"),
    ("Capgemini", "CAP.PA", "FR"),
    ("ASML", "ASML.AS", "NL"), ("ING Group", "INGA.AS", "NL"),
    ("Ahold Delhaize", "AD.AS", "NL"),
    ("Heineken", "HEIA.AS", "NL"), ("Philips", "PHIA.AS", "NL"),
    ("Nokia", "NOKIA.HE", "FI"), ("KONE", "KNEBV.HE", "FI"),
    ("Fortum", "FORTUM.HE", "FI"), ("UPM-Kymmene", "UPM.HE", "FI"),
    ("Sampo", "SAMPO.HE", "FI"), ("Neste", "NESTE.HE", "FI"),
    ("Inditex", "ITX.MC", "ES"), ("Iberdrola", "IBE.MC", "ES"),
    ("Banco Santander", "SAN.MC", "ES"), ("BBVA", "BBVA.MC", "ES"),
    ("Telefonica", "TEF.MC", "ES"),
    ("Enel", "ENEL.MI", "IT"), ("Eni", "ENI.MI", "IT"),
    ("Intesa Sanpaolo", "ISP.MI", "IT"),
    ("UniCredit", "UCG.MI", "IT"), ("Generali", "G.MI", "IT"),
    ("AB InBev", "ABI.BR", "BE"), ("KBC Group", "KBC.BR", "BE"),
    ("Novo Nordisk", "NOVO-B.CO", "DK"),
    ("A.P. Moller-Maersk", "MAERSK-B.CO", "DK"),
    ("DSV", "DSV.CO", "DK"), ("Orsted", "ORSTED.CO", "DK"),
    ("Volvo Group", "VOLV-B.ST", "SE"),
    ("Atlas Copco", "ATCO-A.ST", "SE"),
    ("Ericsson", "ERIC-B.ST", "SE"),
)


def _build() -> tuple[EUListing, ...]:
    rows = []
    for name, symbol, country in _RAW_LISTINGS:
        exchange, currency, suffix = MARKET_QUOTE[country]
        if (country not in EU27 or not symbol.endswith(suffix)
                or not re.fullmatch(r"[A-Z0-9-]+\.[A-Z]{2}", symbol)):
            raise ValueError("Invalid curated EU listing")
        rows.append(EUListing(name, symbol, country, exchange, currency))
    if len(rows) != 50 or len({x.symbol for x in rows}) != 50:
        raise ValueError("EU research list must contain 50 unique symbols")
    return tuple(rows)


EU_WATCHLIST_50 = _build()
EU_BY_SYMBOL = {x.symbol: x for x in EU_WATCHLIST_50}


def eu_isin_prefix_counts(instruments: list[dict]) -> dict:
    """Safe aggregates of *stock* identifiers carrying EU ISIN prefixes.

    ISIN country prefix is NOT proof of headquarters, primary listing,
    exchange, tax domicile, trading currency, or eligibility. EUR quoted
    instruments are NOT all EU stocks. T212 ticker is an internal ID.
    No raw account metadata is emitted.
    """
    seen = set()
    eu_stock_instruments = 0
    eur_quote_eu_isin_instruments = 0
    currency_counts = Counter()
    prefix_counts = Counter()
    for item in instruments:
        if not isinstance(item, dict) or item.get("type") != "STOCK":
            continue
        isin = item.get("isin")
        ccy = item.get("currencyCode")
        ticker = item.get("ticker")
        if (not isinstance(isin, str) or
                not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", isin) or
                isin[:2] not in EU27 or
                not isinstance(ccy, str) or
                not isinstance(ticker, str) or not ticker or
                (isin, ticker) in seen):
            continue
        seen.add((isin, ticker))
        eu_stock_instruments += 1
        eur_quote_eu_isin_instruments += (ccy == "EUR")
        currency_counts[ccy] += 1
        prefix_counts[isin[:2]] += 1
    return {
        "status": "EU_ISIN_PREFIX_METADATA_COUNTS_ONLY",
        "stocks_with_eu_isin_prefix": eu_stock_instruments,
        "eur_quoted_eu_isin_prefix_stocks": eur_quote_eu_isin_instruments,
        "by_isin_prefix": dict(sorted(prefix_counts.items())),
        "by_quote_currency": dict(sorted(currency_counts.items())),
        "listing_venue_verified": False,
        "eu_issuer_domicile_verified": False,
        "price_history_verified": False,
        "strategy_returns_computed": False,
        "real_or_paper_orders_enabled": False,
    }


def eu_research_readiness() -> dict:
    currencies = Counter(x.currency for x in EU_WATCHLIST_50)
    return {
        "mode": "EU_50_WATCHLIST_METADATA_ONLY",
        "curated_listings": len(EU_WATCHLIST_50),
        "sample_symbols_by_currency": dict(sorted(currencies.items())),
        "eu_countries_represented": len({x.country for x in EU_WATCHLIST_50}),
        "unverified_provider_ticker_mapping": True,
        "broker_matches_verified": 0,
        "licensed_adjusted_ohlcv_connected": False,
        "fx_history_required_for": sorted(c for c in currencies if c != "EUR"),
        "eu_abc_backtest_ready": False,
        "survivorship_bias": True,
        "orders_enabled": False,
    }


def main() -> None:
    print(json.dumps(eu_research_readiness(), ensure_ascii=False))


if __name__ == "__main__":
    main()
