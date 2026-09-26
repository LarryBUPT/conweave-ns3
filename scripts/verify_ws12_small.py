#!/usr/bin/env python3
"""Check the six tag-isolated modes on a shared cross-ToR four-flow input."""
import json
import re

from analyze_ws11_full import full_summary
from audit_ws11_inputs import ROOT, TOPO_SHA
from run_ws12_matrix import SIMULATION_COMMIT

IDS = {'fecmp': '20260927-023500-ws12-small-f',
       'dualtrack': '20260927-023500-ws12-small-h',
       'packet-rr': '20260927-022600-ws12-build',
       'packet-random': '20260927-023500-ws12-small-s',
       'packet-adaptive': '20260927-023500-ws12-small-a',
       'packet-drill': '20260927-023500-ws12-small-d'}
FLOW_SHA = '2d55bb4d5dc07904532e0949ba31c2b105db735086deb0fff57623a84ed418b6'
WS08_DUALTRACK_FCT = '3a12b4a9fadbcfefbd73451d3fcc0764b8b3412709a6bb9c9b61bf30ab79353f'
WS08_FLOW_ONLY_FCT = '50eff7c6a0303b2fd91980f737cb8b801857e687942c125ce7a5165b68004d0e'
SMALL_32 = {'flow': ('20260927-031000-ws12-32-flow', {'1': 4}),
            'packet': ('20260927-031000-ws12-32-packet', {'2': 4}),
            'dual': ('20260927-031000-ws12-32-dual', {'1': 2, '2': 2})}


def main():
    result = {}
    for mode, experiment_id in IDS.items():
        base = ROOT / 'results' / experiment_id
        with (base / 'metadata.json').open(encoding='utf-8') as source:
            meta = json.load(source)
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == SIMULATION_COMMIT
        assert meta['algorithm'] == mode and meta['seed'] == 1
        assert meta['input_flow_sha256'] == FLOW_SHA and meta['topology_sha256'] == TOPO_SHA
        assert meta['parameters']['pfc'] == 0 and meta['parameters']['irn'] == 1
        summary = full_summary(experiment_id)
        assert summary['trace_sha256'] == FLOW_SHA
        assert {tag: stats['completed_flows'] for tag, stats in summary['tags'].items()} == {'1': 2, '2': 2}
        raw = base / 'raw' / str(meta['raw_directory'])
        with (raw / 'config.log').open(encoding='utf-8') as source:
            log = source.read()
        assert 'WS06_ROUTING_TAG missing=0' in log
        if mode == 'dualtrack':
            assert re.search(r'WS07_DUALTRACK flow_packets=(\d+) packet_packets=(\d+) packet_multipath=(\d+)', log)
            assert summary['fct_sha256'] == WS08_DUALTRACK_FCT
        if mode.startswith('packet-'):
            route = re.search(r'WS12_ROUTE mode=(\d+) moe_packets=(\d+) background_packets=(\d+) moe_multipath=(\d+)', log)
            assert route is not None
            _, moe, background, multipath = map(int, route.groups())
            assert moe > 0 and background > 0 and multipath == moe
            ports = re.findall(r'WS12_PORT switch=\d+ port=\d+ packets=(\d+)', log)
            assert len(ports) >= 2 and sum(map(int, ports)) == moe
            result[mode] = {'experiment_id': experiment_id, 'moe_source_packets': moe,
                            'background_source_packets': background,
                            'source_ports_used': len(ports)}
        else:
            result[mode] = {'experiment_id': experiment_id}
    small32 = {}
    for name, (experiment_id, expected) in SMALL_32.items():
        base = ROOT / 'results' / experiment_id
        with (base / 'metadata.json').open(encoding='utf-8') as source:
            meta = json.load(source)
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == SIMULATION_COMMIT
        assert meta['algorithm'] == 'packet-rr' and meta['seed'] == 1
        assert meta['parameters']['pfc'] == 0 and meta['parameters']['irn'] == 1
        summary = full_summary(experiment_id)
        assert {tag: stats['completed_flows'] for tag, stats in summary['tags'].items()} == expected
        raw = base / 'raw' / str(meta['raw_directory'])
        with (raw / 'config.log').open(encoding='utf-8') as source:
            log = source.read()
        route = re.search(r'WS12_ROUTE mode=16 moe_packets=(\d+) background_packets=(\d+) moe_multipath=(\d+)', log)
        assert route is not None
        moe, background, multipath = map(int, route.groups())
        assert (moe > 0) == ('2' in expected)
        assert (background > 0) == ('1' in expected)
        assert multipath == moe
        if name == 'flow':
            assert summary['fct_sha256'] == WS08_FLOW_ONLY_FCT
        small32[name] = {'experiment_id': experiment_id,
                         'completed_flows': sum(stats['completed_flows'] for stats in summary['tags'].values())}
    print(json.dumps({'complete': True, 'modes': result, 'small_32': small32}, sort_keys=True))


if __name__ == '__main__':
    main()
