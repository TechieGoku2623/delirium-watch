# Phase 0 harnesses

`make research` runs these in order:

1. `label_agreement/run.py` — pairwise agreement of CAM-ICU, antipsychotic, restraint
2. `base_rate/run.py` — class balance, exclusions, event timing, horizon parameter
3. `leakage_audit/run.py` — inject post-cutoff data; pipeline must reject it
4. `render_docs.py` — write `docs/phase-0/research-memo.md`, `docs/EVALUATION.md`, and the measured tables in `README.md`

No number in the memo is typed by hand. If a quantity cannot be produced here, the memo says **unmeasured** and names the measurement that would settle it.
