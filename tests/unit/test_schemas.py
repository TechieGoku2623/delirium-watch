from __future__ import annotations

import pytest
from pydantic import ValidationError

from delirium_watch.schemas import PredictionConfig


def test_prediction_config_defaults() -> None:
    cfg = PredictionConfig()
    assert cfg.horizon_hours == 12
    assert cfg.reject_leakage is True


def test_prediction_config_rejects_unknown_horizon() -> None:
    with pytest.raises(ValidationError):
        PredictionConfig(horizon_hours=48)  # type: ignore[arg-type]
