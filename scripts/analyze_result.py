#!/usr/bin/env python3
"""Analyze one downloaded ConWeave result without external Python packages."""
import argparse
import csv
import json
import math
import os
import re
import statistics
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ID_RE = re.compile(r'^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}$')


def percentile(sorted_values, percent):
    if not sorted_values:
        raise ValueError('No completed flows within the analysis window')
    pos = (len(sorted_values) - 1) * percent / 100.0
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def write_svg(path, sha, points):
    width, height = 760, 430
    left, right, top, bottom = 75, 35, 42, 64
    chart_width = width - left - right
    chart_height = height - top - bottom
    peak = max(point[2] for point in points)
    y_max = max(1.0, peak * 1.05)
    # Percentile on X; slowdown on Y. The 99th percentile is highlighted.
    poly = ' '.join('%.1f,%.1f' %
                    (left + chart_width * point[0] / 100.0,
                     top + chart_height * (1.0 - point[2] / y_max))
                    for point in points)
    x99 = left + chart_width * 0.99
    y99 = top + chart_height * (1.0 - points[99][2] / y_max)
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="760" height="430" viewBox="0 0 760 430">
<rect width="760" height="430" fill="white"/>
<text x="75" y="25" font-family="Arial,sans-serif" font-size="16">FCT slowdown by percentile</text>
<text x="75" y="405" font-family="Arial,sans-serif" font-size="11" fill="#555">Git commit: %s</text>
<line x1="75" y1="366" x2="725" y2="366" stroke="#333"/>
<line x1="75" y1="42" x2="75" y2="366" stroke="#333"/>
<text x="365" y="391" font-family="Arial,sans-serif" font-size="12">Percentile of completed flows (%%)</text>
<text x="5" y="45" font-family="Arial,sans-serif" font-size="11">Slowdown</text>
<text x="52" y="369" font-family="Arial,sans-serif" font-size="11">0</text>
<text x="32" y="48" font-family="Arial,sans-serif" font-size="11">%.1f</text>
<text x="72" y="383" font-family="Arial,sans-serif" font-size="11">0</text>
<text x="700" y="383" font-family="Arial,sans-serif" font-size="11">100</text>
<polyline fill="none" stroke="#2166ac" stroke-width="2" points="%s"/>
<circle cx="%.1f" cy="%.1f" r="4" fill="#b2182b"/>
<text x="560" y="65" font-family="Arial,sans-serif" font-size="12" fill="#b2182b">p99: %.3f</text>
</svg>''' % (sha, y_max, poly, x99, y99, points[99][2])
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(svg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_id')
    args = parser.parse_args()
    if not ID_RE.match(args.experiment_id):
        raise ValueError('Invalid experiment ID')
    results_root = os.path.realpath(os.path.join(PROJECT, 'results'))
    if not results_root.startswith(PROJECT + os.sep):
        raise ValueError('Local results root escapes project')
    base = os.path.realpath(os.path.join(results_root, args.experiment_id))
    if not base.startswith(results_root + os.sep):
        raise ValueError('Result path escapes project')
    with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as handle:
        metadata = json.load(handle)
    if metadata.get('status') != 'SUCCEEDED':
        raise ValueError('Analyze only a completed simulation')
    raw_id = metadata.get('raw_directory', '')
    if not re.match(r'^[0-9]+$', raw_id):
        raise ValueError('Invalid raw data directory')
    raw_file = os.path.join(base, 'raw', raw_id, raw_id + '_out_fct.txt')
    if os.path.islink(raw_file):
        raise ValueError('Raw file must not be a symlink')
    run_time = float(metadata['parameters']['simul_time'])
    start_limit = 2000000000 + 5000000  # run.py flowgen start + warmup
    end_limit = int((2.0 + run_time) * 1e9) + int(0.05 * 1e9)  # run.py analysis tail
    times_us = []
    slowdowns = []
    all_rows = 0
    with open(raw_file, encoding='utf-8') as handle:
        for line in handle:
            columns = line.split()
            if len(columns) < 8:
                continue
            all_rows += 1
            started_ns, fct_ns, ideal_ns = map(float, columns[5:8])
            if started_ns <= start_limit or started_ns + fct_ns >= end_limit or ideal_ns <= 0:
                continue
            times_us.append(fct_ns / 1000.0)
            slowdowns.append(max(1.0, fct_ns / ideal_ns))
    if not times_us:
        raise ValueError('No completed flows in run.py analysis window')
    times_us.sort()
    slowdowns.sort()
    summary = {
        'experiment_id': args.experiment_id,
        'git_commit': metadata['git_commit'],
        'algorithm': metadata['algorithm'],
        'topology': metadata['topology'],
        'netload_percent': metadata['load'],
        'simul_time_seconds': run_time,
        'seed': metadata['seed'],
        'raw_rows': all_rows,
        'selected_flows': len(times_us),
        'analysis_start_ns': start_limit,
        'analysis_end_ns': end_limit,
        'mean_fct_us': statistics.mean(times_us),
        'p50_fct_us': percentile(times_us, 50),
        'p95_fct_us': percentile(times_us, 95),
        'p99_fct_us': percentile(times_us, 99),
        'mean_slowdown': statistics.mean(slowdowns),
        'p50_slowdown': percentile(slowdowns, 50),
        'p95_slowdown': percentile(slowdowns, 95),
        'p99_slowdown': percentile(slowdowns, 99),
    }
    processed = os.path.join(base, 'processed')
    figures = os.path.join(base, 'figures')
    output_json = os.path.join(processed, 'fct_summary.json')
    output_csv = os.path.join(processed, 'fct_percentiles.csv')
    output_svg = os.path.join(figures, 'fct_slowdown.svg')
    for target in (output_json, output_csv, output_svg):
        if os.path.lexists(target):
            raise ValueError('Analysis output already exists: ' + target)
    points = [(p, percentile(times_us, p), percentile(slowdowns, p)) for p in range(101)]
    with open(output_json, 'w', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    with open(output_csv, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(('percentile', 'fct_us', 'slowdown'))
        writer.writerows(points)
    write_svg(output_svg, metadata['git_commit'], points)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print('Figure: ' + output_svg)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
