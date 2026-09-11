"""Calculate weather-frequency observed/expected ratios for defined samples."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.weather.frequency import labels


PRIMARY_MAX_TIME_DIFFERENCE_MINUTES = 5
DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_FREQUENCY = Path("data/analysis/weather_frequency.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/weather_oe.csv")
F_UPPER_BOUNDS = np.array([5, 10, 15, 20], dtype=float)
FG_UPPER_BOUNDS = np.array([5, 10, 15, 20, 25, 30], dtype=float)
TEMPERATURE_THRESHOLDS = np.array([-6, -3, 0, 3, 6, 9, 12], dtype=float)
TEMPERATURE_LABELS = [
    "<-6",
    "-6--3",
    "-3-0",
    "0-3",
    "3-6",
    "6-9",
    "9-12",
    ">=12",
]
BIN_MERGES = {
    ("f", "20-25"): ">=20",
    ("f", ">=25"): ">=20",
    ("fg", "30-35"): ">=30",
    ("fg", ">=35"): ">=30",
    ("temperature", "12-15"): ">=12",
    ("temperature", ">=15"): ">=12",
}

PERIODS = {
    "All seasons": "All year",
    "Winter": "Winter",
    "Spring": "Spring",
    "Summer": "Summer",
    "Fall": "Autumn",
}
OUTCOMES = {
    "Injury accidents": "All injury accidents",
    "Severe or fatal": "Severe/fatal accidents",
}


@dataclass(frozen=True)
class VariableSpec:
    """Columns and intervals required to analyse one weather variable."""

    variable: str
    accident_column: str
    upper_bounds: np.ndarray
    station_column: str = "weather_station_id"
    distance_column: str = "weather_station_dist_km"
    time_difference_column: str = "weather_time_difference_minutes"
    custom_bin_labels: tuple[str, ...] | None = None
    custom_bin_edges: tuple[float, ...] | None = None

    @property
    def bin_labels(self) -> list[str]:
        if self.custom_bin_labels is not None:
            return list(self.custom_bin_labels)
        return labels(self.upper_bounds)

    @property
    def bin_edges(self) -> list[float]:
        if self.custom_bin_edges is not None:
            return list(self.custom_bin_edges)
        return [0, *self.upper_bounds, np.inf]


VARIABLES = [
    VariableSpec("f", "f", F_UPPER_BOUNDS),
    VariableSpec("fg", "fg", FG_UPPER_BOUNDS),
    VariableSpec(
        "temperature",
        "temperature_c",
        TEMPERATURE_THRESHOLDS,
        station_column="temp_station_id",
        distance_column="temp_distance_km",
        time_difference_column="temp_time_diff_min",
        custom_bin_labels=tuple(TEMPERATURE_LABELS),
        custom_bin_edges=(-np.inf, *TEMPERATURE_THRESHOLDS, np.inf),
    ),
]
SAMPLES = {
    "Injury accidents": lambda data: pd.Series(True, index=data.index),
    "Minor injury": lambda data: data["meidsli"].eq(3),
    "Severe or fatal": lambda data: data["meidsli"].le(2),
}


def read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Read an inspectable analysis CSV and reject other input formats."""
    if path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {path}")
    return pd.read_csv(path, usecols=columns)


def prepare_frequency(frequency: pd.DataFrame) -> pd.DataFrame:
    """Validate the tidy frequency input and combine its upper bins."""
    required = {
        "station",
        "season",
        "variable",
        "bin_label",
        "measurement_count",
        "total_measurements_in_period",
    }
    missing = required - set(frequency)
    if missing:
        raise ValueError(
            f"Frequency table is missing required columns: {sorted(missing)}"
        )

    group_columns = [
        "station",
        "season",
        "variable",
        "bin_label",
        "total_measurements_in_period",
    ]
    if "year" in frequency:
        group_columns.insert(1, "year")
    result = frequency[[*group_columns, "measurement_count"]].copy()
    for (variable, old_label), new_label in BIN_MERGES.items():
        selected = result["variable"].eq(variable) & result["bin_label"].eq(
            old_label
        )
        result.loc[selected, "bin_label"] = new_label
    result = result.groupby(
        group_columns, as_index=False, observed=True, sort=False
    )["measurement_count"].sum()
    result["frequency_pct"] = (
        100
        * result["measurement_count"]
        / result["total_measurements_in_period"]
    )

    valid_labels = {spec.variable: set(spec.bin_labels) for spec in VARIABLES}
    for variable, found in result.groupby("variable")["bin_label"]:
        unexpected = set(found) - valid_labels.get(variable, set())
        if unexpected:
            raise ValueError(
                f"Unexpected bins for {variable}: {sorted(unexpected)}"
            )
    return result


