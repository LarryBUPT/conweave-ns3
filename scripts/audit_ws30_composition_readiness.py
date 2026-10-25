"""Check the frozen composition node after its 14-cell technical acceptance.

Read-only remote preflight; does not launch, rebuild, or change fixture inputs.
"""
import argparse
import collections
import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

import run_ws30_stage3 as r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=r.EV / 'ws30-stage3-composition-readiness-r1.json')
    args = parser.parse_args()
    plan = r.read(r.PLAN)
    accepted = r.read(r.CORRECTNESS_RECEIPT)
    design = r.read(r.EV / 'ws30-composition-design-r3.json')
    assert accepted['verified_ids'] == 14 and accepted['composition_cells'] == 12
    assert accepted['compatibility_checks'] == 2 and accepted['formal_effect_cells_counted'] == 0
    assert accepted['source_sha'] == r.COMPOSITION_SOURCE
    assert accepted['formal_plan_sha256'] == r.stage.sha(r.PLAN)
    assert r.stage.sha(r.PLAN) == '77ca6064d4b4f275b409123302b01bd4eabd97e9c978e013f8d3e67edbf420f8'
    auth = r.read(r.AUTHORIZATION)
    assert auth['approved'] and 'composition' in auth['phases']
    assert auth['correctness_sha256'] == r.stage.sha(r.CORRECTNESS_RECEIPT)
    assert len(plan['composition']) == 12
    assert {(c['swap'], c['continuing'], c['arm']) for c in plan['composition']} == {
        (swap, continuing, arm) for swap in (0, 1) for continuing in (0, 1) for arm in ('E', 'Q16', 'C16')}
    assert not any((r.ROOT / 'results' / c['id']).exists() for c in plan['composition'])
    subprocess.run(['git', 'diff', '--quiet', r.COMPOSITION_SOURCE, 'HEAD', '--', 'src', 'scratch', 'config', 'run.py'], check=True)
    fixed = {}
    for relative in ['config/' + c['trace'] for c in plan['composition']] + ['config/ws30_composition8.txt', 'scratch/ws30-composition-fixture.h']:
        local = (r.ROOT / relative).read_bytes()
        committed = subprocess.check_output(['git', 'show', r.COMPOSITION_SOURCE + ':' + relative])
        if relative.endswith('.h'):
            # Windows checkout line endings are not the bytes built remotely.
            assert committed == local.replace(b'\r\n', b'\n')
        else:
            assert committed == local
        fixed[relative] = {'local_sha256': hashlib.sha256(local).hexdigest(),
                           'fixed_commit_blob_sha256': hashlib.sha256(committed).hexdigest(),
                           'byte_equal': committed == local}
    rows = []
    for row in accepted['rows']:
        identity = row['identity']
        if identity['role'] != 'composition-check':
            continue
        folder = r.ROOT / 'results' / row['id']
        log = (folder / 'logs/config.log').read_text()
        probe = row['composition']['snapshot']
        before = [r.stage.kv(line) for line in log.splitlines() if line.startswith('WS30_COMPOSITION_QUEUE ')
                  and r.stage.kv(line)['time_ns'] < probe['time_ns']]
        assert before and all(x['enqueue'] == 1 for x in before)
        for port in (2, 3):
            enqueued = [x for x in before if x['port'] == port]
            assert len(enqueued) == 64 and sum(x['bytes'] for x in enqueued) == 65536
            background = sum(x['bytes'] for x in enqueued if x['tag'] == 1)
            assert background == probe['b1' if port == 2 else 'b2']
        last_enqueue = max(x['time_ns'] for x in before)
        assert last_enqueue < probe['time_ns'] < design['release_ns']
        assert probe['q1'] == probe['q2'] == 65536
        formal = next(c for c in plan['composition'] if all(c[k] == identity[k] for k in ['swap', 'continuing', 'arm']))
        assert row['trace_sha256'] == formal['trace_sha256']
        trace = (r.ROOT / 'config' / formal['trace']).read_text().splitlines()[1:]
        origin = min(int(Decimal(x.split()[4]) * 10**9) for x in trace if x.split()[5] == '2')
        assert origin == 2000000000 and design['probe']['start_ns'] == 2000020000
        rows.append({'technical_id': row['id'], 'formal_id': formal['id'],
                     'swap': formal['swap'], 'continuing': formal['continuing'], 'arm': formal['arm'],
                     'prefill_packets_per_port': 64, 'wire_bytes_per_port': 65536,
                     'last_prefill_enqueue_ns': last_enqueue, 'probe_arrival_ns': probe['time_ns'],
                     'release_ns': design['release_ns'], 'background_bytes': [probe['b1'], probe['b2']],
                     'tag2_batch_origin_ns': origin, 'probe_origin_ns': design['probe']['start_ns'],
                     'config_log_sha256': r.stage.sha(folder / 'logs/config.log')})
    assert len(rows) == 12
    snapshot = r.Backend().snapshot(plan['composition'])
    assert all(meta is None for meta in snapshot['states'].values())
    assert r.capacity(snapshot['resource'], 4) == 4
    ids = [c['id'] for c in plan['composition']]
    code = r'''
import os,json,sys,subprocess
ids=json.loads(sys.argv[1]); root='/home/fnl/lzy'
occupied=[os.path.join(root,kind,i) for kind in ['runs','results'] for i in ids if os.path.lexists(os.path.join(root,kind,i))]
processes=subprocess.check_output(['ps','-eo','uid,pid,ppid,pcpu,rss,stat,comm','--no-headers']).decode().splitlines()
processes=[line for line in processes if int(line.split()[0])>=1000 and not line.split()[5].startswith('Z')]
locks=subprocess.check_output(['lslocks','-n','-o','PID,PATH']).decode().splitlines()
locks=[line for line in locks if '/home/fnl/lzy/' in line and 'simulation-start.lock' in line]
print(json.dumps({'occupied_paths':occupied,'uid_processes':processes,'simulation_start_lock_holders':locks}))
'''
    command = 'python3 -c ' + shlex.quote(code) + ' ' + shlex.quote(json.dumps(ids))
    isolation = json.loads(subprocess.check_output(r.stage.remote.remote.ssh_base(r.stage.remote.remote.config()) + [command], text=True, timeout=45))
    assert not isolation['occupied_paths'] and not isolation['simulation_start_lock_holders']
    with r.controller_lock():
        pass
    context = None
    for line in args.session_file.open(encoding='utf-8'):
        data = json.loads(line)
        if data.get('type') == 'turn_context':
            context = {k: data['payload'].get(k) for k in ['turn_id', 'model', 'effort']}
    result = {'kind': 'WS-30 composition readiness after accepted 14-cell technical audit',
              'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'plan_sha256': r.stage.sha(r.PLAN), 'source_sha': r.COMPOSITION_SOURCE,
              'correctness_receipt_sha256': r.stage.sha(r.CORRECTNESS_RECEIPT),
              'composition_design_sha256': r.stage.sha(r.EV / 'ws30-composition-design-r3.json'),
              'selected_cap': 4, 'cap_basis': 'Same composition source and fixture passed all 14 technical IDs at cap 4; fresh host and isolation gates passed.',
              'technical_ids_previously_reverified': 14, 'formal_cells': 12, 'fixed_files': fixed,
              'queue_time_audit': rows, 'resource': snapshot['resource'], 'isolation': isolation,
              'local_controller_lock_probe_passed': True, 'preparation_context': context,
              'required_launch_context': {'model': 'gpt-6-luna', 'effort': 'medium'},
              'formal_cells_launched_by_this_audit': 0}
    r.stage.frozen(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['queue_time_audit', 'fixed_files', 'isolation']}))


if __name__ == '__main__':
    main()
