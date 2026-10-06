from __future__ import annotations

import os

from delirium_watch.config import get_settings
from delirium_watch.logging import configure_logging


def test_settings_point_at_committed_sample_dir() -> None:
    settings = get_settings()
    assert (settings.sample_dir / "README.md").is_file()
    assert (settings.research_dir / "run_all.py").is_file()


def test_configure_logging_does_not_raise() -> None:
    configure_logging()
    os.environ["DELIRIUM_WATCH_ENV"] = "prod"
    try:
        configure_logging()
    finally:
        os.environ.pop("DELIRIUM_WATCH_ENV", None)
    configure_logging()
