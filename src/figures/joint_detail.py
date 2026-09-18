"""Five-by-eight joint O/E heatmap and generated interpretation."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.patches import Rectangle
from matplotlib.ticker import FormatStrFormatter
from src.figures.thesis_style import save_figure

INPUT=Path('reports/main/tables/joint_wind_temperature_5x8.csv')
TEX=Path('reports/thesis/generated')


def _pooled_cell(group):
    observed=int(group.observed_accidents.sum())
    expected=float(group.expected_accidents.sum())
    if expected<=0:
        raise ValueError('Pooled expected accident count must be positive')
    return observed/expected,observed,observed<10 or expected<5


def make_figure(data):
    ordered=data.sort_values('cell')
    if ordered.cell.tolist()!=list(range(40)):
        raise ValueError('Expected the complete 5×8 joint weather grid')
    # Margins pool counts, not O/E ratios. The upper-right corner pools all cells.
    cells=[(row.temperature_order,row.wind_order,row.oe,int(row.observed_accidents),bool(row.sparse))
           for row in ordered.itertuples()]
    gap=5/15  # The figure is included at its native 190 mm width.
    for wind,group in data.groupby('wind_order'):
        cells.append((8+gap,wind,*_pooled_cell(group)))
    for temperature,group in data.groupby('temperature_order'):
        cells.append((temperature,5+gap,*_pooled_cell(group)))
    cells.append((8+gap,5+gap,*_pooled_cell(data)))

    mm=1/25.4
    fig=plt.figure(figsize=(190*mm,125*mm))
    left,bottom,cell_mm=25,18,15
    plot_width,plot_height=(9+gap)*cell_mm,(6+gap)*cell_mm
    ax=fig.add_axes([left/190,bottom/125,plot_width/190,plot_height/125])
    # Logarithmic numeric scale, with neutral white retained at O/E = 1.
    norm=LogNorm(vmin=.62,vmax=7.63,clip=True)
    neutral=float(norm(1))
    palette=LinearSegmentedColormap.from_list('joint_oe_linear',[
        (0,'#6FAFD4'),(neutral,'#F7F7F7'),(.5,'#E99679'),(1,'#7F001F')])
    for x,y,oe,observed,sparse in cells:
        color=palette(norm(oe))
        ax.add_patch(Rectangle((x-.5,y-.5),1,1,facecolor=color,
                               edgecolor='white',linewidth=.7))
        rgb=color[:3]
        luminance=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
        marker='*' if sparse else ''
        ax.text(x,y,f'{oe:.2f}{marker}\nn={observed}',ha='center',va='center',
                fontsize=8,color='white' if luminance<.5 else 'black')
    # Give each separated block the same black outer box as the original heatmap.
    for x,y,width,height in ((-.5,-.5,8,5),(-.5,4.5+gap,8,1),
                             (7.5+gap,-.5,1,5),(7.5+gap,4.5+gap,1,1)):
        ax.add_patch(Rectangle((x,y),width,height,fill=False,
                               edgecolor='black',linewidth=.8,zorder=3))
    ax.set_xlim(-.5,8.5+gap)
    ax.set_ylim(-.5,5.5+gap)
    ax.set_aspect('equal')
    ax.set_xticks([*range(8),8+gap],
                  ['<−6','[−6, −3]','[−3, 0]','[0, 3]','[3, 6]',
                   '[6, 9]','[9, 12]','≥12','All\ntemperatures'])
    ax.set_yticks([*range(5),5+gap],
                  ['0–5','5–10','10–15','15–20','≥20','All wind\nspeeds'])
    ax.tick_params(length=0,pad=4,labelsize=8)
    ax.set_xlabel('Temperature interval (°C)',fontsize=9.5,labelpad=4)
    ax.set_ylabel('Mean wind interval (m/s)',fontsize=9.5,labelpad=4)
    for spine in ax.spines.values():spine.set_visible(False)
    # Fixed dimensions keep the marginal gaps and doubled 8 mm colour bar stable.
    cax=fig.add_axes([(left+plot_width+4)/190,(bottom+10)/125,8/190,75/125])
    bar=fig.colorbar(ScalarMappable(norm=norm,cmap=palette),cax=cax)
    bar.set_label('Observed / expected accidents (O/E)',fontsize=8,labelpad=4)
    bar.set_ticks(range(1,8))
    bar.ax.yaxis.set_major_formatter(FormatStrFormatter('%d'))
    bar.ax.minorticks_off()
    bar.ax.tick_params(labelsize=8)
    return fig


def narrative(data):
    if data.sort_values('cell').cell.tolist()!=list(range(40)):
        raise ValueError('Narrative requires the complete 5×8 grid')
    cells=data.set_index(['wind_order','temperature_order'])
    warm=data.query('temperature_order == 7').sort_values('wind_order')
    freezing=data.query('temperature_order == 2')
    assert warm.oe.gt(1).all() and freezing.oe.gt(1).all()
    assert warm['sparse'].tolist()==[False,False,False,True,True]
    supported=data.query('wind_order == 3 and not sparse')
    high=data.query('wind_order == 4')
    highest=data.loc[data.oe.idxmax()]
    assert len(supported)==7 and supported.loc[supported.oe.idxmin(),'temperature_order']==4
    assert supported.loc[supported.oe.idxmax(),'temperature_order']==2
    assert high['sparse'].sum()==6 and int(highest.cell)==39 and highest['sparse']
    assert int(data.observed_accidents.sum())==6259
    assert np.isclose(data.expected_accidents.sum(),6259,rtol=0,atol=1e-8)
    results=(
        r'The warm-weather excess is not confined to strong wind. '
        +r'At temperatures of at least 12$^{\circ}$C, accidents were more frequent'+'\n'
        +r'than expected from local weather frequency in every wind category.'+'\n'
        +r'However, the two highest wind categories contained too few accidents'+'\n'
        +r'for reliable comparisons. '
        +r'O/E is also above one immediately below freezing in every wind category (see Figure~\ref{fig:joint-weather-detail}).'
        +'\n\n'
        +rf'Cold conditions do not show a uniform excess. Below $-6$$^{{\circ}}$C, O/E is {cells.loc[(0,0),"oe"]:.2f} at wind speeds below 5 m/s but {cells.loc[(3,0),"oe"]:.2f} at 15--20 m/s. '
        +r'This illustrates how the temperature pattern varies across wind categories without establishing a statistical interaction.'
        +rf' Within the 15--20 m/s row, cells meeting the support rule range from O/E {supported.oe.min():.2f} at 3--6$^{{\circ}}$C to {supported.oe.max():.2f} immediately below freezing.'
        +'\n\n'
        +r'Six of the eight cells at wind speeds of at least 20 m/s have limited support. '
        +rf'The largest O/E ({highest.oe:.2f}) occurs at 20 m/s or above and at least 12$^{{\circ}}$C, but represents only {int(highest.observed_accidents)} observed accidents versus {highest.expected_accidents:.2f} expected. '
        +r'That extreme cell should not be interpreted as reliable evidence of an especially strong combined effect.'+'\n')
    discussion=(r'The finer joint grid retains the upper-wind and non-linear temperature patterns visible in the marginal figures. '
                +r'Crossing the two variables leaves most cells at 20 m/s or above sparsely supported. Differences between individual temperature-specific wind ratios remain descriptive and do not establish interaction.'+'\n')
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
