"""Minimal YNAB API client for read-only Personal CFO capabilities."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from config import ynab_access_token


YNAB_API_BASE_URL = "https://api.ynab.com/v1"


@dataclass(frozen=True)
class YnabApiResult:
    ok: bool
    data: dict[str, Any]
    message: str


def get_json(path: str, query: dict[str, str] | None = None) -> YnabApiResult:
    token = ynab_access_token()
    if not token:
        return YnabApiResult(
            ok=False,
            data={},
            message=(
                "YNAB_ACCESS_TOKEN is not set. Add it to the repository root .env file."
            ),
        )

    url = f"{YNAB_API_BASE_URL}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            return YnabApiResult(
                ok=False,
                data={},
                message="YNAB access token was rejected. Check YNAB_ACCESS_TOKEN in .env.",
            )

        return YnabApiResult(
            ok=False,
            data={},
            message=f"YNAB API request failed with HTTP {error.code}.",
        )
    except urllib.error.URLError as error:
        return YnabApiResult(
            ok=False,
            data={},
            message=f"YNAB API request failed: {error.reason}.",
        )
    except TimeoutError:
        return YnabApiResult(
            ok=False,
            data={},
            message="YNAB API request timed out.",
        )
    except json.JSONDecodeError:
        return YnabApiResult(
            ok=False,
            data={},
            message="YNAB API response was not valid JSON.",
        )

    return YnabApiResult(ok=True, data=payload, message="YNAB API request succeeded.")

