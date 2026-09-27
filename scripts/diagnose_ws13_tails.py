#!/usr/bin/env python3
"""Pair WS-12 background FCTs in the preregistered safety failures.

Outputs are descriptive. Aggregate ToR counters cannot identify a flow path.
"""
import collections
import csv
import json
import math
from pathlib import Path

from analyze_result import percentile


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / 'docs/research/ws12-packet-strategies-formal-summary.json'
OUT = ROOT / 'docs/research/evidence'
CASES = [('original', 192), ('20261103', 128)]
MODES = ['dualtrack', 'packet-rr', 'packet-random', 'packet-adaptive', 'packet-drill']
COLORS = {'fecmp': '#222222', 'dualtrack': '#9b59b6', 'packet-rr': '#e67e22',
          'packet-random': '#2ca02c', 'packet-adaptive': '#1f77b4',
          'packet-drill': '#d62728'}


def files(cell):
    base = ROOT / 'results' / cell['id']
    raw = base / 'raw' / str(cell['raw_directory'])
    return base / 'config/traffic_trace.txt', raw / (str(cell['raw_directory']) + '_out_fct.txt'), raw


def flows(cell):
    trace, fct, _ = files(cell)
    sport = collections.defaultdict(lambda: 10000)
    dport = collections.defaultdict(lambda: 100)
    input_by_key = {}
    with trace.open(encoding='utf-8') as source:
        expected = int(source.readline())
        for line in source:
            src, dst, _, size, start, tag = line.split()
            src, dst, size, tag = map(int, (src, dst, size, tag))
            key = (src, dst, sport[src], dport[dst], size)
            sport[src] += 1
            dport[dst] += 1
            assert key not in input_by_key
            input_by_key[key] = (tag, round(float(start) * 1e9))
    assert len(input_by_key) == expected
    completed = {}
    with fct.open(encoding='utf-8') as source:
        for line in source:
            values = list(map(int, line.split()))
            assert len(values) == 8
            key = tuple(values[:5])
            assert key in input_by_key and key not in completed
            assert abs(values[5] - input_by_key[key][1]) <= 2
            completed[key] = values[6]
    assert len(completed) == expected
    return {key: fct_ns for key, fct_ns in completed.items()
            if input_by_key[key][0] == 1}


def host_tors(path):
    result = {}
    with path.open(encoding='utf-8') as source:
        source.readline()
        source.readline()
        for line in source:
            values = line.split()
            if len(values) < 2:
                continue
            a, b = map(int, values[:2])
            if a < 1280 <= b:
                result[a] = b
            elif b < 1280 <= a:
                result[b] = a
    assert len(result) == 1280
    return result


def uplink_tor(raw, tor):
    values = {}
    path = next(raw.glob('*_out_uplink.txt'))
    with path.open(encoding='utf-8') as source:
        for line in source:
            t, node, port, tx = map(int, line.split(','))
            if node == tor and 2000000000 <= t <= 2010000000:
                entry = values.setdefault(port, [t, tx, t, tx])
                entry[2:] = [t, tx]
    return {port: item[3] - item[1] for port, item in values.items()
            if item[2] > item[0]}


def cnp_by_node(raw):
    totals = collections.defaultdict(lambda: [0, 0, 0])
    path = next(raw.glob('*_out_cnp.txt'))
    with path.open(encoding='utf-8') as source:
        for line in source:
            t, node, ecn, ooo, total = map(int, line.split())
            assert t >= 2000000000 and total >= max(ecn, ooo)
            row = totals[node]
            row[0] += ecn
            row[1] += ooo
            row[2] += total
    return totals


