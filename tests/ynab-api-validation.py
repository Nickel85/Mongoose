"""Validate the read-only YNAB API foundation without live API calls."""

from __future__ import annotations

import json
import sys
import urllib.error
from datetime import date
from pathlib import Path


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = REPO_ROOT / "agents" / "midas"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from ynab_api import (  # noqa: E402
    YnabClient,
    choose_plan,
    format_currency,
    parse_iso_date,
)


class FakeResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.requests: list[str] = []

    def __call__(self, request, timeout: int):
        self.requests.append(request.full_url)
        path = request.full_url.split("/v1/", 1)[1]
        response = self.responses[path]
        if isinstance(response, BaseException):
            raise response
        return response


fixture_plan = {
    "id": "plan-1",
    "name": "Household",
    "accounts": [
        {"id": "account-1", "name": "Checking", "balance": 123450, "closed": False},
    ],
    "categories": [
        {"id": "category-1", "name": "Groceries", "balance": 25000, "hidden": False},
    ],
}

opener = FakeOpener(
    {
        "plans": FakeResponse({"data": {"plans": [{"id": "plan-1", "name": "Household"}]}}),
        "plans/plan-1": FakeResponse({"data": {"plan": fixture_plan}}),
        "plans/plan-1/accounts": FakeResponse({"data": {"accounts": fixture_plan["accounts"]}}),
        "plans/plan-1/categories": FakeResponse({"data": {"categories": fixture_plan["categories"]}}),
        "plans/plan-1/months": FakeResponse({"data": {"months": [{"month": "2026-05-01"}]}}),
        "plans/plan-1/transactions?since_date=2026-05-01&type=uncategorized": FakeResponse(
            {"data": {"transactions": [{"id": "transaction-1", "date": "2026-05-05"}]}}
        ),
        "plans/plan-1/scheduled_transactions": FakeResponse(
            {"data": {"scheduled_transactions": [{"id": "scheduled-1"}]}}
        ),
    }
)
client = YnabClient("secret-token", opener=opener)

plans = client.list_plans()
assert_true(plans.ok, plans.message)
assert_true(plans.items[0]["name"] == "Household", "Plans were not parsed.")

plan = client.get_plan("plan-1")
assert_true(plan.ok, plan.message)
assert_true(plan.data["id"] == "plan-1", "Plan detail was not parsed.")

accounts = client.list_accounts("plan-1")
assert_true(accounts.ok and accounts.items[0]["id"] == "account-1", "Accounts were not parsed.")

categories = client.list_categories("plan-1")
assert_true(categories.ok and categories.items[0]["id"] == "category-1", "Categories were not parsed.")

months = client.list_months("plan-1")
assert_true(months.ok and months.items[0]["month"] == "2026-05-01", "Months were not parsed.")

transactions = client.list_transactions(
    "plan-1",
    since_date=date(2026, 5, 1),
    type_filter="uncategorized",
)
assert_true(
    transactions.ok and transactions.items[0]["id"] == "transaction-1",
    "Transactions were not parsed.",
)

scheduled = client.list_scheduled_transactions("plan-1")
assert_true(
    scheduled.ok and scheduled.items[0]["id"] == "scheduled-1",
    "Scheduled transactions were not parsed.",
)

assert_true(format_currency(123456) == "$123.46", "Milliunits were not formatted correctly.")
assert_true(parse_iso_date("2026-05-30") == date(2026, 5, 30), "ISO date was not parsed.")
assert_true(parse_iso_date("bad-date") is None, "Invalid date should return None.")
assert_true(
    choose_plan([{"id": "one"}, {"id": "two"}], "two") == {"id": "two"},
    "Configured plan selection failed.",
)
assert_true(
    choose_plan([{"id": "one"}], "") == {"id": "one"},
    "Single-plan selection failed.",
)
assert_true(
    choose_plan([{"id": "one"}], "missing") is None,
    "Missing configured plan should not silently fall back.",
)

missing_token = YnabClient("", opener=opener).list_plans()
assert_true(not missing_token.ok, "Missing token unexpectedly succeeded.")
assert_true("YNAB_ACCESS_TOKEN" in missing_token.message, "Missing token message was not actionable.")

auth_error = urllib.error.HTTPError("https://api.ynab.com/v1/plans", 401, "No token", {}, None)
auth = YnabClient("secret-token", opener=FakeOpener({"plans": auth_error})).list_plans()
assert_true(not auth.ok and auth.status_code == 401, "Auth error was not structured.")
assert_true("secret-token" not in auth.message, "Auth message leaked the token.")

not_found_error = urllib.error.HTTPError("https://api.ynab.com/v1/plans/missing", 404, "Missing", {}, None)
not_found = YnabClient("secret-token", opener=FakeOpener({"plans/missing": not_found_error})).get_plan("missing")
assert_true(not not_found.ok and not_found.status_code == 404, "404 was not structured.")

rate_error = urllib.error.HTTPError("https://api.ynab.com/v1/plans", 429, "Slow down", {}, None)
rate = YnabClient("secret-token", opener=FakeOpener({"plans": rate_error})).list_plans()
assert_true(not rate.ok and rate.status_code == 429, "Rate limit error was not structured.")

malformed = YnabClient("secret-token", opener=FakeOpener({"plans": FakeResponse(b"{")})).list_plans()
assert_true(not malformed.ok, "Malformed JSON unexpectedly succeeded.")
assert_true("not valid JSON" in malformed.message, "Malformed JSON message was not actionable.")

timeout = YnabClient("secret-token", opener=FakeOpener({"plans": TimeoutError()})).list_plans()
assert_true(not timeout.ok, "Timeout unexpectedly succeeded.")
assert_true("timed out" in timeout.message, "Timeout message was not actionable.")

url_error = YnabClient(
    "secret-token",
    opener=FakeOpener({"plans": urllib.error.URLError("token=secret-token")}),
).list_plans()
assert_true(not url_error.ok, "URL error unexpectedly succeeded.")
assert_true("secret-token" not in url_error.message, "URL error leaked secret detail.")

missing_list = YnabClient(
    "secret-token",
    opener=FakeOpener({"plans/plan-1/accounts": FakeResponse({"data": {"wrong": []}})}),
).list_accounts("plan-1")
assert_true(not missing_list.ok, "Missing list response unexpectedly succeeded.")
assert_true("'accounts' list" in missing_list.message, "Missing list message was not actionable.")

print("YNAB API validation passed.")
