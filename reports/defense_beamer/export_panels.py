"""Presentation-only layout of the thesis plot artists; no analysis or CSV writes.
Run from repository root. Default exports six validated seasonal figures.
Original bars, labels, bins, limits and ticks are snapshotted before layout changes.
"""
from pathlib import Path
import argparse, json, hashlib, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.figures import oe_histo, weather_rate, traffic_weather_response
from src.figures.thesis_style import style_figure
from src.tables.monthly_vkt_rate import severity_rates

OUT=Path(__file__).resolve().parent/'assets'
POSITIONS=[(.58,.725,.39,.245),(.07,.385,.42,.265),(.565,.385,.42,.265),(.07,.068,.42,.265),(.565,.068,.42,.265)]

def signature(ax):
    return {'limits':list(ax.get_ylim()),'yticks':ax.get_yticks().tolist(),
            'xticks':[t.get_text() for t in ax.get_xticklabels()],
            'bars':[[p.get_x(),p.get_y(),p.get_width(),p.get_height(),list(p.get_facecolor())] for p in ax.patches],
            'texts':[t.get_text() for t in ax.texts]}

def arrange(fig,name,metric,xlabel):
    style_figure(fig);fig.canvas.draw()
    axes=fig.axes
    assert len(axes)==5
    before=[signature(a) for a in axes]
    fig.set_layout_engine(None)
    fig.set_size_inches(16,9)
    for ax,position,snap in zip(axes,POSITIONS,before):
        ax.set_position(position)
        ax.set_yticks(snap['yticks']);ax.set_ylim(snap['limits'])
    for leg in list(fig.legends):leg.remove()
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.045,.755),ncols=2,frameon=False,fontsize=12)
    fig.supxlabel(xlabel,x=.53,y=.012,fontsize=15)
    fig.supylabel(metric,x=.011,y=.36,fontsize=15)
    fig.canvas.draw()
    after=[signature(a) for a in axes]
    assert before==after, 'Layout altered scientific plot content'
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT/f'{name}.pdf')
    fig.savefig(OUT/f'{name}.png',dpi=120)
    plt.close(fig)
    return {'name':name,'panels':before,'unchanged_artist_check':True}

def traffic_panel():
    captured=[]
    original=traffic_weather_response.save_figure
    traffic_weather_response.save_figure=lambda fig,*a,**kw:captured.append(fig)
    try:
        traffic_weather_response.make_figure(pd.read_csv('data/analysis/traffic_weather_response.csv'),OUT/'unused.pdf')
    finally:
        traffic_weather_response.save_figure=original
    fig=captured[0];style_figure(fig);fig.canvas.draw()
    before=[signature(a) for a in fig.axes]
    fig.set_layout_engine(None);fig.set_size_inches(16,7.3)
    for ax,position,snap in zip(fig.axes,[(.065,.59,.42,.36),(.565,.59,.42,.36),(.28,.1,.5,.36)],before):
        ax.set_position(position);ax.set_yticks(snap['yticks']);ax.set_ylim(snap['limits'])
        # Keep panel headings clear of percentage annotations.
        for heading in ax.texts[:2]:
            heading.set_y(1.025);heading.set_verticalalignment('bottom')
    fig.supylabel('Observed traffic / expected traffic (%)',x=.012,y=.53,fontsize=15)
    fig.canvas.draw()
    assert before==[signature(a) for a in fig.axes]
    fig.savefig(OUT/'traffic_response.pdf')
    plt.close(fig)
    return {'name':'traffic_response','panels':before,'unchanged_artist_check':True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prototype',action='store_true');ap.add_argument('--traffic-only',action='store_true');args=ap.parse_args()
    if args.traffic_only:
        result=traffic_panel()
        (OUT/'traffic_audit.json').write_text(json.dumps(result,indent=2,default=lambda v:v.item()))
        return
    original_save=oe_histo.save_figure
    captured=[]
    oe_histo.save_figure=lambda fig,*a,**kw:captured.append(fig)
    data=oe_histo.disjoint_outcomes(pd.read_csv('reports/main/tables/weather_oe.csv'))
    audit=[]
    for var in (('f',) if args.prototype else oe_histo.VARIABLES):
        oe_histo.plot_variable(data,var,OUT/'unused.pdf')
        audit.append(arrange(captured.pop(),f'oe_{var}','Observed / expected accidents (O/E)',oe_histo.X_LABELS[var]))
    oe_histo.save_figure=original_save
    if not args.prototype:
        # Exact existing thesis display routine; validates retained event counts
        # against stored section totals and published annual severity rates.
        data=severity_rates(pd.read_csv('data/analysis/monthly_vkt_section.csv'),pd.read_csv('data/analysis/monthly_vkt.csv'),pd.read_csv('data/analysis/vkt_accidents.csv'))
        data=data.rename(columns={'observed_accidents':'accidents'})
        data['outcome']=data.outcome.replace({'Serious or fatal injury accidents':'Severe/fatal accidents'})
        captured=[];original_save=weather_rate.save_figure
        weather_rate.save_figure=lambda fig,path,**kw:captured.append((fig,Path(path).name))
        weather_rate.make_figures(data,OUT,variables=weather_rate.VARIABLES,prefix='unused_',annual_variables=('f','fg'))
        for fig,name in captured:
            if 'weather_rate_annual' in name:plt.close(fig);continue
            var=name.removeprefix('unused_').removesuffix('_traffic_rate_panels.png')
            audit.append(arrange(fig,f'vkt_{var}','Accidents per million estimated vehicle-km',weather_rate.X_LABELS[var]))
        weather_rate.save_figure=original_save
    if not args.prototype:
        result=traffic_panel()
        (OUT/'traffic_audit.json').write_text(json.dumps(result,indent=2,default=lambda v:v.item()))
    (OUT/('prototype_audit.json' if args.prototype else 'panel_audit.json')).write_text(json.dumps(audit,indent=2,default=lambda v:v.item()))
    print('Exported',len(audit),'presentation figures; original artists unchanged')
if __name__=='__main__':main()