def load_data(
    accidents_path: Path,
    conditions_path: Path,
    frequency_path: Path,
    start: str | None,
    end: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and combine the compact inputs used by O/E analyses."""
    event_columns = ["id", "timestamp", "meidsli", "season"]
    condition_columns = [
        "id",
        "weather_station_id",
        "weather_station_dist_km",
        "weather_time_difference_minutes",
        "f",
        "fg",
        "temp_station_id",
        "temp_distance_km",
        "temp_time_diff_min",
        "temperature_c",
    ]
    events = read_csv(accidents_path, event_columns)
    conditions = read_csv(conditions_path, condition_columns)
    if not events["id"].is_unique or not conditions["id"].is_unique:
        raise ValueError("Accident event and condition IDs must each be unique")
    accidents = events.merge(
        conditions, on="id", how="left", validate="one_to_one"
    )
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"])
    if start:
        accidents = accidents[accidents["timestamp"].ge(pd.Timestamp(start))]
    if end:
        accidents = accidents[accidents["timestamp"].le(pd.Timestamp(end))]
    accidents = accidents.copy()
    accidents["year"] = accidents["timestamp"].dt.year

    frequency = prepare_frequency(read_csv(frequency_path))
    frequency = frequency.rename(columns={"station": "weather_station_id"})
    frequency["weather_station_id"] = pd.to_numeric(
        frequency["weather_station_id"], errors="raise"
    ).astype(int)
    return accidents, frequency


def station_frequency_scenario(
    accidents: pd.DataFrame,
    frequency: pd.DataFrame,
    spec: VariableSpec,
    radius: int,
    severity: str,
    analysis_season: str,
    max_time_difference_minutes: float = PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Build observed and expected counts for one station-frequency scenario."""
    scoped = accidents[
        accidents[spec.distance_column].le(radius)
        & accidents[spec.time_difference_column].le(max_time_difference_minutes)
        & accidents[spec.accident_column].notna()
        & accidents[spec.station_column].notna()
        & SAMPLES[severity](accidents)
    ].copy()
    if analysis_season != "All seasons":
        scoped = scoped[scoped["season"].eq(analysis_season)].copy()

    # All variables use this internal name after their independent match.
    scoped["weather_station_id"] = scoped[spec.station_column].astype(int)
    scoped["weather_bin"] = pd.cut(
        scoped[spec.accident_column],
        bins=spec.bin_edges,
        labels=spec.bin_labels,
        right=False,
        include_lowest=True,
        ordered=True,
    )
    scoped = scoped.dropna(subset=["weather_bin"])

    group_columns = ["weather_station_id", "season"]
    if "year" in frequency.columns:
        group_columns.append("year")
    group_totals = (
        scoped.groupby(group_columns, observed=False)["id"]
        .nunique()
        .rename("group_accidents")
        .reset_index()
    )
    observed = (
        scoped.groupby([*group_columns, "weather_bin"], observed=False)["id"]
        .nunique()
        .rename("observed_accidents")
        .reset_index()
    )
    background = frequency[frequency["variable"].eq(spec.variable)][
        [
            *group_columns,
            "bin_label",
            "measurement_count",
            "total_measurements_in_period",
            "frequency_pct",
        ]
    ].rename(columns={"bin_label": "weather_bin"})
    if background.duplicated([*group_columns, "weather_bin"]).any():
        raise ValueError(
            f"Duplicate background bins found for variable {spec.variable}"
        )
    frequency_totals = background.groupby(group_columns)["frequency_pct"].sum()
    bad = ~np.isclose(frequency_totals.to_numpy(float), 100.0, atol=1e-6)
    if bad.any():
        examples = frequency_totals[bad].head().to_dict()
        raise ValueError(
            f"Background frequencies for {spec.variable} do not sum to 100%; "
            f"examples={examples}"
        )

    details = group_totals.merge(
        background, on=group_columns, how="inner", validate="one_to_many"
    ).merge(
        observed,
        on=[*group_columns, "weather_bin"],
        how="left",
        validate="one_to_one",
    )
    details["observed_accidents"] = (
        details["observed_accidents"].fillna(0).astype(int)
    )
    details["expected_accidents"] = (
        details["group_accidents"] * details["frequency_pct"] / 100
    )
    details["variable"] = spec.variable
    details["radius_km"] = radius
    details["severity_group"] = severity
    details["analysis_season"] = analysis_season
    details["max_time_difference_minutes"] = max_time_difference_minutes

    result = (
        details.groupby("weather_bin", as_index=False, sort=False)
        .agg(
            observed_accidents=("observed_accidents", "sum"),
            expected_accidents=("expected_accidents", "sum"),
            background_measurements=("measurement_count", "sum"),
            station_periods=("group_accidents", "size"),
            stations=("weather_station_id", "nunique"),
        )
    )
    result["relative_accident_frequency"] = (
        result["observed_accidents"] / result["expected_accidents"]
    )
    result["sparse_bin"] = result["observed_accidents"].lt(20)
    result["variable"] = spec.variable
    result["radius_km"] = radius
    result["severity_group"] = severity
    result["analysis_season"] = analysis_season
    result["max_time_difference_minutes"] = max_time_difference_minutes
    result["bin_order"] = result["weather_bin"].map(
        {label: index for index, label in enumerate(spec.bin_labels)}
    )

    analysed_ids = details[group_columns].drop_duplicates().merge(
        scoped[["id", *group_columns]], on=group_columns, how="inner"
    )["id"].nunique()
    coverage = {
        "variable": spec.variable,
        "radius_km": radius,
        "severity_group": severity,
        "analysis_season": analysis_season,
        "max_time_difference_minutes": max_time_difference_minutes,
        "eligible_accidents": len(scoped),
        "analysed_accidents": int(analysed_ids),
        "coverage_pct": 100 * analysed_ids / len(scoped) if len(scoped) else np.nan,
        "expected_sum": details["expected_accidents"].sum(),
        "observed_sum": details["observed_accidents"].sum(),
    }
    return result, details, coverage


def analyse(
    accidents: pd.DataFrame,
    frequency: pd.DataFrame,
    max_distance_km: float = 20,
    max_time_difference_minutes: float = PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
) -> pd.DataFrame:
    """Return the bar heights and supporting values for all requested panels."""
    results: list[pd.DataFrame] = []
    for spec in VARIABLES:
        for severity, outcome in OUTCOMES.items():
            for analysis_season, period in PERIODS.items():
                result, _, coverage = station_frequency_scenario(
                    accidents,
                    frequency,
                    spec,
                    max_distance_km,
                    severity,
                    analysis_season,
                    max_time_difference_minutes=max_time_difference_minutes,
                )
                observed_total = int(result["observed_accidents"].sum())
                expected_total = float(result["expected_accidents"].sum())
                analysed_total = int(coverage["analysed_accidents"])
                if observed_total != analysed_total or not np.isclose(
                    expected_total, analysed_total, atol=1e-6
                ):
                    raise ValueError(
                        "Observed and expected bins do not reconstruct the "
                        f"{spec.variable}, {severity}, {analysis_season} sample"
                    )
                result = result.rename(
                    columns={
                        "weather_bin": "bin_label",
                        "stations": "contributing_stations",
                    }
                )
                result["outcome"] = outcome
                result["period"] = period
                result["analysed_accidents"] = coverage["analysed_accidents"]
                result["max_distance_km"] = max_distance_km
                results.append(result)

    output = pd.concat(results, ignore_index=True)
    variable_order = {
        spec.variable: index for index, spec in enumerate(VARIABLES)
    }
    outcome_order = {name: index for index, name in enumerate(OUTCOMES.values())}
    period_order = {name: index for index, name in enumerate(PERIODS.values())}
    output["_variable_order"] = output["variable"].map(variable_order)
    output["_outcome_order"] = output["outcome"].map(outcome_order)
    output["_period_order"] = output["period"].map(period_order)
    output = output.sort_values(
        ["_variable_order", "_outcome_order", "_period_order", "bin_order"]
    )
    columns = [
        "variable",
        "outcome",
        "period",
        "bin_label",
        "bin_order",
        "observed_accidents",
        "expected_accidents",
        "relative_accident_frequency",
        "analysed_accidents",
        "contributing_stations",
        "background_measurements",
        "sparse_bin",
        "max_distance_km",
        "max_time_difference_minutes",
    ]
    return output[columns].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-C", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-f", "--frequency", type=Path, default=DEFAULT_FREQUENCY)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20)
    parser.add_argument(
        "-t",
        "--max-time-difference-minutes",
        type=float,
        default=PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
    )
    parser.add_argument("-s", "--start")
    parser.add_argument("-e", "--end")
    args = parser.parse_args()

    accidents, frequency = load_data(
        args.accidents, args.conditions, args.frequency, args.start, args.end
    )
    result = analyse(
        accidents,
        frequency,
        max_distance_km=args.max_distance_km,
        max_time_difference_minutes=args.max_time_difference_minutes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    scenarios = result[["variable", "outcome", "period"]].drop_duplicates()
    print(
        f"wrote={args.output} rows={len(result):,} "
        f"scenarios={len(scenarios):,}"
    )


if __name__ == "__main__":
    main()
