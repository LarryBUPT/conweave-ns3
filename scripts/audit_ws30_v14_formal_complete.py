"""Reconcile completed formal raw with frozen receipts and analysis outputs.

Local reads only. Creates a new receipt; never mutates experimental results.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

import run_ws30_v14 as v
import resume_ws30_v14 as resume


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--session-file', type=Path, required=True)
    args = parser.parse_args()
    context = v.require_model(args.session_file, 'analysis')
    source = args.analysis.resolve()
    assert source.is_relative_to(v.ROOT)
    receipt, retained, remaining = resume.load_resume()
    auth = v.read(resume.AUTH)
    assert auth['control_sha256'] == resume.controls()
    assert auth['resume_plan_sha256'] == digest(resume.PLAN)
    state = v.read(resume.STATE)
    assert len(state['verified']) == 140 and not state['pending'] and not state['failures']
    assert state['events'][-1]['event'] == 'formal_rest_combined_accepted'
    plan = v.read(v.CONTRACT)
    formal = plan['formal_disabled']
    assert len(formal) == 168 and len(retained) == 24 and len(remaining) == 140
    first = v.read(v.ROOT / 'results/ws30-v14-formal-first-execution-r1.json')
    assert len(first['verified']) == 4 and not first['failures']
    assert set(first['verified']) | set(receipt['retained_ids']) | set(state['verified']) == {c['id'] for c in formal}
    assert len(set(first['verified']) & set(receipt['retained_ids'])) == 0
    status = {r['id']: r for r in v.read(source / 'cell-status.json')}
    old = {r['id']: r for r in receipt['retained_successes']}
    rows = []
    for c in formal:
        row = status[c['id']]
        assert row['status'] == 'VERIFIED', (c['id'], row)
        prior = state['verified'].get(c['id']) or first['verified'].get(c['id']) or old[c['id']]
        assert row['fct_sha256'] == prior['fct_sha256']
        folder = v.ROOT / 'results' / c['id']
        metadata = v.read(folder / 'metadata.json')
        if c['id'] in old:
            assert digest(folder / 'metadata.json') == old[c['id']]['metadata_sha256']
            assert digest(folder / 'logs/config.log') == old[c['id']]['config_log_sha256']
        raw = folder / 'raw' / str(metadata['raw_directory'])
        files = [{'path': str(p.relative_to(v.ROOT)).replace('\\', '/'),
                  'bytes': p.stat().st_size, 'sha256': digest(p)}
                 for p in sorted(raw.rglob('*')) if p.is_file()]
        resource = v.read(folder / 'logs/resource-summary.json')
        samples = [json.loads(line) for line in (folder / 'logs/resource-samples.jsonl').read_text().splitlines() if line]
        rows.append(dict(row, origin='first4' if c['id'] in first['verified'] else 'retained24' if c['id'] in old else 'resumed140',
                         source_sha=c['source_sha'], simulation_seed=metadata['simulation_seed'],
                         demand_seed=metadata['demand_seed'], cap=metadata['concurrency_cap'],
                         raw_files=files, resource=resource, resource_peak_load=max(s['load_1m'] for s in samples)))
    def csvrows(name):
        with (source/name).open(newline='', encoding='utf-8') as stream:
            return list(csv.DictReader(stream))
    pairs = [r for r in csvrows('paired-endpoints.csv') if r['status'] == 'PAIRED']
    counts = []
    groups = collections.defaultdict(list)
    for row in pairs:
        groups[(row['cohort'], row['candidate'], row['reference'])].append(row)
    tails = csvrows('tail-decomposition.csv')
    for key, group in groups.items():
        ts = [r for r in tails if (r['cohort'], r['candidate'], r['reference']) == key and r['round'] == 'all']
        assert all(abs(float(t['batch_delta_ns']) - float(t['old_tail_delta_ns']) - float(t['replacement_gap_ns'])) < 1e-6 for t in ts)
        counts.append(dict(cohort=key[0], candidate=key[1], reference=key[2], n=len(group),
                           foreground_shorter=sum(float(r['foreground_change_pct']) < 0 for r in group),
                           background_p99_shorter=sum(float(r['background_p99_change_pct']) < 0 for r in group),
                           both_shorter=sum(float(r['foreground_change_pct']) < 0 and float(r['background_p99_change_pct']) < 0 for r in group),
                           tail_identity_changed=sum(t['tail_identity_changed'] == 'True' for t in ts),
                           median_old_tail_delta_ns=statistics.median(float(t['old_tail_delta_ns']) for t in ts),
                           median_replacement_gap_ns=statistics.median(float(t['replacement_gap_ns']) for t in ts),
                           all_tail_decompositions_exact=True))
    recovery = collections.defaultdict(list)
    for row in csvrows('recovery-costs.csv'):
        recovery[(row['cohort'], row['arm'], row['tag'])].append(row)
    costs = []
    for key, group in recovery.items():
        costs.append(dict(cohort=key[0], arm=key[1], tag=key[2], n=len(group),
                          retransmission_payload_pct_median=statistics.median(float(r['retransmission_payload_pct']) for r in group),
                          retransmission_payload_pct_range=[min(float(r['retransmission_payload_pct']) for r in group), max(float(r['retransmission_payload_pct']) for r in group)],
                          retransmit_bytes_total=sum(int(r['retransmit_bytes']) for r in group),
                          timeout_total=sum(int(r['timeout']) for r in group)))
    report = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'analysis_context': {k: context.get(k) for k in ('model','effort','turn_id')},
        'scope': 'formal only; first4 + retained24 + resumed140; Engineering48 and W5_36 remain open',
        'commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=v.ROOT, text=True).strip(),
        'source_sha': receipt['source_sha'], 'plan_sha256': digest(resume.PLAN),
        'authorization_sha256': digest(resume.AUTH), 'control_sha256': resume.controls(),
        'original_evidence_unchanged': receipt['original_evidence_sha256'],
        'completed': {'formal': 168, 'first4': 4, 'retained24': 24, 'resumed140': 140, 'pending': 0, 'simulation_failures': 0,
                      'fct_rows': sum(r['completed_rows'] for r in rows),
                      'payload_bytes': sum(r['completed_payload_bytes'] for r in rows),
                      'all_identity_and_byte_conservation': all(r['expected_rows'] == r['completed_rows'] and r['expected_payload_bytes'] == r['completed_payload_bytes'] for r in rows)},
        'resource': {'peak_load_1m': max(r['resource_peak_load'] for r in rows),
                     'minimum_mem_available_gib': min(r['resource']['minimum_mem_available_gib'] for r in rows),
                     'minimum_free_gib': min(r['resource']['minimum_free_gib'] for r in rows),
                     'peak_per_cell_rss_mib': max(r['resource']['peak_tree_rss_mib'] for r in rows)},
        'analysis_summary': v.read(source/'summary.json'),
        'paired_direction_and_tail_audit': counts, 'recovery_costs': costs,
        'raw_cells': rows,
        'analysis_outputs': {p.name: {'sha256': digest(p), 'bytes': p.stat().st_size} for p in sorted(source.iterdir()) if p.is_file()},
        'remaining': {'engineering_cells': 48, 'W5_including_qualification_cells': 36, 'manuscript_integration': 'pending', 'WS30': 'ACTIVE'},
        'simulations_launched_by_audit': 0,
    }
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'formal_verified':168, 'fct_rows':report['completed']['fct_rows'], 'historical48_match':report['analysis_summary']['historical_all48_FCT_match'], 'receipt':str(args.out)}))


if __name__ == '__main__':
    main()
