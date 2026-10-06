"""Pairwise agreement across the three competing label definitions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from delirium_watch.labels import cohen_kappa, percent_agreement


def compare_label_rows(rows: Sequence[dict[str, object]]) -> dict[str, Any]:
    """Compute pairwise kappa on included (not excluded) parquet rows."""

    included = [r for r in rows if not bool(r.get("excluded"))]
    pairs = (
        ("cam_icu", "antipsychotic"),
        ("cam_icu", "restraint"),
        ("antipsychotic", "restraint"),
    )
    table: list[dict[str, object]] = []
    kappas: list[float] = []
    for left, right in pairs:
        bits = [(bool(r[left]), bool(r[right])) for r in included]
        both = sum(1 for a, b in bits if a and b)
        left_only = sum(1 for a, b in bits if a and not b)
        right_only = sum(1 for a, b in bits if (not a) and b)
        neither = sum(1 for a, b in bits if (not a) and not b)
        kappa = cohen_kappa(bits)
        kappas.append(kappa)
        table.append(
            {
                "pair": f"{left} vs {right}",
                "n": len(bits),
                "both+": both,
                "left_only": left_only,
                "right_only": right_only,
                "neither": neither,
                "agreement": percent_agreement(bits),
                "kappa": kappa,
            }
        )
    mean_kappa = sum(kappas) / len(kappas) if kappas else 0.0
    n_cam = sum(1 for r in included if bool(r["cam_icu"]))
    n_ap = sum(1 for r in included if bool(r["antipsychotic"]))
    n_re = sum(1 for r in included if bool(r["restraint"]))
    n_excl = sum(1 for r in rows if bool(r.get("excluded")))
    return {
        "n_raw": len(rows),
        "n_included": len(included),
        "n_excluded": n_excl,
        "prevalence": {
            "cam_icu": n_cam / len(included) if included else 0.0,
            "antipsychotic": n_ap / len(included) if included else 0.0,
            "restraint": n_re / len(included) if included else 0.0,
        },
        "pairs": table,
        "mean_kappa": mean_kappa,
        "label_choice_dominates": mean_kappa < 0.60,
    }
