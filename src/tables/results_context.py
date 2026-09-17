"""Generate focused Results sentences from the retained numerical outputs."""
from pathlib import Path
import pandas as pd

OUT=Path('reports/thesis/generated')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    traffic=pd.read_csv('data/analysis/traffic_weather_response.csv').set_index(['variable','bin_label'])
    f=-traffic.loc[('f','>=20'),'traffic_change_pct'];g=-traffic.loc[('fg','>=30'),'traffic_change_pct']
    text=(f'Daily traffic is {f:.1f}\\% below its calendar expectation at mean wind of at least 20 m/s and {g:.1f}\\% below expectation at gusts of at least 30 m/s. '
          'These reductions describe the denominator response used by the correction, not an accident-rate change.\n')
    (OUT/'traffic_response_results.tex').write_text(text)
    oe=pd.read_csv('reports/main/tables/weather_oe.csv')
    t=oe[oe.variable.eq('temperature')&oe.period.eq('All year')&oe.outcome.eq('All injury accidents')].set_index('bin_label')
    text=(r'The all-injury O/E is '+f'{t.loc["-3-0","relative_accident_frequency"]:.2f}'
          +r' immediately below freezing, falls to '+f'{t.loc["3-6","relative_accident_frequency"]:.2f}'
          +r' at 3--6$^{\circ}$C, and rises to '+f'{t.loc[">=12","relative_accident_frequency"]:.2f}'
          +r' at temperatures of at least 12$^{\circ}$C. The coldest group, below $-6$$^{\circ}$C, has O/E '
          +f'{t.loc["<-6","relative_accident_frequency"]:.2f}'+r'; thus the pattern is not a uniform cold-weather excess. Seasonal warm-end components are smaller and less stable than the pooled comparison.'+'\n')
    (OUT/'temperature_oe_results.tex').write_text(text)
    rates=pd.read_csv('reports/main/tables/monthly_vkt_seasonal.csv')
    from src.figures.weather_rate import combine_seasonal_tails
    # Same pooling used by the figure; rename only its observed-count field.
    rates=combine_seasonal_tails(rates.rename(columns={'observed_accidents':'accidents'}))
    for variable,name in [('f','mean_wind'),('fg','gust')]:
        subset=rates[rates.variable.eq(variable)&rates.outcome.eq('All injury accidents')&rates.period.ne('All year')]
        rows=[]
        for period in ['Winter','Spring','Summer','Autumn']:
            p=subset[subset.period.eq(period)].sort_values('bin_order')
            if p.empty:raise ValueError('Missing seasonal rate')
            lo,hi=p.iloc[0],p.iloc[-1]
            rows.append((period,hi.rate_per_million_vehicle_km/lo.rate_per_million_vehicle_km,int(hi.accidents)))
        text=('Upper-to-lowest-interval rate ratios are '+', '.join(f'{ratio:.2f}' for _,ratio,_ in rows[:3])
              +' and '+f'{rows[3][1]:.2f}'+' in winter, spring, summer and autumn, respectively. '
              +'The upper groups contain '+', '.join(str(n) for _,_,n in rows[:3])+' and '+str(rows[3][2])
              +' accidents. These descriptive ratios summarise the seasonal panels; limited counts and different seasonal exposure do not support a stable ranking of seasons.\n')
        (OUT/f'{name}_seasonal_results.tex').write_text(text)


if __name__=='__main__':main()
