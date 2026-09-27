#!/usr/bin/env python3
"""Generate independent demand draws for WS-13 calibration, never permutations.

The sampling frame and sizes follow the imported full-MoE generator, while
expert membership, each expert's receivers, and background pairs are drawn
afresh for each seed. Calibration files are not formal validation inputs.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config'
SEEDS = (20261301, 20261302, 20261303)
ALIGNED = tuple(range(0, 1280, 4))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(seed):
    rng = random.Random(seed)
    experts = sorted(rng.sample(ALIGNED, 256))
    background = sorted(set(ALIGNED) - set(experts))
    moe = []
    for src in experts:
        for dst in sorted(rng.sample([n for n in experts if n != src], 64)):
            moe.append(f'{src} {dst} 3 8192 2.000000000 2\n')
    pairs = rng.sample([(src, dst) for src in background for dst in background if src != dst], 192)
    bg = [f'{src} {dst} 3 8388608 2.000000000 1\n' for src, dst in pairs]
    assert len(moe) == 16384 and len(set(moe)) == len(moe)
    assert len(bg) == 192 and len(set(bg)) == len(bg)
    name = f'ws13_calibration_seed{seed}_b192.txt'
    path = CONFIG / name
    content = str(len(moe) + len(bg)) + '\n' + ''.join(bg + moe)
    if path.exists():
        assert path.read_text(encoding='utf-8') == content, 'Refusing to overwrite different trace'
    else:
        with path.open('x', encoding='utf-8', newline='\n') as output:
            output.write(content)
    return {'seed': seed, 'file': name, 'sha256': sha(path),
            'moe_flows': len(moe), 'background_flows': len(bg),
            'moe_bytes': len(moe) * 8192, 'background_bytes': len(bg) * 8388608,
            'total_offered_bytes': len(moe) * 8192 + len(bg) * 8388608,
            'expert_membership_sha256': hashlib.sha256(','.join(map(str, experts)).encode()).hexdigest(),
            'background_pairs_sha256': hashlib.sha256(str(pairs).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    records = [generate(seed) for seed in SEEDS]
    assert len({record['sha256'] for record in records}) == len(SEEDS)
    manifest = {'role': 'calibration-only', 'generator': 'scripts/make_ws13_calibration_traces.py',
                'sampling_frame': '320 hosts where host_id % 4 == 0; independently sample 256 experts, 64 background hosts per seed',
                'trace_replicates': records, 'simulator_seed': 1,
                'topology_sha256': sha(CONFIG / 'topo_1280_400G_400G_OS1.txt')}
    path = ROOT / 'docs/research/evidence/ws13-calibration-traces.json'
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    if path.exists():
        assert path.read_text(encoding='utf-8') == rendered, 'Manifest differs'
    elif not args.verify:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding='utf-8')
    else:
        raise ValueError('Manifest absent')
    print(json.dumps({'trace_hashes': [r['sha256'] for r in records], 'verified': args.verify}))


if __name__ == '__main__':
    main()
