"""Write Phase 3 evaluation artefacts from the synthetic cohort."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from delirium_watch.cohort import load_cohort
from delirium_watch.evaluate import evaluate_cohort, format_eval_text

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


def main() -> None:
    cohort = load_cohort()
    payload = evaluate_cohort(cohort)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "results.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    text = format_eval_text(payload)
    (RESULTS / "results.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.exit(main())
