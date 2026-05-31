"""Read-only YNAB API client helpers for Njord capabilities."""

from __future__ import annotations

from datetime import date
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from config import ynab_access_token


YNAB_API_BASE_URL = "https://api.ynab.com/v1"
DEFAULT_TIMEOUT_SECONDS = 20
PLAN_RESOURCE = "plans"
SECRET_WORDS = ("token", "authorization", "bearer", "secret", "password", "api_key")


@dataclass(frozen=True)
class YnabApiResult:
    ok: bool
    data: dict[str, Any]
    message: str
    status_code: int | None = None


@dataclass(frozen=True)
class YnabResourceResult:
    ok: bool
    items: list[dict[str, Any]]
    message: str
    status_code: int | None = None


UrlOpen = Callable[..., Any]


def sanitize_error_detail(detail: Any) -> str:
    text = str(detail)
    lowered = text.lower()
    if any(word in lowered for word in SECRET_WORDS):
        return "[redacted]"
    return text


def milliunits_to_decimal(amount: int | float | None) -> float:
    return (amount or 0) / 1000


def format_currency(amount: int | float | None) -> str:
    return f"${milliunits_to_decimal(amount):,.2f}"


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def normalize_query(query: dict[str, Any] | None) -> dict[str, str] | None:
    if not query:
        return None
    normalized = {
        key: value.isoformat() if isinstance(value, date) else str(value)
        for key, value in query.items()
        if value is not None and value != ""
    }
    return normalized or None


def data_items(result: YnabApiResult, key: str) -> YnabResourceResult:
    if not result.ok:
        return YnabResourceResult(
            ok=False,
            items=[],
            message=result.message,
            status_code=result.status_code,
        )

    container = result.data.get("data")
    if not isinstance(container, dict):
        return YnabResourceResult(
            ok=False,
            items=[],
            message="YNAB API response did not include a data object.",
            status_code=result.status_code,
        )

    items = container.get(key)
    if not isinstance(items, list):
        return YnabResourceResult(
            ok=False,
            items=[],
            message=f"YNAB API response did not include a '{key}' list.",
            status_code=result.status_code,
        )

    return YnabResourceResult(
        ok=True,
        items=items,
        message=result.message,
        status_code=result.status_code,
    )


def data_object(result: YnabApiResult, key: str) -> YnabApiResult:
    if not result.ok:
        return result

    container = result.data.get("data")
    if not isinstance(container, dict):
        return YnabApiResult(
            ok=False,
            data={},
            message="YNAB API response did not include a data object.",
            status_code=result.status_code,
        )

    item = container.get(key)
    if not isinstance(item, dict):
        return YnabApiResult(
            ok=False,
            data={},
            message=f"YNAB API response did not include a '{key}' object.",
            status_code=result.status_code,
        )

    return YnabApiResult(
        ok=True,
        data=item,
        message=result.message,
        status_code=result.status_code,
    )


class YnabClient:
    def __init__(
        self,
        token: str,
        base_url: str = YNAB_API_BASE_URL,
        opener: UrlOpen | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.token = token.strip()
        self.base_url = base_url.rstrip("/")
        self.opener = opener or urllib.request.urlopen
        self.timeout = timeout

    def get_json(self, path: str, query: dict[str, Any] | None = None) -> YnabApiResult:
        if not self.token:
            return YnabApiResult(
                ok=False,
                data={},
                message=(
                    "YNAB_ACCESS_TOKEN is not configured. Run 'Njord config status' "
                    "or add it to the preferred user-local config file."
                ),
            )

        url = f"{self.base_url}/{path.lstrip('/')}"
        normalized_query = normalize_query(query)
        if normalized_query:
            url = f"{url}?{urllib.parse.urlencode(normalized_query)}"

        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with self.opener(request, timeout=self.timeout) as response:
                status_code = getattr(response, "status", None) or getattr(response, "code", None)
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                return YnabApiResult(
                    ok=False,
                    data={},
                    message="YNAB access token was rejected. Run 'Njord config status' and refresh YNAB_ACCESS_TOKEN.",
                    status_code=error.code,
                )

            return YnabApiResult(
                ok=False,
                data={},
                message=f"YNAB API request failed with HTTP {error.code}.",
                status_code=error.code,
            )
        except urllib.error.URLError as error:
            return YnabApiResult(
                ok=False,
                data={},
                message=f"YNAB API request failed: {sanitize_error_detail(error.reason)}.",
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

        return YnabApiResult(
            ok=True,
            data=payload,
            message="YNAB API request succeeded.",
            status_code=status_code,
        )

    def list_plans(self) -> YnabResourceResult:
        return data_items(self.get_json(PLAN_RESOURCE), "plans")

    def get_plan(self, plan_id: str) -> YnabApiResult:
        return data_object(self.get_json(f"{PLAN_RESOURCE}/{plan_id}"), "plan")

    def list_accounts(self, plan_id: str) -> YnabResourceResult:
        return data_items(self.get_json(f"{PLAN_RESOURCE}/{plan_id}/accounts"), "accounts")

    def list_categories(self, plan_id: str) -> YnabResourceResult:
        return data_items(self.get_json(f"{PLAN_RESOURCE}/{plan_id}/categories"), "categories")

    def list_months(self, plan_id: str) -> YnabResourceResult:
        return data_items(self.get_json(f"{PLAN_RESOURCE}/{plan_id}/months"), "months")

    def list_transactions(
        self,
        plan_id: str,
        since_date: date | str | None = None,
        type_filter: str | None = None,
    ) -> YnabResourceResult:
        query = {
            "since_date": since_date,
            "type": type_filter,
        }
        return data_items(
            self.get_json(f"{PLAN_RESOURCE}/{plan_id}/transactions", query=query),
            "transactions",
        )

    def list_scheduled_transactions(self, plan_id: str) -> YnabResourceResult:
        return data_items(
            self.get_json(f"{PLAN_RESOURCE}/{plan_id}/scheduled_transactions"),
            "scheduled_transactions",
        )

    # Budget aliases keep caller language stable while YNAB's current API uses plans.
    def list_budgets(self) -> YnabResourceResult:
        return self.list_plans()

    def get_budget(self, budget_id: str) -> YnabApiResult:
        return self.get_plan(budget_id)


def client() -> YnabClient:
    return YnabClient(ynab_access_token())


def choose_plan(plans: list[dict[str, Any]], configured_id: str = "") -> dict[str, Any] | None:
    if configured_id:
        for plan in plans:
            if plan.get("id") == configured_id:
                return plan
        return None

    if len(plans) == 1:
        return plans[0]

    return plans[0] if plans else None


def get_json(path: str, query: dict[str, str] | None = None) -> YnabApiResult:
    return client().get_json(path, query)


def list_plans() -> YnabResourceResult:
    return client().list_plans()


def get_plan(plan_id: str) -> YnabApiResult:
    return client().get_plan(plan_id)


def list_accounts(plan_id: str) -> YnabResourceResult:
    return client().list_accounts(plan_id)


def list_categories(plan_id: str) -> YnabResourceResult:
    return client().list_categories(plan_id)


def list_months(plan_id: str) -> YnabResourceResult:
    return client().list_months(plan_id)


def list_transactions(
    plan_id: str,
    since_date: date | str | None = None,
    type_filter: str | None = None,
) -> YnabResourceResult:
    return client().list_transactions(plan_id, since_date=since_date, type_filter=type_filter)


def list_scheduled_transactions(plan_id: str) -> YnabResourceResult:
    return client().list_scheduled_transactions(plan_id)


