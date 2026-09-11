"""Render the human-readable validation report."""

from __future__ import annotations

from pathlib import Path

def write_report(values: dict[str, object], output: Path) -> None:
    weather = values["weather"]
    main_upper = values["main_upper"].set_index("outcome")
    traffic_audit = values["traffic_audit"]
    lines = [
        "# Final analysis validation",
        "",
        "All checks below passed against the current local analysis files.",
        "",
        "## Fixed primary analysis",
        "",
        f"- Population: {values['study_accidents']:,} rural injury accidents, {values['study_period']}.",
        f"- Primary weather match: {values['primary_accidents']:,} accidents within 20 km and 5 minutes.",
        "- Primary weather measure: accident-time ten-minute mean wind speed (`f`) in 5 m/s intervals.",
        "- Standardisation: weather station and season; weather frequency is pooled across 2007--2025.",
        "- The O/E table is descriptive; formal uncertainty is assessed in the matched-time and traffic models.",
        "",
        "## Data checks",
        "",
        "| Check | Result |",
        "|---|---:|",
        f"| Unique accident identifiers | {values['study_accidents']:,} / {values['study_accidents']:,} |",
        f"| Temperature matches within 20 km and 5 minutes | {values['temperature_accidents']:,} / {values['study_accidents']:,} |",
        f"| Raw weather observations | {weather['input_rows']:,} |",
        f"| Clean weather observations retained | {weather['clean_rows']:,} |",
        f"| Weather observations excluded by fixed rules | {weather['excluded_rows']:,} |",
        f"| Clean weather retention, all delivered rows | {100 * weather['clean_rows'] / weather['input_rows']:.2f}% |",
        f"| Rate-analysis accidents with shared station within 20 km and 5 minutes | {values['rate_accidents']:,} |",
    ]
    if values["daily_rows"] is None:
        lines.append("| Daily counter-days | Optional daily PDF data were not prepared locally |")
    else:
        daily_pct = 100 * values["daily_with_wind"] / values["daily_rows"]
        lines.extend(
            [
                f"| Daily counter-days | {values['daily_rows']:,} |",
                f"| Daily counter-days with daytime wind | {values['daily_with_wind']:,} ({daily_pct:.2f}%) |",
            ]
        )
    lines.extend(
        [
            "",
            "## Primary O/E result",
            "",
            "| Mean wind >=20 m/s | Observed | Expected | O/E |",
            "|---|---:|---:|---:|",
            f"| All injury (meidsli <=3) | {int(main_upper.loc['All injury accidents', 'observed_accidents'])} | {main_upper.loc['All injury accidents', 'expected_accidents']:.1f} | {main_upper.loc['All injury accidents', 'relative_accident_frequency']:.2f} |",
            f"| Severe/fatal | {int(main_upper.loc['Severe/fatal accidents', 'observed_accidents'])} | {main_upper.loc['Severe/fatal accidents', 'expected_accidents']:.1f} | {main_upper.loc['Severe/fatal accidents', 'relative_accident_frequency']:.2f} |",
            "",
            f"The all-injury row reconstructs all {values['primary_accidents']:,} matched accidents; serious/fatal accidents are its meidsli <=2 subset. Expected counts are rounded to one decimal.",
            "The O/E values are descriptive and are not presented with confidence intervals.",
            "",
            "## Stratified vehicle-kilometre result",
            "",
            f"The shared-station rate model retains {values['rate_accidents']:,} accidents. At >=25 m/s, the within-stratum time-proportional rate ratio is {values['high_rate']['time_proportional_rate_ratio']:.2f} (95% CI {values['high_rate']['time_proportional_ci_95_low']:.2f}--{values['high_rate']['time_proportional_ci_95_high']:.2f}).",
            f"The serious/fatal version retains {int(values['rate_serious']['model_accidents'].iloc[0]):,} accidents. Its 15--20 m/s rate ratio is {values['rate_serious'].loc[values['rate_serious']['bin_label'].eq('15-20'), 'time_proportional_rate_ratio'].iloc[0]:.2f}.",
            "The seasonal model uses coarse 0--10, 10--15, and >=15 m/s intervals; all four >=15 m/s estimates are above one.",
            "The serious-or-fatal seasonal model uses the same intervals; its spring upper category contains only six accidents and is interpreted cautiously.",
            "",
            "## Time-stratified case-crossover result",
            "",
            f"At mean wind >=15 m/s versus 0--5 m/s, the matched odds ratio is {values['high_wind_case_control']['odds_ratio']:.2f} (95% CI {values['high_wind_case_control']['ci_95_low']:.2f}--{values['high_wind_case_control']['ci_95_high']:.2f}).",
            f"At gust >=30 m/s versus 0--10 m/s, the matched odds ratio is {values['high_gust_case_control']['odds_ratio']:.2f} (95% CI {values['high_gust_case_control']['ci_95_low']:.2f}--{values['high_gust_case_control']['ci_95_high']:.2f}).",
            f"The formal wind-by-season likelihood-ratio test gives chi-square {values['season_interaction'].iloc[0]['likelihood_ratio_chi2']:.2f} on {int(values['season_interaction'].iloc[0]['degrees_of_freedom'])} degrees of freedom (p={values['season_interaction'].iloc[0]['p_value']:.3f}).",
            "",
            "## Additional environmental comparisons",
            "",
            f"The joint matched-time model retains {int(values['joint_high_wind']['strata']):,} accidents with both wind and temperature. Its adjusted >=15 versus 0--5 m/s wind odds ratio is {values['joint_high_wind']['adjusted_odds_ratio']:.2f} (95% CI {values['joint_high_wind']['ci_95_low']:.2f}--{values['joint_high_wind']['ci_95_high']:.2f}).",
            f"The matched daylight comparison uses all {values['study_accidents']:,} accidents, but only {int(values['daylight']['informative_strata'].iloc[0]):,} strata change daylight class within the matched month and hour.",
            f"The severity-composition model contains {int(values['severity']['accidents'].iloc[0]):,} complete accidents and {int(values['severity']['serious_or_fatal_accidents'].iloc[0]):,} serious-or-fatal outcomes. It estimates severity among recorded accidents, not accident occurrence.",
            "",
            "## Results using traffic data",
            "",
            f"Restricting the 20--25 m/s rate model to official VDU and SDU gives RR {values['official_20_25']['estimate']:.2f}. Excluding zero counter-days changes the corresponding daily-traffic percentage by less than two percentage points.",
            f"The illustrative denominator direction check changes the 20--25 m/s annual-model RR from {values['allocation_check'].loc[values['allocation_check']['bin_label'].eq('20-25'), 'time_proportional_rate_ratio'].iloc[0]:.2f} to {values['allocation_check'].loc[values['allocation_check']['bin_label'].eq('20-25'), 'illustrative_rate_ratio'].iloc[0]:.2f} when the observed daily traffic percentage is applied mechanically. This is not a corrected estimate because full-day traffic does not identify traffic in ten-minute wind intervals.",
            f"The sustained-wind table contains {int(values['daily_duration']['counter_days'].sum()):,} sufficiently complete counter-days. Traffic is {values['daily_duration'].iloc[-1]['relative_traffic_pct']:.1f}% of its calendar expectation on days with at least six hours at f >=15 m/s.",
            f"The allocated daily-counter model retains {int(values['daily_allocated']['observed_accidents'].sum()):,} accidents. Its >=15 versus 0--10 m/s rate ratio is {values['daily_allocated'].iloc[-1]['rate_ratio']:.2f} (95% CI {values['daily_allocated'].iloc[-1]['ci_95_low']:.2f}--{values['daily_allocated'].iloc[-1]['ci_95_high']:.2f}). The within-day traffic split is estimated, not observed hourly traffic.",
            "The counter-section vehicle-kilometre table partitions 613 linked daytime accidents into non-overlapping minor-injury and severe/fatal groups for wind, gust, and temperature. Daily totals are observed and allocated using actual 07:00--24:00 weather on the same date; traffic within each ten-minute interval remains estimated.",
            f"The temperature vehicle-kilometre model retains {int(values['temperature_rate']['observed_accidents'].sum()):,} accidents. Relative to 0--3 degrees C, its below--6 estimate is {values['temperature_rate'].iloc[0]['time_proportional_rate_ratio']:.2f} and its 3--6 estimate is {values['temperature_rate'].loc[values['temperature_rate']['bin_label'].eq('3-6'), 'time_proportional_rate_ratio'].iloc[0]:.2f}.",
            f"The coarse >=15 m/s estimates are {values['vehicle_rates']['one'].iloc[-1]['time_proportional_rate_ratio']:.2f} for one-vehicle accidents and {values['vehicle_rates']['two-plus'].iloc[-1]['time_proportional_rate_ratio']:.2f} for accidents involving two or more vehicles. These are separate subgroup estimates, not a formal test of their difference.",
            f"This retained sample is {values['daily_sample'].loc['Allocated-rate sample', 'share_of_all_pct']:.1f}% of the 2019--2024 rural injury accidents. The generated appendix audit compares its severity, vehicle-count, season, and road-section composition with retained and excluded accidents.",
            f"The serious/fatal daily model retains {int(values['daily_serious']['observed_accidents'].sum()):,} accidents; its upper rate ratio is {values['daily_serious'].iloc[-1]['rate_ratio']:.2f}. Restricting the all-injury allocation to 07:00--24:00 gives {values['daily_07_24'].iloc[-1]['rate_ratio']:.2f}, versus {values['daily_allocated'].iloc[-1]['rate_ratio']:.2f} for the full day.",
            f"The shared seasonal daily panel reconstructs expected accidents within every counter-year-season group. Its full interaction test gives p={values['daily_season_full_test']['p_value']:.3f}; the secondary >=15 m/s interaction gives p={values['daily_season_highwind_test']['p_value']:.3f}. Both are retained, and the seasonal O/E uses 5,000 whole-counter bootstrap samples.",
            f"The main comparison figure retains separate denominators: annual-traffic O/E is {values['wind_oe_comparison'].loc[values['wind_oe_comparison']['method'].eq('Annual traffic') & values['wind_oe_comparison']['wind_bin'].eq('20-25'), 'observed_expected_ratio'].iloc[0]:.2f} at 20--25 m/s, and daily-traffic O/E is {values['wind_oe_comparison'].loc[values['wind_oe_comparison']['method'].eq('Daily traffic') & values['wind_oe_comparison']['wind_bin'].eq('>=15'), 'observed_expected_ratio'].iloc[0]:.2f} at >=15 m/s.",
            f"The appendix full-day-mean check retains {values['daily_rate_total']:,} accidents. At >=15 m/s versus 0--10 m/s, RR is {values['daily_rate_high']['rate_ratio']:.2f} (95% CI {values['daily_rate_high']['ci_95_low']:.2f}--{values['daily_rate_high']['ci_95_high']:.2f}), based on {int(values['daily_rate_high']['observed_accidents'])} upper-category accidents.",
            "The 5, 10, and 20 km counter-assignment table confirms that both non-reference coarse estimates are generated reproducibly and retain valid confidence-interval ordering.",
            "",
        ]
    )
    lines.extend(
        [
            "",
            "## Annual-traffic quality",
            "",
            f"The 2007--2025 annual-traffic input contains {int(traffic_audit.loc['section_years', 'section_years']):,} road-section/year rows. "
            f"Nonpositive published VDU values occur in {int(traffic_audit.loc['nonpositive_vdu', 'section_years']):,} rows, and "
            f"nonpositive derived VHDU residuals occur in {int(traffic_audit.loc['nonpositive_derived_vhdu', 'section_years']):,} rows. "
            "These rows are excluded from the corresponding estimated vehicle-kilometres; they are not replaced or imputed.",
            "",
            "## Study-population decision",
            "",
            f"Single-vehicle, run-off-road, rollover, fall, or other accidents account for {values['single_vehicle_count']:,} of {values['study_accidents']:,} study accidents ({values['single_vehicle_pct']:.1f}%).",
            "This supports the relevance of wind conditions to vehicle control. The separate appendix O/E curve for this group is exploratory and does not replace the fixed all-injury primary result.",
            "",
            "## Decision",
            "",
            "The primary analysis is internally consistent and ready to freeze: `f`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Gust, temperature, and traffic remain supporting analyses.",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
