"""Analysis eligibility, distinct from the broader cleaned archive domain."""

import numpy as np

MIN_TEMPERATURE_C = -30.0
MAX_TEMPERATURE_C = 30.0


def valid_temperature(values):
    """Accept finite temperatures in the thesis's inclusive [-30, 30] °C range."""
    return (
        np.isfinite(values)
        & (values >= MIN_TEMPERATURE_C)
        & (values <= MAX_TEMPERATURE_C)
    )
