#!/usr/bin/env python3
"""Check ALL fixed-trace identities/bytes/demand origins, without a completed-flow window."""
import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def expected_flows(trace):
    lines = trace.read_text(encoding='ascii').splitlines()
    rows = [line.split() for line in lines[1:] if line.strip()]
    if len(rows) != int(lines[0]):
        raise ValueError('Trace count mismatch')
    src_ports, dst_ports = defaultdict(lambda: 10000), defaultdict(lambda: 100)
    result = {}
    for index, row in enumerate(rows):
        src, dst, pg, size = map(int, row[:4])
        # Legacy ns-3 Time::FromDouble -> int64x64 -> GetHigh conversion.
        # Use the exact binary float rather than rounding the decimal trace.
        ns = int(Fraction.from_float(float(row[4])) * 10**9)
        key = (src, dst, src_ports[src], dst_ports[dst])
        if key in result:
            raise ValueError('Trace tuple reuse not supported by this fixture verifier')
        result[key] = {'index': index, 'size': size, 'demand_ns': ns}
        src_ports[src] += 1
        dst_ports[dst] += 1
    return result


def verify(trace, fct, log=None):
    expected = expected_flows(trace)
    found = {}
    for line in fct.read_text(encoding='ascii').splitlines():
        row = list(map(int, line.split()))
        if len(row) != 8:
            raise ValueError('FCT schema mismatch')
        key = tuple(row[:4])
        if key not in expected or key in found:
            raise ValueError('Unexpected or duplicate completion: ' + str(key))
        e = expected[key]
        if row[4] != e['size'] or row[5] != e['demand_ns'] or row[6] < 0 or row[7] <= 0:
            raise ValueError('Bytes or demand-origin mismatch: ' + str(key))
        found[key] = row
    if set(found) != set(expected):
        raise ValueError('Missing completions: {}'.format(len(set(expected)-set(found))))
    c2 = {}
    if log:
        for line in log.read_text(encoding='utf-8', errors='replace').splitlines():
            if not line.startswith('WS31_C2_FINISH '):
                continue
            values = dict(token.split('=', 1) for token in line.split()[1:])
            values = {k: int(v) for k, v in values.items()}
            i = values['flow_id']
            if i in c2:
                raise ValueError('Duplicate C2 completion')
            if not (values['demand_ns'] <= values['launch_ns'] <= values['finish_ns']):
                raise ValueError('C2 time order violation')
            if values['wait_ns'] != values['launch_ns']-values['demand_ns'] or not 0 <= values['wait_ns'] <= 500:
                raise ValueError('C2 wait not accounted or outside bound')
            if values['fct_ns'] != values['finish_ns']-values['demand_ns']:
                raise ValueError('C2 FCT omits source waiting')
            c2[i] = values
        if c2:
            if set(c2) != set(range(len(expected))):
                raise ValueError('C2 observed identities do not match input')
            for key, e in expected.items():
                v = c2[e['index']]
                if (v['demand_ns'],v['size'],v['fct_ns']) != (found[key][5],found[key][4],found[key][6]):
                    raise ValueError('C2 observations disagree with raw FCT')
    return {'flows': len(found), 'payload_bytes': sum(row[4] for row in found.values()),
            'all_completed': True, 'all_demand_origins_match': True, 'c2_timing_rows_checked': len(c2),
            'trace_sha256': hashlib.sha256(trace.read_bytes()).hexdigest(),
            'fct_sha256': hashlib.sha256(fct.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('fct', type=Path)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--equal-fct', type=Path, help='required byte-identical regression/control')
    args = parser.parse_args()
    receipt = verify(args.trace, args.fct, args.log)
    if args.equal_fct:
        if args.fct.read_bytes() != args.equal_fct.read_bytes():
            raise ValueError('Required byte-identical FCT regression failed')
        receipt['byte_identical_control'] = str(args.equal_fct)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
