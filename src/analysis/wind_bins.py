"""Fixed wind intervals shared by compact-data analysis scripts."""

import numpy as np

F_UPPER_BOUNDS = np.arange(3, 25, 3, dtype=float)
FG_UPPER_BOUNDS = np.arange(3, 37, 3, dtype=float)
FG_MINUS_F_UPPER_BOUNDS = np.array([2, 4, 6, 8, 10, 12, 14, 16, 18, 20], dtype=float)


def labels(upper_bounds: np.ndarray) -> list[str]:
    lower = np.concatenate(([0.0], upper_bounds[:-1]))
    return [f"{lo:g}-{hi:g}" for lo, hi in zip(lower, upper_bounds, strict=True)] + [f">={upper_bounds[-1]:g}"]
