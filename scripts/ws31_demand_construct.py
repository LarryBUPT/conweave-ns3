"""Accepted WS-31 v2 abstract demand constructor; never launches a simulator.

Online CSV is an abstract transport/current-label interface, NOT the legacy
driver format. Runtime packet framing, native adapters and endpoint gates are
separate. Evaluation grouping is written only to the evaluation sidecar.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

PROTOCOL_SHA = '5d676baeb674f488fe25686207be3fb9925b007d238c1fa1f340e04d1c9310c8'
VERSION = 'v2'
T0 = 2005000000
K0_SEEDS = tuple(range(5310001, 5310009))
ONLINE_FIELDS = ('request_id', 'generation', 'src', 'dst', 'sport', 'dport',
                 'pg', 'payload_bytes', 'demand_ns', 'policy_tag', 'flow_id')
EVAL_FIELDS = ('request_id', 'original_tag', 'business_task', 'construction_block',
               'physical_index', 'event_tie_rank')


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


class Stream:
    def __init__(self, family, seed, name):
        if family not in ('D1', 'D2') or '|' in name:
            raise ValueError('Invalid stream identity')
        self.prefix = '{}|{}|{}|{}|'.format(VERSION, family, int(seed), name)
        self.counter = 0

    def word(self):
        raw = (self.prefix + str(self.counter)).encode('utf-8')
        self.counter += 1
        return int.from_bytes(hashlib.sha256(raw).digest(), 'big')

    def below(self, n):
        if not 0 < n <= 2**256:
            raise ValueError('Invalid rejection-sampling range')
        limit = 2**256 - (2**256 % n)
        while True:
            value = self.word()
            if value < limit:
                return value % n

    def permutation(self, values):
        result = list(values)
        for i in range(len(result)-1, 0, -1):
            j = self.below(i+1)
            result[i], result[j] = result[j], result[i]
        return result


def reference_framed_bytes(payload):
    """Protocol planning reference, not certified runtime wire bytes."""
    return payload + 48 * ((payload + 999) // 1000)


def physical_requests(family, seed):
    if family not in ('D1', 'D2'):
        raise ValueError('Unknown family')
    sizes = {src: 16384 for src in range(16)}
    if family == 'D2':
        positions = Stream(family, seed, 'source-size-permutation').permutation(range(16))
        sizes = {src: (16384 if src in positions[:8] else 262144) for src in range(16)}
    wire = 70 * sum(reference_framed_bytes(sizes[src]) for src in range(16))
    horizon = (8 * wire + 279) // 280
    requests = []
    for block in range(70):
        if family == 'D1':
            destinations = Stream(family, seed, 'destination:{}'.format(block)).permutation(range(64, 80))
            dest = dict(zip(range(16), destinations))
        else:
            dest = {}
            for size, pool in [(16384, range(64, 72)), (262144, range(72, 80))]:
                sources = [src for src in range(16) if sizes[src] == size]
                destinations = Stream(family, seed, 'destination:{}:{}'.format(block, size)).permutation(pool)
                dest.update(zip(sources, destinations))
        for src in range(16):
            if family == 'D1' and block < 6:
                demand = T0 + block * horizon // 6
            else:
                demand = T0 + Stream(family, seed, 'arrival:{}:{}'.format(block, src)).below(horizon)
            requests.append({'src': src, 'dst': dest[src], 'payload_bytes': sizes[src],
                             'demand_ns': demand, 'construction_block': block,
                             'physical_index': block*16+src})
    return requests, wire, horizon


def construct(family, seed):
    # Physical construction is complete before D2's independently sampled goal.
    physical, wire, horizon = physical_requests(family, seed)
    targets = (list(range(6)) if family == 'D1' else
               sorted(Stream(family, seed, 'target-blocks').permutation(range(70))[:6]))
    tasks = {block: i for i, block in enumerate(targets)}
    order = Stream(family, seed, 'event-order').permutation(range(1120))
    for request in physical:
        request['event_tie_rank'] = order[request['physical_index']]
    ordered = sorted(physical, key=lambda r: (r['demand_ns'], r['event_tie_rank']))
    online, evaluation = [], []
    for ordinal, request in enumerate(ordered):
        block = request['construction_block']
        tag = 2 if block in tasks else 1
        online.append({'request_id': ordinal, 'generation': 0,
                       'src': request['src'], 'dst': request['dst'],
                       'sport': 10000+ordinal, 'dport': 100, 'pg': 3,
                       'payload_bytes': request['payload_bytes'], 'demand_ns': request['demand_ns'],
                       'policy_tag': tag, 'flow_id': ordinal})
        evaluation.append({'request_id': ordinal, 'original_tag': tag,
                           'business_task': tasks.get(block, ''), 'construction_block': block,
                           'physical_index': request['physical_index'],
                           'event_tie_rank': request['event_tie_rank']})
    metadata = {'family': family, 'seed': int(seed), 'stage': 'K0', 'request_count': 1120,
                'business_requests': 96, 'background_requests': 1024, 'business_tasks': 6,
                'reference_W_bytes': wire, 'H_ns': horizon, 't0_ns': T0,
                'stop_ns': T0+horizon+max(10*horizon, 10000000),
                'reference_mtu_payload_bytes': 1000, 'reference_overhead_bytes': 48,
                'actual_runtime_framing_verified': False, 'target_blocks_evaluation_only': targets}
    return online, evaluation, metadata


def csv_bytes(records, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n', extrasaction='raise')
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode('utf-8')


def bundle_bytes(family, seed):
    online, evaluation, metadata = construct(family, seed)
    files = {'online-current.csv': csv_bytes(online, ONLINE_FIELDS),
             'evaluation-only.csv': csv_bytes(evaluation, EVAL_FIELDS)}
    manifest = dict(metadata, schema='ws31-abstract-demand-r1', protocol_sha256=PROTOCOL_SHA,
                    constructor_sha256=sha_bytes(Path(__file__).read_bytes()),
                    status='ABSTRACT_ONLY_NOT_NATIVE_RUNTIME_MANIFEST',
                    native_adapter_verified=False, endpoint_correctness_verified=False,
                    files={name: {'sha256': sha_bytes(raw), 'bytes': len(raw)} for name, raw in files.items()})
    files['manifest.json'] = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode('utf-8')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-k0', action='store_true', required=True)
    args = parser.parse_args()
    implementation = Path(__file__).resolve().parents[1]
    project = implementation.parents[1]
    evidence = project/'workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/evidence/consensus-resumption-20261108-r1'
    release = json.loads((evidence/'g2-constructor-release.json').read_text(encoding='utf-8'))
    if not release.get('finite_checks_passed') or release.get('constructor_sha256') != sha_bytes(Path(__file__).read_bytes()):
        raise SystemExit('Finite checks and exact-source main release are required before abstract K0 generation')
    if release['protocol_sha256'] != PROTOCOL_SHA:
        raise SystemExit('Protocol identity mismatch')
    root = implementation/'results/ws31-consensus-v2-inputs-r1/K0'
    # Existing failed or successful directories are retained; no overwrite path.
    destinations = [(family, seed, root/'{}-{}'.format(family, seed))
                    for family in ('D1', 'D2') for seed in K0_SEEDS]
    if any(path.exists() for _, _, path in destinations):
        raise SystemExit('An output directory already exists; preserve it and reconcile the attempt')
    count = total_bytes = 0
    for family, seed, path in destinations:
        path.mkdir(parents=True, exist_ok=False)
        for name, raw in bundle_bytes(family, seed).items():
            with (path/name).open('xb') as handle:
                handle.write(raw)
            total_bytes += len(raw)
        count += 1
    print(json.dumps({'status': 'ABSTRACT_K0_CONSTRUCTION_COMPLETE', 'demands': count,
                      'output_bytes': total_bytes, 'root': str(root), 'simulator_runs': 0}))


if __name__ == '__main__':
    main()
