"""Persist execution/model/source/reference evidence for the completed composition node."""
import argparse
import json
from pathlib import Path
import subprocess

from analyze_ws30_stage3_composition import ROOT, EV, sha, write
import run_ws30_stage3 as runner


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--session-file',type=Path,required=True)
    parser.add_argument('--references',type=Path,required=True)
    args=parser.parse_args()
    context=None
    for line in args.session_file.open(encoding='utf-8'):
        x=json.loads(line)
        if x.get('type')=='turn_context':context=x
    ctx=context['payload'];assert (ctx['model'],ctx['effort'])==('gpt-6.1-sol','medium')
    ctx={k:ctx[k] for k in ('turn_id','model','effort')}|{'timestamp':context['timestamp']}
    analysis=runner.read(EV/'ws30-stage3-composition-analysis-r1.json')
    summary_path=ROOT/'results/ws30-stage3-composition-summary-r5.json'
    summary=runner.read(summary_path)
    launch_path=ROOT/'results/ws30-stage3-composition-readiness-launch-r1.json'
    launch=runner.read(launch_path)
    terminal_path=ROOT/'results/ws30-stage3-composition-terminal-snapshot-r1.json'
    terminal=runner.read(terminal_path)
    cells=runner.read(runner.PLAN)['composition'];ids={c['id'] for c in cells}
    assert len(summary['verified'])==12 and not summary['failures'] and not summary['pending']
    starts=[e for e in summary['events'] if e['event']=='started']
    assert len(starts)==12 and {e['id'] for e in starts}==ids
    assert not [e for e in summary['events'] if e['event'] in ('controller_stop','admission_stop','start_attention')]
    assert set(terminal['states'])==ids
    assert all(m['status']=='SUCCEEDED' and m['git_commit']==runner.COMPOSITION_SOURCE for m in terminal['states'].values())
    assert launch['preparation_context']['model']=='gpt-6-luna' and launch['preparation_context']['effort']=='medium'
    assert not terminal['resource']['other_users'] and not terminal['resource']['unexpected_simulation_pids']
    resources=dict(analysis['resources_from_simulation_watchers'])
    for e in summary['events']:
        if e.get('window'):
            for k in resources:
                resources[k]=(max if k.startswith('peak') else min)(resources[k],e['window'][k])
    audit={'kind':'WS-30 formal composition terminal execution audit r1','source_sha':runner.COMPOSITION_SOURCE,
        'plan_sha256':sha(runner.PLAN),'launch_context':launch['preparation_context'],'analysis_context':ctx,
        'controller_pid':7896,'controller_started_utc':summary['events'][0]['utc'],
        'controller_completed_utc':summary['events'][-1]['utc'],'unique_start_events':len(starts),
        'successful_cell_reruns':0,'local_verified':12,'remote_succeeded':12,'failures':0,'pending':0,'actual_cap_cells':{'4':12},
        'first_simulation_started_utc':min(r['started_utc'] for r in analysis['rows']),
        'last_simulation_finished_utc':max(r['finished_utc'] for r in analysis['rows']),
        'recorded_resource_extrema':resources,'resource_sampling_limit':analysis['resource_rss_note'],
        'terminal_resource':terminal['resource'],'controller_events':summary['events'],
        'launch_readiness_sha256':sha(launch_path),'terminal_snapshot_sha256':sha(terminal_path),
        'controller_summary_sha256':sha(summary_path),'results_index_sha256':sha(EV/'ws30-stage3-composition-results-r5.json'),
        'formal_ids':[c['id'] for c in cells],
        'trace_sha256':{c['trace']:c['trace_sha256'] for c in cells},
        'topology_sha256':cells[0]['topology_sha256']}
    write(EV/'ws30-stage3-composition-execution-audit-r1.json',audit)
    entries=[]
    details=[('diffflow-2016','arXiv:1604.05107v1','paper-v1.pdf',
        'Technical sections 7-9 and verification sections 1-2',
        'Fix shared-queue and service conditions while separating class source and routing decisions.',
        'The node holds real shared FIFO queues and swaps class composition at equal wire-byte backlog; it does not introduce per-class queues or packet spraying.',
        'DiffFlow uses sampled long-flow classification, Java without full TCP, and class-independent queues. Its normalized mean FCT cannot establish this node\'s RDMA batch/P99 gain.'),
        ('seqbalance-2024','arXiv:2407.09808v1','paper-v1.pdf',
        'Technical section 3 and verification sections 1,3-4',
        'Use the maximum completion time with the full request/batch origin; inspect per-QP paths and actual transport costs.',
        'The node aggregates three existing tag2 QPs from 2.000000 s and separately measures the probe released at 2.000020 s. It does not split WQEs, create child QPs or use path-blacklist feedback.',
        'The fixed preprint\'s final journal text was not compared. Host shaper and aggregate-CQE semantics and author FCT figures cannot be transferred as project evidence.'),
        ('letflow-2017','NSDI 2017 USENIX official PDF; 15 pages including cover','paper-local.pdf',
        'Technical sections 5-6 and version/evidence verification',
        'Check transport-dependent opportunities to adapt and distinguish changed allocation from business completion time.',
        'The node pins every probe packet to its first chosen port; equal backlog and common release hold give no flowlet adaptation opportunity. Later arrivals reveal cost transfer between destination groups.',
        'Random flowlet reselection, elastic flowlet size, TCP/OMNeT++ and hardware results do not establish a gain for the fixed RDMA QP fixture or MoE batches.')]
    for name,version,pdf,sections,method,difference,boundary in details:
        files=[f'papers/{name}/{pdf}',f'papers/{name}/analysis-technical.md',f'papers/{name}/verification.md']
        entries.append({'paper':name,'version':version,'reading_scope':sections,'borrowed_method':method,
                        'project_difference_and_applicable_condition':difference,'boundary':boundary,
                        'files':{f:sha(args.references/f) for f in files}})
    ref={'kind':'WS-30 composition formal-node reference borrowing review r1',
        'entry_files':{f:sha(args.references/f) for f in ('README.md','reading-log.md')},
        'entries':entries,'new_mechanism_admitted':False,'author_effects_used_as_project_evidence':False,
        'scope':'Read current entry files, relevant local technical analyses and verification records; recompute fixed PDF hashes.'}
    write(EV/'ws30-stage3-composition-reference-review-r1.json',ref)
    sourcefiles=['src/point-to-point/model/switch-node.cc','src/point-to-point/model/qbb-net-device.cc',
                 'scratch/network-load-balance.cc','scratch/ws30-composition-fixture.h','config/ws30_composition8.txt']
    sourcehashes={}
    import hashlib
    for f in sourcefiles:
        blob=subprocess.check_output(['git','show',runner.COMPOSITION_SOURCE+':'+f],cwd=ROOT)
        sourcehashes[f]=hashlib.sha256(blob).hexdigest()
    provenance={'kind':'WS-30 composition analysis provenance r1','analysis_context':ctx,
        'controller_head_at_launch':'eda78d7d5ac749fbbfeb18df79591af964d7545b','source_sha':runner.COMPOSITION_SOURCE,
        'source_file_blob_sha256':sourcehashes,'plan_sha256':sha(runner.PLAN),
        'scripts':{f:sha(ROOT/f) for f in ('scripts/analyze_ws30_stage3_composition.py','scripts/plot_ws30_stage3_composition.py','scripts/record_ws30_stage3_composition_audit.py')},
        'inputs':{f:sha(EV/f) for f in ('ws30-stage3-composition-results-r5.json','ws30-stage3-composition-node-authorization-r1.json','ws30-stage3-correctness-combined-r1.json')},
        'outputs':{p.name:sha(p) for p in EV.glob('ws30-stage3-composition-*r1.*') if p.suffix in ('.json','.csv') and 'provenance' not in p.name}}
    write(EV/'ws30-stage3-composition-analysis-provenance-r1.json',provenance)
    print(json.dumps({'analysis_context':ctx,'resource_extrema':resources,'source_files':len(sourcehashes),'references':len(entries)}))


if __name__=='__main__':main()
