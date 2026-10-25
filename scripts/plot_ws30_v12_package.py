"""Final manuscript evidence figures; every paired demand/queue event is retained."""
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research/evidence/ws30-v12-r1'
OUT=ROOT/'docs/research/figures/ws30-v12-r1'
sys.path.insert(0,str(Path.home()/'.codex/skills/nature-figure/scripts'))
from audit_panel_alignment import require_matplotlib_panel_alignment


def load(name):return list(csv.DictReader((DATA/name).open(encoding='utf-8')))
def export(fig,name):
    base=OUT/name;fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(base)+'.alignment.json',strict=True)
    fig.savefig(str(base)+'.svg')
    fig.savefig(str(base)+'.pdf')
    p=base.with_suffix('.svg');p.write_text('\n'.join(l.rstrip() for l in p.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    fig.savefig(str(base)+'.png',dpi=600);plt.close(fig)


def paired(name,family,specs,height):
    points=load('figure-points.csv');stats=load('figure-estimates.csv')
    fig,axes=plt.subplots(1,2,figsize=(7.2,height),sharey=True)
    fig.subplots_adjust(left=.23,right=.98,bottom=.14,top=.90,wspace=.16)
    for pi,(ax,metric,title) in enumerate(zip(axes,['moe_batch','background_p99'],['MoE batch completion','Background P99 FCT'])):
        for j,(condition,contrast,label,color) in enumerate(specs):
            selected=[p for p in points if (p['family'],p['condition'],p['contrast'],p['metric'])==(family,condition,contrast,metric)]
            assert len(selected)==24
            values=[float(p['value']) for p in selected];y=len(specs)-j-1
            ax.scatter(values,y+np.linspace(-.16,.16,24),s=11,color=color,alpha=.65,linewidths=0,zorder=2)
            s=next(p for p in stats if (p['family'],p['condition'],p['contrast'],p['metric'])==(family,condition,contrast,metric))
            center,low,high=(float(s[k]) for k in ('median_pct','ci_low_pct','ci_high_pct'))
            ax.errorbar(center,y,xerr=[[center-low],[high-center]],fmt='D',color='#17242D',markersize=3.6,linewidth=1.1,capsize=2.5,zorder=4)
        ax.axvline(0,color='#8B959B',linewidth=.7,zorder=0)
        if metric=='background_p99' and family in ('F1','F2'):ax.axvline(3,color='#A66D40',linestyle='--',linewidth=.7,zorder=0)
        ax.set(yticks=list(range(len(specs)-1,-1,-1)),yticklabels=[r[2] for r in specs],
               ylim=(-.5,len(specs)-.5),xlabel='Paired change (%)',title=f'({chr(97+pi)}) {title}')
        ax.tick_params(axis='y',length=0)
        ax.margins(x=.08)
    export(fig,name)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
        'font.size':8,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,
        'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,
        'svg.fonttype':'none','pdf.fonttype':42,'legend.frameon':False})
    blue='#397A9B';gray='#8B979E'
    paired('F1-four-cohorts','F1',[(c,'Full/E',label,blue) for c,label in [
        ('old','Old cohort (n = 24)'),('main_history','Historical main (n = 24)'),
        ('factorial','A/B cohort (n = 24)'),('new','New cohort (n = 24)')]],3.6)
    paired('F2-eight-arms','F2',[('synchronous',a+'/E',a,blue) for a in ['E','H16','R16','Q16','C16','U16','Q12','M16']],4.8)
    paired('F3-main-attribution','F3',[('synchronous',c,c,blue) for c in ['H16/E','R16/H16','Q16/R16','Q16/H16','U16/Q16','Q12/E','Q16/Q12','C16/Q16','Q16/M16']],5.3)
    paired('F4-class-and-timing','F4',[(condition,c,c+' | '+label,color)
        for c in ['C16/Q16','Q16/E','C16/E'] for condition,label,color in [('synchronous','Sync',gray),('lead20us','Lead 20 μs',blue)]],4.4)

    events=load('F5-queue-events.csv')
    metrics=load('F5-metrics.csv');ports={r['id']:int(r['chosen_port']) for r in metrics}
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.6),sharex=True,sharey=True)
    fig.subplots_adjust(left=.11,right=.98,bottom=.18,top=.75,wspace=.16)
    for pi,(ax,cont,title) in enumerate(zip(axes,[0,1],['Stop after prefill','Later background arrivals'])):
        ids=list(dict.fromkeys(e['id'] for e in events if int(e['continuing'])==cont));assert len(ids)==6
        for exp in ids:
            for port in (2,3):
                stream=[e for e in events if e['id']==exp and int(e['port'])==port]
                times=[0]+[(int(e['time_ns'])-2000000000)/1000 for e in stream]
                queues=[0]+[int(e['total'])/1024 for e in stream]
                ax.step(times,queues,where='post',color=blue if port==ports[exp] else gray,alpha=.4,linewidth=.85)
        ax.axvline(21.020,color='#607079',linestyle=':',linewidth=.8)
        ax.axvline(22,color='#17242D',linestyle='--',linewidth=.7)
        ax.set(xlim=(0,75),xlabel='Time from full tag-2 origin (μs)',title=f'({chr(97+pi)}) {title}')
    axes[0].set_ylabel('Output queue (KiB)')
    handles=[Line2D([0],[0],color=blue,label='Chosen port'),Line2D([0],[0],color=gray,label='Other port'),
             Line2D([0],[0],color='#607079',linestyle=':',label='Probe arrives: 21.020 μs'),
             Line2D([0],[0],color='#17242D',linestyle='--',label='Hold released: 22 μs')]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.54,.995),ncol=2,columnspacing=2)
    export(fig,'F5-composition-queue-timing')
    contract={'archetype':'quantitative grids','backend':'Python / Matplotlib',
        'core_claim':'Local queue information and QP decision granularity have identifiable paired effects; class weighting changes controlled decisions without an identified batch-time increment.',
        'figures':{'F1':'four independent cohorts kept separate; both business metrics',
                   'F2':'all eight arms vs E; all 24 demand points per arm',
                   'F3':'nine frozen attribution contrasts; exact denominators and both metrics',
                   'F4':'same 24 demands under correlated sync/lead conditions; all three contrasts',
                   'F5':'all 12 formal fixture runs and both real output queues, no event thinning'},
        'statistics':'Points: fixed demand-level paired percentages. Diamonds: median. Bars: nominal 95% bootstrap percentile intervals (10000 demand resamples). No significance labels. F5 has raw trajectories and no interval.',
        'data_exclusions':[],'dimensions':'183 mm nominal width; 600-dpi PNG and editable PDF/SVG',
        'F5_overlap':'Each panel overlays six runs x two output ports; chosen/other normalization is per actual probe decision, not averaging.'}
    (OUT/'figure-contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
