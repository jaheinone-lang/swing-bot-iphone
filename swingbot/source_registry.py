"""Explicit source readiness visible in the public iPhone research dashboard.

No tokens, user account data, scan counts or raw licensed prices.
Configured here means an adapter exists, NOT that it has been activated.
"""
from __future__ import annotations


def public_source_readiness() -> list[dict]:
    return [
        {"name":"Bitvavo","role":"Kryptojen historialliset EUR-päiväkynttilät",
         "status":"ACTIVE_PUBLIC","needs_user_action":False,
         "limitation":"Ei reaaliaikaista toteutusta eikä toimeksiantoja"},
        {"name":"Yahoo Finance (epävirallinen)",
         "role":"SAP.DE:n historiallisen EUR-kurssin tutkimussyöte",
         "status":"ACTIVE_LIMITED","needs_user_action":False,
         "limitation":"Epävirallinen; oikaistut yhtiötapahtumat eivät täysin varmennettu"},
        {"name":"ECB / Frankfurter","role":"USD, GBP, CHF, NOK, SEK ja DKK -> EUR viitekurssit",
         "status":"ADAPTER_TESTED_NOT_CONNECTED","needs_user_action":False,
         "limitation":"Päiväkurssi ei ole toteutuva FX-vaihtokurssi; ei vielä tuotantovirtaan"},
        {"name":"SEC EDGAR","role":"US-yhtiöiden tilinpäätöstiedot ja IPO-hakemukset",
         "status":"ADAPTER_TESTED_NEEDS_SEC_USER_AGENT","needs_user_action":True,
         "limitation":"Virallinen filing ei ole listautumisen vahvistus; US-yhtiöt"},
        {"name":"EODHD (valinnainen)",
         "role":"Globaali osake- ja ETF-historia, OHLCV ja yhtiötapahtumat",
         "status":"ADAPTER_TESTED_NEEDS_PRIVATE_TOKEN_AND_LICENSE",
         "needs_user_action":True,
         "limitation":"Ei tilattua hintadataa; oikaisut pitää varmentaa"},
        {"name":"Massive US Stocks Basic (maksuton)",
         "role":"8 yhdysvaltalaisen osakkeen split-oikaistu USD-päiväkurssitutkimus",
         "status":"ADAPTER_TESTED_NEEDS_MASSIVE_FREE_KEY",
         "needs_user_action":True,
         "limitation":"Maksuton 5 API-pyyntöä/min, 2 vuoden historia; vain US, ei osinkokorjausta eikä EUR-paperikauppoja. API-avain ei ole vielä kytketty"},
        {"name":"Trading 212 Invest DEMO","role":"Harjoittelutilin osake-/ETF-metatiedot (laskentatiedot)",
         "status":"DEMO_METADATA_COUNTS_VERIFIED",
         "needs_user_action":False,
         "limitation":"API-yhteys testattu 18.10.2026; jatkuvan haun tila näkyy erillisessä katalogiraportissa. Ei kurssihistoriaa, yritystuloksia tai toimeksiantoja"},
        {"name":"IPO-watch","role":"Vahvistettujen listautumisten riskiseulonta",
         "status":"RESEARCH_RULES_ONLY",
         "needs_user_action":False,
         "limitation":"Todellinen vaihto, spread ja ensimmäiset päivät vielä vaaditaan"},
    ]
