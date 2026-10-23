"""Read-only WS-25/27/28 raw audit; writes only new WS-30 evidence."""
import csv
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_moe_tags as tags

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git_text(ref, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', ref + ':' + path]).decode('utf-8')

def function(text, name):
    start = text.index('uint32_t SwitchNode::' + name + '(')
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

def main():
    old = 'ce699dffe2845dc83e2171a1c309c6d96b96d2b3'
    new = 'ee236f27920aa56b3dd562ed971e5abee9e1e659'
    source = {}
    for path in ['scripts/make_ws25_demand.py', 'scratch/network-load-balance.cc',
                 'src/point-to-point/model/rdma-hw.cc',
                 'src/point-to-point/model/conga-routing.cc',
                 'src/point-to-point/model/letflow-routing.cc',
                 'src/point-to-point/model/conweave-routing.cc']:
        a, b = git_text(old, path), git_text(new, path)
        source[path] = {'identical': a == b, 'old_sha256': hashlib.sha256(a.encode()).hexdigest(),
                        'new_sha256': hashlib.sha256(b.encode()).hexdigest()}
    path = 'src/point-to-point/model/switch-node.cc'
    for name in ['DoLbClassReserve', 'DoLbFlowECMP', 'DoLbDrill', 'CalculateInterfaceLoad']:
        a, b = function(git_text(old, path), name), function(git_text(new, path), name)
        source[name] = {'identical': a == b, 'old_sha256': hashlib.sha256(a.encode()).hexdigest(),
                        'new_sha256': hashlib.sha256(b.encode()).hexdigest()}
    groups = [
        ('ws25', 'ws25-first-paper', '20261004-070000-ws25-formal', old),
        ('ws27', 'ws27-guardhash-compare', '20261013-030000-ws27-confirm', new),
        ('ws28native', 'ws28-classreserve-explanation', '20261014-010000-ws28-native', new),
        ('ws28ablation', 'ws28-classreserve-explanation', '20261015-020000-ws28-ablation',
         '955d26b580c9ca9249e66dea68638b22e0e32e2c')]
    rows, manifests = [], []
    for group, folder, prefix, commit in groups:
        base = WORKSPACE / folder
        tags.PROJECT = str(base)
        paths = sorted((base / 'results').glob(prefix + '*'))
        for p in paths:
            if not p.is_dir() or not (p / 'metadata.json').exists():
                continue
            meta = json.loads((p / 'metadata.json').read_text(encoding='utf-8'))
            # Main audit is 192-background only; native/ablation are all 192.
            trace = p / 'config/traffic_trace.txt'
            if int(trace.open().readline()) != 16576:
                continue
            assert meta['git_commit'] == commit and meta['seed'] == 1
            assert sha(p / 'config/topology.txt') == meta['topology_sha256']
            cfg = dict(line.split(None, 1) for line in
                       (p / 'config/config.txt').read_text().splitlines() if line.strip())
            common = {k: v for k, v in cfg.items() if not ('FILE' in k or 'PATH' in k or
                       k.startswith('CONWEAVE') or k == 'LB_MODE')}
            summary = tags.summarize(p.name)
            assert {k: t['input_flows'] for k, t in summary['tags'].items()} == {'1': 192, '2': 16384}
            assert all(t['unfinished_flows'] == 0 for t in summary['tags'].values())
            rs = json.loads((p / 'logs/resource-summary.json').read_text())
            samples = [json.loads(x) for x in (p / 'logs/resource-samples.jsonl').read_text().splitlines() if x]
            assert rs['final_status'] == 'SUCCEEDED' and rs['samples'] == len(samples) > 0
            assert rs['peak_tree_rss_mib'] <= 32768 and rs['minimum_mem_available_gib'] >= 32
            assert rs['minimum_free_gib'] >= 100 and max(x['load_1m'] for x in samples) <= 20
            seed = int(meta['parameters']['flow_file'].split('seed')[1].split('_')[0])
            rows.append({'group': group, 'seed': seed, 'id': p.name, 'mode': meta['algorithm'],
                         'moe_batch_us': summary['tags']['2']['synthetic_batch_completion_us'],
                         'background_p99_us': summary['tags']['1']['p99_fct_us'],
                         'fct_sha256': summary['fct_sha256'], 'trace_sha256': summary['trace_sha256']})
            manifests.append({'id': p.name, 'source_sha': commit, 'metadata_sha256': sha(p/'metadata.json'),
                              'config_sha256': sha(p/'config/config.txt'), 'common_config': common,
                              'topology_sha256': meta['topology_sha256'], 'resource': rs})
        print(group, sum(r['group'] == group for r in rows), flush=True)
    # Same-input controls are shared between WS-27 and WS-28 native.
    controls = {r['seed']: r for r in rows if r['mode'] == 'fecmp'}
    for row in rows:
        ctl = controls[row['seed']]
        assert row['trace_sha256'] == ctl['trace_sha256']
        row['moe_change_pct'] = 100*(row['moe_batch_us']/ctl['moe_batch_us']-1)
        row['bg_change_pct'] = 100*(row['background_p99_us']/ctl['background_p99_us']-1)
    effects = []
    for group, _, _, _ in groups:
        for mode in sorted({r['mode'] for r in rows if r['group'] == group}):
            subset = [r for r in rows if r['group'] == group and r['mode'] == mode]
            effects.append({'group': group, 'mode': mode, 'n': len(subset),
                            'batch_median_pct': statistics.median(r['moe_change_pct'] for r in subset),
                            'background_median_pct': statistics.median(r['bg_change_pct'] for r in subset),
                            'batch_improved': sum(r['moe_change_pct'] < 0 for r in subset),
                            'background_gt3': sum(r['bg_change_pct'] > 3 for r in subset)})
    common_variants = {}
    for item in manifests:
        for k, v in item['common_config'].items():
            common_variants.setdefault(k, set()).add(v)
    out = ROOT / 'docs/research/evidence'
    result = {'source_audit': source, 'verified_cells': len(rows), 'effects': effects,
              'common_config_variants': {k: sorted(v) for k, v in common_variants.items()},
              'cells': rows, 'receipts': manifests}
    dest = out / 'ws30-historical-raw-audit.json'
    with dest.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write('\n')
    with (out/'ws30-historical-cell-metrics.csv').open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(json.dumps({'source': source, 'verified_cells': len(rows), 'effects': effects,
                      'varying_common_config': {k: sorted(v) for k,v in common_variants.items() if len(v)>1}}, indent=2))

if __name__ == '__main__':
    main()
