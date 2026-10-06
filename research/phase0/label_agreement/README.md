# label_agreement

## What is measured

Pairwise percent agreement and Cohen's kappa between three delirium labels
on the synthetic cohort: CAM-ICU-like assessments, antipsychotic
administration, and restraint orders. Comfort-care stays are excluded.

## Why it decides something

If the three labels disagree substantially (mean kappa < 0.60), label
choice dominates every downstream discrimination and calibration number.
Phase 2 cannot pick a silent primary label.

## How to run

```bash
uv run python research/phase0/label_agreement/run.py
```

Seed: 0. The cohort is the committed synthetic generator, not MIMIC-IV.
