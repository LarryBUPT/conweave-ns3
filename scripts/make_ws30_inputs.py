"""Freeze WS-30 inputs before execution; refuse replacement of different bytes."""
import hashlib
import json
import random
import subprocess
from pathlib import Path
from make_ws25_demand import make

ROOT=Path(__file__).resolve().parents[1]
def put(path,data):
    if path.exists():
        if path.read_bytes()!=data: raise RuntimeError('Immutable input differs: '+str(path))
    else: path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
def item(path):
    lines=path.read_text().splitlines()
    counts={};previous=-1.0
    for line in lines[1:]:
        parts=line.split(); tag=parts[5] if len(parts)==6 else '0'
        start=float(parts[4]);assert start>=previous,('Input time decreases',path)
        previous=start
        counts[tag]=counts.get(tag,0)+1
    assert int(lines[0])==sum(counts.values())
    return {'trace':path.name,'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'input_flows':int(lines[0]),'expected_tags':counts}
def main():
    config=ROOT/'config';rows=[]
    for seed in range(20263021,20263045):
        make(seed,config,levels=(192,))
        sync=config/f'ws25_seed{seed}_b192.txt'; rows.append({'seed':seed,'condition':'sync',**item(sync)})
        lines=sync.read_text().splitlines();lead=[lines[0]]
        for line in lines[1:]:
            parts=line.split()
            if parts[5]=='2':parts[4]='2.000020000'
            lead.append(' '.join(parts))
        dest=config/f'ws30_seed{seed}_lead20us.txt'
        put(dest,('\n'.join(lead)+'\n').encode('ascii'))
        rows.append({'seed':seed,'condition':'lead20us',**item(dest)})
    # Technical traffic only: many contenders, multiple packet QPs, labels 0/3.
    rng=random.Random(20263004)
    lines=[]
    for i in range(32):
        lines.append(f'{(i%8)*4} {320+(i%4)*4} 3 262144 2.000000000 1')
    for i in range(128):
        lines.append(f'{64+(i%16)*4} {320+(i%8)*4} 3 8192 2.000000000 2')
    for label in (0,3):
        for i in range(4): lines.append(f'{128+i*4} {320+i*4} 3 8192 2.000000000 {label}')
    # Keep controlled contention and same-time insertion order fixed.
    tech=config/'ws30_technical168.txt'
    put(tech,(str(len(lines))+'\n'+'\n'.join(lines)+'\n').encode('ascii'))
    five=config/'ws30_fivecol4.txt'
    put(five,b'4\n4 320 3 8192 2.000000000\n8 324 3 8192 2.000000000\n12 328 3 8192 2.000000000\n16 332 3 8192 2.000000000\n')
    # Stable chronological order is required by the streaming input parser.
    # Keep the original invalid fixture as a failed-input audit artifact.
    techlead=config/'ws30_technical168_lead_v2.txt'
    shifted=tech.read_text().replace('2.000000000 2','2.000020000 2').splitlines()
    ordered=sorted(shifted[1:],key=lambda line:float(line.split()[4]))
    put(techlead,('\n'.join([shifted[0]]+ordered)+'\n').encode('ascii'))
    result={'new_inputs':rows,'technical':[item(x) for x in (tech,five,techlead)],
            'generator_sha256':hashlib.sha256(subprocess.check_output(
                ['git','-C',str(ROOT),'show','HEAD:scripts/make_ws25_demand.py'])).hexdigest(),
            'generator_hash_convention':'Git blob LF bytes; local Windows checkout may use CRLF',
            'topology_sha256':hashlib.sha256((config/'topo_1280_400G_400G_OS1.txt').read_bytes()).hexdigest()}
    dest=ROOT/'docs/research/evidence/ws30-inputs-v3.json'
    put(dest,(json.dumps(result,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps({'new_inputs':len(rows),'technical_inputs':3,'manifest_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
