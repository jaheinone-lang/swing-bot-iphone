"""40 illustrative Helsinki Main Market stock research symbols, not broker matches.

No orders, network requests or price feeds. Exact EODHD instrument
identifiers, active listings, share classes and broker membership need
verification before any signal or strategy result.
"""
from __future__ import annotations
import json

HELSINKI_40 = (
    ("Nokia","NOKIA.HE"),("KONE","KNEBV.HE"),
    ("Sampo","SAMPO.HE"),("Fortum","FORTUM.HE"),
    ("Neste","NESTE.HE"),("UPM-Kymmene","UPM.HE"),
    ("Elisa","ELISA.HE"),("Nordea","NDA-FI.HE"),
    ("Wartsila","WRT1V.HE"),("Stora Enso","STERV.HE"),
    ("Metsa Board","METSB.HE"),("Valmet","VALMT.HE"),
    ("Kesko","KESKOB.HE"),("Orion","ORNBV.HE"),
    ("Huhtamaki","HUH1V.HE"),("Konecranes","KCR.HE"),
    ("Metso","METSO.HE"),("Outokumpu","OUT1V.HE"),
    ("SSAB A Helsinki","SSABAH.HE"),("Kemira","KEMIRA.HE"),
    ("Tietoevry","TIETO.HE"),("Revenio","REG1V.HE"),
    ("Qt Group","QTCOM.HE"),("Harvia","HARVIA.HE"),
    ("Tokmanni","TOKMAN.HE"),("Puuilo","PUUILO.HE"),
    ("Musti Group","MUSTI.HE"),("Kempower","KEMPOWR.HE"),
    ("Cargotec","CGCBV.HE"),("Mandatum","MANTA.HE"),
    ("Citycon","CTY1S.HE"),("Finnair","FIA1S.HE"),
    ("Raisio","RAIVV.HE"),("Ponsse","PON1V.HE"),
    ("Uponor (historical candidate)","UPONOR.HE"),
    ("Anora","ANORA.HE"),("Alma Media","ALMA.HE"),
    ("Sanoma","SAA1V.HE"),("Marimekko","MEKKO.HE"),
    ("Bittium","BITTI.HE"),
)
# Curated research candidates can include stale/delisted names. No live
# universe, exchange, broker or EODHD identifier is asserted.
assert len(HELSINKI_40) == 40
assert len({s for _, s in HELSINKI_40}) == 40
assert all(s.endswith(".HE") for _, s in HELSINKI_40)


def summary() -> dict:
    return {
        "status":"HELSINKI_40_UNVERIFIED_RESEARCH_CANDIDATES",
        "symbols":len(HELSINKI_40),
        "currency_assumption":"EUR_VERIFY_IN_PROVIDER",
        "exchange_assumption":"XHEL_VERIFY_ACTIVE_SHARE_CLASS",
        "active_listings_verified":False,
        "trading212_membership_verified":False,
        "eodhd_symbol_mapping_verified":False,
        "historical_tradability_verified":False,
        "read_only":True,
        "orders_enabled":False,
    }


if __name__ == "__main__":
    print(json.dumps(summary(),ensure_ascii=False))
