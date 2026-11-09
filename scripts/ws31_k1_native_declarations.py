"""Encode registered abstract K1 tables as strict C++ declaration inputs.

This is not a simulator driver. No Node, QP, event, label producer, transport
profile, physical framing or generation/drain behavior is certified here.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

import ws31_k1_demand_construct as k1

PROTOCOL_SHA = '5d676baeb674f488fe25686207be3fb9925b007d238c1fa1f340e04d1c9310c8'
CONSTRUCTOR_SHA = '261cee65f90dd72119694f00d93778e705ec59fa84b302984cc64000b1ebdc8d'
MAGIC = 'WS31_V2_DECL_R1'
FIELDS = ('request_id', 'generation', 'src', 'dst', 'src_ip', 'dst_ip', 'pg',
          'bytes', 'demand_ns', 'original_tag', 'policy_present', 'policy_tag',
          'sport', 'dport', 'flow_id')
U32 = 2**32-1
U64 = 2**64-1
I64 = 2**63-1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError('WS31 declaration: ' + message)


def number(word, limit=U64):
    need(bool(word) and word.isascii() and word.isdecimal(), 'non-decimal integer')
    need(len(word) == 1 or word[0] != '0', 'non-canonical leading zero')
    value = int(word)
    need(value <= limit, 'integer overflow')
    return value


def node_ip(node):
    # Exact Settings::node_id_to_ip mapping, not an interface-installation claim.
    need(0 <= node < 128, 'host out of OS2 range')
    return 0x0b000001 + (node//256)*0x10000 + (node % 256)*0x100


def lexical_lines(text):
    """ASCII only, LF/CRLF lines; optional final terminator; SP/TAB fields."""
    text = text.replace('\r\n', '\n')
    need(all(c in '\t\n' or ' ' <= c <= '~' for c in text), 'unsupported text byte')
    lines = text.split('\n')
    if lines[-1] == '':
        lines.pop()
    return lines


def words(line):
    return re.findall(r'[^ \t]+', line)


def parse_text(text):
    lines = lexical_lines(text)
    need(len(lines) >= 3, 'missing header')
    h = words(lines[0])
    need(len(h) == 10 and h[0] == MAGIC and h[1] == 'K1', 'wrong schema or stage')
    family = h[2]
    need(family in ('D1', 'D2'), 'unknown family')
    seed, count, t0, horizon, stop, mtu, overhead = [number(v) for v in h[3:]]
    need(seed in k1.K1_SEEDS and count == 1120, 'unregistered K1 seed/count')
    need(t0 == 2005000000 and horizon == {'D1':550400, 'D2':4671488}[family], 'reference time mismatch')
    need(stop == t0+horizon+max(10*horizon, 10000000) and stop <= I64, 'stop mismatch')
    need(mtu == 1000 and overhead == 48, 'reference framing mismatch')
    need(words(lines[1]) == ['PROTOCOL_SHA256', PROTOCOL_SHA], 'protocol identity mismatch')
    need(words(lines[2]) == ['CONSTRUCTOR_SHA256', CONSTRUCTOR_SHA], 'constructor identity mismatch')
    need(len(lines) == count+3, 'incomplete or extra rows')
    records, keys = [], set()
    src_counts, dst_counts, sizes = Counter(), Counter(), Counter()
    fixed_size, waves = {}, Counter()
    wire = 0
    previous_time = -1
    for ordinal, line in enumerate(lines[3:]):
        fields = words(line)
        need(len(fields) == len(FIELDS), 'row width')
        r = dict(zip(FIELDS, (number(w) for w in fields)))
        need(r['request_id'] == r['flow_id'] == ordinal and r['generation'] == 0, 'identity/order/generation')
        need(0 <= r['src'] < 16 and 64 <= r['dst'] < 80, 'endpoint range')
        need(r['src_ip'] == node_ip(r['src']) and r['dst_ip'] == node_ip(r['dst']), 'IP binding')
        need(r['pg'] == 3 and 0 < r['sport'] < 65536 and 0 < r['dport'] < 65536, 'PG/port range')
        need(t0 <= r['demand_ns'] < t0+horizon and r['demand_ns'] >= previous_time, 'demand/order')
        previous_time = r['demand_ns']
        need(r['original_tag'] in (1, 2), 'original class')
        need(r['policy_present'] in (0, 1) and r['policy_tag'] <= U32, 'policy encoding')
        need(r['policy_present'] or r['policy_tag'] == 0, 'absent policy must be canonical0')
        need(r['bytes'] in ((16384,) if family == 'D1' else (16384, 262144)), 'size')
        key = (r['src_ip'], r['dst_ip'], r['sport'], r['dport'])
        need(key not in keys, 'duplicate route key')
        keys.add(key)
        tag = r['original_tag']
        src_counts[tag, r['src']] += 1
        dst_counts[tag, r['dst']] += 1
        sizes[tag, r['bytes']] += 1
        wire += r['bytes'] + 48*((r['bytes']+999)//1000)
        if family == 'D1' and tag == 2:
            need(any(r['demand_ns'] == t0+k*horizon//6 for k in range(6)), 'D1 wave time')
            waves[r['demand_ns'], r['src']] += 1
        if family == 'D2':
            need(r['src'] not in fixed_size or fixed_size[r['src']] == r['bytes'], 'D2 common source sizes')
            fixed_size[r['src']] = r['bytes']
            need((r['bytes'] == 16384) == (r['dst'] < 72), 'D2 destination size half')
        records.append(r)
    for tag, per_node in [(1,64), (2,6)]:
        need(all(src_counts[tag,s] == per_node for s in range(16)), 'source class margins')
        need(all(dst_counts[tag,d] == per_node for d in range(64,80)), 'destination class margins')
    if family == 'D1':
        need(all(waves[t0+k*horizon//6,s] == 1 for k in range(6) for s in range(16)), 'D1 wave sources')
    else:
        need(sizes[1,16384] == sizes[1,262144] == 512 and sizes[2,16384] == sizes[2,262144] == 48, 'D2 class sizes')
    need(horizon == (8*wire+279)//280, 'reference byte arithmetic')
    return {'stage':'K1','family':family,'seed':seed,'count':count,'t0_ns':t0,'H_ns':horizon,'stop_ns':stop,
            'reference_W_bytes':wire}, records


def encode_bundle(directory):
    meta = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    need(meta['protocol_sha256'] == PROTOCOL_SHA and meta['constructor_sha256'] == CONSTRUCTOR_SHA, 'abstract provenance')
    need(meta['stage'] == 'K1' and meta['seed'] in k1.K1_SEEDS, 'K1 stage/seed')
    need(meta['k1_generator_sha256'] == sha(Path(k1.__file__)), 'K1 generator identity')
    for name, identity in meta['files'].items():
        need(sha(directory/name) == identity['sha256'] and (directory/name).stat().st_size == identity['bytes'], 'abstract bytes')
    with (directory/'online-current.csv').open(encoding='utf-8',newline='') as handle:
        online = list(csv.DictReader(handle))
    with (directory/'evaluation-only.csv').open(encoding='utf-8',newline='') as handle:
        evaluation = list(csv.DictReader(handle))
    need(len(online) == len(evaluation) == 1120, 'abstract row count')
    lines = ['{} K1 {} {} 1120 {} {} {} 1000 48'.format(
        MAGIC,meta['family'],meta['seed'],meta['t0_ns'],meta['H_ns'],meta['stop_ns']),
        'PROTOCOL_SHA256 '+PROTOCOL_SHA, 'CONSTRUCTOR_SHA256 '+CONSTRUCTOR_SHA]
    for raw, truth in zip(online, evaluation):
        need(raw['request_id'] == truth['request_id'], 'evaluation join')
        r = {k:number(v) for k,v in raw.items()}
        values = [r['request_id'],r['generation'],r['src'],r['dst'],node_ip(r['src']),node_ip(r['dst']),
                  r['pg'],r['payload_bytes'],r['demand_ns'],number(truth['original_tag']),1,r['policy_tag'],
                  r['sport'],r['dport'],r['flow_id']]
        lines.append(' '.join(str(v) for v in values))
    text = '\n'.join(lines)+'\n'
    parsed, _ = parse_text(text)
    return text.encode('ascii'), parsed


def write_one(directory, destination):
    need(not destination.exists(), 'refuse existing output')
    data, summary = encode_bundle(directory)
    manifest = dict(summary, schema='ws31-native-declaration-r1', protocol_sha256=PROTOCOL_SHA,
                    constructor_sha256=CONSTRUCTOR_SHA, encoder_sha256=sha(Path(__file__)),
                    k1_generator_sha256=sha(Path(k1.__file__)),
                    parent_manifest_sha256=sha(directory/'manifest.json'),
                    parent_evaluation_sha256=sha(directory/'evaluation-only.csv'),
                    native_cpp_decoder_compiled=False, native_objects=0, label_producer_wired=False,
                    endpoint_correctness_verified=False, actual_runtime_framing_verified=False,
                    stage_status='DECLARATION_BYTES_ONLY_NOT_RUNTIME_FREEZE',
                    declaration_sha256=hashlib.sha256(data).hexdigest(), declaration_bytes=len(data))
    destination.mkdir(parents=True,exist_ok=False)
    with (destination/'requests.native').open('xb') as handle:
        handle.write(data)
    with (destination/'manifest.json').open('xb') as handle:
        handle.write((json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode('utf-8'))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-k1',required=True,action='store_true')
    parser.parse_args()
    implementation=Path(__file__).resolve().parents[1]
    main_root=implementation.parents[1]/'workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main'
    release=json.loads((main_root/'evidence/c1-k1-input-freeze-r1/codec-release.json').read_text(encoding='utf-8'))
    need(release.get('finite_python_checks_passed') and release.get('encoder_sha256') == sha(Path(__file__)), 'K1 exact-source release missing')
    need(release['protocol_sha256'] == PROTOCOL_SHA, 'release protocol')
    source=implementation/'results/ws31-consensus-v2-inputs-r1/K1'
    target=implementation/'results/ws31-v2-native-declarations-r1/K1'
    names=['{}-{}'.format(f,s) for f in ('D1','D2') for s in k1.K1_SEEDS]
    need(all(not (target/name).exists() for name in names), 'existing declaration output')
    manifests=[write_one(source/name,target/name) for name in names]
    print(json.dumps({'status':'DECLARATION_BYTES_WRITTEN_ONLY','demands':len(manifests),
                      'requests':sum(x['count'] for x in manifests),'native_objects':0,'network_runs':0}))


if __name__=='__main__':
    main()
