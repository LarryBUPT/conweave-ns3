"""Composition rule response and every matched background-flow cost, Python only."""
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
OUT=ROOT/'docs/research/figures/ws30-stage3-composition-r1'
sys.path.insert(0,str(Path.home()/'.codex/skills/nature-figure/scripts'))
from audit_panel_alignment import require_matplotlib_panel_alignment


def export(fig,name):
    base=OUT/name
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(base)+'.alignment.json',strict=True)
    fig.savefig(str(base)+'.pdf')
    fig.savefig(str(base)+'.svg')
    svg=base.with_suffix('.svg')
    svg.write_text('\n'.join(l.rstrip() for l in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    fig.savefig(str(base)+'.png',dpi=600)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
        'font.size':8,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,
        'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,
        'svg.fonttype':'none','pdf.fonttype':42,'legend.frameon':False})
    data=json.loads((EV/'ws30-stage3-composition-analysis-r1.json').read_text(encoding='utf-8'))
    rows={(r['swap'],r['continuing'],r['arm']):r for r in data['rows']}
    conditions=[(0,0),(1,0),(0,1),(1,1)]
    labels=['Stop / swap 0','Stop / swap 1','Continue / swap 0','Continue / swap 1']
    arms=['E','Q16','C16']
    ports=np.array([[rows[s,c,a]['decision']['chosen_port'] for a in arms] for s,c in conditions])
    fig,ax=plt.subplots(figsize=(4.7,2.6))
    fig.subplots_adjust(left=.34,right=.95,bottom=.18,top=.85)
    ax.imshow(ports,cmap=ListedColormap(['#D6DEE2','#9BC1D2']),vmin=2,vmax=3,aspect='auto')
    for y in range(4):
        for x in range(3):ax.text(x,y,str(ports[y,x]),ha='center',va='center',fontsize=11,color='#17242D')
    ax.set(xticks=range(3),xticklabels=arms,yticks=range(4),yticklabels=labels,title='Probe output port')
    ax.tick_params(length=0,pad=7)
    for spine in ax.spines.values():spine.set_visible(False)
    export(fig,'probe-choice')

    flows=list(csv.DictReader((EV/'ws30-stage3-composition-flow-contrasts-r1.csv').open(encoding='utf-8')))
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.9),sharey=True)
    fig.subplots_adjust(left=.21,right=.98,bottom=.17,top=.82,wspace=.18)
    styles=[('Prefill',lambda f:int(f['size'])==31232,'#687982','s'),
            ('Later dst 1',lambda f:int(f['size'])==8000 and int(f['dst'])==1,'#397A9B','o'),
            ('Later dst 2',lambda f:int(f['size'])==8000 and int(f['dst'])==2,'#B4774A','^')]
    for pi,(ax,contrast) in enumerate(zip(axes,['C16/Q16','C16/E'])):
        for j,(swap,cont) in enumerate(conditions):
            values=[f for f in flows if f['contrast']==contrast and int(f['swap'])==swap and int(f['continuing'])==cont and int(f['tag'])==1]
            assert len(values)==(34 if cont else 2)
            for label,select,color,marker in styles:
                group=[f for f in values if select(f)]
                if not group:continue
                ys=3-j+np.linspace(-.13,.13,len(group))
                ax.scatter([int(f['change_ns'])/1000 for f in group],ys,s=13,c=color,marker=marker,
                    alpha=.75,linewidths=0,label=label if j==2 and pi==0 else None,zorder=3)
        ax.axvline(0,color='#A7ADB2',linewidth=.65,zorder=0)
        ax.set(xlim=(-4.2,4.2),ylim=(-.5,3.5),xticks=[-4,-2,0,2,4],yticks=[3,2,1,0],yticklabels=labels,
               xlabel='Background FCT change (us)',title=f'({chr(97+pi)}) {contrast}')
        ax.tick_params(axis='y',length=0)
    axes[0].legend(loc='upper center',bbox_to_anchor=(1.08,1.22),ncol=3,handletextpad=.3,columnspacing=1.1)
    export(fig,'background-flow-transfer')


if __name__=='__main__':main()
