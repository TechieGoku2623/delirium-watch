"""Evaluation metrics. No scikit-learn; keep the dependency surface small."""

from __future__ import annotations

from collections.abc import Sequence
from math import exp


def _pairs(y_true: Sequence[int], scores: Sequence[float]) -> list[tuple[int, float]]:
    if len(y_true) != len(scores):
        raise ValueError("y_true and scores must be the same length")
    return list(zip(y_true, scores, strict=True))


def brier_score(y_true: Sequence[int], probs: Sequence[float]) -> float:
    if not y_true:
        return 0.0
    return sum((p - y) ** 2 for y, p in _pairs(y_true, probs)) / len(y_true)


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + exp(-x))
    z = exp(x)
    return z / (1.0 + z)


def auprc(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """Average precision (area under the precision-recall curve)."""

    n = len(y_true)
    if n == 0:
        return 0.0
    n_pos = sum(y_true)
    if n_pos == 0:
        return 0.0
    order = sorted(range(n), key=lambda i: (-scores[i], -y_true[i]))
    tp = 0
    fp = 0
    prev_recall = 0.0
    area = 0.0
    prev_score: float | None = None
    for idx in order:
        score = scores[idx]
        if prev_score is not None and score != prev_score:
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / n_pos
            area += precision * (recall - prev_recall)
            prev_recall = recall
        if y_true[idx] == 1:
            tp += 1
        else:
            fp += 1
        prev_score = score
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / n_pos
    area += precision * (recall - prev_recall)
    return area


def auroc(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """Mann–Whitney AUROC. Secondary to AUPRC."""

    pos = [s for y, s in _pairs(y_true, scores) if y == 1]
    neg = [s for y, s in _pairs(y_true, scores) if y == 0]
    if not pos or not neg:
        return 0.0
    better = 0.0
    for p in pos:
        for n_score in neg:
            if p > n_score:
                better += 1.0
            elif p == n_score:
                better += 0.5
    return better / (len(pos) * len(neg))


def reliability_bins(
    y_true: Sequence[int],
    probs: Sequence[float],
    n_bins: int = 5,
) -> list[dict[str, float]]:
    if not y_true:
        return []
    out: list[dict[str, float]] = []
    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        members = [k for k, p in enumerate(probs) if (p >= lo if i == 0 else p > lo) and p <= hi]
        if not members:
            out.append(
                {"bin": float(i), "lo": lo, "hi": hi, "n": 0.0, "mean_p": 0.0, "mean_y": 0.0}
            )
            continue
        out.append(
            {
                "bin": float(i),
                "lo": lo,
                "hi": hi,
                "n": float(len(members)),
                "mean_p": sum(probs[k] for k in members) / len(members),
                "mean_y": sum(y_true[k] for k in members) / len(members),
            }
        )
    return out


def alert_burden(
    y_true: Sequence[int],
    probs: Sequence[float],
    *,
    threshold: float,
    patient_days: float,
) -> dict[str, float]:
    alerts = [1 if p >= threshold else 0 for p in probs]
    n_alert = sum(alerts)
    tp = sum(1 for a, y in zip(alerts, y_true, strict=True) if a and y)
    ppv = tp / n_alert if n_alert else 0.0
    per_100 = (n_alert / patient_days * 100.0) if patient_days > 0 else 0.0
    return {
        "threshold": threshold,
        "n_alert": float(n_alert),
        "tp": float(tp),
        "ppv": ppv,
        "alarms_per_100_patient_days": per_100,
    }
