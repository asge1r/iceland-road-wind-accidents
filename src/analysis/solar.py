"""Calculate approximate solar elevation and daylight classes in Iceland."""

from __future__ import annotations

import numpy as np
import pandas as pd


DAYLIGHT_BINS = [-np.inf, -6, 0, np.inf]
DAYLIGHT_LABELS = ["Darkness", "Civil twilight", "Daylight"]


def solar_elevation(
    timestamp: pd.Series, latitude: pd.Series, longitude: pd.Series
) -> np.ndarray:
    """Return approximate solar elevation for Icelandic local time (UTC)."""
    time = pd.to_datetime(timestamp, errors="raise")
    day = time.dt.dayofyear.to_numpy(float)
    hour = (
        time.dt.hour.to_numpy(float)
        + time.dt.minute.to_numpy(float) / 60
        + time.dt.second.to_numpy(float) / 3600
    )
    gamma = 2 * np.pi / 365 * (day - 1 + (hour - 12) / 24)
    equation_of_time = 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2 * gamma)
        - 0.040849 * np.sin(2 * gamma)
    )
    declination = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2 * gamma)
        + 0.000907 * np.sin(2 * gamma)
        - 0.002697 * np.cos(3 * gamma)
        + 0.00148 * np.sin(3 * gamma)
    )
    solar_minutes = hour * 60 + equation_of_time + 4 * longitude.to_numpy(float)
    hour_angle = np.radians(solar_minutes / 4 - 180)
    lat_radians = np.radians(latitude.to_numpy(float))
    cosine_zenith = (
        np.sin(lat_radians) * np.sin(declination)
        + np.cos(lat_radians) * np.cos(declination) * np.cos(hour_angle)
    )
    return 90 - np.degrees(np.arccos(np.clip(cosine_zenith, -1, 1)))


def daylight_class(elevation: pd.Series | np.ndarray) -> pd.Series:
    """Classify solar elevation as darkness, civil twilight, or daylight."""
    return pd.cut(
        elevation,
        bins=DAYLIGHT_BINS,
        labels=DAYLIGHT_LABELS,
        right=False,
    ).astype("string")
