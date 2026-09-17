"""Generate data-derived LaTeX tables used throughout the thesis."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT = Path("reports/thesis/generated")


def data_chapter_tables(output: Path) -> None:
    """Write compact selection totals and disjoint high-wind O/E examples."""
    from src.figures.oe_histo import disjoint_outcomes

    plotted = disjoint_outcomes(pd.read_csv("reports/main/tables/weather_oe.csv"))
    high = plotted[
        plotted.variable.eq("f") & plotted.period.eq("All year")
        & plotted.bin_label.eq(">=20")
    ]
    rows = []
    for name, code in [("Minor injury accidents", "3"), ("Severe/fatal accidents", "1 or 2")]:
        row = high[high.outcome.eq(name)].iloc[0]
        display_name = "Serious or fatal injury accidents" if name == "Severe/fatal accidents" else name
        rows.append([display_name, code, int(row.observed_accidents),
                     f"{row.expected_accidents:.2f}", f"{row.relative_accident_frequency:.2f}"])
    write_table(output / "windy_group_examples.tex",
                "Worked examples for the two O/E groups: mean wind at least 20 m/s, all years and seasons pooled.",
                "tab:windy-group-examples", "lrrrr",
                ["Group", r"\texttt{meidsli}", "Observed", "Expected", "O/E"], rows,
                short_caption="Worked high-wind O/E examples.")

    selection = pd.read_csv("data/analysis/selection_summary.csv").set_index(["dataset", "step"]).records
    samples = selection.loc["analysis_samples"]
    accidents = selection.loc["accidents"]
    weather = pd.read_csv("data/analysis/weather_cleaning.csv")
    weather = weather[weather.year.astype(str).ne("total")]
    daily = selection.loc["daily_traffic"]
    entries = [
        ("Valid accident records", samples.source_accidents, accidents.valid_time_and_coordinates, "Invalid time or coordinates."),
        ("Rural accidents", accidents.valid_time_and_coordinates, accidents.rural_accidents, "Inside the urban study boundary."),
        ("Rural injury accidents", accidents.rural_accidents, samples.rural_injury_2007_2025, "No recorded injury."),
        ("Accidents for weather-only analysis", samples.rural_injury_2007_2025, samples.weather_oe, "No qualifying weather within 20 km and five minutes."),
        ("Accidents for VKT analysis", samples.rural_injury_2019_2024, samples.same_day_weather_vkt, "Separate 2019--2024 sample: counter linkage, daytime, weather and traffic eligibility."),
        ("Wind observations", weather.input_rows.sum(), weather.clean_wind_rows.sum(), "Wind exclusions in the cleaning overview."),
        ("Counter-days for traffic-response analysis", daily.counter_days, daily.counter_days_with_daytime_wind, "Usable daytime weather summary."),
    ]
    rows = [[name, f"{int(before):,}", f"{100*(before-after)/before:.2f}\\%", f"{int(after):,}", reason]
            for name, before, after, reason in entries]
    # tex() escapes the percent sign; supply it without a pre-existing escape.
    for row in rows:
        row[2] = row[2].replace("\\%", "%")
        if row[2] == "0.00%":
            row[2] = r"$<0.01$%"
    write_table(output / "data_trimming.tex",
                "Overview of primary data selections for accidents, weather and traffic counts. "
                "The first four rows are sequential; the last three rows start from separate populations. "
                "Each removal percentage uses the count entering that row.",
                "tab:data-trimming", r"L{0.23\textwidth}rL{0.13\textwidth}rX",
                ["Selection", "Entering", "Removed at step (\\%)", "Retained", "Reason"], rows,
                size="footnotesize", width=r"\textwidth",
                short_caption="Primary data selections.")


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
    short_caption: str | None = None,
) -> None:
    environment = "tabularx" if width else "tabular"
    begin = rf"\begin{{{environment}}}{{{width}}}{{{columns}}}" if width else rf"\begin{{{environment}}}{{{columns}}}"
    label_line = rf"\label{{{label}}}" if label else ""
    caption_line = (
        rf"\caption[{short_caption}]{{{caption}}}"
        if short_caption else rf"\caption{{{caption}}}"
    )
    body = []
    for index, row in enumerate(rows):
        rule = r" \\ \grayhline" if index < len(rows) - 1 else r" \\"
        body.append(" & ".join(tex(value) for value in row) + rule)
    content = "\n".join(
        [
            r"\begin{table}[htbp]", r"\centering", rf"\{size}",
            caption_line, label_line, begin, r"\toprule",
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
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)", text)
    if match:
        lower, upper = match.groups()
        if lower.startswith("-"):
            lower = rf"${lower}$"
        if upper.startswith("-"):
            upper = rf"${upper}$"
        return f"{lower}--{upper}"
    return text


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
        ("All supplied station-time observations", "input_rows"),
        (r"Missing \texttt{f} or \texttt{fg}", "missing_wind"),
        (r"$f<0$, $fg<0$, $f\geq45$ or $fg\geq65$ m/s", None),
        (r"$fg=0<f$ or $fg+0.5<f$ (m/s)", None),
        (r"All-zero runs $\geq 2$ hr", "frozen_zero"),
        ("Wind observations retained", "clean_wind_rows"),
    ]
    invalid_range = int(data["negative"].sum() + data["upper_threshold"].sum())
    inconsistent = int(
        data["inconsistent_zero_gust"].sum() + data["gust_below_mean"].sum()
    )
    special = iter([invalid_range, inconsistent])
    rows = []
    for name, column in categories:
        value = int(data[column].sum()) if column else next(special)
        denominator = total if name == "All supplied station-time observations" else assessed
        rows.append([name, f"{value:,}", f"{100 * value / denominator:.2f}%"])
    scope_note = " Every supplied station-year contains at least one wind measurement."
    if outside_scope:
        rows.insert(1, [
            "Rows assessed for wind cleaning", f"{assessed:,}",
            f"{100 * assessed / total:.2f}%",
        ])
        scope_note = (
            f" {outside_scope:,} supplied observations from station-years without wind "
            "measurements are outside that scope."
        )
    denominator_note = (
        "Cleaning-rule shares use the rows in station-years containing wind data as their denominator."
        if outside_scope else
        "Cleaning-rule shares use all supplied observations."
    )
    write_table(
        output / "weather_cleaning.tex",
        "Overview of cleaning of wind measurement records, 2007--2025. " + denominator_note + scope_note,
        "tab:weather-cleaning", "lrr", ["Category", "Records", "Share"], rows,
        short_caption="Overview of cleaning of wind measurement records, 2007--2025.",
    )

    path = output / "weather_cleaning.tex"
    content = path.read_text().replace(r"\grayhline" + "\nWind observations retained", r"\midrule" + "\nWind observations retained")
    path.write_text(content)


def coverage(output: Path) -> None:
    selection = pd.read_csv("data/analysis/selection_summary.csv")
    samples = selection[selection["dataset"].eq("analysis_samples")].set_index("step")["records"]
    allocated = pd.read_csv("reports/main/tables/allocated_rate.csv")
    allocated_counts = allocated["model_accidents"].dropna().astype(int).unique()
    if len(allocated_counts) != 1:
        raise ValueError("Allocated-rate table does not contain one validated sample size")
    rows = [
        ("Source records", int(samples["source_accidents"]), "Accident database, 2007--2025."),
        ("Rural injury accidents", int(samples["rural_injury_2007_2025"]), "Study population."),
        ("Q1: Primary O/E", int(samples["weather_oe"]), "Main weather-frequency analysis."),
        ("Q2: Approximate traffic correction", int(samples["weather_oe"]), "Same accident sample as Q1; denominator reweighted using counter-derived traffic response."),
        ("Q3: Traffic-based rates", int(samples["same_day_weather_vkt"]), "Main counter-linked traffic analysis, 2019--2024."),
        ("Supporting matched-time", int(samples["matched_time"]), "Time-matched robustness analysis."),
        ("Supporting annual traffic", int(samples["annual_rate"]), "Broader road-linked traffic model."),
        ("Supporting allocated daily-counter", int(allocated_counts[0]), "Alternative daily-counter model."),
    ]
    rows = [[label, f"{count:,}", purpose] for label, count, purpose in rows]
    write_table(
        output / "coverage.tex",
        "Accident selection and analysis sample sizes.",
        "tab:coverage", r"L{0.34\textwidth}rX",
        ["Stage", "Accidents", "Purpose"], rows,
        size="footnotesize",
        width=r"\textwidth",
        short_caption="Analysis sample sizes.",
    )


def severity_conditions(output: Path) -> None:
    data = pd.read_csv("reports/main/tables/severity_conditions.csv")
    rows = []
    for row in data.itertuples(index=False):
        comparison_value = str(row.comparison).replace("Fall", "Autumn").replace(" m/s", "").replace(" °C", "").replace(" ºC", "")
        reference_value = str(row.reference).replace("Fall", "Autumn").replace(" m/s", "").replace(" °C", "").replace(" ºC", "")
        # Some source labels already include their units. Strip them here
        # because the reader-facing table adds the unit explicitly below.
        comparison_value = re.sub(r"\s*(?:m/s|°C|ºC)\s*$", "", comparison_value).strip()
        reference_value = re.sub(r"\s*(?:m/s|°C|ºC)\s*$", "", reference_value).strip()
        # The source label ``-6-3`` denotes -6 to -3 C, not -6 to +3 C.
        # Make the upper negative sign explicit before the generic interval parser.
        if row.predictor == "Temperature" and comparison_value == "-6-3":
            comparison_value = "-6--3"
        if row.predictor == "Temperature" and reference_value == "-6-3":
            reference_value = "-6--3"
        left = interval(comparison_value)
        right = interval(reference_value)
        unit = ""
        if row.predictor == "Mean wind":
            unit = " m/s"
        elif row.predictor == "Temperature":
            unit = r"~$^{\circ}$C"
            if comparison_value == "<-6":
                left = r"$<-6$"
        comparison = f"{left}{unit} vs {right}{unit}"
        if row.predictor == "Temperature":
            comparison = r"\mbox{" + f"{left}{unit}" + r"} vs \mbox{" + f"{right}{unit}" + "}"
        rows.append([
            row.predictor,
            comparison,
            f"{row.odds_ratio:.2f} ({row.ci_95_low:.2f}--{row.ci_95_high:.2f})",
        ])
    write_table(
        output / "severity_conditions.tex",
        "Adjusted odds ratios for a serious or fatal outcome among recorded injury accidents. All listed variables are included in the same model.",
        "tab:severity-conditions",
        r"L{0.20\textwidth}L{0.45\textwidth}X",
        ["Variable", "Comparison", r"Adjusted OR (95\% CI)"],
        rows,
        size="footnotesize",
        width=r"\textwidth",
        short_caption="Adjusted model of injury severity.",
    )


def traffic_methods(output: Path) -> None:
    selection = pd.read_csv("data/analysis/selection_summary.csv")
    samples = selection[selection["dataset"].eq("analysis_samples")].set_index("step")["records"]
    allocated = pd.read_csv("reports/main/tables/allocated_rate.csv")
    allocated_counts = allocated["model_accidents"].dropna().astype(int).unique()
    if len(allocated_counts) != 1:
        raise ValueError("Allocated-rate table does not contain one validated sample size")
    rows = [
        [
            "Annual road sections", f"2007--2025 ({int(samples['annual_rate']):,})",
            "VDU, SDU and derived VHDU",
            "Traffic is allocated by wind frequency within each period.",
        ],
        [
            "Allocated daily counters", f"2019--2024 ({int(allocated_counts[0]):,})",
            "Observed daily totals",
            "Within-day traffic is estimated; locations and upper bins are sparse.",
        ],
    ]
    write_table(
        output / "traffic_methods.tex",
        "Traffic inputs for the supporting vehicle-kilometre analyses.",
        "tab:traffic-methods",
        r"L{0.17\textwidth}L{0.17\textwidth}L{0.22\textwidth}L{0.32\textwidth}",
        ["Analysis", "Years (accidents)", "Traffic basis", "Main limitation"],
        rows, size="footnotesize", width=r"\textwidth",
    )


def match_quality(output: Path) -> None:
    data = pd.read_csv("data/processed/accidents/rural_injury.csv")
    rows = []
    for distance in (5, 10, 20, 30):
        matched = data.weather_station_dist_km.le(distance) & data.weather_time_difference_minutes.le(5) & data.f.notna() & data.fg.notna()
        n = int(matched.sum())
        rows.append([distance, f"{n:,}", f"{100*n/len(data):.1f}%"])
    write_table(output / "match_quality.tex",
        "Weather-match coverage at alternative station-distance thresholds. "
        "The denominator is 6,414 rural injury accidents, 2007--2025; all matches require valid mean wind and gust within five minutes.",
        "tab:match-quality", "rrr", ["Maximum distance (km)", "Matched accidents", r"Matched (\%)"], rows,
        short_caption="Weather-match coverage by distance threshold.")


def year_comparison(output: Path) -> None:
    yearly = pd.read_csv("reports/main/tables/year_oe.csv")
    pooled = pd.read_csv("reports/main/tables/weather_oe.csv")
    pooled = pooled[
        pooled["period"].eq("All year")
        & pooled["outcome"].eq("All injury accidents")
    ].groupby(
        ["variable", "bin_label"],
        as_index=False,
        observed=True,
    ).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
    )
    pooled["observed_expected_ratio"] = pooled["observed_accidents"] / pooled["expected_accidents"]
    selected = {
        "f": ["15-20", ">=20"],
        "temperature": ["-3-0", "0-3", "3-6", ">=12"],
    }
    names = {"f": "Mean wind (m/s)", "temperature": r"Temperature ($^{\circ}$C)"}
    rows = []
    for variable, intervals in selected.items():
        pooled_variable = pooled[pooled["variable"].eq(variable)].set_index("bin_label")
        adjusted = yearly[yearly["variable"].eq(variable)].set_index("coarse_bin")
        for bin_label in intervals:
            first = pooled_variable.loc[bin_label]
            second = adjusted.loc[bin_label]
            display_interval = interval(bin_label)
            rows.append([
                names[variable], display_interval,
                f"{int(second.observed_accidents):,}",
                f"{first.observed_expected_ratio:.2f}",
                f"{second.observed_expected_ratio:.2f}",
            ])
    write_table(
        output / "year_oe.tex",
        "Selected O/E estimates with and without year-specific standardisation",
        "tab:year-oe", r"L{0.17\textwidth}L{0.09\textwidth}rL{0.27\textwidth}X",
        [
            "Variable", "Interval", "Observed",
            r"Station + season O/E",
            r"Station + season + year O/E",
        ],
        rows, size="footnotesize", width=r"\textwidth",
    )


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
    write_table(output / "adu_quality.tex", "Consistency of observed daily PDF traffic with official ADU", None, "Xrrrr", ["Data included", r"\(N\)", "Median", "10th--90th pct.", r"\(r_{\log}\)"], rows, width=r"\textwidth")

    audit = pd.read_csv("reports/working/tables/day_rate_audit.csv").set_index("metric")["value"]
    rows = [
        ["Rural injury accidents in 2019--2024", f"{int(audit['rural_injury_accidents_2019_2024']):,}", "100.0%"],
        ["Exact road-section/year counter candidate", f"{int(audit['exact_road_section_counter_candidates']):,}", f"{100*audit['exact_road_section_counter_candidates']/audit['rural_injury_accidents_2019_2024']:.1f}%"],
        ["Assigned counter within 20 km", f"{int(audit['within_distance']):,}", f"{100*audit['within_distance']/audit['rural_injury_accidents_2019_2024']:.1f}%"],
        ["Positive count and valid full-day wind", f"{int(audit['with_valid_counter_day']):,}", f"{100*audit['with_valid_counter_day']/audit['rural_injury_accidents_2019_2024']:.1f}%"],
    ]
    write_table(output / "daily_selection.tex", "Selection of accidents for the supporting allocated daily-counter model.", "tab:allocated-selection", "Xrr", ["Selection step", "Accidents", "Share of 2019--2024 sample"], rows, width=r"0.86\textwidth", short_caption="Selection for the supporting counter model.")

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
        "Characteristics of accidents retained and excluded by the linkage used for the supporting allocated daily-counter model.",
        "tab:allocated-sample",
        "Xrrrr",
        headers,
        rows,
        size="footnotesize",
        width=r"\textwidth",
        short_caption="Characteristics by counter-linkage status.",
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
    write_table(output / "daily_radius.tex", "Upper-bin estimate from the daily-mean-wind counter model under three accident-to-counter assignment distances.", "tab:allocated-radius", "rrrrr", ["Maximum distance", "Included accidents", "Upper-bin accidents", "Rate ratio", r"95\% CI"], rows, short_caption="Assignment-distance sensitivity of the daily-mean-wind model.")

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

    traffic_sensitivity(output)

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


def traffic_sensitivity(output: Path) -> None:
    quality = pd.read_csv("reports/main/tables/traffic_checks.csv")
    quality = quality[quality["check"].str.startswith("Daily traffic")]
    rows = []
    for row in quality.itertuples(index=False):
        value = f"{row.estimate:.2f}%"
        if pd.notna(row.ci_95_low):
            value += f" ({row.ci_95_low:.2f}--{row.ci_95_high:.2f})"
        unit = " days"
        check = str(row.check).replace("20-25", "20--25")
        rows.append([check, row.primary_or_full_scope, value, f"{int(row.records):,}{unit}"])
    write_table(output / "traffic_quality.tex", "Effect of excluding zero counter-days on the daily traffic response.", "tab:traffic-sensitivity", r"L{0.19\textwidth}L{0.27\textwidth}L{0.22\textwidth}X", ["Check", "Data included", r"Estimate (95\% interval)", "Records"], rows, size="footnotesize", width=r"\textwidth")



def _legacy_evidence(output: Path) -> None:
    """Legacy pre-Q1/Q2/Q3 summary; intentionally not called by main()."""
    oe = pd.read_csv("reports/main/tables/weather_oe.csv")
    case = pd.read_csv("reports/main/tables/matched_weather.csv")
    rate = pd.read_csv("reports/main/tables/wind_rate.csv")
    daily = pd.read_csv("data/analysis/daily_vkt.csv")
    a_rows = oe[
        oe["variable"].eq("f") & oe["period"].eq("All year")
        & oe["bin_label"].eq(">=20")
        & oe["outcome"].eq("All injury accidents")
    ]
    a_observed = int(a_rows["observed_accidents"].sum())
    a_expected = float(a_rows["expected_accidents"].sum())
    b = case[(case["exposure"].eq("mean_wind")) & (case["comparison"].eq(">=15"))].iloc[0]
    c = rate[rate["bin_label"].eq("20-25")].iloc[0]
    daily = daily[
        daily["variable"].eq("f") & daily["period"].eq("All year")
    ].groupby("bin_label", as_index=True, observed=True).agg(
        accidents=("accidents", "sum"),
        estimated_vehicle_km=("estimated_vehicle_km", "first"),
    )
    daily["rate"] = daily["accidents"] / daily["estimated_vehicle_km"] * 1_000_000
    rows = [
        ["Weather-frequency O/E", rf"$\geq20$ m/s: O/E {a_observed/a_expected:.2f}", "Primary result; local wind frequency, no traffic."],
        ["Matched time", r"$\geq15$ vs 0--5 m/s: " + estimate(b, "odds_ratio", "ci_95_low", "ci_95_high", "OR "), "Same station and calendar time."],
        ["Annual traffic", "20--25 vs 0--5 m/s: " + estimate(c, "time_proportional_rate_ratio", "time_proportional_ci_95_low", "time_proportional_ci_95_high", "RR "), "Broader traffic sample; traffic allocated within periods."],
        ["Daily traffic, same-day weather", rf"$\geq20$ vs 0--5 m/s: {daily.loc['>=20', 'rate']:.2f} vs {daily.loc['0-5', 'rate']:.2f} per million vehicle-km", f"Observed daily totals on rural road portions; {int(daily.accidents.sum())} accidents, {int(daily.loc['>=20', 'accidents'])} in the upper interval."],
    ]
    write_table(
        output / "evidence.tex",
        "Main result and supporting comparisons.",
        "tab:evidence-summary",
        r"L{0.19\textwidth}L{0.37\textwidth}L{0.34\textwidth}",
        ["Analysis", "Estimate", "Role"],
        rows,
        size="footnotesize",
        width=r"\textwidth",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    from src.tables.cleaned_example import cleaned_example
    cleaned_example(args.output)
    from src.tables.headline_summary import headline_summary
    headline_summary(args.output)
    data_chapter_tables(args.output)
    weather_cleaning(args.output)
    match_quality(args.output)
    print(f"wrote generated thesis tables to {args.output}")


if __name__ == "__main__":
    main()
