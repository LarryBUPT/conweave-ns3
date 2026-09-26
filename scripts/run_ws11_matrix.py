#!/usr/bin/env python3
"""Run/recover preregistered WS-11 full-input cells with isolated receipts."""
import argparse
import contextlib
import concurrent.futures
import datetime
import glob
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

from analyze_ws11_full import full_summary
from audit_ws11_inputs import EXPECTED, ROOT as ROOT_PATH, TOPO_SHA

ROOT = str(ROOT_PATH)
CONTROLLER = os.path.join(ROOT, 'scripts', 'remote_experiment.py')
RESULTS = os.path.join(ROOT, 'results')
PLAN = os.path.join(RESULTS, 'ws11-formal-plan.json')
RECEIPTS = os.path.join(RESULTS, 'ws11-formal-receipts.jsonl')
SEQUENCE = ((0, 'fecmp'), (0, 'dualtrack'), (64, 'dualtrack'),
            (64, 'fecmp'), (128, 'fecmp'), (128, 'dualtrack'),
            (192, 'dualtrack'), (192, 'fecmp'))
LOCK = threading.Lock()
REMOTE_SLOTS = threading.Semaphore(8)
QUICK_REMOTE_SLOTS = threading.Semaphore(2)
BUILD_SLOTS = threading.Semaphore(8)
CPU_TOKENS = threading.BoundedSemaphore(18)  # Reserve two of 20 physical cores.


@contextlib.contextmanager
def cpu_tokens(count):
    for _ in range(count):
        CPU_TOKENS.acquire()
    try:
        yield
    finally:
        for _ in range(count):
            CPU_TOKENS.release()


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def call(argv):
    done = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    if done.returncode:
        raise RuntimeError('%s failed: %s' % (argv[1:4], done.stdout[-1200:]))
    return done.stdout


def controller(*args):
    if args and args[0] == 'build':
        with REMOTE_SLOTS:
            return call([sys.executable, CONTROLLER] + list(args))
    with QUICK_REMOTE_SLOTS, REMOTE_SLOTS:
        for attempt in range(2 if args and args[0] in ('check', 'status') else 1):
            try:
                return call([sys.executable, CONTROLLER] + list(args))
            except RuntimeError as error:
                if attempt == 0 and ('Connection closed' in str(error) or
                                     'exit status 255' in str(error)):
                    time.sleep(5)
                    continue
                raise


def status(experiment_id):
    message = controller('status', experiment_id)
    return json.JSONDecoder().raw_decode(message[message.index('{'):])[0]


def audit():
    lines = controller('check').splitlines()
    result = dict(line.split('=', 1) for line in lines if '=' in line)
    if float(result['load_1m']) > 20 or float(result['mem_available_gib']) < 32 or \
            float(result['free_gib']) < 100:
        raise RuntimeError('Host resource stop line reached')
    return result


def receipt(event, cell, **details):
    row = {'event': event, 'id': cell['id'], 'group': cell['group'],
           'background': cell['background'], 'mode': cell['mode'],
           'utc': datetime.datetime.utcnow().isoformat() + 'Z'}
    row.update(details)
    with LOCK:
        with open(RECEIPTS, 'a', encoding='utf-8') as output:
            output.write(json.dumps(row, sort_keys=True) + '\n')
            output.flush()


def input_for(group, bg, manifest):
    if group == 'original':
        name = ('moe_1280group_256to8_8round_8KB' +
                ('' if bg == 0 else '_hybrid_%dfecmp' % bg) + '.txt')
        return name, EXPECTED[bg]
    info = manifest['inputs'][str(group)][str(bg)]
    return info['file'], info['sha256']


