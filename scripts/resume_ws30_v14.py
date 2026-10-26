"""Prepare and run only the 140 untouched formal-rest IDs after explicit review.

inspect is local/read-only. prepare audits local raw and remote inventory without
building, running, fetching, syncing or deploying. run needs a separate approved
receipt and the actual Luna/Medium session; the original failed receipt is sealed.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess

import run_ws30_v14 as v

ROOT, EV = v.ROOT, v.EV
PLAN = EV / 'ws30-v14-formal-rest-resume-plan-r2.json'
AUTH = EV / 'ws30-v14-formal-rest-resume-authorization-r2.json'
STATE = ROOT / 'results/ws30-v14-formal-rest-resume-execution-r2.json'
FAILED = ROOT / 'results/ws30-v14-formal-rest-execution-r1.json'
RECONCILED = ROOT / 'results/ws30-v14-formal-rest-recovery-r1.json'
CONTROLS = v.CONTROLS + ('scripts/resume_ws30_v14.py',)
RECONCILED_SHA = '79c803d14e33680d67b87f37b13dfc0fce73a9d15242868ae638e59fb04815ea'


def relative(path):
    return path.relative_to(ROOT).as_posix()


def controls():
    return {p: v.sha(ROOT / p) for p in CONTROLS}


def partition(schedule, cells, reconciled, failed):
    ids = schedule['phases']['formal-rest']['ids']
    accepted = [c['id'] for c in reconciled['cells']]
    v.require(len(accepted) == len(set(accepted)) == 24, 'Recovery must contain exactly 24 unique successes')
    v.require(accepted == ids[:24], 'Retained IDs differ from the frozen prefix')
    remaining = ids[24:]
    v.require(len(ids) == 164 and len(remaining) == 140 and remaining == reconciled['not_started_ids'],
              '140 untouched IDs changed')
    v.require(set(failed['verified']) <= set(accepted) and set(failed['pending']) <= set(accepted),
              'Original receipt contains an unreconciled ID')
    v.require(set(failed['failures']) == {'validation'} and
              failed['failures']['validation']['error'] == "'NoneType' object is not subscriptable",
              'Original failure differs; investigate instead of clearing it')
    v.require({cells[i]['source_sha'] for i in ids} == {reconciled['source_sha']} ==
              {'2c9f3a50bafad0740b461496ba24fa81941a9bc7'}, 'Preserved source changed')
    return [cells[i] for i in accepted], [cells[i] for i in remaining]


def verify_retained(cells, records):
    byid = {r['id']: r for r in records}
    output = []
    for c in cells:
        row = byid[c['id']]
        fresh = v.verify_common(c)
        folder = ROOT / 'results' / c['id']
        v.require(fresh['fct_sha256'] == row['fct_sha256'] and fresh['completed_rows'] == row['fct_rows'],
                  'Retained FCT changed: ' + c['id'])
        for path, key in ((folder/'metadata.json', 'metadata_sha256'),
                          (folder/'logs/config.log', 'config_log_sha256')):
            v.require(v.sha(path) == row[key], 'Retained evidence changed: ' + c['id'])
        output.append(row)
    return output


def local_inventory(c):
    return [p for p in [ROOT/'results'/c['id'],
                       ROOT/'results/ws30-v14-build-intents'/(c['id']+'.json')] +
            list((ROOT/'results').glob('.incoming-'+c['id']+'-*')) if os.path.lexists(p)]


def remote_inventory(cells):
    cfg = v.legacy.stage.remote.remote.config()
    ids = [c['id'] for c in cells]
    v.require(all(v.legacy.stage.remote.remote.ID_RE.fullmatch(i) for i in ids), 'Invalid inventory ID')
    code = """import json,os
ids=%r
out={}
for i in ids:
    row={}
    for name in ('runs','results'):
        p='/home/fnl/lzy/'+name+'/'+i
        exists=os.path.lexists(p)
        if exists: assert os.path.isdir(p) and os.path.realpath(p)==p
        row[name]=exists
    out[i]=row
