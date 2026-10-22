#!/usr/bin/env python3
"""Freeze only engineering cells; never launches SSH or an effect matrix."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gitbytes(source, name):
    return subprocess.check_output(['git', 'show', source + ':' + name], cwd=ROOT)


def reference(folder):
    meta = json.loads((folder / 'metadata.json').read_text())
    raw = str(meta['raw_directory'])
    return {'id': folder.name, 'root': str(folder), 'source_sha': meta['git_commit'],
            'seed': meta['seed'], 'parameters': meta['parameters'],
            'trace_sha256': sha(folder / 'config/traffic_trace.txt'),
            'topology_sha256': sha(folder / 'config/topology.txt'),
            'config_sha256': sha(folder / 'config/config.txt'),
            'metadata_sha256': sha(folder / 'metadata.json'),
            'fct_sha256': sha(folder / 'raw' / raw / (raw + '_out_fct.txt'))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--id-prefix', default='20261022-150000-ws29-eng')
    parser.add_argument('--output', type=Path, default=ROOT /
                        'docs/research/evidence/ws29-engineering-plan.json')
    args = parser.parse_args()
    source = subprocess.check_output(['git', 'rev-parse', args.source_sha], cwd=ROOT,
                                     text=True).strip()
    cells = []
    def cell(label, arm, trace='ws21_heartbeat_fat_k4_long_flow.txt', topo='fat_k4_100G_OS2',
             bw=100, fault=0, tor=32, start=2006100000, end=2006900000,
             synthetic=False, old=None, mode='classreserve'):
        inputs = gitbytes(source, 'config/' + trace)
        topology = gitbytes(source, 'config/' + topo + '.txt')
        lines = [line.split() for line in inputs.decode().splitlines()[1:] if line.strip()]
        tags = {}
        for line in lines: tags[line[5]] = tags.get(line[5], 0) + 1
        row = {'id': args.id_prefix + '-' + label, 'label': label,
               'arm': arm, 'mode': mode, 'source_sha': source, 'trace': trace, 'topology': topo,
               'trace_sha256': hashlib.sha256(inputs).hexdigest(),
               'topology_sha256': hashlib.sha256(topology).hexdigest(), 'bw': bw,
               'pfc': 0, 'irn': 1, 'buffer': 9, 'ns3_seed': 1, 'simul_time': '0.01',
               'input_flows': len(lines), 'input_bytes': sum(int(line[3]) for line in lines),
               'tags': tags, 'fault': fault, 'fault_tor': tor, 'fault_port': 6,
               'fault_start_ns': start if fault else 0, 'fault_end_ns': end if fault else 0,
               'synthetic': synthetic, 'expected_completion_fraction': 1.0,
               'expected_queue_violations': 0, 'expected_overflow': 0}
        if old: row['reference'] = reference(old)
        if arm == -1:
            row['legacy_control_options'] = {'ws18_path': 1, 'ws21_identity': 1,
                'ws21_heartbeat': 1, 'ws21_heartbeat_interval_ns': 200000}
        row['control_options'] = {'ws21_identity': 1,
            'ws21_feedback': int(arm in (1, 2, 3)),
            'ws21_heartbeat': int(arm in (-1, 1, 2)),
            'ws21_feedback_interval_ns': 10000, 'ws21_heartbeat_interval_ns': 200000}
        if fault in (1, 2): row['expected_single_drops'] = 1; row['expected_unknown'] = 0
        if 3 <= fault <= 8:
            row['expected_injected_rejected_delta'] = 1
            row['expected_injected_accepted_delta'] = int(fault == 4)
        if fault in (15, 16, 17):
            row['expected_synthetic_events'] = 1
            row['expected_adopted_changed_min'] = 1 if fault == 15 else 0
            if fault != 15: row['expected_adopted_changed_max'] = 0
        cells.append(row)
    cell('legacy-v2-hb200', -1, mode='ws18', old=BASE / 'LarryBUPT-conweave-ns3/results' /
         '20260930-020200-ws21hb-k4-200us')
    cell('mixed8-c0', 0, 'ws25_v1fix_mixed8.txt', 'topo_1280_400G_400G_OS1', 400,
         old=BASE / 'ws28-classreserve-explanation/results/20261015-000010-ws28-technical-classreserve')
    cell('main-c0', 0, 'ws25_seed20262721_b192.txt', 'topo_1280_400G_400G_OS1', 400,
         old=BASE / 'ws27-guardhash-compare/results/20261013-030000-ws27-confirm-s20262721-b192-classreserve')
    for arm in (1, 2, 3):
        cell('main-c' + str(arm), arm, 'ws25_seed20262721_b192.txt',
             'topo_1280_400G_400G_OS1', 400)
    cell('k4-c1-normal', 1)
    for fault in range(1, 12):
        cell('protocol-' + str(fault), 1, fault=fault, tor=34 if fault == 11 else 32,
             synthetic=fault in (3, 4, 5, 6, 7, 8, 10, 11))
    for arm in (0, 1, 2):
        for fault in (20, 23): cell('link-' + str(fault) + '-c' + str(arm), arm, fault=fault)
    for fault in (15, 16, 17):
        cell('synthetic-' + str(fault), 2, trace='ws29_state_machine_k4.txt', fault=fault,
             synthetic=True)
    plan = {'kind': 'WS-29 engineering only; remote GO pending', 'source_sha': source,
            'observation_revision': 'v2; lifecycle raw evidence only; scoring and demands unchanged',
            'unit_id': '20261022-173000-ws29-eng-unit-compat-r1',
            'candidate': 'v1', 'candidate_count_on_remote_start': 1, 'candidate_limit': 3,
            'diagnostic_revision_limit': 1, 'max_concurrent': 1,
            'state_interval_ns': 10000, 'heartbeat_interval_ns': 200000,
            'decision_window_end_age_max_ns': 20000, 'state_wire_payload_v3_bytes': 38,
            'requirements': ['optimized build', 'devices-point-to-point unit suite',
                             'A07-C0 main regression before independent pilot',
                             'no synthetic fault in natural-demand effect cells'],
            'resource_limits': {'rss_mib_max': 32768, 'available_memory_gib_min': 32,
                                'free_disk_gib_min': 100, 'load_1m_max': 20,
                                'max_text_log_bytes': 50 * 1024 * 1024}, 'cells': cells}
    data = json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if args.output.exists() and args.output.read_text(encoding='utf-8') != data:
        raise ValueError('Refusing to replace a frozen plan; use a new filename/IDs')
    args.output.write_text(data, encoding='utf-8')
    print(json.dumps({'cells': len(cells), 'source_sha': source, 'sha256': sha(args.output)}))


if __name__ == '__main__':
    main()