def make_plan():
    if os.path.exists(PLAN):
        with open(PLAN, encoding='utf-8') as source:
            return json.load(source)
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(ROOT, 'docs', 'research', 'ws11-permutation-manifest.json'),
              encoding='utf-8') as source:
        manifest = json.load(source)
    commit = call(['git', 'rev-parse', 'HEAD']).strip()
    assert call(['git', 'status', '--porcelain']).strip() == ''
    assert sha(os.path.join(ROOT, 'config', 'topo_1280_400G_400G_OS1.txt')) == TOPO_SHA
    prefix = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    cells = []
    for group in ['original'] + manifest['seeds']:
        for bg, mode in SEQUENCE:
            name, expected = input_for(group, bg, manifest)
            assert sha(os.path.join(ROOT, 'config', name)) == expected
            code = 'o' if group == 'original' else str(group)[-2:]
            experiment_id = '%s-ws11-%s-b%d-%s' % (
                prefix, code, bg, 'p' if mode == 'dualtrack' else 'f')
            cells.append({'id': experiment_id, 'group': group, 'background': bg,
                          'mode': mode, 'flow_file': name, 'flow_sha256': expected})
    plan = {'git_commit': commit, 'topology_sha256': TOPO_SHA,
            'prereg': 'docs/research/ws11-full-moe-prereg-v1.md', 'cells': cells}
    with open(PLAN, 'x', encoding='utf-8') as target:
        json.dump(plan, target, indent=2, sort_keys=True)
        target.write('\n')
    return plan


def start_watch(experiment_id):
    remote = '/home/fnl/lzy/results/%s/logs' % experiment_id
    command = ('test -e %s/resource-samples.jsonl || '
               'nohup python3 /home/fnl/lzy/.research-workflow/ws11_resource_watch.py '
               '%s > %s/resource-watch.log 2>&1 < /dev/null &') % (
                   remote, experiment_id, remote)
    with QUICK_REMOTE_SLOTS, REMOTE_SLOTS:
        call(['ssh', '-o', 'BatchMode=yes', '-o', 'ClearAllForwardings=yes',
              'fnl@10.112.14.167', command])


