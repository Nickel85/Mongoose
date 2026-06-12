# Njord YNAB Write Safety Model

This document defines the safety contract for future Njord capabilities that
prepare or execute YNAB write operations. It is intentionally design-only: no
write executor is implemented by this roadmap slice.

## Safety Principles

- Natural-language requests must never mutate YNAB directly.
- Njord must separate read analysis, draft recommendations, proposed write
  plans, approved plans, executed writes, and reconciliation records.
- Every write batch requires explicit user approval before execution.
- Every executable plan must include source evidence, before/after values,
  risk classification, preconditions, approval text, idempotency keys, and an
  audit record shape.
- Unsupported, stale, ambiguous, or high-risk requests fail closed.
- Secrets such as `YNAB_ACCESS_TOKEN` must never be stored in plans, approvals,
  audit records, logs, or reconciliation records.

## Lifecycle States

| State | Meaning | May write to YNAB |
| --- | --- | --- |
| Draft recommendation | Read-only guidance generated from YNAB state, review flags, spending summaries, or user intent. | No |
| Proposed write plan | Structured dry-run plan containing one or more candidate changes, evidence, risk, and required approval text. | No |
| Approved plan | Proposed plan with explicit user approval of the exact batch, target resources, and before/after values. | No |
| Executed write | Approved plan that passed stale-state and policy checks, then produced YNAB write request/response metadata. | Yes |
| Reconciliation record | Post-write comparison of intended changes against current YNAB state. | No |

## Supported Write Operation Classes

Future implementations may support these operation classes only after they are
represented in a proposed write plan and approved by the user.

| Operation class | Initial risk | Required preconditions | Required approval text |
| --- | --- | --- | --- |
| Category budget adjustment | Medium | Current month, category ID, category name, current assigned amount, proposed assigned amount, amount delta, source snapshot timestamp, and reason. | "Approve assigning `<delta>` to `<category>` for `<month>`, changing assigned from `<before>` to `<after>`." |
| Money movement between categories | Medium | Source category ID/name, destination category ID/name, current balances, transfer amount, source remains non-negative unless explicitly allowed, destination need, source snapshot timestamp, and reason. | "Approve moving `<amount>` from `<source>` to `<destination>` for `<month>`." |
| New-money allocation | Medium | Current ready-to-assign amount, destination category ID/name, current assigned/balance, allocation amount, remaining ready-to-assign estimate, source snapshot timestamp, and reason. | "Approve allocating `<amount>` of ready-to-assign money to `<category>` for `<month>`." |
| Transaction category update | Medium | Transaction ID, payee, date, amount, current category, proposed category, confidence evidence, and user-visible transaction identity. | "Approve changing transaction `<payee>` on `<date>` for `<amount>` from `<before>` to `<after>`." |
| Transaction memo update | Low | Transaction ID, payee, date, amount, current memo, proposed memo, and reason. | "Approve changing the memo for `<payee>` on `<date>` to `<after>`." |
| Scheduled transaction update | High | Scheduled transaction ID, payee, next date, amount, current fields, proposed fields, recurrence impact, and explicit reason. | "Approve changing scheduled transaction `<payee>` from `<before>` to `<after>`." |
| Account metadata update | High | Account ID/name, current metadata, proposed metadata, downstream impact, and explicit reason. | "Approve changing account `<account>` metadata from `<before>` to `<after>`." |

The first executor should start with one narrow low-risk or medium-risk
operation, preferably category budget adjustment or new-money allocation. It
must not combine unrelated operation classes in the first implementation.

## Prohibited Automatic Operations

Njord must not perform these operations automatically:

- Delete budgets, accounts, categories, transactions, scheduled transactions,
  payees, or months.
- Close accounts.
- Create debt, loan, or account metadata changes without a separate design.
- Move money out of categories marked as protected by user policy.
- Move money that would create or worsen overspending unless the user explicitly
  approves that exact negative outcome.
- Execute high-risk scheduled transaction or account metadata changes without a
  dedicated issue, tests, and expanded approval language.
- Execute any plan generated from stale YNAB state.
- Execute any write from a natural-language command that has not produced an
  approved plan record.

## Proposed Write Plan Schema

Proposed write plans are local, private records. They should be serializable to
JSON and safe to display.

```json
{
  "schema_version": 1,
  "plan_id": "plan_20260611_001",
  "created_at": "2026-06-11T12:00:00Z",
  "expires_at": "2026-06-11T13:00:00Z",
  "budget_id": "ynab-budget-id",
  "budget_name": "Household",
  "source_snapshot": {
    "fetched_at": "2026-06-11T11:59:00Z",
    "etag": "optional-provider-state-token"
  },
  "request": {
    "user_intent": "allocate my new money",
    "route": "budget-maintenance-plan"
  },
  "risk": "medium",
  "status": "proposed",
  "operations": [
    {
      "operation_id": "op_001",
      "operation_class": "new_money_allocation",
      "risk": "medium",
      "resource": {
        "type": "category",
        "id": "category-groceries",
        "name": "Groceries"
      },
      "before": {
        "assigned": 250000,
        "balance": 50000,
        "ready_to_assign": 100000
      },
      "after": {
        "assigned": 300000,
        "balance": 100000,
        "ready_to_assign": 50000
      },
      "amount_delta": 50000,
      "currency": "USD",
      "evidence": [
        "Groceries has expected spending pressure this month.",
        "Ready-to-assign has enough available money."
      ],
      "rationale": "Allocate part of new money to near-term grocery pressure.",
      "expected_impact": "Groceries has more available money and ready-to-assign decreases.",
      "preconditions": [
        "ready_to_assign >= 50000",
        "category-groceries assigned amount is still 250000"
      ],
      "approval_text": "Approve allocating $50.00 of ready-to-assign money to Groceries for 2026-06."
    }
  ],
  "idempotency_key": "sha256-of-budget-plan-and-operations"
}
```

