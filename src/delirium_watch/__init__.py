"""delirium-watch: multimodal early warning for ICU delirium onset.

Retrospective research on de-identified or synthetic data. Not for clinical
deployment. Not a medical device. Not a diagnostic.
"""

__version__ = "0.1.0"

SAFETY_DISCLAIMER = (
    "Research tool only. Retrospective analysis on synthetic or de-identified "
    "data. This is not a medical device, not a diagnostic, and not for "
    "clinical deployment."
)

HORIZONS_HOURS: tuple[int, ...] = (6, 12, 24)
