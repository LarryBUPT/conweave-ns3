"""Python figure pipeline for verified future inputs. Never draws mock data.
Existing engineering data are parser fixtures only and are refused here.
"""
import argparse
import collections
import csv
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_ws30_v13_pending import ROOT,CONTRACT,DISPLAY,read,sha,require,write_json
from run_ws30_v14 import require_model

COHORT={'fresh-pairs':'Fresh-QP demands','historical-A':'Historical demand set A','historical-B':'Historical demand set B','sustained-pilot':'Sustained workload pilot'}

def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser();p.add_argument('analysis',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--qa-tools',type=Path);p.add_argument('--session-file',type=Path);p.add_argument('--contrast',action='append',help='Internal candidate:reference key; exported labels use scientific method names');p.add_argument('--allow-partial-descriptive',action='store_true');args=p.parse_args()
    source=args.analysis.resolve();out=args.out.resolve();require(source.is_relative_to(ROOT) and out.is_relative_to(ROOT),'Use this worktree only')
    require(not (source/'parser-validation.json').exists(),'Engineering/parser fixtures are not formal figure inputs')
    summary=read(source/'summary.json');require(summary['contract_sha256']==sha(CONTRACT),'Analysis contract mismatch')
    out.mkdir(parents=True,exist_ok=False)
    points=[r for r in rows(source/'paired-endpoints.csv') if r['status']=='PAIRED']
    groups=collections.defaultdict(list)
    for row in points:
        if args.contrast and row['candidate']+':'+row['reference'] not in args.contrast:continue
        groups[(row['cohort'],row['condition'],row['candidate'],row['reference'])].append(row)
    manifest={'analysis_summary_sha256':sha(source/'summary.json'),'contract_sha256':sha(CONTRACT),'script_sha256':sha(Path(__file__)),'source_map_sha256':sha(source/'source-map.json'),'publication_labels_contain_project_ids':False,'figures':[],'skipped':[],'paper_release_ready':False}
    if not groups:
        manifest['skipped'].append({'reason':'No verified paired target raw; no empty or simulated-result figures generated','cell_status_counts':summary['status_counts']})
        write_json(out/'figure-manifest.json',manifest);print('No verified target pairs: 0 figures; pending status preserved.');return
    require(args.qa_tools is not None,'Selected-backend QA tools directory required before rendering')
    require_model(args.session_file,'analysis')
    for script in ('audit_pdf_text.py','audit_figure_collisions.py'):require((args.qa_tools/script).is_file(),'Missing selected-backend QA tool: '+script)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7})
    dist=rows(source/'per-input-distributions.csv');tail=rows(source/'tail-decomposition.csv');rounds=rows(source/'round-pairs.csv');cost=read(source/'costs.json')
    blue='#376A98';orange='#B87539';gray='#777777'
    def save(fig,name,group,kind,data,n,expected,notes):
        fig.tight_layout();stem=out/name
        for extension in ('svg','pdf','png'):fig.savefig(str(stem)+'.'+extension,dpi=180 if extension=='png' else 600)
        plt.close(fig)
        write_json(Path(str(stem)+'.source.json'),data)
        glyph=subprocess.run([sys.executable,str(args.qa_tools/'audit_pdf_text.py'),str(stem)+'.pdf','--min-pt','5','--json'],text=True,capture_output=True)
        Path(str(stem)+'.glyph-qa.json').write_text(glyph.stdout,encoding='utf-8')
        collision=subprocess.run([sys.executable,str(args.qa_tools/'audit_figure_collisions.py'),str(stem)+'.pdf','--json-out',str(stem)+'.collision-qa.json'],text=True,capture_output=True)
        manifest['figures'].append({'name':name,'kind':kind,'cohort':group[0],'condition':group[1],'candidate':group[2],'reference':group[3],'display_candidate':DISPLAY[group[2]],'display_reference':DISPLAY[group[3]],'n_independent_demands':n,'expected_n':expected,'partial_descriptive':n!=expected,'notes':notes,'alignment':'not applicable: single panel','glyph_returncode':glyph.returncode,'collision_returncode':collision.returncode,'visual_review':'PENDING at final size; automatic checks do not certify scientific interpretation','pdf_sha256':sha(Path(str(stem)+'.pdf'))})
        write_json(out/'figure-manifest.json',manifest)
        require(glyph.returncode==0 and collision.returncode==0,'Rendered QA failed; exports retained, publication delivery blocked')
    for group,data in sorted(groups.items()):
        cohort,condition,candidate,reference=group;data=sorted(data,key=lambda r:int(r['demand_seed']));n=len(data);expected=2 if cohort=='sustained-pilot' else 24
        if n!=expected and not args.allow_partial_descriptive:
            manifest['skipped'].append({'group':group,'paired_n':n,'expected_n':expected,'reason':'incomplete cohort; explicit partial descriptive opt-in required'});continue
        seedindex={r['demand_seed']:i+1 for i,r in enumerate(data)}
        name=cohort+'-'+condition+'-'+candidate.lower()+'-vs-'+reference.lower()
        title='\n'.join(textwrap.wrap(DISPLAY[candidate]+' versus '+DISPLAY[reference],65))
        subtitle=COHORT[cohort]+', '+condition+'; n='+str(n)+' demands'+(' (descriptive pilot)' if expected==2 else '')+(' [INCOMPLETE '+str(n)+'/'+str(expected)+']' if n!=expected else '')
        def canvas():
            fig,ax=plt.subplots(figsize=(7.2,4.2));ax.set_title(title+'\n'+subtitle);ax.axhline(0,color='#aaaaaa',linewidth=.6,zorder=0);return fig,ax
        fig,ax=canvas();ax.axvline(0,color='#aaaaaa',linewidth=.6,zorder=0)
        ax.scatter([float(r['foreground_change_pct']) for r in data],[float(r['background_p99_change_pct']) for r in data],s=24,color=blue,edgecolor='white',linewidth=.4)
        ax.set_xlabel('Foreground completion span change (%)');ax.set_ylabel('Background P99 FCT change (%)')
        save(fig,name+'-paired-tradeoff',group,'paired endpoint scatter',data,n,expected,'One point per matched demand; negative values mean shorter times on each axis. No pooled-flow inference.')
        match=lambda r:(r['cohort'],r['condition'],r['candidate'],r['reference'])==group
        for tag in ('1','2'):
            selected=[r for r in dist if match(r) and r['tag']==tag];index={(r['demand_seed'],float(r['quantile'])):r for r in selected}
            fig,ax=canvas()
            for seed,x in seedindex.items():
                lo=float(index[(seed,.1)]['paired_change_pct']);med=float(index[(seed,.5)]['paired_change_pct']);hi=float(index[(seed,.9)]['paired_change_pct'])
                ax.vlines(x,lo,hi,color=gray,linewidth=1);ax.scatter([x],[med],color=blue,s=20)
            ax.set_xticks(range(1,n+1));ax.set_xlabel('Matched demand (ordinal; see source map)');ax.set_ylabel(('Background' if tag=='1' else 'Message')+' identity-paired FCT change (%)')
            save(fig,name+'-tag'+tag+'-within-demand',group,'within-demand matched-flow distribution',selected,n,expected,'Bars: 10th–90th percentiles of identity-paired flow changes; dots: medians. Bars are within-demand heterogeneity, not confidence intervals.')
        selected=sorted([r for r in tail if match(r) and r['round']=='all'],key=lambda r:int(r['demand_seed']))
        fig,ax=canvas();x=list(range(1,n+1));old=[float(r['old_tail_delta_ns'])/1000 for r in selected];replacement=[float(r['replacement_gap_ns'])/1000 for r in selected];total=[float(r['batch_delta_ns'])/1000 for r in selected]
        ax.bar(x,old,color=blue,label='Original tail change');ax.bar(x,replacement,bottom=old,color=orange,label='Replacement gap');ax.scatter(x,total,color='black',s=12,label='Total change',zorder=3)
        ax.set_xticks(x);ax.set_xlabel('Matched demand (ordinal)');ax.set_ylabel('Foreground span change (µs)');ax.legend(loc='best')
        save(fig,name+'-tail-decomposition',group,'algebraic original/replacement tail decomposition',selected,n,expected,'Total = candidate change on original reference tail + nonnegative replacement gap. Identity ties are retained in source data. Algebra, not causal mediation.')
        lookup={(r['demand_seed'],r['arm']):r for r in cost if r['cohort']==cohort and r['condition']==condition}
        cache=[]
        for seed,x in seedindex.items():
            for arm in (reference,candidate):
                obs=lookup.get((int(seed),arm)) or lookup.get((seed,arm))
                if obs and obs['state']:cache.append({'demand_seed':seed,'ordinal':x,'arm':arm,'sum_per_switch_peaks':sum(r['peak'] for r in obs['state']['per_switch'])})
        if cache:
            fig,ax=canvas()
            for arm,color,marker in ((reference,gray,'o'),(candidate,blue,'x')):
                values=[r for r in cache if r['arm']==arm]
                if values:ax.scatter([r['ordinal'] for r in values],[r['sum_per_switch_peaks'] for r in values],color=color,marker=marker,s=22,label=DISPLAY[arm])
            ax.set_xticks(range(1,n+1));ax.set_xlabel('Matched demand (ordinal)');ax.set_ylabel('Sum of per-switch peak cache entries');ax.legend(loc='best')
            save(fig,name+'-cache-entries',group,'observed cache allocation',cache,n,expected,'Sum of independently observed switch peaks; not a simultaneous network peak or byte memory. Missing arms lack this observer and are not zero-filled.')
        else:manifest['skipped'].append({'group':group,'figure':'cache-entries','reason':'No cache entry observer; memory cost is unknown, not zero'})
        for tag in ('1','2'):
            selected=[]
            for seed,x in seedindex.items():
                for arm in (reference,candidate):
                    obs=lookup.get((int(seed),arm)) or lookup.get((seed,arm))
                    if obs and obs['transport'] and tag in obs['transport']:
                        selected.append({'demand_seed':seed,'ordinal':x,'arm':arm,'retransmission_payload_pct':100*obs['transport'][tag]['retransmit_bytes']/obs['payload_bytes_by_tag'][tag]})
            if not selected:
                manifest['skipped'].append({'group':group,'figure':'recovery-tag'+tag,'reason':'Recovery counters unavailable; not interpreted as zero'});continue
            fig,ax=canvas()
            for arm,color,marker in ((reference,gray,'o'),(candidate,blue,'x')):
                values=[r for r in selected if r['arm']==arm]
                if values:ax.scatter([r['ordinal'] for r in values],[r['retransmission_payload_pct'] for r in values],color=color,marker=marker,s=22,label=DISPLAY[arm])
            ax.set_xticks(range(1,n+1));ax.set_xlabel('Matched demand (ordinal)');ax.set_ylabel(('Background' if tag=='1' else 'Message')+' retransmitted bytes / input payload (%)');ax.legend(loc='best')
            save(fig,name+'-tag'+tag+'-recovery',group,'actual retransmission cost',selected,n,expected,'Missing observer fields are absent, never zero-filled; numerator is actual repeated payload bytes, not inferred packet gaps.')
        if cohort=='sustained-pilot':
            selected=[r for r in rounds if match(r)];fig,ax=canvas()
            for j,(seed,x) in enumerate(seedindex.items()):
                points=sorted([r for r in selected if r['demand_seed']==seed],key=lambda r:int(r['round']))
                ax.plot([int(r['round'])+1 for r in points],[float(r['batch_change_pct']) for r in points],marker=('o','s')[j%2],color=(blue,orange)[j%2],label='Demand '+str(x))
            ax.set_xticks(range(1,9));ax.set_xlabel('Request round');ax.set_ylabel('Round batch time change (%)');ax.legend(loc='best')
            save(fig,name+'-rounds',group,'round trajectories within the same two demands',selected,n,expected,'Eight rounds per seed are repeated measures; n remains two. Each round uses its own original demand origin.')
    write_json(out/'figure-manifest.json',manifest);print(json.dumps({'figures':len(manifest['figures']),'skipped':len(manifest['skipped']),'visual_review_pending':True}))
if __name__=='__main__':main()
