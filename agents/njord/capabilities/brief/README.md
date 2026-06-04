# Manual Financial Brief

## Purpose

Produce a manually runnable weekly-style financial brief from YNAB data without
requiring scheduling, event automation, or LLM narration.

The brief reuses Njord's deterministic read layers:

- normalized financial snapshots.
- spending review.
- review-needed detection.
- evidence-backed recommendations.

## Usage

From the repository root:

```powershell
python agents\njord\agent.py brief
```

After installing Njord:

```powershell
Njord brief
```

Natural-language routing:

```powershell
Njord "Give me a weekly financial brief."
```

## Output

The brief separates:

- observations.
- spending highlights.
- notable transactions.
- review items.
- suggested next actions.
- read-only boundaries.

## Constraints

- Read-only.
- No live API calls in validation tests.
- No LLM required.
- Recommendations are conservative review prompts, not automatic financial decisions.
