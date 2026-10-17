"""Read-only Trading 212 Invest DEMO account adapter.

This module intentionally supports DEMO only and GET only. It is never
used for order placement. Credentials must come from environment variables,
never the source repo or CLI parameters.

Required env: TRADING212_DEMO_KEY and TRADING212_DEMO_SECRET.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

DEMO_BASE = "https://demo.trading212.com/api/v0"
ACCOUNT_CASH_PATH = "/equity/account/cash"


class DemoCredentialsMissing(RuntimeError):
    pass


class DemoAPIError(RuntimeError):
    pass


def demo_cash_balance(*, api_key: str | None = None,
                      api_secret: str | None = None) -> dict:
    key = api_key if api_key is not None else os.getenv("TRADING212_DEMO_KEY", "")
    secret = api_secret if api_secret is not None else os.getenv(
        "TRADING212_DEMO_SECRET", ""
    )
    if not key or not secret:
        raise DemoCredentialsMissing("Demo-only API keys are required")
    token = base64.b64encode(f"{key}:{secret}".encode()).decode("ascii")
    req = urllib.request.Request(
        DEMO_BASE + ACCOUNT_CASH_PATH,
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read(100_000)
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise DemoAPIError("Unexpected demo cash response")
        # Print no account credentials, never return the auth header.
        return body
    except (urllib.error.HTTPError, urllib.error.URLError,
            json.JSONDecodeError, ValueError) as exc:
        raise DemoAPIError(f"Trading 212 demo read failed: {type(exc).__name__}") from exc
