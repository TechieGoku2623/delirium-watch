# base_rate

## What is measured

Cohort size before and after comfort-care exclusion, class balance under
each of the three labels, hours to first event, and the share of stays
that would be positive at the 6 / 12 / 24 hour prediction horizons.

## Why it decides something

A 24-hour horizon on a rare label is a different product from a 6-hour
horizon on a common one. Phase 2 cannot pick a horizon after seeing
model scores.

## How to run

```bash
uv run python research/phase0/base_rate/run.py
```

Queries the committed synthetic tables through DuckDB.
