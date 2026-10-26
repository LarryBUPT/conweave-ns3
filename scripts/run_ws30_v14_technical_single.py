"""Single-cell engineering entry using a separate, sealed authorization.

The completed formal receipts and all original controller files remain unchanged.
No phase expansion, ID replacement, resume, sync, deployment or push is supported.
"""
import argparse
import json
from pathlib import Path
import sys

import run_ws30_v14 as v
import resume_ws30_v14 as resume

PHASE = 'technical-single'
ID = '20261026-120000-w30v14-t01-e-o0'
SOURCE = '0673e4c3de34d83585dd40f6be7fbd3ed000a9ee'
ORIGINAL_AUTH = v.AUTH
AUTH = v.EV / 'ws30-v14-technical-single-authorization-r1.json'
STATE = v.ROOT / 'results/ws30-v14-technical-single-execution-r1.json'


def check_scope(gate):
    v.require(gate.get('approved') is True and gate.get('external_sync_approved') is True,
              'Explicit single-cell authorization required')
    v.require(gate.get('phases') == [PHASE] and gate.get('phase_caps') == {PHASE: 1},
              'Only technical-single at cap 1 is permitted')
    v.require(gate.get('ids') == [ID] and gate.get('fixed_source_sha') == SOURCE,
              'Engineering ID/source differs')
    v.require(bool(gate.get('authorization_evidence')), 'Authorization evidence absent')


def validate(session, role):
    # The actual role is verified before reading remote config or writing state.
    context = v.require_model(session, role)
    gate = v.read(AUTH)
    check_scope(gate)
    v.require(gate['entry_sha256'] == v.sha(Path(__file__)), 'Single-cell entry changed')
    v.require(gate['original_authorization_sha256'] == v.sha(ORIGINAL_AUTH),
              'Sealed formal authorization changed')
    v.require(gate['contract_sha256'] == v.sha(v.CONTRACT)
              and gate['schedule_sha256'] == v.sha(v.SCHEDULE), 'Frozen plan changed')
    v.require(gate['control_sha256'] == {p: v.sha(v.ROOT/p) for p in v.CONTROLS},
              'Original control bytes changed')
    for name, policy in v.MODEL_POLICY.items():
        v.require((gate.get(name+'_model'), gate.get(name+'_effort')) == policy,
                  'Model policy changed')
    for rel, digest in gate['acceptance_evidence_sha256'].items():
        path = (v.ROOT.parents[1]/rel).resolve()
        v.require(path.is_relative_to(v.ROOT.parents[1]) and v.sha(path) == digest,
                  'Formal acceptance evidence changed')
    resume.load_resume()  # Original formal failure/recovery receipts remain sealed.
    state = v.read(resume.STATE)
    v.require(len(state['verified']) == 140 and not state['pending'] and not state['failures'],
              'Formal phase is not complete')
    plan, sched, cells = v.load()
    spec = sched['phases'][PHASE]
    v.require(spec['ids'] == [ID] and spec['maximum_cap'] == 1
              and spec['source_sha'] == SOURCE, 'Single-cell schedule changed')
    return context, gate, cells[ID]


def preflight(session, role='analysis'):
    context, gate, cell = validate(session, role)
    v.require(not STATE.exists(), 'Execution receipt already exists; preserve and inspect')
    v.require(not resume.local_inventory(cell), 'Local ID/staging/build intent occupied')
    backend = v.Backend([cell])
    backend.compatible()
    snapshot = backend.snapshot([cell])
    inventory = resume.remote_inventory([cell])
    v.require(snapshot['states'][ID] is None and not any(inventory[ID].values()),
              'Remote ID/path occupied; never replace or reissue')
    resource = backend.gate()
    v.require(not resource['other_users'] and not resource['unexpected_simulation_pids'],
              'Other work blocks admission')
    return {'id': ID, 'source_sha': SOURCE, 'cap': 1, 'new_simulations': 0,
            'actual_context': {k: context.get(k) for k in ('model','effort','turn_id')},
            'resource': resource}


def run(session):
    preflight(session, 'supervision')
    # Reuse the original complete authorization, controller-lock, resource,
    # isolated build/start, fetch and raw-verification implementation unchanged.
    v.AUTH = AUTH
    sys.argv = [str(v.ROOT/'scripts/run_ws30_v14.py'), 'run', '--phase', PHASE,
                '--session-file', str(session)]
    v.main()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect','preflight','run'), default='inspect', nargs='?')
    parser.add_argument('--session-file', type=Path)
    args = parser.parse_args()
    if args.command == 'inspect':
        print(json.dumps({'phase': PHASE, 'ids': [ID], 'source_sha': SOURCE,
                          'cap': 1, 'new_simulations': 0, 'authorization': str(AUTH)}))
    elif args.command == 'preflight':
        print(json.dumps(preflight(args.session_file)))
    else:
        run(args.session_file)


if __name__ == '__main__':
    main()