def write_svg(cells):
    lookup = {(str(c['group']), c['background'], c['mode']): c for c in cells}
    # Plot absolute same-level differences from ECMP: x = background P99 cost,
    # y = MoE synthetic batch benefit. A line joins additive-background levels.
    rows = []
    for group in ['original', '20261101', '20261102', '20261103', '20261104']:
        for mode in MODES:
            points = []
            for bg in (64, 128, 192):
                c = lookup[(group, bg, mode)]
                e = lookup[(group, bg, 'fecmp')]
                points.append((c['background_flows']['p99_fct_us'] - e['background_flows']['p99_fct_us'],
                               e['moe']['synthetic_batch_completion_us'] - c['moe']['synthetic_batch_completion_us'], bg))
            rows.append((group, mode, points))
    xs = [p[0] for _, _, points in rows for p in points] + [0]
    ys = [p[1] for _, _, points in rows for p in points] + [0]
    x0, x1 = math.floor(min(xs) / 20) * 20 - 20, math.ceil(max(xs) / 20) * 20 + 20
    y0, y1 = math.floor(min(ys) / 2) * 2 - 2, math.ceil(max(ys) / 2) * 2 + 2
    left, top, width, height = 92, 45, 800, 500
    px = lambda x: left + (x - x0) * width / (x1 - x0)
    py = lambda y: top + height - (y - y0) * height / (y1 - y0)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="675" viewBox="0 0 1050 675">',
           '<rect width="1050" height="675" fill="white"/>',
           '<text x="92" y="25" font-family="sans-serif" font-size="18">WS-12 same-level MoE–background tradeoff (descriptive)</text>',
           f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="none" stroke="#555"/>',
           f'<line x1="{px(0):.1f}" x2="{px(0):.1f}" y1="{top}" y2="{top+height}" stroke="#aaa" stroke-dasharray="5 4"/>',
           f'<line x1="{left}" x2="{left+width}" y1="{py(0):.1f}" y2="{py(0):.1f}" stroke="#aaa" stroke-dasharray="5 4"/>']
    for x in range(math.ceil(x0 / 20) * 20, math.floor(x1 / 20) * 20 + 1, 20):
        svg.append(f'<text x="{px(x):.1f}" y="{top+height+20}" text-anchor="middle" font-family="sans-serif" font-size="11">{x}</text>')
    for y in range(math.ceil(y0 / 2) * 2, math.floor(y1 / 2) * 2 + 1, 2):
        svg.append(f'<text x="{left-10}" y="{py(y)+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11">{y}</text>')
    svg += [f'<text x="{left+width/2}" y="{top+height+50}" text-anchor="middle" font-family="sans-serif" font-size="13">Background P99 − same-level ECMP (µs; left is better)</text>',
            f'<text transform="translate(25,{top+height/2}) rotate(-90)" text-anchor="middle" font-family="sans-serif" font-size="13">ECMP − candidate MoE batch (µs; up is better)</text>']
    for group, mode, points in rows:
        color = COLORS[mode]
        opacity = '1' if group == 'original' else '.22'
        coords = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y, _ in points)
        svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{2.5 if group=="original" else 1.2}" opacity="{opacity}"/>')
        for x, y, bg in points:
            svg.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="{4 if group=="original" else 2}" fill="{color}" opacity="{opacity}"/>')
            if group == 'original' and bg == 192:
                svg.append(f'<text x="{px(x)+5:.1f}" y="{py(y)-5:.1f}" font-family="sans-serif" font-size="10" fill="{color}">192</text>')
    for i, mode in enumerate(MODES):
        svg.append(f'<line x1="{925}" y1="{80+i*27}" x2="{948}" y2="{80+i*27}" stroke="{COLORS[mode]}" stroke-width="3"/>')
        svg.append(f'<text x="955" y="{84+i*27}" font-family="sans-serif" font-size="11">{mode.replace("packet-", "")}</text>')
    svg.append('<text x="92" y="635" font-family="sans-serif" font-size="11">Opaque: original input; pale: four order permutations of the same flow multiset. Connected levels add background bytes.</text>')
    svg.append('</svg>')
    (OUT / 'ws13-tradeoff.svg').write_text('\n'.join(svg), encoding='utf-8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = json.loads(SUMMARY.read_text(encoding='utf-8'))
    assert summary['complete'] and summary['formal_cell_count'] == 120
    lookup = {(str(c['group']), c['background'], c['mode']): c for c in summary['cells']}
    first = lookup[('original', 192, 'fecmp')]
    tors = host_tors(ROOT / 'results' / first['id'] / 'config/topology.txt')
    hotspot = {tors[h['destination']] for h in first['hotspot_destinations']}
    rows, case_summaries = [], []
    for group, bg in CASES:
        base = lookup[(group, bg, 'fecmp')]
        base_flows = flows(base)
        base_raw = files(base)[2]
        base_cnp = cnp_by_node(base_raw)
        baseline_p99 = percentile(sorted(x / 1000 for x in base_flows.values()), 99)
        assert abs(baseline_p99 - base['background_flows']['p99_fct_us']) < 1e-6
        for mode in MODES:
            current = lookup[(group, bg, mode)]
            observed = flows(current)
            assert set(observed) == set(base_flows)
            rank = {key: i + 1 for i, (key, _) in enumerate(sorted(observed.items(), key=lambda v: (-v[1], v[0])))}
            count = len(observed)
            top_n = math.ceil(.01 * count)
            current_p99 = percentile(sorted(x / 1000 for x in observed.values()), 99)
            assert abs(current_p99 - current['background_flows']['p99_fct_us']) < 1e-6
            route = current.get('route_counters')
            case_summaries.append({'group': group, 'background': bg, 'mode': mode,
                                   'ecmp_id': base['id'], 'candidate_id': current['id'],
                                   'trace_sha256': current['trace_sha256'],
                                   'background_p99_ecmp_us': baseline_p99,
                                   'background_p99_candidate_us': current_p99,
                                   'background_p99_delta_us': current_p99 - baseline_p99,
                                   'moe_batch_ecmp_us': base['moe']['synthetic_batch_completion_us'],
                                   'moe_batch_candidate_us': current['moe']['synthetic_batch_completion_us'],
                                   'cnp_bytes_ecmp': base['raw_files']['cnp']['bytes'],
                                   'cnp_bytes_candidate': current['raw_files']['cnp']['bytes'],
                                   'route_counters': route, 'tail_count': top_n})
            current_raw = files(current)[2]
            current_cnp = cnp_by_node(current_raw)
            case_summaries[-1]['cnp_event_totals_ecmp'] = [sum(row[i] for row in base_cnp.values()) for i in range(3)]
            case_summaries[-1]['cnp_event_totals_candidate'] = [sum(row[i] for row in current_cnp.values()) for i in range(3)]
            uplink_cache = {}
            for key in sorted(observed):
                src, dst, sport, dport, size = key
                src_tor, dst_tor = tors[src], tors[dst]
                if src_tor not in uplink_cache:
                    uplink_cache[src_tor] = (uplink_tor(base_raw, src_tor), uplink_tor(current_raw, src_tor))
                eport, cport = uplink_cache[src_tor]
                common = sorted(set(eport) & set(cport))
                rows.append({'group': group, 'background': bg, 'mode': mode,
                             'ecmp_id': base['id'], 'candidate_id': current['id'],
                             'src': src, 'dst': dst, 'sport': sport, 'dport': dport, 'size_bytes': size,
                             'src_tor': src_tor, 'dst_tor': dst_tor, 'dst_tor_has_top8_moe_hotspot': int(dst_tor in hotspot),
                             'ecmp_fct_us': base_flows[key] / 1000, 'candidate_fct_us': observed[key] / 1000,
                             'paired_delta_us': (observed[key] - base_flows[key]) / 1000,
                             'candidate_tail_rank': rank[key], 'in_candidate_top1pct': int(rank[key] <= top_n),
                             'dst_host_cnp_ecmp_ecn': base_cnp[dst][0],
                             'dst_host_cnp_ecmp_ooo': base_cnp[dst][1],
                             'dst_host_cnp_candidate_ecn': current_cnp[dst][0],
                             'dst_host_cnp_candidate_ooo': current_cnp[dst][1],
                             'src_tor_aggregate_uplink_ecmp_bytes': sum(eport.values()),
                             'src_tor_aggregate_uplink_candidate_bytes': sum(cport.values()),
                             'src_tor_common_uplink_ports': len(common),
                             'src_tor_max_port_delta_bytes': max((cport[p] - eport[p] for p in common), default=0)})
    columns = list(rows[0])
    with (OUT / 'ws13-tail-paired-flows.csv').open('w', newline='', encoding='utf-8') as destination:
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    (OUT / 'ws13-tail-cases.json').write_text(json.dumps(case_summaries, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    write_svg(summary['cells'])
    print(json.dumps({'cases': len(case_summaries), 'paired_flow_rows': len(rows),
                      'top_tail': [{**c, 'route_counters': None} for c in case_summaries]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