def wait_watch(experiment_id):
    remote = ('/home/fnl/lzy/results/%s/logs/resource-summary.json' % experiment_id)
    for _ in range(8):
        with QUICK_REMOTE_SLOTS, REMOTE_SLOTS:
            check = subprocess.run(['ssh', '-o', 'BatchMode=yes',
                                    '-o', 'ClearAllForwardings=yes', 'fnl@10.112.14.167',
                                    'test -s ' + remote], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        if check.returncode == 0:
            return
        time.sleep(5)
    raise RuntimeError('Resource watcher did not finish: ' + experiment_id)


def verify(cell, commit):
    experiment_id = cell['id']
    base = os.path.join(RESULTS, experiment_id)
    with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as source:
        meta = json.load(source)
    assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == commit
    assert meta['input_flow_sha256'] == cell['flow_sha256']
    assert meta['topology_sha256'] == TOPO_SHA
    summary = full_summary(experiment_id)
    assert summary['trace_sha256'] == cell['flow_sha256']
    assert summary['tags']['2']['input_flows'] == 16384
    assert summary['tags']['2']['completed_flows'] == 16384
    if cell['background']:
        assert summary['tags']['1']['completed_flows'] == cell['background']
    pfc = glob.glob(os.path.join(base, 'raw', '*', '*_out_pfc.txt'))
    assert len(pfc) == 1 and os.path.getsize(pfc[0]) == 0
    with open(os.path.join(base, 'logs', 'resource-summary.json'), encoding='utf-8') as source:
        resources = json.load(source)
    assert resources['samples'] > 0 and resources['final_status'] == 'SUCCEEDED'
    assert resources['peak_tree_rss_mib'] <= 32768
    assert resources['minimum_mem_available_gib'] >= 32
    assert resources['minimum_free_gib'] >= 100
    for hotspot in summary['hotspot_destinations']:
        assert hotspot['input_flows'] == hotspot['completed_flows']
    return summary


def run_cell(cell, commit, cap, simulation_slots, stop_event):
    if stop_event.is_set():
        raise RuntimeError('Batch stopped before this cell')
    experiment_id = cell['id']
    local = os.path.join(RESULTS, experiment_id)
    if os.path.isdir(local):
        summary = verify(cell, commit)
        receipt('verified', cell, fct_sha256=summary['fct_sha256'], resumed=True)
        return
    try:
        audit()
        try:
            state = status(experiment_id)
        except RuntimeError as error:
            if 'metadata.json' not in str(error) and 'No such file' not in str(error):
                raise
            started = time.monotonic()
            with BUILD_SLOTS, cpu_tokens(2):
                if stop_event.is_set():
                    raise RuntimeError('Batch stopped before build')
                audit()
                controller('build', '--repo-local', ROOT, '--id', experiment_id,
                           '--source-sha', commit)
            state = status(experiment_id)
            receipt('built', cell, build_seconds=time.monotonic() - started)
        if state['git_commit'] != commit:
            raise RuntimeError('Source SHA mismatch: ' + experiment_id)
        if state['status'] in ('BUILT', 'RUNNING'):
            with simulation_slots, cpu_tokens(1):
                if state['status'] == 'BUILT':
                    if stop_event.is_set():
                        raise RuntimeError('Batch stopped before simulation')
                    audit()
                    controller('run', experiment_id, '--lb', cell['mode'], '--pfc', '0',
                               '--irn', '1', '--simul-time', '0.01', '--netload', '10',
                               '--bw', '400', '--buffer', '9',
                               '--topo', 'topo_1280_400G_400G_OS1',
                               '--cdf', 'AliStorage2019', '--flow-file', cell['flow_file'],
                               '--max-concurrent', str(cap))
                    receipt('started', cell, concurrency_cap=cap)
                    state = status(experiment_id)
                if state['status'] == 'RUNNING':
                    start_watch(experiment_id)
                    while state['status'] == 'RUNNING':
                        time.sleep(60)
                        state = status(experiment_id)
                        try:
                            audit()
                        except RuntimeError:
                            # Preserve the in-flight result; prevent new cells.
                            stop_event.set()
        if state['status'] != 'SUCCEEDED':
            raise RuntimeError('Experiment stopped: %s %s' % (experiment_id, state['status']))
    except Exception:
        stop_event.set()
        raise
    wait_watch(experiment_id)
    controller('fetch', experiment_id)
    summary = verify(cell, commit)
    receipt('verified', cell, fct_sha256=summary['fct_sha256'],
            trace_sha256=summary['trace_sha256'], topology_sha256=TOPO_SHA,
            moe_batch_us=summary['tags']['2']['synthetic_batch_completion_us'],
            background_p99_us=summary['tags'].get('1', {}).get('p99_fct_us'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan', 'formal'))
    parser.add_argument('--concurrency', type=int, choices=(1, 2, 4, 8, 12), default=1)
    parser.add_argument('--max-new-cells', type=int,
                        help='run only this many unverified cells, then return for a resource review')
    args = parser.parse_args()
    plan = make_plan()
    if args.phase == 'plan':
        print('Planned %d cells at %s' % (len(plan['cells']), plan['git_commit']))
        return
    audit()
    rows = []
    if os.path.exists(RECEIPTS):
        with open(RECEIPTS, encoding='utf-8') as source:
            rows = [json.loads(line) for line in source]
    done = {row['id'] for row in rows if row['event'] == 'verified'}
    cells = [cell for cell in plan['cells'] if cell['id'] not in done]
    if args.max_new_cells is not None:
        if args.max_new_cells <= 0:
            raise RuntimeError('max-new-cells must be positive')
        cells = cells[:args.max_new_cells]
    if not cells:
        print('All planned WS-11 cells are already verified')
        return
    audit()
    stop_event = threading.Event()
    simulation_slots = threading.Semaphore(args.concurrency)
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(cells), args.concurrency + 8)) as pool:
        futures = [pool.submit(run_cell, cell, plan['git_commit'], args.concurrency,
                               simulation_slots, stop_event) for cell in cells]
        problems = []
        for cell, future in zip(cells, futures):
            try:
                future.result()
            except Exception as error:
                receipt('stopped', cell, error=str(error))
                problems.append(error)
        if problems:
            raise RuntimeError('%d cell(s) stopped; inspect receipts before recovery' % len(problems))


if __name__ == '__main__':
    main()
