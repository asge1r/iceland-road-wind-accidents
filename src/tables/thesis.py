"""Generate data-derived LaTeX tables used throughout the thesis."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT = Path("reports/thesis/generated")


def tex(value: object) -> str:
    text = str(value)
    replacements = {
        "&": r"\&", "%": r"\%", "_": r"\_", ">=": r"$\geq$",
        "–": "--", "−": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_table(
    path: Path,
    caption: str,
    label: str | None,
    columns: str,
    headers: list[str],
    rows: list[list[object]],
    size: str = "small",
    width: str | None = None,
) -> None:
    environment = "tabularx" if width else "tabular"
    begin = rf"\begin{{{environment}}}{{{width}}}{{{columns}}}" if width else rf"\begin{{{environment}}}{{{columns}}}"
    label_line = rf"\label{{{label}}}" if label else ""
    body = []
    for index, row in enumerate(rows):
        rule = r" \\ \grayhline" if index < len(rows) - 1 else r" \\"
        body.append(" & ".join(tex(value) for value in row) + rule)
    content = "\n".join(
        [
            r"\begin{table}[H]", r"\centering", rf"\{size}",
            rf"\caption{{{caption}}}", label_line, begin, r"\toprule",
            " & ".join(headers) + r" \\", r"\midrule", *body,
            r"\bottomrule", rf"\end{{{environment}}}", r"\end{table}", "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def interval(value: object) -> str:
    text = str(value)
    if text.startswith(">="):
        return rf"$\geq${text[2:]}"
    return text.replace("-", "--")


def estimate(row: pd.Series, estimate: str, low: str, high: str, prefix: str = "") -> str:
    return f"{prefix}{row[estimate]:.2f} ({row[low]:.2f}--{row[high]:.2f})"


def accident_sample(output: Path) -> None:
    path = Path("data/analysis/accidents.csv")
    data = pd.read_csv(path)
    required = {
        "id", "timestamp", "lat", "lon", "meidsli", "tegohapps",
        "road_section",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    timestamps = pd.to_datetime(data["timestamp"], errors="coerce")
    if timestamps.isna().any():
        raise ValueError(f"{path} contains invalid timestamps")
    sample = data.assign(_timestamp=timestamps).sort_values(
        ["_timestamp", "id"]
    ).head(10)
    rows = []
    for _, row in sample.iterrows():
        rows.append([
            int(row["id"]), row["_timestamp"].strftime("%Y-%m-%d"),
            row["_timestamp"].strftime("%H:%M"), f"{row['lat']:.4f}",
            f"{row['lon']:.4f}", int(row["meidsli"]),
            int(row["tegohapps"]),
            row["road_section"] if pd.notna(row["road_section"]) else "Missing",
        ])
    write_table(
        output / "accident_sample.tex",
        "First chronological records in the canonical rural injury-accident analysis file",
        "tab:accident-source-example",
        r"rL{0.11\textwidth}L{0.07\textwidth}rrrL{0.10\textwidth}X",
        [
            r"\texttt{id}", "Date", "Time", "Lat.", "Lon.",
            r"\texttt{meidsli}", r"\texttt{tegohapps}", "Road section",
        ],
        rows,
        size="scriptsize",
        width=r"\textwidth",
    )


def weather_cleaning(output: Path) -> None:
    data = pd.read_csv("data/analysis/weather_cleaning.csv")
    data = data[data["year"].astype(str).ne("total")]
    total = int(data["input_rows"].sum())
    outside_scope = int(data["no_wind_station_year"].sum())
    assessed = total - outside_scope
    categories = [
        ("All delivered station-time rows", "input_rows"),
        ("Rows in station-years containing wind data", None),
        (r"Missing \texttt{f} or \texttt{fg}", "missing_wind"),
        ("Negative or upper-threshold wind", None),
        (r"Internally inconsistent \texttt{f}/\texttt{fg}", None),
        (r"Frozen all-zero runs ($\geq 2$ hours)", "frozen_zero"),
        ("Clean wind observations retained", "clean_wind_rows"),
    ]
    invalid_range = int(data["negative"].sum() + data["upper_threshold"].sum())
    inconsistent = int(
        data["inconsistent_zero_gust"].sum() + data["gust_below_mean"].sum()
    )
    special = iter([assessed, invalid_range, inconsistent])
    rows = []
    for name, column in categories:
        value = int(data[column].sum()) if column else next(special)
        denominator = total if name == "All delivered station-time rows" else assessed
        rows.append([name, f"{value:,}", f"{100 * value / denominator:.2f}%"])
    scope_note = (
        f" {outside_scope:,} delivered rows from station-years without wind "
        "measurements are outside that scope."
        if outside_scope else
        " Every delivered station-year contains at least one wind measurement."
    )
    write_table(
        output / "weather_cleaning.tex",
        "Wind-data scope and quality audit, 2007--2025. Quality-rule shares use "
        "the rows in station-years containing wind data as their denominator."
        + scope_note,
        "tab:weather-cleaning", "lrr", ["Category", "Records", "Share"], rows,
    )


def coverage(output: Path) -> None:
    match = pd.read_csv("reports/main/tables/wind_coverage.csv")
    temp = pd.read_csv("reports/main/tables/temperature_coverage.csv").iloc[0]
    accidents = pd.read_csv("data/analysis/accidents.csv", usecols=["id", "year", "road_section"])
    annual = pd.read_csv("data/analysis/annual_traffic.csv", usecols=["year", "road_section"])
    accidents["road_section"] = accidents["road_section"].astype("string").str.strip().str.lower()
    annual["road_section"] = annual["road_section"].astype("string").str.strip().str.lower()
    exact = accidents.merge(annual.drop_duplicates(), on=["year", "road_section"], how="inner")["id"].nunique()
    rate = pd.read_csv("reports/main/tables/wind_rate.csv").iloc[0]
    selection = pd.read_csv("data/analysis/selection_summary.csv")
    daily_total = int(selection.loc[selection["step"].eq("counter_days"), "records"].iloc[0])
    daily_wind = int(selection.loc[selection["step"].eq("counter_days_with_daytime_wind"), "records"].iloc[0])
    allocated = pd.read_csv("reports/working/tables/allocated_rate_audit.csv").set_index("metric")["value"]
    full = pd.read_csv("reports/working/tables/day_rate_audit.csv").set_index("metric")["value"]
    total = int(match["scope_accidents"].max())
    rows = []
    for radius in [10, 20, 30]:
        row = match[match["radius_km"].eq(radius)].iloc[0]
        name = f"Wind match within {radius} km" + (" (primary)" if radius == 20 else "")
        rows.append([name, f"{int(row.analysed_accidents):,}", f"{total:,}", f"{row.coverage_pct:.2f}%"])
    rows.extend(
        [
            ["Temperature match within 20 km", f"{int(temp.temperature_available):,}", f"{total:,}", f"{temp.temperature_coverage_pct:.2f}%"],
            ["Exact annual road-section match, 2007--2025", f"{exact:,}", f"{total:,}", f"{100*exact/total:.2f}%"],
            ["Stratified accident-rate analysis", f"{int(rate.model_accidents):,}", f"{int(match.loc[match['radius_km'].eq(20), 'analysed_accidents'].iloc[0]):,}", f"{100*rate.model_accidents/int(match.loc[match['radius_km'].eq(20), 'analysed_accidents'].iloc[0]):.2f}%"],
            ["Daily counter-days with daytime wind", f"{daily_wind:,}", f"{daily_total:,}", f"{100*daily_wind/daily_total:.2f}%"],
            ["Allocated daily-counter rate, 2019--2024", f"{int(allocated['same_station_valid_daily_traffic_and_accident_wind']):,}", "1,863", f"{100*allocated['same_station_valid_daily_traffic_and_accident_wind']/1863:.2f}%"],
            ["Full-day-mean daily-counter check, 2019--2024", f"{int(full['with_valid_counter_day']):,}", "1,863", f"{100*full['with_valid_counter_day']/1863:.2f}%"],
        ]
    )
    write_table(
        output / "coverage.tex",
        "Coverage of the retained analyses. One counter-day is one physical counter site on one date. A counter-day with daytime wind has a matched station within 20 km and at least one valid ten-minute mean-wind observation between 10:00 and 21:59; its traffic value is still the observed 24-hour total.",
        "tab:coverage", "Xrrr",
        ["Analysis step", "Retained", "Starting set", "Share"], rows,
        width=r"\textwidth",
    )


def match_quality(output: Path) -> None:
    data = pd.read_csv("reports/main/tables/match_quality.csv")
    rows = []
    for row in data.itertuples(index=False):
        rows.append([
            row.weather_variable,
            f"{int(row.matched_accidents):,}",
            f"{row.matched_pct:.1f}%",
            f"{int(row.stations_used):,}",
            f"{row.median_distance_km:.1f} / {row.p90_distance_km:.1f}",
        ])
    write_table(
        output / "match_quality.tex",
        "Share of accidents with weather information from a station with a valid measurement within 20 km. Distance is shown as median / P90; every retained observation is within five minutes of the accident time.",
        "tab:match-quality", "lrrrr",
        ["Variable", "Accidents", "Share", "Stations", "Distance (km)"],
        rows, size="footnotesize",
    )


def year_comparison(output: Path) -> None:
    yearly = pd.read_csv("reports/main/tables/year_oe.csv")
    pooled_sources = {
        "f": ("reports/main/tables/mean_wind_oe.csv", "mean_wind_interval_ms"),
        "temperature": (
            "reports/main/tables/temperature_oe.csv", "temperature_interval_c"
        ),
    }
    selected = {
        "f": ["15-20", "20-25", ">=25"],
        "temperature": ["-3-0", "0-3", "3-6"],
    }
    names = {"f": "Mean wind (m/s)", "temperature": "Temperature (deg C)"}
    rows = []
    for variable, intervals in selected.items():
        path, bin_column = pooled_sources[variable]
        pooled = pd.read_csv(path).set_index(bin_column)
        adjusted = yearly[yearly["variable"].eq(variable)].set_index("coarse_bin")
        for bin_label in intervals:
            first = pooled.loc[bin_label]
            second = adjusted.loc[bin_label]
            display_interval = interval(bin_label)
            rows.append([
                names[variable], display_interval,
                f"{int(second.observed_accidents):,}",
                estimate(
                    first, "observed_expected_ratio",
                    "station_bootstrap_ci_95_low", "station_bootstrap_ci_95_high"
                ),
                estimate(
                    second, "observed_expected_ratio",
                    "bootstrap_ci_95_low", "bootstrap_ci_95_high"
                ),
            ])
    write_table(
        output / "year_oe.tex",
        "Selected pooled and year-adjusted O/E estimates",
        "tab:year-oe", r"L{0.17\textwidth}L{0.09\textwidth}rL{0.27\textwidth}X",
        [
            "Variable", "Interval", "Observed",
            r"Station + season O/E (95\% interval)",
            r"Station + season + year O/E (95\% interval)",
        ],
        rows, size="footnotesize", width=r"\textwidth",
    )


def radius_tables(output: Path) -> None:
    wind = pd.read_csv("reports/main/tables/wind_radius.csv")
    rows = []
    for item in wind.itertuples(index=False):
        rows.append([
            f"{item.radius_km} km", "Yes" if item.primary_radius else "No",
            interval(item.coarse_bin), f"{item.observed_accidents:,}", f"{item.expected_accidents:.1f}",
            f"{item.relative_accident_frequency:.2f} ({item.bootstrap_ci_95_low:.2f}--{item.bootstrap_ci_95_high:.2f})",
        ])
    write_table(output / "mean_wind_radius.tex", "Primary mean-wind O/E under three weather-station distance limits", "tab:mean-wind-radius", "rrlrrr", ["Radius", "Primary", "Mean wind", "Observed", "Expected", r"O/E (95\% interval)"], rows)
    results = pd.read_csv("reports/main/tables/oe_results.csv")
    gust = results[
        results["variable"].eq("fg") & results["severity_group"].eq("Injury accidents")
        & results["analysis_season"].eq("All seasons") & results["coarse_bin"].eq(">=35")
        & results["radius_km"].isin([10, 20, 30])
    ].sort_values("radius_km")
    rows = [[
        f"{int(row.radius_km)} km" + (" (primary)" if row.radius_km == 20 else ""),
        f"{int(results[(results.variable.eq('fg')) & (results.radius_km.eq(row.radius_km)) & (results.severity_group.eq('Injury accidents')) & (results.analysis_season.eq('All seasons'))].observed_accidents.sum()):,}",
        f"{int(row.observed_accidents):,}", f"{row.relative_accident_frequency:.2f}",
        f"{row.bootstrap_ci_95_low:.2f}--{row.bootstrap_ci_95_high:.2f}",
    ] for row in gust.itertuples(index=False)]
    write_table(output / "gust_radius.tex", "Highest-gust result under three weather-station distance limits", "tab:radius-comparison", "rrrrr", ["Maximum distance", "Matched accidents", r"Observed at $\geq35$", "O/E", r"95\% interval"], rows)


def traffic_tables(output: Path) -> None:
    validation = pd.read_csv("data/analysis/counter_check.csv")
    locations = pd.read_csv("data/analysis/counter_locations.csv")
    matched = validation[validation["status"].eq("matched")]
    rows = [
        ["Counter-site years in analysis location table", f"{len(locations):,}"],
        ["Counter-site years located from road geometry", f"{locations['lon'].notna().sum():,}"],
        ["Distinct located counter sites", f"{locations.loc[locations['lon'].notna(), 'counter_id'].nunique():,}"],
        ["Sites matched to an official 20 m road-station point within 10 m", f"{len(matched):,}"],
        ["Median / 90th-percentile coordinate difference", f"{matched.coordinate_difference_m.median():.1f} / {matched.coordinate_difference_m.quantile(.9):.1f} m"],
    ]
    write_table(output / "counter_locations.tex", "Counter-location construction and independent coordinate check", None, "Xr", ["Check", "Result"], rows, width=r"0.9\textwidth")

    adu = pd.read_csv("reports/main/tables/counter_adu.csv")
    names = ["All exact matches", "At least 300 observed days", "At least 300 days, one counter per section"]
    rows = [[name, f"{int(row.counter_years):,}", f"{row.median_mean_to_adu_ratio:.3f}", f"{row.p10_mean_to_adu_ratio:.3f}--{row.p90_mean_to_adu_ratio:.3f}", f"{row.pearson_log_correlation:.3f}"] for name, row in zip(names, adu.itertuples(index=False), strict=True)]
    write_table(output / "adu_quality.tex", "Consistency of observed daily PDF traffic with official ADU", None, "Xrrrr", ["Data included", r"\(N\)", "Median", "P10--P90", r"\(r_{\log}\)"], rows, width=r"\textwidth")

    audit = pd.read_csv("reports/working/tables/day_rate_audit.csv").set_index("metric")["value"]
    rows = [
        ["Rural injury accidents in 2019--2024", f"{int(audit['rural_injury_accidents_2019_2024']):,}", "100.0%"],
        ["Exact road-section/year counter candidate", f"{int(audit['exact_road_section_counter_candidates']):,}", f"{100*audit['exact_road_section_counter_candidates']/audit['rural_injury_accidents_2019_2024']:.1f}%"],
        ["Assigned counter within 20 km", f"{int(audit['within_distance']):,}", f"{100*audit['within_distance']/audit['rural_injury_accidents_2019_2024']:.1f}%"],
        ["Positive count and valid full-day wind", f"{int(audit['with_valid_counter_day']):,}", f"{100*audit['with_valid_counter_day']/audit['rural_injury_accidents_2019_2024']:.1f}%"],
    ]
    write_table(output / "daily_selection.tex", "Selection of accidents for the observed daily-counter analysis", None, "Xrr", ["Selection step", "Accidents", "Share of 2019--2024 sample"], rows, width=r"0.86\textwidth")

    sample = pd.read_csv("reports/main/tables/daily_sample.csv").set_index("group")
    groups = [
        "All accidents", "No exact counter link", "Exact link, not retained",
        "Allocated-rate sample",
    ]
    headers = ["Characteristic", "All", "No link", "Linked, excluded", "Retained"]
    metrics = [
        ("Accidents", "accidents", lambda value: f"{int(value):,}"),
        ("Share of all accidents", "share_of_all_pct", lambda value: f"{value:.1f}%"),
        ("Distinct road sections", "road_sections", lambda value: f"{int(value):,}"),
        ("Serious or fatal", "serious_or_fatal_pct", lambda value: f"{value:.1f}%"),
        ("One vehicle", "one_vehicle_pct", lambda value: f"{value:.1f}%"),
        ("Winter", "winter_pct", lambda value: f"{value:.1f}%"),
        ("Spring", "spring_pct", lambda value: f"{value:.1f}%"),
        ("Summer", "summer_pct", lambda value: f"{value:.1f}%"),
        ("Autumn", "fall_pct", lambda value: f"{value:.1f}%"),
    ]
    rows = [
        [label, *[formatter(sample.loc[group, column]) for group in groups]]
        for label, column, formatter in metrics
    ]
    write_table(
        output / "daily_sample.tex",
        "Characteristics of accidents retained and excluded by the daily-counter linkage",
        None,
        "Xrrrr",
        headers,
        rows,
        size="footnotesize",
        width=r"\textwidth",
    )
    exclusions = pd.read_csv("reports/main/tables/daily_exclusions.csv")
    rows = [
        [row.reason, f"{int(row.accidents):,}", f"{row.share_of_all_pct:.1f}%"]
        for row in exclusions.itertuples(index=False)
    ]
    write_table(
        output / "daily_exclusions.tex",
        "Reasons an exact same-year daily-counter link was unavailable",
        None,
        "Xrr",
        ["Reason", "Accidents", "Share of all accidents"],
        rows,
        width=r"0.9\textwidth",
    )

    daily = pd.read_csv("reports/main/tables/day_rate.csv")
    rows = []
    for row in daily.itertuples(index=False):
        ratio = "1.00 (reference)" if row.wind_bin == "0-5" else f"{row.rate_ratio:.2f} ({row.ci_95_low:.2f}--{row.ci_95_high:,.2f})"
        rows.append([f"{interval(row.wind_bin)} m/s", f"{int(row.observed_accidents):,}", f"{int(row.observed_vehicles):,}", f"{int(row.counters):,}", ratio])
    write_table(output / "daily_rate.tex", "Detailed daily counter-based rural injury-accident rate comparison, 2019--2024", None, "lrrrr", ["Mean wind", "Accidents", "Counted vehicles", "Counters", r"Rate ratio (95\% CI)"], rows, size="footnotesize")

    radius = pd.read_csv("reports/main/tables/counter_radius.csv")
    radius = radius[radius["wind_bin"].eq(">=15")]
    rows = [[f"{int(row.max_counter_distance_km)} km", f"{int(row.with_valid_counter_day):,}", f"{int(row.observed_accidents):,}", f"{row.rate_ratio:.2f}", f"{row.ci_95_low:.2f}--{row.ci_95_high:.2f}"] for row in radius.itertuples(index=False)]
    write_table(output / "daily_radius.tex", "Upper daily-counter estimate under three assignment distances", None, "rrrrr", ["Maximum distance", "Included accidents", "Upper-bin accidents", "Rate ratio", r"95\% CI"], rows)

    absolute = pd.read_csv("reports/main/tables/absolute_rate.csv")
    rows = [[interval(row.wind_bin), f"{int(row.observed_accidents):,}", f"{row.rate_per_100m_vehicle_km:.1f}"] for row in absolute.itertuples(index=False)]
    write_table(output / "estimated_rate.tex", "Estimated rural injury-accident rate by mean wind speed, all traffic periods", "tab:estimated-rate", "lrr", ["Mean wind", "Accidents", "Estimated accidents per 100 million vehicle-km"], rows, size="footnotesize")

    full = pd.read_csv("reports/main/tables/wind_rate.csv")
    official = pd.read_csv("reports/working/tables/wind_rate_official.csv")
    rows = []
    for wind_bin in ["15-20", "20-25", ">=25"]:
        a = full[full["bin_label"].eq(wind_bin)].iloc[0]
        b = official[official["bin_label"].eq(wind_bin)].iloc[0]
        rows.append([interval(wind_bin), f"{estimate(a, 'time_proportional_rate_ratio', 'time_proportional_ci_95_low', 'time_proportional_ci_95_high')}, $n={int(a.observed_accidents)}$", f"{estimate(b, 'time_proportional_rate_ratio', 'time_proportional_ci_95_low', 'time_proportional_ci_95_high')}, $n={int(b.observed_accidents)}$"])
    write_table(output / "traffic_scope.tex", "Conditional rate ratios in the upper mean-wind intervals: all periods versus official VDU and SDU periods only", "tab:traffic-scope", "lrr", ["Mean wind", "All periods", "Official VDU+SDU only"], rows)

    quality = pd.read_csv("reports/main/tables/traffic_checks.csv")
    rows = []
    for row in quality.itertuples(index=False):
        if "Rate model" in row.check:
            value = f"RR {row.estimate:.2f}"
        elif "Daily traffic" in row.check:
            value = f"{row.estimate:.2f}%"
        else:
            value = f"{row.estimate:.2f}% excluded"
        if pd.notna(row.ci_95_low):
            value += f" ({row.ci_95_low:.2f}--{row.ci_95_high:.2f})"
        unit = " accidents" if "Rate model" in row.check else (" days" if "Daily traffic" in row.check else " section-years")
        rows.append([row.check, row.primary_or_full_scope, value, f"{int(row.records):,}{unit}"])
    write_table(output / "traffic_quality.tex", "Comparison and quality checks for the traffic analyses", "tab:traffic-sensitivity", r"L{0.22\textwidth}L{0.31\textwidth}L{0.22\textwidth}X", ["Check", "Data included", r"Estimate (95\% interval)", "Records"], rows, size="footnotesize", width=r"\textwidth")

    direction = pd.read_csv(
        "reports/main/tables/allocation_check.csv"
    )
    rows = [
        [
            interval(row.bin_label),
            f"{row.time_proportional_rate_ratio:.2f}",
            f"{row.relative_traffic_pct:.1f}%",
            f"{row.illustrative_rate_ratio:.2f}",
        ]
        for row in direction.itertuples(index=False)
    ]
    write_table(
        output / "allocation_check.tex",
        "Illustrative direction check using observed daily traffic response",
        "tab:traffic-allocation-direction",
        "lrrr",
        ["Mean wind", "Annual-model RR", "Daily traffic", "Illustrative RR"],
        rows,
        size="footnotesize",
    )


def evidence(output: Path) -> None:
    oe = pd.read_csv("reports/main/tables/mean_wind_oe.csv")
    case = pd.read_csv("reports/main/tables/matched_weather.csv")
    rate = pd.read_csv("reports/main/tables/wind_rate.csv")
    daily = pd.read_csv("reports/main/tables/allocated_rate.csv")
    a = oe[oe["mean_wind_interval_ms"].eq("20-25")].iloc[0]
    b = case[(case["exposure"].eq("mean_wind")) & (case["comparison"].eq(">=15"))].iloc[0]
    c = rate[rate["bin_label"].eq("20-25")].iloc[0]
    d = daily[daily["wind_bin"].eq(">=15")].iloc[0]
    rows = [
        ["Primary O/E", "20--25 m/s", estimate(a, "observed_expected_ratio", "station_bootstrap_ci_95_low", "station_bootstrap_ci_95_high"), "Accident occurrence relative to local wind frequency; traffic is not included."],
        ["Matched time", r"$\geq15$ vs 0--5 m/s", estimate(b, "odds_ratio", "ci_95_low", "ci_95_high", "OR "), "Same calendar time; no direct measure of unusual daily travel changes."],
        ["Road-section traffic", "20--25 vs 0--5 m/s", estimate(c, "time_proportional_rate_ratio", "time_proportional_ci_95_low", "time_proportional_ci_95_high", "RR "), "Within road, year and traffic period; traffic is estimated from annual values."],
        ["Allocated daily rate", r"$\geq15$ vs 0--10 m/s", estimate(d, "rate_ratio", "ci_95_low", "ci_95_high", "RR "), f"Observed daily total with estimated within-day allocation; {int(d.model_accidents)} linked accidents."],
    ]
    write_table(output / "evidence.tex", "Summary of the evidence used to interpret the main result", "tab:evidence-summary", r"L{0.19\textwidth}L{0.22\textwidth}L{0.20\textwidth}X", ["Analysis", "Comparison", r"Estimate (95\% interval)", "Interpretation and principal limitation"], rows, width=r"\textwidth")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    accident_sample(args.output)
    weather_cleaning(args.output)
    match_quality(args.output)
    year_comparison(args.output)
    coverage(args.output)
    radius_tables(args.output)
    traffic_tables(args.output)
    evidence(args.output)
    print(f"wrote generated thesis tables to {args.output}")


if __name__ == "__main__":
    main()
