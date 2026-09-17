"""Heatmap and generated interpretation of fixed joint weather-frequency O/E."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from src.figures.thesis_style import save_figure
from src.tables.joint_detail import WIND_LABELS,TEMP_LABELS,contrasts

INPUT=Path('reports/main/tables/joint_wind_temperature_detail.csv')
TEX=Path('reports/thesis/generated')


def make_figure(data):
    ordered=data.sort_values('cell')
    values=ordered.oe.to_numpy().reshape(4,5)
    fig,ax=plt.subplots(figsize=(10.2,5.5),layout='constrained')
    norm=TwoSlopeNorm(vmin=0,vcenter=1,vmax=max(2.,float(np.nanmax(values))))
    palette=plt.get_cmap('RdBu_r')
    shown=ax.imshow(values,origin='lower',aspect='auto',cmap=palette,norm=norm)
    ax.set_xticks(range(5),['<−3', '[−3, 0)', '[0, 6)', '[6, 12)', '≥12'])
    ax.set_yticks(range(4),WIND_LABELS)
    ax.set_xlabel('Temperature interval (°C)')
    ax.set_ylabel('Mean wind interval (m/s)')
    ax.grid(False)
    for row in ordered.itertuples():
        rgb=palette(norm(row.oe))[:3]
        luminance=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
        marker='*' if row.sparse else ''
        ax.text(row.temperature_order,row.wind_order,f'{row.oe:.2f}{marker}\nn={row.observed_accidents}',
                ha='center',va='center',fontsize=12,color='white' if luminance<.5 else 'black')
    # Fine separators distinguish all cells without obscuring their colours.
    for x in np.arange(.5,4.5):ax.axvline(x,color='white',linewidth=.7)
    for y in np.arange(.5,3.5):ax.axhline(y,color='white',linewidth=.7)
    bar=fig.colorbar(shown,ax=ax,pad=.025,shrink=.85)
    bar.set_label('Observed / expected accidents (O/E)',fontsize=12)
    bar.set_ticks([0,.5,1,1.5,2,2.5])
    return fig


def narrative(data):
    cells=data.set_index(['wind_order','temperature_order'])
    rates=lambda w,t: f'{cells.loc[(w,t),"oe"]:.2f}'
    c=contrasts(data).set_index(['contrast','group'])
    ratio=lambda kind,group: f'{c.loc[(kind,group),"oe_ratio"]:.2f}'
    # Scientific prose below describes checked orderings, not a searched binning.
    for t in (0,1):assert np.all(np.diff([cells.loc[(w,t),'oe'] for w in range(4)])>0)
    assert np.all(np.diff([cells.loc[(w,2),'oe'] for w in range(3)])<0)
    assert cells.loc[(3,2),'oe']>cells.loc[(2,2),'oe']
    assert cells.loc[(1,3),'oe']>max(cells.loc[(0,3),'oe'],cells.loc[(2,3),'oe'])
    assert all(cells.loc[(3,t),'oe']>1 for t in range(4))
    assert all(cells.loc[(w,1),'oe']>1 for w in range(4))
    assert all(cells.loc[(w,4),'oe']>cells.loc[(w,3),'oe'] for w in range(3))
    highest=data.loc[data.oe.idxmax()]
    assert int(highest.cell)==19 and highest['sparse']
    supported=c.loc['High/low wind'].query('adequate_support')
    upper=data.query('wind_order == 3 and not sparse')
    assert len(upper)==4 and len(supported)==4
    assert upper.loc[upper.oe.idxmin(),'temperature_order']==2
    assert upper.loc[upper.oe.idxmax(),'temperature_order']==1
    assert all(cells.loc[(w,4),'oe']>1 for w in range(3))
    assert data['sparse'].sum()==1
    results=(
        r'Figure~\ref{fig:joint-weather-detail} shows that the upper-wind excess is not confined to one temperature range. '
        +r'Among the four temperature groups with adequate support, O/E at mean wind of at least 15 m/s ranges from '
        +f'{upper.oe.min():.2f}'+r' at 0--6$^{\circ}$C to '+f'{upper.oe.max():.2f} immediately below freezing. '
        +f'The corresponding high-to-low-wind contrasts range from {supported.oe_ratio.min():.2f} to {supported.oe_ratio.max():.2f}, '
        +r'indicating that the magnitude of the wind pattern is not uniform across temperature groups; however, no formal interaction is estimated.'
        +'\n\n'
        +r'The elevation immediately below freezing is present in every wind category, while temperatures of at least 12$^{\circ}$C remain elevated in all three wind groups below 15 m/s. '
        +r'The cell combining mean wind of at least 15 m/s with temperature of at least 12$^{\circ}$C has the largest O/E ('
        +f'{highest.oe:.2f}), but it contains only {int(highest.observed_accidents)} observed accidents compared with {highest.expected_accidents:.2f} expected and is the only sparse cell. '
        +r'It is therefore not interpreted as evidence of an especially strong combined effect. Overall, the joint results retain both the broad upper-wind excess and the non-linear temperature pattern.'+'\n')
    discussion=(r'The detailed joint description places the upper-wind excess in several temperature ranges and retains the warm-end elevation at winds below 15 m/s. '
                +r'However, the high-to-low-wind O/E contrast varies from '+ratio('High/low wind','0–6')
                +r' at 0--6$^{\circ}$C to '+ratio('High/low wind','<−3')
                +r' below $-3$$^{\circ}$C. This descriptive difference motivates further study of whether the wind association varies with temperature, but does not establish interaction. The combined high-wind warm estimate has too little support for a firm interpretation.'+'\n')
    return results,discussion


def main():
    data=pd.read_csv(INPUT)
    fig=make_figure(data)
    save_figure(fig,Path('reports/main/figures/joint_wind_temperature_detail.png'),dpi=240)
    plt.close(fig)
    results,discussion=narrative(data)
    TEX.mkdir(parents=True,exist_ok=True)
    (TEX/'joint_detail_results.tex').write_text(results)
    (TEX/'joint_detail_discussion.tex').write_text(discussion)


if __name__=='__main__':main()
