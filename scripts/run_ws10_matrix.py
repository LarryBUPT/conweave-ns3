#!/usr/bin/env python3
"""Run the frozen WS-10 matrix sequentially and retain resource receipts."""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys
import time

from verify_ws10_traces import ROOT, SEEDS, TOTAL, sha


TOPOLOGY = 'topo_1280_400G_400G_OS1'
TOPOLOGY_SHA = '74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba'
SEQUENCE = ((0, 'fecmp'), (0, 'dualtrack'),
            (2, 'dualtrack'), (2, 'fecmp'),
            (4, 'fecmp'), (4, 'dualtrack'))
CONTROLLER = os.path.join(ROOT, 'scripts', 'remote_experiment.py')
ANALYZER = os.path.join(ROOT, 'scripts', 'analyze_moe_tags.py')


def invoke(*args):
    result = subprocess.run([sys.executable] + list(args), cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    if result.returncode:
        raise RuntimeError('Command failed: %s\n%s' % (' '.join(args), result.stdout[-3000:]))
    return result.stdout


def audit():
    lines = invoke(CONTROLLER, 'check').splitlines()
    return dict(line.split('=', 1) for line in lines if '=' in line)


def safe(a):
    assert float(a['load_1m']) <= 20, a
    assert float(a['mem_available_gib']) >= 16, a
    assert float(a['free_gib']) >= 100, a
    assert not a['active_simulation_pids'], a


def status(experiment_id):
    output = invoke(CONTROLLER, 'status', experiment_id)
    return json.JSONDecoder().raw_decode(output)[0]


def receipt(handle, record):
    handle.write(json.dumps(record, sort_keys=True) + '\n')
    handle.flush()
    print(json.dumps({key: record.get(key) for key in
                      ('event', 'id', 'seed', 'background', 'mode', 'status', 'error')},
                     sort_keys=True), flush=True)


def run_cell(handle, seed, background, mode, sha_commit):
    name = 'ws07_fixed_s%d_t256_b4_bg%d.txt' % (seed, background)
    with open(os.path.join(ROOT, 'docs', 'research',
                           'ws10-fixed-s%d-manifest.json' % seed), encoding='utf-8-sig') as source:
        manifest = json.load(source)
    experiment_id = (datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S') +
                     '-ws10-%d-b%d-%s' % (seed, background, 'p' if mode == 'dualtrack' else 'f'))
    assert sha(os.path.join(ROOT, 'config', name)) == manifest['traces'][name]['sha256']
    before = audit()
    safe(before)
    start_build = time.monotonic()
    invoke(CONTROLLER, 'build', '--repo-local', ROOT, '--id', experiment_id)
    build_s = time.monotonic() - start_build
    built = status(experiment_id)
    assert built['status'] == 'BUILT' and built['git_commit'] == sha_commit
    receipt(handle, {'event': 'built', 'id': experiment_id, 'seed': seed,
                     'background': background, 'mode': mode, 'build_seconds': build_s,
                     'before': before, 'git_commit': sha_commit})
    if build_s > 1200:
        raise RuntimeError('Build exceeded 20-minute budget; no run launched')
    safe(audit())
    invoke(CONTROLLER, 'run', experiment_id, '--lb', mode, '--pfc', '0', '--irn', '1',
           '--simul-time', '0.01', '--netload', '10', '--bw', '400', '--buffer', '9',
           '--topo', TOPOLOGY, '--cdf', 'AliStorage2019', '--flow-file', name)
    start_sim = time.monotonic()
    peak_rss = 0.0
    min_memory = float(before['mem_available_gib'])
    min_disk = float(before['free_gib'])
    budget_breach = []
    while True:
        time.sleep(15)
        current = audit()
        peak_rss = max(peak_rss, float(current['simulation_max_process_rss_mib']))
        min_memory = min(min_memory, float(current['mem_available_gib']))
        min_disk = min(min_disk, float(current['free_gib']))
        elapsed = time.monotonic() - start_sim
        if peak_rss > 16384 and 'rss' not in budget_breach:
            budget_breach.append('rss')
        if min_memory < 16 and 'memory' not in budget_breach:
            budget_breach.append('memory')
        if min_disk < 100 and 'disk' not in budget_breach:
            budget_breach.append('disk')
        if elapsed > 2700 and 'wall' not in budget_breach:
            budget_breach.append('wall')
        state = status(experiment_id)
        if state['status'] != 'RUNNING':
            break
    after = audit()
    sim_s = time.monotonic() - start_sim
    record = {'event': 'finished', 'id': experiment_id, 'seed': seed,
              'background': background, 'mode': mode, 'status': state['status'],
              'build_seconds': build_s, 'simulation_seconds': sim_s,
              'sampled_peak_process_rss_mib': peak_rss,
              'minimum_mem_available_gib': min_memory, 'minimum_free_gib': min_disk,
              'disk_free_delta_gib': float(before['free_gib']) - float(after['free_gib']),
              'budget_breach': budget_breach, 'before': before, 'after': after}
    receipt(handle, record)
    if state['status'] != 'SUCCEEDED':
        raise RuntimeError('Simulation did not succeed: ' + experiment_id)
    invoke(CONTROLLER, 'fetch', experiment_id)
    output = json.loads(invoke(ANALYZER, experiment_id,
                               '--target-trace', 'config/' + manifest['target_file']))
    tags = json.loads(invoke(ANALYZER, experiment_id))
    base = os.path.join(ROOT, 'results', experiment_id)
    with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as source:
        meta = json.load(source)
    assert meta['git_commit'] == sha_commit
    assert meta['input_flow_sha256'] == manifest['traces'][name]['sha256']
    assert meta['topology_sha256'] == TOPOLOGY_SHA
    assert output['target_trace_sha256'] == manifest['target_sha256']
    assert output['target_moe']['completed_flows'] == 256
    assert all(value['completion_rate'] == 1 for value in tags['tags'].values())
    assert sum(value['input_flows'] for value in tags['tags'].values()) == len(
        open(os.path.join(base, 'config', 'traffic_trace.txt'), encoding='utf-8').readlines()) - 1
    assert sum(int(line.split()[3]) for line in
               open(os.path.join(base, 'config', 'traffic_trace.txt'), encoding='utf-8').readlines()[1:]) == TOTAL
    pfc = glob.glob(os.path.join(base, 'raw', '*', '*_out_pfc.txt'))
    assert len(pfc) == 1 and os.path.getsize(pfc[0]) == 0
    record = {'event': 'verified', 'id': experiment_id, 'seed': seed,
              'background': background, 'mode': mode, 'status': 'SUCCEEDED',
              'git_commit': sha_commit, 'trace_sha256': meta['input_flow_sha256'],
              'topology_sha256': meta['topology_sha256'],
              'target_sha256': output['target_trace_sha256'],
              'fct_sha256': output['fct_sha256'], 'target': output['target_moe'],
              'tags': tags['tags'], 'pfc_bytes': 0, 'budget_breach': budget_breach,
              'disk_free_delta_gib': record['disk_free_delta_gib']}
    receipt(handle, record)
    if budget_breach or record['disk_free_delta_gib'] > 5:
        raise RuntimeError('Resource budget breached: ' + experiment_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('pilot', 'formal'))
    args = parser.parse_args()
    invoke(os.path.join(ROOT, 'scripts', 'verify_ws10_traces.py'))
    sha_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                         cwd=ROOT).decode().strip()
    assert sha(os.path.join(ROOT, 'config', TOPOLOGY + '.txt')) == TOPOLOGY_SHA
    log = os.path.join(ROOT, 'results', 'ws10-' + args.phase + '-receipts.jsonl')
    if os.path.exists(log):
        raise RuntimeError('Receipt log already exists: ' + log)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    seeds = (SEEDS[0],) if args.phase == 'pilot' else SEEDS[1:]
    prior_seconds = 0.0
    if args.phase == 'formal':
        pilot_log = os.path.join(ROOT, 'results', 'ws10-pilot-receipts.jsonl')
        with open(pilot_log, encoding='utf-8') as source:
            pilot = [json.loads(line) for line in source]
        verified = [row for row in pilot if row['event'] == 'verified']
        assert len(verified) == 6 and not any(row['event'] == 'stopped' for row in pilot)
        assert all(row['git_commit'] == sha_commit and not row['budget_breach']
                   for row in verified)
        prior_seconds = sum(row['build_seconds'] + row['simulation_seconds']
                            for row in pilot if row['event'] == 'finished')
    start_total = time.monotonic()
    initial_free = float(audit()['free_gib'])
    with open(log, 'x', encoding='utf-8') as handle:
        for seed in seeds:
            for background, mode in SEQUENCE:
                try:
                    if prior_seconds + time.monotonic() - start_total > 43200:
                        raise RuntimeError('Cumulative 12-hour wall budget reached')
                    if initial_free - float(audit()['free_gib']) > 100:
                        raise RuntimeError('Cumulative 100-GiB disk budget reached')
                    run_cell(handle, seed, background, mode, sha_commit)
                except Exception as error:
                    receipt(handle, {'event': 'stopped', 'seed': seed,
                                     'background': background, 'mode': mode,
                                     'status': 'STOPPED', 'error': str(error)})
                    raise


if __name__ == '__main__':
    main()
