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
        {"name":"Alpaca Markets Basic · IEX (maksuton)",
         "role":"50 US-osakkeen historiallinen USD-päivädata ja alustava hintatrenditutkimus",
         "status":"ALPACA_US_HISTORICAL_SIP_50_AND_ABC_VERIFIED",
         "needs_user_action":False,
         "limitation":"PAPER-tilin historiallinen IEX/SIP 50/50 -haku ja A/B/C tutkimusajo onnistuivat 19.–20.10.2026. Ei reaaliaikaista spread- eikä Trading 212 -saatavuustodennusta. Ei ostoja/myyntejä eikä julkista raakaa hintadataa tai TOP20-rankingia"},
        {"name":"Massive US Stocks Basic (maksuton)",
         "role":"US-osakkeiden EOD-datan tekninen luku: 8/8 testattu 18.10.2026",
         "status":"MASSIVE_API_VERIFIED_STRATEGY_LICENSE_UNCONFIRMED",
         "needs_user_action":True,
         "limitation":"API-testi onnistui, mutta Massiven käyttöehdot rajoittavat non-display sijoitusstrategia-analyysiä; automaattinen käyttö estetty kunnes erillinen lupa varmistetaan. 50 osakkeen ranking on offline-valmis vain synteettiselle tai lisensoidulle datalle"},
        {"name":"EU-27 osakkeet · 50 tutkimusyhtiötä",
         "role":"9 EU-maan 50 suuren osakkeen seurantalista, EU-ISIN-metadata ja EUR/DKK/SEK-erottelu",
         "status":"EU_OFFLINE_ABC_ENGINE_TESTED_NO_REAL_EOD",
         "needs_user_action":True,
         "limitation":"EUR-määräinen EU A/B/C tutkimusmoottori ja 4 keinotekoista markkinaskenaariota testattu 20.10.2026; oikeaa EU-hintadataa ei vielä ole liitetty. Trading 212 -tarkat osumat, splittikorjaukset, käyttöoikeus ja SEK/DKK->EUR-valuuttahistoria ovat vahvistamatta. Ei toimeksiantoja"},
        {"name":"Trading 212 Invest DEMO","role":"Harjoittelutilin osake-/ETF-metatiedot (laskentatiedot)",
         "status":"DEMO_METADATA_COUNTS_VERIFIED",
         "needs_user_action":False,
         "limitation":"API-yhteys testattu 18.10.2026; jatkuvan haun tila näkyy erillisessä katalogiraportissa. Ei kurssihistoriaa, yritystuloksia tai toimeksiantoja"},
        {"name":"IPO-watch","role":"Vahvistettujen listautumisten riskiseulonta",
         "status":"RESEARCH_RULES_ONLY",
         "needs_user_action":False,
         "limitation":"Todellinen vaihto, spread ja ensimmäiset päivät vielä vaaditaan"},
    ]
