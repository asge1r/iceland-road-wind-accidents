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
        'Primary mean-wind and gust results. Each method is rescaled to its own 0--5 m/s reference: upper-bin O/E divided by reference O/E, or upper-bin VKT rate divided by reference rate. '
        'The dimensionless ratios have a common upper-to-reference interpretation, but different samples and denominators mean they are not identical estimands.',
        'tab:evidence-summary',r'L{0.13\textwidth}XL{0.23\textwidth}L{0.15\textwidth}',
        ['Parameter','Method','Comparison (m/s)','Relative contrast'],
        [[r.parameter,r.method,rf'$\geq{r.upper_bin[2:]}$ vs 0--5',f'{r.relative_contrast:.2f}'] for r in data.itertuples()],
        width=r'\textwidth',short_caption='Primary mean-wind and gust results.')

if __name__=='__main__': headline_summary(Path('reports/thesis/generated'))
