# leakage_audit

## What is measured

Whether `leakage_safe_window` rejects post-cutoff events, naming the
offending feature and timestamp. P005 already carries a deliberate
`heart_rate` at icu_intime+30h. The harness also injects a fresh
post-cutoff event into P001.

## Why it decides something

This is built before any model. A leaky feature window makes every later
AUPRC uninterpretable. Non-zero exit if a post-cutoff event is placed in
`used`.

## How to run

```bash
uv run python research/phase0/leakage_audit/run.py
```