Amounts use YNAB milliunits in machine-readable fields. User-facing text should
format amounts as currency.

## Approval Record Schema

Approval records capture the user's decision about a proposed plan. Editing a
plan creates a new proposed plan ID; approval must apply to one exact plan.

```json
{
  "schema_version": 1,
  "approval_id": "approval_20260611_001",
  "plan_id": "plan_20260611_001",
  "decided_at": "2026-06-11T12:05:00Z",
  "decision": "approved",
  "decision_by": "local-user",
  "approved_operation_ids": ["op_001"],
  "approval_text": "Approve allocating $50.00 of ready-to-assign money to Groceries for 2026-06.",
  "plan_hash": "sha256-of-approved-plan",
  "expires_at": "2026-06-11T13:00:00Z"
}
```

Valid decisions are `approved`, `rejected`, `edited`, `deferred`, and
`expired`. Rejected, edited, deferred, and expired plans must not execute.

## Execution Preconditions

A future executor must verify all of these conditions before sending any YNAB
write request:

- The plan status is `approved`.
- The approval record references the exact plan hash and operation IDs.
- The plan has not expired.
- The operation class is supported by the executor.
- The current YNAB state still satisfies every operation precondition.
- The operation complies with user policy, including protected categories and
  maximum amount thresholds.
- The idempotency key has not already produced a successful write.
- The audit record can be written locally before or atomically with execution
  metadata.

If any condition fails, the executor must refuse to write and produce an
actionable failure record.

## Audit Record Schema

Audit records make every write traceable from analysis to approval to provider
response. They must not include access tokens or unnecessary sensitive data.

```json
{
  "schema_version": 1,
  "audit_id": "audit_20260611_001",
  "plan_id": "plan_20260611_001",
  "approval_id": "approval_20260611_001",
  "operation_id": "op_001",
  "started_at": "2026-06-11T12:06:00Z",
  "completed_at": "2026-06-11T12:06:02Z",
  "operation_class": "new_money_allocation",
  "risk": "medium",
  "budget_id": "ynab-budget-id",
  "resource": {
    "type": "category",
    "id": "category-groceries",
    "name": "Groceries"
  },
  "before": {
    "assigned": 250000,
    "balance": 50000,
    "ready_to_assign": 100000
  },
  "after_intended": {
    "assigned": 300000,
    "balance": 100000,
    "ready_to_assign": 50000
  },
  "provider_request": {
    "method": "PATCH",
    "path": "/budgets/{budget_id}/months/{month}/categories/{category_id}",
    "body_hash": "sha256-of-redacted-body"
  },
  "provider_response": {
    "status_code": 200,
    "request_id": "provider-request-id",
    "body_hash": "sha256-of-redacted-response"
  },
  "status": "succeeded",
  "idempotency_key": "sha256-of-budget-plan-and-operations"
}
```

Valid execution statuses are `refused`, `started`, `succeeded`, `failed`, and
`unknown`. Partial batches must record per-operation status.

## Reconciliation Record Schema

Reconciliation compares the intended result with current YNAB state after a
write attempt.

```json
{
  "schema_version": 1,
  "reconciliation_id": "reconcile_20260611_001",
  "audit_id": "audit_20260611_001",
  "checked_at": "2026-06-11T12:10:00Z",
  "status": "success",
  "expected": {
    "assigned": 300000,
    "balance": 100000
  },
  "actual": {
    "assigned": 300000,
    "balance": 100000
  },
  "differences": [],
  "notes": [
    "YNAB state matched the approved operation after execution."
  ]
}
```

Valid reconciliation statuses are `success`, `partial_success`, `drift`,
`failed`, and `unknown`.

## Dry-Run And Idempotency

- Proposed plans are always dry-run artifacts.
- Dry-run output must show what would change, why, and what approval text is
  required.
- Idempotency keys must be derived from the budget ID, operation class,
  resource IDs, before/after values, source snapshot marker, and plan hash.
- Retrying an operation with the same idempotency key must not create duplicate
  or conflicting writes.

## Rollback And Recovery

YNAB write operations should be treated as forward-only unless a future issue
defines a tested compensating action. For the first executor:

- Prefer refusal and regeneration over automatic rollback.
- If a write fails after a partial provider response, record `unknown` or
  `failed` and require reconciliation before another write attempt.
- If reconciliation finds drift, generate a new proposed plan rather than
  mutating state automatically.

## Implementation Gate For Later Issues

Issues that implement draft plans, approvals, write execution, reconciliation,
decision metrics, or auto-approval must preserve this sequence:

```text
read analysis
-> proposed write plan
-> explicit approval
-> stale-state and policy checks
-> guarded execution
-> audit record
-> reconciliation record
-> decision outcome metrics
```

Any implementation that bypasses this sequence is out of roadmap scope.
