"""Rescale each retained method to its own measured low-wind reference."""
from pathlib import Path
import pandas as pd
from src.tables.thesis import write_table


def relative_contrasts(q1, q2, q3):
    rows=[]
    for variable,name,high in [('f','Mean wind','>=20'),('fg','Wind gust','>=30')]:
        for data,method,column in [(q1,'Weather-frequency O/E analysis','relative_accident_frequency'),
                (q2,'Approximate traffic-corrected O/E analysis','traffic_corrected_oe'),
                (q3,'VKT analysis','rate_per_million_vehicle_km')]:
            part=data[data.variable.eq(variable)&data.outcome.eq('All injury accidents')]
            if 'period' in part: part=part[part.period.eq('All year')]
            if part.bin_label.duplicated().any(): raise ValueError('Duplicate primary result')
            part=part.set_index('bin_label')
            reference=float(part.loc['0-5',column]);upper=float(part.loc[high,column])
            if reference<=0: raise ValueError('Nonpositive reference')
            rows.append(dict(variable=variable,parameter=name,method=method,upper_bin=high,
                reference_bin='0-5',upper_metric=upper,reference_metric=reference,relative_contrast=upper/reference))
    return pd.DataFrame(rows)


def headline_summary(output):
    data=relative_contrasts(pd.read_csv('reports/main/tables/weather_oe.csv'),
        pd.read_csv('reports/main/tables/weather_oe_traffic_corrected.csv'),pd.read_csv('reports/main/tables/monthly_vkt_rate.csv'))
    data.to_csv('reports/working/tables/primary_relative_contrasts.csv',index=False)
    write_table(output/'evidence.tex',
        'Mean-wind and gust results. Ratios compare the highest wind or gust interval with 0--5 m/s,\n'
        'using O/E for the first two methods and accident rates for VKT.\n'
        'The methods use different samples and denominators. '
        'Both O/E methods use 2007--2025 weather-matched rural injury accidents. The correction uses 2019--2024 counter data. '
        'VKT uses 2019--2024 accidents on counter-covered sections.',
        'tab:evidence-summary',r'L{0.13\textwidth}XL{0.23\textwidth}L{0.15\textwidth}',
        ['Parameter','Method','Comparison (m/s)','Ratio'],
        [[r.parameter,r.method,rf'$\geq{r.upper_bin[2:]}$ vs 0--5',f'{r.relative_contrast:.2f}'] for r in data.itertuples()],
        width=r'\textwidth',short_caption='Mean-wind and gust results.',
        row_rules={2: r'\specialrule{\lightrulewidth}{1mm}{1mm}'})

if __name__=='__main__': headline_summary(Path('reports/thesis/generated'))