print(json.dumps(out))
""" % ids
    output = subprocess.check_output(v.legacy.stage.remote.remote.ssh_base(cfg) +
                                     ['python3 -c '+shlex.quote(code)],
                                     encoding='utf-8', errors='replace', timeout=45)
    return json.loads(output)


def require_empty(cells, snapshot, inventory):
    for c in cells:
        i = c['id']
        v.require(not local_inventory(c), 'Local ID, staging or build intent occupied: ' + i)
        v.require(snapshot['states'][i] is None and not any(inventory[i].values()),
                  'Remote run/result path occupied, including metadata-free residue: ' + i)


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, indent=2, sort_keys=True)+'\n')


def prepare(session):
    context = v.require_model(session, 'analysis')
    v.require(not PLAN.exists() and not AUTH.exists() and not STATE.exists(),
              'Resume artifacts already exist; preserve and inspect them')
    plan, schedule, cells = v.load()
    v.require(v.sha(RECONCILED) == RECONCILED_SHA, 'Original reconciliation changed')
    reconciled, failed = v.read(RECONCILED), v.read(FAILED)
    retained, remaining = partition(schedule, cells, reconciled, failed)
    verified = verify_retained(retained, reconciled['cells'])
    v.prerequisite('formal-rest', plan, schedule, cells)
    backend = v.Backend(retained+remaining)
    backend.compatible()
    snapshot = backend.snapshot(retained+remaining)
    inventory = remote_inventory(retained+remaining)
    for c in retained:
        meta = snapshot['states'][c['id']]
        v.require(meta and meta['status'] == 'SUCCEEDED' and meta['git_commit'] == c['source_sha'],
                  'Retained remote terminal/source changed')
    require_empty(remaining, snapshot, inventory)
    resource = backend.gate()
    v.require(v.recovery.capacity(resource, 8) > 0, 'Resource gate closed')
    evidence = {relative(p): v.sha(p) for p in (FAILED, RECONCILED, v.AUTH,
                ROOT/'results/ws30-v14-formal-first-execution-r1.json')}
    receipt = {
        'kind': 'WS-30 formal-rest recovery plan', 'revision': 2,
        'execution_enabled': False, 'main_chat_acceptance_required': True,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'prepared_by': {k: context.get(k) for k in ('model','effort','turn_id')},
        'source_thread_id': os.environ.get('CODEX_THREAD_ID'),
        'contract_sha256': v.sha(v.CONTRACT), 'schedule_sha256': v.sha(v.SCHEDULE),
        'original_evidence_sha256': evidence, 'control_sha256': controls(),
        'source_sha': reconciled['source_sha'], 'phase': 'formal-rest', 'cap': 8,
        'retained_successes': verified, 'retained_ids': [c['id'] for c in retained],
        'remaining_cells': remaining, 'remaining_ids': [c['id'] for c in remaining],
        'resume_state': relative(STATE), 'original_state_never_written': relative(FAILED),
        'remote_status_counts': {'SUCCEEDED': len(retained), 'ABSENT': len(remaining)},
        'remote_path_inventory': inventory, 'resource_at_preparation': resource,
        'run_policy': 'Revalidate retained raw; check every run/result/staging/intent path; '
                      'build and start only remaining IDs; resume owned reservations; '
                      'fetch terminal successes without rerunning; retain failures and stop admissions',
        'authorization_scope': 'Existing formal-rest authorization only; a separate main-chat '
                               'acceptance of this plan and these controller hashes is required. '
                               'Engineering 48 and W5 36 remain required and outside this run.'}
    previous = EV/'ws30-v14-formal-rest-resume-plan-r1.json'
    if previous.exists():
        receipt['supersedes_unapproved_draft'] = {relative(previous): v.sha(previous)}
    write_new(PLAN, receipt)
    gate = {
        'approved': False, 'external_sync_approved': True,
        'main_chat_acceptance': None, 'resume_plan_sha256': v.sha(PLAN),
        'contract_sha256': v.sha(v.CONTRACT), 'schedule_sha256': v.sha(v.SCHEDULE),
        'control_sha256': controls(), 'phases': ['formal-rest'], 'phase_caps': {'formal-rest': 8},
        'fixed_source_sha': reconciled['source_sha'],
        'supervision_model': 'gpt-6-luna', 'supervision_effort': 'medium',
        'analysis_model': 'gpt-6.1-sol', 'analysis_effort': 'medium',
        'authorization_evidence': {'original_authorization_sha256': v.sha(v.AUTH),
            'review_request_source_thread_id': '01a0cfac-3176-7590-bf34-c0f176a45118',
            'scope': 'Prepare and locally test recovery; do not start 140 cells before main-chat acceptance.'}}
    write_new(AUTH, gate)
    return {'retained_verified': len(retained), 'remaining_untouched': len(remaining),
            'new_builds': 0, 'new_simulations': 0, 'approved': False, 'plan_sha256': v.sha(PLAN)}


def load_resume():
    v.require(PLAN.exists(), 'Prepare and review a resume plan first')
    receipt = v.read(PLAN)
    _, schedule, cells = v.load()
    v.require(receipt['contract_sha256'] == v.sha(v.CONTRACT) and
              receipt['schedule_sha256'] == v.sha(v.SCHEDULE) and
              receipt['control_sha256'] == controls(), 'Resume contract/schedule/controller changed')
    for name, digest in receipt['original_evidence_sha256'].items():
        v.require(v.sha(ROOT/name) == digest, 'Sealed original evidence changed: ' + name)
    retained, remaining = partition(schedule, cells, v.read(RECONCILED), v.read(FAILED))
    v.require(receipt['remaining_cells'] == remaining and receipt['retained_ids'] == [c['id'] for c in retained]
              and receipt['remaining_ids'] == [c['id'] for c in remaining]
              and receipt['resume_state'] == relative(STATE), 'Resume partition/state path changed')
    return receipt, retained, remaining


def authorize(session):
    v.require(AUTH.exists(), 'Resume execution closed: approval receipt absent')
    gate = v.read(AUTH)
    v.require(gate.get('approved') is True and gate.get('main_chat_acceptance') and
              gate.get('external_sync_approved') is True, 'Resume execution closed: main-chat acceptance pending')
    receipt, retained, remaining = load_resume()
    v.require(gate.get('resume_plan_sha256') == v.sha(PLAN) and
              gate.get('control_sha256') == controls() and
              gate.get('contract_sha256') == v.sha(v.CONTRACT) and
              gate.get('schedule_sha256') == v.sha(v.SCHEDULE), 'Resume approval hash mismatch')
    v.require(gate.get('phases') == ['formal-rest'] and gate.get('phase_caps') == {'formal-rest': 8}
              and gate.get('fixed_source_sha') == receipt['source_sha'], 'Resume approval scope changed')
    for role, policy in v.MODEL_POLICY.items():
        v.require((gate.get(role+'_model'),gate.get(role+'_effort')) == policy, 'Resume model policy changed')
    v.require_model(session, 'supervision')
    return receipt, retained, remaining


def check_owned_resumption(runner, remaining, snapshot, inventory):
    reserved = {i for event in runner.state['events'] if event['event'] == 'batch_reserved'
                for i in event['ids']}
    v.require(reserved <= {c['id'] for c in remaining} and
              set(runner.state['verified']) <= reserved and set(runner.state['pending']) <= reserved,
              'Resume state contains unreserved IDs')
    for c in remaining:
        i = c['id']
        if i not in reserved:
            require_empty([c], snapshot, inventory)
            continue
        meta = snapshot['states'][i]
        occupied = any(inventory[i].values())
        intent = ROOT/'results/ws30-v14-build-intents'/(i+'.json')
        v.require(not list((ROOT/'results').glob('.incoming-'+i+'-*')), 'Partial fetch retained; inspect before resuming')
        if occupied:
            v.require(meta and intent.is_file(), 'Ambiguous reserved remote path; never reissue build: ' + i)
            record = v.read(intent)
            v.require(record['id'] == i and record['source_sha'] == c['source_sha'] and
                      record['contract_sha256'] == v.sha(v.CONTRACT), 'Build intent/source collision')


def run(session):
    # Approval, hashes and actual model are checked before any SSH or writes.
    receipt, retained, remaining = authorize(session)
    with v.recovery.controller_lock():
        verify_retained(retained, receipt['retained_successes'])
        backend = v.Backend(remaining)
        backend.compatible()
        all_cells = retained+remaining
        snapshot = backend.snapshot(all_cells)
        for c in retained:
            meta = snapshot['states'][c['id']]
            v.require(meta and meta['status'] == 'SUCCEEDED', 'Retained remote success changed')
        inventory = remote_inventory(all_cells)
        runner = v.Runner(remaining, backend, STATE, cap=8)
        check_owned_resumption(runner, remaining, snapshot, inventory)
        backend.gate()
        runner.save('reviewed_resume_started', pid=os.getpid(), plan_sha256=v.sha(PLAN),
                    authorization_sha256=v.sha(AUTH), retained_successes=24,
                    source_sha=receipt['source_sha'])
        runner.run()
        v.require(len(runner.state['verified']) == 140 and not runner.state['failures'], 'Incomplete resumed phase')
        verify_retained(retained, receipt['retained_successes'])
        load_resume()  # Recheck sealed old receipts before accepting the combined phase.
        runner.save('formal_rest_combined_accepted', retained=24, resumed=140, total=164)
    return {'formal_rest_verified': 164, 'retained': 24, 'resumed': 140}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect','prepare','run'), nargs='?', default='inspect')
    parser.add_argument('--session-file', type=Path)
    args = parser.parse_args()
    if args.command == 'inspect':
        print(json.dumps({'execution_enabled': False, 'plan_exists': PLAN.exists(),
                          'approval_exists': AUTH.exists(), 'new_simulations': 0}))
    elif args.command == 'prepare':
        with v.recovery.controller_lock():
            print(json.dumps(prepare(args.session_file)))
    else:
        print(json.dumps(run(args.session_file)))


if __name__ == '__main__':
    main()
