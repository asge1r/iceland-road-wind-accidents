"""Render the existing Q1--Q3 headline estimates without changing calculations."""
from pathlib import Path
import pandas as pd
from src.tables.thesis import write_table


def headline_summary(output: Path) -> None:
    q1 = pd.read_csv('reports/main/tables/weather_oe.csv')
    q2 = pd.read_csv('reports/main/tables/weather_oe_traffic_corrected.csv')
    q3 = pd.read_csv('reports/main/tables/monthly_vkt_rate.csv')
    rows = []
    for variable, name, high in [('f', 'Mean wind', '>=20'), ('fg', 'Wind gust', '>=30')]:
        def select(data, label):
            part = data[data.variable.eq(variable) & data.outcome.eq('All injury accidents') & data.bin_label.eq(label)]
            if 'period' in part:
                part = part[part.period.eq('All year')]
            if len(part) != 1:
                raise ValueError('Expected one published headline row')
            return part.iloc[0]
        a,b,c = select(q1, high), select(q2, high), select(q3, high)
        baseline = select(q3, '0-5')
        interval = rf'$\geq{high[2:]}$ m/s'
        rows.extend([
            [name, 'Weather-frequency O/E', interval, f'O/E {a.relative_accident_frequency:.2f}', 'Local weather frequency'],
            [name, 'Approximate traffic-corrected O/E', interval, f'O/E {b.traffic_corrected_oe:.2f}', 'Traffic-reweighted weather frequency'],
            [name, 'Monthly-frequency VKT', interval + ' vs 0--5', f'{c.rate_per_million_vehicle_km / baseline.rate_per_million_vehicle_km:.2f}' + r'$\times$', 'Estimated VKT (monthly allocation)'],
        ])
    write_table(output/'evidence.tex',
        'Headline mean-wind and gust results. The weather-frequency and approximate traffic-corrected O/E analyses report O/E; the monthly-frequency VKT analysis reports the upper-bin rate divided by the 0--5 m/s rate. '
        'The estimates use different denominators and are not repeated estimates of one parameter. The monthly-frequency VKT analysis uses a smaller counter-linked sample, with 11 accidents in each upper interval.',
        'tab:evidence-summary', r'L{0.12\textwidth}L{0.17\textwidth}L{0.19\textwidth}L{0.12\textwidth}X',
        ['Parameter','Method','Comparison','Estimate','Denominator'], rows,
        size='small', width=r'\textwidth', short_caption='Headline wind and gust results.')


if __name__ == '__main__':
    headline_summary(Path('reports/thesis/generated'))
