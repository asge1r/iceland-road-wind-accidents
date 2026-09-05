"""Shared mappings for the accident-type codes used in the thesis."""

from __future__ import annotations


SINGLE_VEHICLE_FAMILY = "Single vehicle: run-off-road, rollover, fall, or other"


def broad_accident_family(code: int) -> str:
    """Map a detailed accident code to a small interpretable family."""
    if 11 <= code <= 95:
        return SINGLE_VEHICLE_FAMILY
    if 111 <= code <= 160:
        return "Same direction: overtaking, lane change, or rear-end"
    if 211 <= code <= 280:
        return "Opposing, overtaking, or reversing vehicles"
    if 310 <= code <= 440:
        return "Turning and changes in direction"
    if 510 <= code <= 696:
        return "Junctions, roundabouts, and priority"
    if 710 <= code <= 743:
        return "Stopped or parked vehicles"
    if 810 <= code <= 880:
        return "Pedestrians and horse riders"
    if 910 <= code <= 999:
        return "Animals, fixed objects, and other events"
    if 1090 <= code <= 1095:
        return "Bicycles"
    return "Unclassified"
