"""Publish monthly-frequency rates and seasonal summaries of existing exposure."""
from pathlib import Path

import numpy as np
import pandas as pd

INPUT = Path("data/analysis/monthly_vkt.csv")
SECTIONS = Path("data/analysis/monthly_vkt_section.csv")
OUTPUT = Path("reports/main/tables/monthly_vkt_rate.csv")
SEASONAL_OUTPUT = Path("reports/main/tables/monthly_vkt_seasonal.csv")


def seasonal_rates(sections: pd.DataFrame, pooled: pd.DataFrame) -> pd.DataFrame:
    """Sum stored seasonal counts/exposure; never average section rates."""
    keys = ["variable", "bin_label", "bin_order"]
    values = ["observed_accidents", "estimated_vehicle_km"]
    unique = ["variable", "counter_section_id", "year", "season", "bin_label"]
    if sections.duplicated(unique).any():
        raise ValueError("Duplicate section-year-season bins")
    if set(sections.variable) != {"f", "fg"}:
        raise ValueError("Monthly VKT supports only mean wind and gust")
    if (sections[values] < 0).any().any():
        raise ValueError("Negative seasonal counts or exposure")
    data = sections.assign(period=sections.season.replace({"Fall": "Autumn"}))
    if set(data.period) != {"Winter", "Spring", "Summer", "Autumn"}:
        raise ValueError("Missing or unexpected season")
    seasonal = data.groupby([*keys, "period"], as_index=False, observed=True)[values].sum()
    total = seasonal.groupby(keys, observed=True)[values].sum().sort_index()
    original = pooled[pooled.outcome.eq("All injury accidents")].set_index(keys)[values].sort_index()
    pd.testing.assert_index_equal(total.index, original.index)
    if not np.allclose(total, original, rtol=1e-12, atol=1e-6):
        raise ValueError("Seasonal counts/exposure do not reproduce published All year rates")
    annual = original.reset_index().assign(period="All year")
    result = pd.concat([annual, seasonal], ignore_index=True)
    result["rate_per_million_vehicle_km"] = (
        result.observed_accidents / result.estimated_vehicle_km.where(result.estimated_vehicle_km.gt(0)) * 1e6
    )
    result["outcome"] = "All injury accidents"
    return result


def main() -> None:
    data = pd.read_csv(INPUT)
    seasonal = seasonal_rates(pd.read_csv(SECTIONS), data)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT, index=False)
    seasonal.to_csv(SEASONAL_OUTPUT, index=False)
    print(f"wrote={OUTPUT}; {SEASONAL_OUTPUT}")


def severity_rates(sections: pd.DataFrame, pooled: pd.DataFrame,
                   accidents: pd.DataFrame) -> pd.DataFrame:
    """Decompose stored exposure using the unchanged eligible event records."""
    from src.traffic.monthly_vkt import _bin_values

    if accidents.id.duplicated().any() or not accidents.meidsli.isin([1, 2, 3]).all():
        raise ValueError('Accidents must be unique and in disjoint injury codes 1–3')
    totals = seasonal_rates(sections, pooled)
    keys = ['variable', 'bin_label', 'bin_order', 'period']
    parts = []
    for variable in ('f', 'fg'):
        events = accidents.copy()
        events['bin_label'] = _bin_values(events[variable], variable)
        if events.bin_label.isna().any():
            raise ValueError('Unclassified accident weather')
        section_keys = ['counter_section_id', 'year', 'season', 'bin_label']
        actual = events.groupby(section_keys, observed=True).size().rename('observed_accidents')
        expected = sections[sections.variable.eq(variable)].set_index(section_keys).observed_accidents
        # Compare every section cell, including event cells outside stored exposure.
        union = expected.index.union(actual.index)
        if not expected.reindex(union, fill_value=0).eq(actual.reindex(union, fill_value=0)).all():
            raise ValueError('Event records do not reproduce stored section counts')
        events['period'] = events.season.replace({'Fall': 'Autumn'})
        for outcome, mask in [('Minor injury accidents', events.meidsli.eq(3)),
                              ('Serious or fatal injury accidents', events.meidsli.isin([1, 2]))]:
            selected = events[mask]
            seasonal = selected.groupby(['bin_label', 'period'], observed=True).size()
            annual = selected.groupby('bin_label', observed=True).size()
            part = totals[totals.variable.eq(variable)].copy()
            part['observed_accidents'] = [int(annual.get(row.bin_label, 0)) if row.period == 'All year'
                else int(seasonal.get((row.bin_label, row.period), 0)) for row in part.itertuples()]
            part['outcome'] = outcome
            part['rate_per_million_vehicle_km'] = (part.observed_accidents /
                part.estimated_vehicle_km.where(part.estimated_vehicle_km.gt(0)) * 1e6)
            parts.append(part)
    result = pd.concat(parts, ignore_index=True)
    sum_components = result.groupby(keys)[['observed_accidents', 'rate_per_million_vehicle_km']].sum().sort_index()
    original = totals.set_index(keys)[sum_components.columns].sort_index()
    if not np.allclose(sum_components, original, rtol=1e-12, atol=1e-12, equal_nan=True):
        raise ValueError('Severity components do not reproduce all-injury results')
    # The All year decomposition must also reproduce the already published injury rows.
    annual = result[result.period.eq('All year')].set_index(['variable','bin_label','outcome'])
    known = pooled[pooled.outcome.ne('All injury accidents')].set_index(['variable','bin_label','outcome'])
    columns = ['observed_accidents','estimated_vehicle_km','rate_per_million_vehicle_km']
    if not np.allclose(annual[columns].sort_index(),known[columns].sort_index(),rtol=1e-12,atol=1e-6):
        raise ValueError('Decomposition differs from published injury-specific rates')
    return result


if __name__ == "__main__":
    main()
