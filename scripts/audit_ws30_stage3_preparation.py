"""Audit the completed small checks and all still-closed WS-30 formal plans."""
import argparse
import datetime
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

import run_ws30_stage3 as runner


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--session-file',type=Path)
    args=parser.parse_args();root,evidence=runner.ROOT,runner.EV
    plan=runner.read(runner.PLAN);check=runner.read(runner.CHECK_PLAN)
    result_path=evidence/'ws30-stage3-correctness-results-r5.json'
    recorded=runner.read(result_path)
    assert recorded['verified_cells']==8 and recorded['formal_effect_cells_counted']==0
    assert recorded['plan_sha256']==runner.stage.sha(runner.CHECK_PLAN)
    rows=[]
    for cell,row in zip(check['cells'],recorded['rows']):
        verified=runner.verify(cell)
        assert verified==row
        meta=runner.read(root/'results'/cell['id']/'metadata.json')
        rows.append(dict(verified,started_utc=meta['started_utc'],finished_utc=meta['finished_utc'],
                         metadata_sha256=runner.stage.sha(root/'results'/cell['id']/'metadata.json')))
    assert len({r['id'] for r in rows})==8
    fixture=[(c,r) for c,r in zip(check['cells'],rows) if c.get('composition')]
    assert len(fixture)==6
    c16={(c['swap'],c['continuing']):r['composition']['chosen_port']
         for c,r in fixture if c['arm']=='C16'}
    assert c16=={(0,0):3,(1,0):2,(0,1):3,(1,1):2}
    assert all(r['composition']['snapshot']['q1']==r['composition']['snapshot']['q2']==65536
               for c,r in fixture)
    assert sum(c['role']=='compatibility-check' for c in check['cells'])==2
    review=runner.read(evidence/'ws30-stage3-review-plan-r1.json')
    for phase in ['main','lead']:
        assert len(plan[phase])==len(review[phase])
        for before,after in zip(review[phase],plan[phase]):assert all(after[k]==v for k,v in before.items())
    cells=sum([plan[p] for p in ['main','lead','composition']],[])
    assert len(cells)==len({c['id'] for c in cells})==276
    assert not any((root/'results'/c['id']).exists() for c in cells)
    assert not runner.AUTHORIZATION.exists()
    all_formal={c['id'] for c in cells}
    for version in range(1,6):
        prior=runner.read(evidence/('ws30-stage3-execution-plan-r%d.json'%version))
        all_formal.update(c['id'] for phase in ['main','lead','composition'] for c in prior[phase])
    assert all(runner.stage.remote.remote.ID_RE.fullmatch(i) for i in all_formal)
    remote_code=("import os,json; root='/home/fnl/lzy/results'; ids=json.loads(%r); "
                 "print(json.dumps([i for i in ids if os.path.lexists(os.path.join(root,i))]))")%json.dumps(sorted(all_formal))
    remote=subprocess.check_output(runner.stage.remote.remote.ssh_base(runner.stage.remote.remote.config())+
                                   ['python3 -c '+shlex.quote(remote_code)],text=True,timeout=45)
    assert json.loads(remote)==[],remote
    unchanged=['src/point-to-point/model/switch-node.cc','src/point-to-point/model/rdma-hw.cc',
               'src/point-to-point/model/ws30-observer.h','src/point-to-point/model/switch-mmu.cc']
    subprocess.run(['git','diff','--quiet',runner.stage.SOURCE,runner.COMPOSITION_SOURCE,'--']+unchanged,check=True)
    failures=[]
    for name in plan['preserved_failed_ids']:
        folder=root/'results'/name;meta=runner.read(folder/'metadata.json')
        resource=runner.read(folder/'logs/resource-summary.json')
        assert meta['status']==resource['final_status']=='FAILED'
        files={str(p.relative_to(folder)).replace('\\','/'):runner.stage.sha(p)
               for p in sorted(folder.rglob('*')) if p.is_file()}
        assert files
        fct=list((folder/'raw').rglob('*_out_fct.txt'))
        failures.append({'id':name,'source_sha':meta['git_commit'],'files':files,
                         'nonempty_fct_present':any(p.stat().st_size for p in fct),
                         'excluded_from_effects':True,'resource':resource})
    old=runner.stage.remote.status(plan['preserved_unrun_build'])
    assert old['status']=='BUILT' and 'started_utc' not in old
    gate=runner.stage.resources.host_gate(reject_active=True)
    tests=subprocess.run([sys.executable,str(root/'scripts/test_ws30_stage3_runner.py')],
                         capture_output=True,text=True,check=True)
    count=int(re.search(r'Ran (\d+) tests',tests.stderr).group(1))
    closed=subprocess.run([sys.executable,str(root/'scripts/run_ws30_stage3.py'),'run','--phase','main'],
                          capture_output=True,text=True)
    assert closed.returncode and 'Formal execution is closed' in closed.stderr
    receipt={
        'kind':'WS-30 stage-3 preparation raw acceptance r1',
        'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'main_source_sha':runner.stage.SOURCE,'composition_source_sha':runner.COMPOSITION_SOURCE,
        'execution_plan_sha256':runner.stage.sha(runner.PLAN),
        'correctness_result_sha256':runner.stage.sha(result_path),
        'small_correctness_cells_verified':8,'composition_branch_checks':6,
        'fixture_disabled_historical_matches':2,'formal_main_lead_cells_unchanged':264,
        'formal_counts':plan['required_counts'],'formal_cells_executed':0,
        'formal_ids_checked_remote_absent':len(all_formal),'authorization_present':False,
        'c16_chosen_ports':{'swap%d_cont%d'%k:v for k,v in c16.items()},
        'unit_and_recovery_tests_passed':count,
        'unchanged_algorithm_transport_observer_paths':unchanged,
        'actual_rows':rows,'preserved_failed_attempts':failures,
        'preserved_unrun_build':old,'terminal_host_gate':gate,
        'pending_after_review':['resource escalation pilot under approximately 18 total CPU tokens',
                                'verified remaining-resource allocation if other jobs exist',
                                'main-chat runner/fixture review and actual Luna Medium switch',
                                '192 main + 72 lead + 12 composition and two-sided figures'],
    }
    if args.session_file:
        contexts=[]
        for line in args.session_file.open(encoding='utf-8'):
            data=json.loads(line)
            if data.get('type')=='turn_context':
                c=data['payload'];contexts.append({'timestamp':data.get('timestamp'),'model':c.get('model'),'effort':c.get('effort')})
        receipt['actual_model_turn_context']=contexts[-1]
    destination=evidence/'ws30-stage3-preparation-acceptance-r1.json'
    if destination.exists():
        previous=runner.read(destination)
        receipt['checked_utc']=previous['checked_utc']
        # Host snapshots are dated observations, not a byte-stable raw result.
        receipt['terminal_host_gate']=previous['terminal_host_gate']
        if not args.session_file and 'actual_model_turn_context' in previous:
            receipt['actual_model_turn_context']=previous['actual_model_turn_context']
    runner.stage.frozen(destination,receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['actual_rows','preserved_failed_attempts']},indent=2))


if __name__=='__main__':main()
