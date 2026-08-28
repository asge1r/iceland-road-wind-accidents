"""Small shared formatting helpers for thesis figures."""

from __future__ import annotations

import re

import pandas as pd


NUMBER_RANGE = re.compile(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$")


def interval_label(value: object) -> str:
    """Return a publication-style interval label."""
    label = str(value)
    if label.startswith(">="):
        return "≥" + label[2:].replace("-", "−")
    if label.startswith("<-"):
        return "<−" + label[2:]
    match = NUMBER_RANGE.fullmatch(label)
    if match:
        lower, upper = match.groups()
        return f"{lower.replace('-', '−')}–{upper.replace('-', '−')}"
    return label


def interval_labels(values: pd.Series) -> pd.Series:
    """Format a series of stored interval labels for display only."""
    return values.astype("string").map(interval_label)
