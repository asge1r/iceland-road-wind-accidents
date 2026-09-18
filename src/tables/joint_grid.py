"""Five-by-eight joint wind/temperature O/E grid for Figure 4.6.

Expected counts use simultaneous, quality-controlled weather observations at
each accident's station and season. The bins match Figures 4.3 and 4.5.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.tables.joint_detail import verify_simultaneous_records
from src.weather.eligibility import valid_temperature
from src.weather.frequency import (
    OE_F_UPPER_BOUNDS, OE_TEMPERATURE_LABELS,
    OE_TEMPERATURE_UPPER_BOUNDS, SEASONS, labels, season_index, station_ids,
)

WEATHER = Path('data/processed/weather/weather.parquet')
ACCIDENTS = Path('data/processed/accidents/rural_injury.csv')
OUTPUT = Path('reports/main/tables/joint_wind_temperature_5x8.csv')
FREQUENCY_AUDIT = Path('reports/working/tables/joint_5x8_frequency.csv')
MATCH_AUDIT = Path('reports/working/tables/joint_5x8_simultaneous_events.csv')
WIND_LABELS = labels(OE_F_UPPER_BOUNDS)
TEMP_LABELS = OE_TEMPERATURE_LABELS
WIND_COUNT, TEMP_COUNT = len(WIND_LABELS), len(TEMP_LABELS)
CELL_COUNT = WIND_COUNT * TEMP_COUNT


def category(wind, temperature):
    wind, temperature = np.asarray(wind), np.asarray(temperature)
    if not (np.isfinite(wind).all() and np.isfinite(temperature).all()
            and (wind >= 0).all()):
        raise ValueError('Joint classification requires finite weather and nonnegative wind')
    return (np.searchsorted(OE_F_UPPER_BOUNDS, wind, side='right') * TEMP_COUNT
            + np.searchsorted(OE_TEMPERATURE_UPPER_BOUNDS, temperature, side='right'))


def eligible_events(path=ACCIDENTS):
    events = pd.read_csv(path)
    events['timestamp'] = pd.to_datetime(events.timestamp)
    events['season'] = SEASONS[season_index(events.timestamp.dt.month.to_numpy())]
    valid = (events.within_20km & events.weather_station_dist_km.le(20)
             & events.weather_time_difference_minutes.le(5)
             & events.temp_distance_km.le(20) & events.temp_time_diff_min.le(5)
             & events.f.notna() & events.temperature_c.between(-30, 30))
    events = events[valid].copy()
    if not (events.weather_station_id.eq(events.temp_station_id).all()
            and events.weather_time_difference_minutes.eq(events.temp_time_diff_min).all()):
        raise ValueError('Joint events must share station and observation time')
    return events


def weather_frequency(path=WEATHER):
    source = pq.ParquetFile(path)
    stations = station_ids(source, source.num_row_groups)
    counts = np.zeros((len(stations) * len(SEASONS), CELL_COUNT), dtype=np.int64)
    valid_total = 0
    for index, batch in enumerate(source.iter_batches(
            batch_size=1_000_000, columns=['station', 'time', 'f', 'fg', 't'])):
        station, time, wind, gust, temp = [
            batch.column(name).to_numpy(zero_copy_only=False)
            for name in ('station', 'time', 'f', 'fg', 't')
        ]
        year = time.astype('datetime64[Y]').astype(int) + 1970
        month = time.astype('datetime64[M]').astype(int) % 12 + 1
        # Keep precisely the eligibility used by the existing joint analysis.
        valid = (valid_temperature(temp) & np.isfinite(wind) & np.isfinite(gust)
                 & (wind >= 0) & (wind < 45) & (gust >= 0) & (gust < 65)
                 & (gust + .5 >= wind) & ~((gust == 0) & (wind > 0))
                 & (year >= 2007) & (year <= 2025))
        group = np.searchsorted(stations, station[valid]) * len(SEASONS) + season_index(month[valid])
        cell = category(wind[valid], temp[valid])
        counts += np.bincount(group * CELL_COUNT + cell, minlength=counts.size).reshape(counts.shape)
        valid_total += int(valid.sum())
        if (index + 1) % 30 == 0:
            print(f'Joint 5x8 weather batches={index + 1}', flush=True)
    if counts.sum() != valid_total:
        raise ValueError('Joint weather counts did not conserve observations')
    result = pd.DataFrame({
        'weather_station_id': np.repeat(stations, len(SEASONS) * CELL_COUNT),
        'season': np.tile(np.repeat(SEASONS, CELL_COUNT), len(stations)),
        'cell': np.tile(np.arange(CELL_COUNT), len(stations) * len(SEASONS)),
        'measurements': counts.ravel(),
        'total_measurements': np.repeat(counts.sum(axis=1), CELL_COUNT),
    })
    result['frequency'] = result.measurements / result.total_measurements.where(
        result.total_measurements.gt(0))
    return result


def calculate(events, frequency):
    keys = ['weather_station_id', 'season']
    if events.id.duplicated().any():
        raise ValueError('Duplicate joint events')
    events = events.copy()
    events['cell'] = category(events.f, events.temperature_c)
    groups = events.groupby(keys).size().rename('accidents').reset_index()
    background = frequency.merge(groups, on=keys, how='inner', validate='many_to_one')
    if len(background) != CELL_COUNT * len(groups) or background.duplicated(keys + ['cell']).any():
        raise ValueError('Missing or duplicate joint frequency cells')
    if not np.isfinite(background.frequency).all() or (background.frequency < 0).any():
        raise ValueError('Invalid joint weather frequencies')
    if not np.allclose(background.groupby(keys).frequency.sum(), 1, rtol=0, atol=1e-12):
        raise ValueError('Joint weather frequencies do not conserve totals')
    background['expected_accidents'] = background.accidents * background.frequency
    observed = events.groupby(keys + ['cell']).size().rename('observed_accidents').reset_index()
    background = background.merge(observed, on=keys + ['cell'], how='left', validate='one_to_one')
    background['observed_accidents'] = background.observed_accidents.fillna(0).astype(int)
    result = (background.groupby('cell')[['observed_accidents', 'expected_accidents']]
              .sum().reindex(range(CELL_COUNT), fill_value=0).reset_index())
    result['wind_order'] = result.cell // TEMP_COUNT
    result['temperature_order'] = result.cell % TEMP_COUNT
    result['wind_bin'] = result.wind_order.map(dict(enumerate(WIND_LABELS)))
    result['temperature_bin'] = result.temperature_order.map(dict(enumerate(TEMP_LABELS)))
    result['oe'] = result.observed_accidents / result.expected_accidents.where(
        result.expected_accidents.gt(0))
    result['sample_percent'] = result.observed_accidents / len(events) * 100
    result['sparse'] = result.observed_accidents.lt(10) | result.expected_accidents.lt(5)
    if (result.observed_accidents.sum() != len(events)
            or not np.isclose(result.expected_accidents.sum(), len(events), rtol=0, atol=1e-8)):
        raise ValueError('Joint totals differ from eligible sample')
    return result


def check_previous_partition(result, path=Path('reports/main/tables/joint_wind_temperature_detail.csv')):
    """Reconcile with the saved 4x5 snapshot (allowing minor archive revisions)."""
    if not path.exists():
        return
    old_temperature = np.array([0, 0, 1, 2, 2, 3, 3, 4])
    old_cell = np.minimum(result.wind_order, 3) * 5 + old_temperature[result.temperature_order]
    pooled = result.assign(old_cell=old_cell).groupby('old_cell')[
        ['observed_accidents', 'expected_accidents']].sum()
    previous = pd.read_csv(path).set_index('cell').sort_index()
    np.testing.assert_array_equal(pooled.observed_accidents, previous.observed_accidents)
    # The current cleaned weather archive differs slightly from the archived
    # 4x5 table: no cell moves by more than 0.05 expected accidents.
    np.testing.assert_allclose(pooled.expected_accidents, previous.expected_accidents,
                               rtol=0, atol=.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accidents', type=Path, default=ACCIDENTS)
    parser.add_argument('--weather', type=Path, default=WEATHER)
    args = parser.parse_args()
    events = eligible_events(args.accidents)
    if len(events) != 6259:
        raise ValueError('Eligible joint population changed')
    matched = verify_simultaneous_records(events, args.weather)
    frequency = weather_frequency(args.weather)
    result = calculate(events, frequency)
    check_previous_partition(result)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    FREQUENCY_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    frequency.to_csv(FREQUENCY_AUDIT, index=False)
    matched.to_csv(MATCH_AUDIT, index=False)
    print(result.to_string(index=False))


if __name__ == '__main__':
    main()
