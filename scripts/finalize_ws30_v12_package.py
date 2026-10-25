"""Record fixed literature/source/model provenance and hash the final v12 handoff."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import platform

import numpy as np
import matplotlib

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research/evidence/ws30-v12-r1'
FIG=ROOT/'docs/research/figures/ws30-v12-r1'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,data):(DATA/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser();p.add_argument('--session-file',type=Path,required=True);p.add_argument('--references',type=Path,required=True);a=p.parse_args()
    context=None
    for line in a.session_file.open(encoding='utf-8'):
        d=json.loads(line)
        if d.get('type')=='turn_context':context=d
    c=context['payload'];assert (c['model'],c['effort'])==('gpt-6.1-sol','medium')
    mappings=[
        ('diffflow-2016','arXiv:1604.05107v1','paper-v1.pdf','analysis-technical.md','verification.md','separate class source, forwarding granularity and queue service contract','Sampled long-flow classification and blind spraying, Java simplified transport and class-independent queues differ from this fixed-QP shared RDMA queue. No project batch/P99 evidence.'),
        ('seqbalance-2024','arXiv:2407.09808v1','paper-v1.pdf','analysis-technical.md','verification.md','maximum completion aggregation and QP path scope','Splits WQEs into child QPs and uses feedback; this project preserves original QPs. Final journal body not compared. Parent-CQE and hardware results do not transfer.'),
        ('letflow-2017','NSDI 2017 USENIX official PDF, 15 pages including cover','paper-local.pdf','analysis-technical.md','verification.md','adaptation opportunity and actual flowlet actions','Random flowlet reselection and elastic flowlet size differ from pinned QP placement; 20-us release offset is not a flowlet threshold. TCP/hardware results are not project effects.'),
        ('conweave-2023','ACM SIGCOMM 2023 fixed local PDF','paper-local.pdf','analysis-technical.md','verification.md','separate RTT/control feedback, rerouting and receive VOQ; keep baseline faithful','Epoch/phase control, TAIL/CLEAR and in-network reordering differ from first-packet placement. Current common PFC-off/IRN-on simulation does not measure the original hardware or every dynamic regime.'),
        ('gemma','IEEE HPCC 2024 fixed six-page PDF','paper-local.pdf','analysis-technical.md','verification.md','separate local/downstream information and reordering cost','Downstream queue synchronization, packet rerouting and switch-side queues differ from local-QP placement. No hardware/production or MoE/P99 transfer.'),
        ('sglb-2025','ACM SIGCOMM 2025 fixed 20-page local PDF','paper-local.pdf','analysis-technical.md','verification.md','global feedback age and scalable state as a distinct design axis','GLB engines/SyncMesh and cluster state differ from local first-packet placement. Hardware, CCT and production gains cannot be substituted for these paired batch/P99 effects.'),
        ('hula-2016','ACM SOSR 2016 fixed local PDF','paper-local.pdf','analysis-technical.md','verification.md','per-hop bottleneck state, probe freshness and flowlet opportunity','Probe-maintained destination next hop and flowlet forwarding differ from two local QP candidates. TCP/ns-2 and P4 feasibility are outside current measurements.'),
        ('drill-2017','SIGCOMM 2017 author-hosted PDF','paper-author.pdf',None,'ws30-citation-receipt.md','per-packet local-queue comparison and correct baseline citation','Citation and mechanism scope only; candidate directory has no completed page-by-page technical review. U16 fixes the first candidate pair and is not the native DRILL implementation. Historical DRILL recovery counters remain unobserved.')]
    entries=[]
    for folder,version,pdf,technical,verification,method,boundary in mappings:
        files=[f'papers/{folder}/{pdf}',f'papers/{folder}/{verification}']
        if technical:files.append(f'papers/{folder}/{technical}')
        entries.append({'paper':folder,'version':version,'borrowed_method':method,'difference_and_nontransferable_claim':boundary,
            'reading_scope':'relevant local technical analysis and verification; PDF hash recomputed' if technical else 'existing citation and mechanism receipt; full technical reading not claimed',
            'file_sha256':{f:sha(a.references/f) for f in files}})
    save('reference-review.json',{'node':'WS-30 final cross-stage v12 synthesis','entry_files':{f:sha(a.references/f) for f in ('README.md','reading-log.md')},
        'entries':entries,'new_mechanism_admitted':False,'author_effects_used_as_project_evidence':False,
        'historical_project_mapping_note':'Paper-folder project descriptions reflect their reading dates; current mechanism is checked against the fixed WS-30 source, not copied from historical prose.'})
    save('related-work-mapping.json',entries)
    sourcefiles=['src/point-to-point/model/switch-node.cc','src/point-to-point/model/switch-node.h',
        'src/point-to-point/model/rdma-hw.cc','src/point-to-point/model/workload-tag.h','src/point-to-point/model/workload-tag.cc',
        'src/applications/model/rdma-client.cc','scratch/network-load-balance.cc','scripts/make_ws25_demand.py']
    blobs={}
    source='1ef424749e3c551dd788d0a709bd8e21c7cc89c9'
    for f in sourcefiles:blobs[f]=hashlib.sha256(subprocess.check_output(['git','show',source+':'+f],cwd=ROOT)).hexdigest()
    scripts=['build_ws30_v12_package.py','plot_ws30_v12_package.py','write_ws30_v12_synthesis.py','finalize_ws30_v12_package.py','verify_ws30_v12_package.py']
    summaries={}
    for phase in ('main','lead','composition'):
        f=ROOT/f'results/ws30-stage3-{phase}-summary-r5.json'
        d=json.loads(f.read_text());summaries[phase]={'sha256':sha(f),'verified':len(d['verified']),'failures':len(d['failures']),
            'pending':len(d['pending']),'controller_events':[e for e in d['events'] if e['event'] in ('controller_started','controller_stop','admission_stop')]}
    provenance={'analysis_context':{'timestamp':context['timestamp'],**{k:c[k] for k in ('turn_id','model','effort')}},
        'base_delivery_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'new_remote_experiments':0,'source_sha':source,'composition_source_sha':'2d7e31a9f6ae24f1514d02cbf341d27e6ec0717f','source_blob_sha256':blobs,
        'software':{'python':sys.version,'numpy':np.__version__,'matplotlib':matplotlib.__version__,'platform':platform.platform(),
                    'bootstrap':'random.Random(20263003) 10000 x 24 indices; numpy median, numpy percentile default linear interpolation'},
        'scripts':{f'scripts/{f}':sha(ROOT/'scripts'/f) for f in scripts},'controller_summaries':summaries,
        'numeric_package_sha256':sha(DATA/'package.json'),'reviews_sha256':sha(DATA/'review-sources.json'),
        'limits':['Historical native DRILL independent retransmit/gap counters unavailable.',
                  'Formal full packet end-to-end paths were not logged; technical full paths and formal switch-QP summaries are separate.',
                  'Main unknown-PID original snapshot lacks complete identity; lead PID further attribution unresolved.',
                  'Short fixture simulations can finish between RSS samples; zero sampled RSS is not a zero peak.',
                  'No dynamic-activation workload, hardware, production SLO or real training validation.']}
    save('provenance.json',provenance)
    manifest={}
    for directory in (DATA,FIG):
        for f in directory.iterdir():
            if f.is_file() and f.name!='manifest.json':manifest[str(f.relative_to(ROOT)).replace('\\','/')]=sha(f)
    for f in ('ws30-v12-evidence-synthesis-r1.md','ws30-v12-review-acceptance-r1.md'):
        path=ROOT/'docs/research'/f;manifest[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
    save('manifest.json',{'file_sha256':manifest,'scope':'new cross-stage numeric/figure/report package; original per-cell raw hashes and locations are in D4',
        'linked_reused_figures':{'docs/research/figures/ws30-stage3-composition-r1/probe-choice.png':sha(ROOT/'docs/research/figures/ws30-stage3-composition-r1/probe-choice.png')}})
    print(json.dumps({'model':c['model'],'effort':c['effort'],'references':len(entries),'manifest_files':len(manifest)}))


if __name__=='__main__':main()
