"""Read-only credential smoke test for Alpaca PAPER account.

No market data, account details, orders, or secret values are printed.
Uses the paper-only host and a GET account call to test credentials.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

HOST = "https://paper-api.alpaca.markets/v2/account"


def check_paper_connection(*, key: str | None = None, secret: str | None = None,
                           urlopen=urllib.request.urlopen) -> dict:
    key = key if key is not None else os.getenv("ALPACA_DATA_KEY_ID", "")
    secret = secret if secret is not None else os.getenv("ALPACA_DATA_SECRET_KEY", "")
    if not key or not secret:
        return {"status": "MISSING_PAPER_KEYS", "paper_only": True,
                "market_data_requested": False, "orders_sent": False}
    req = urllib.request.Request(HOST, method="GET", headers={
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
        "User-Agent": "SwingBotPaperConnectionCheck/1.0",
    })
    try:
        with urlopen(req, timeout=12) as response:
            # Deliberately do not read account body or expose account metadata.
            code = getattr(response, "status", 200)
        status = "PAPER_API_OK" if code == 200 else "PAPER_API_UNEXPECTED_HTTP"
    except urllib.error.HTTPError as exc:
        status = ("PAPER_API_UNAUTHORIZED" if exc.code in (401, 403)
                  else "PAPER_API_HTTP_ERROR")
    except (urllib.error.URLError, TimeoutError, OSError):
        status = "PAPER_API_NETWORK_ERROR"
    return {"status": status, "paper_only": True,
            "market_data_requested": False, "orders_sent": False}


def main() -> None:
    outcome = check_paper_connection()
    print(json.dumps(outcome))
    if outcome["status"] != "PAPER_API_OK":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
