"""Finite lexical correctness fixtures from existing declarations, not new demands."""
import argparse
import hashlib
import json
from pathlib import Path
import ws31_native_declarations as codec


def canonical(text):
    header, rows = codec.parse_text(text)
    lines = ['{} K0 {} {} {} {} {} {} 1000 48'.format(
        codec.MAGIC, header['family'], header['seed'], header['count'],
        header['t0_ns'], header['H_ns'], header['stop_ns']),
        'PROTOCOL_SHA256 '+codec.PROTOCOL_SHA,
        'CONSTRUCTOR_SHA256 '+codec.CONSTRUCTOR_SHA]
    lines.extend(' '.join(str(row[key]) for key in codec.FIELDS) for row in rows)
    return ('\n'.join(lines)+'\n').encode('ascii')


def cases(base):
    codec.need(base[302] == 10 and base[238] == 32, 'witness offsets drifted')
    result = []
    def add(name, data, accept):
        result.append((name+'.native', data, accept))
    add('lf', base, True)
    add('crlf', base.replace(b'\n', b'\r\n'), True)
    add('no-final-lf', base[:-1], True)
    add('no-final-crlf', base.replace(b'\n', b'\r\n')[:-2], True)
    add('tabs', base.replace(b' ', b'\t'), True)
    add('repeated-and-edge-space-tab', b'\n'.join(
        b' \t'+line.replace(b' ', b' \t  ')+b'\t ' for line in base.split(b'\n')[:-1])+b'\n', True)
    lines=base.split(b'\n')[:-1]
    add('mixed-lf-crlf', b''.join(line+(b'\r\n' if i%2 else b'\n')
                                for i,line in enumerate(lines)), True)
    add('witness-vt-offset302', base[:302]+b'\x0b'+base[303:], False)
    add('witness-us-offset238', base[:238]+b'\x1f'+base[239:], False)
    for name,value in [('nul',0),('vt',11),('ff',12),('fs',28),('gs',29),
                       ('rs',30),('us',31),('del',127),('byte80',128),('byteff',255)]:
        add('field-'+name,base[:238]+bytes([value])+base[239:],False)
    add('bare-cr-between-lines',base[:302]+b'\r'+base[303:],False)
    add('bare-cr-at-eof',base[:-1]+b'\r',False)
    add('double-crlf',base.replace(b'\n',b'\r\r\n',1),False)
    add('utf8-bom',b'\xef\xbb\xbf'+base,False)
    add('utf8-nbsp',base[:238]+b'\xc2\xa0'+base[239:],False)
    add('utf8-line-separator',base[:302]+b'\xe2\x80\xa8'+base[303:],False)
    add('extra-blank-line',base+b'\n',False)
    add('truncated',b'\n'.join(base.split(b'\n')[:-2])+b'\n',False)
    add('bad-stage',base.replace(b' K0 ',b' K1 ',1),False)
    return result


def check(data, accepted, expected=None):
    try:
        actual=canonical(data.decode('ascii'))
    except (ValueError, UnicodeDecodeError):
        codec.need(not accepted,'positive fixture rejected')
        return
    codec.need(accepted,'negative fixture accepted')
    codec.need(actual == expected,'field roundtrip mismatch')


def build(native_root, output):
    codec.need(not output.exists(),'refuse existing corpus')
    base=(native_root/'D1-5310001/requests.native').read_bytes()
    items=cases(base)
    for family in ('D1','D2'):
        for seed in range(5310001,5310009):
            name='valid-{}-{}'.format(family,seed)
            items.append((name+'.native',(native_root/(name[6:]+'/requests.native')).read_bytes(),True))
    files={}
    listing=[]
    for name,data,accepted in items:
        reference=canonical(data.decode('ascii')) if accepted else None
        check(data,accepted,reference)
        files[name]=data
        expected=name+'.canonical' if accepted else '-'
        if accepted:
            files[expected]=reference
        listing.append('{}\t{}\t{}\t{}'.format(name,'ACCEPT' if accepted else 'REJECT',expected,
                                               hashlib.sha256(data).hexdigest()))
    files['cases.tsv']=('\n'.join(listing)+'\n').encode('ascii')
    manifest={'schema':'ws31-native-lexical-corpus-r2','protocol_sha256':codec.PROTOCOL_SHA,
              'cases':len(items),'accept':sum(int(x[2]) for x in items),
              'reject':sum(int(not x[2]) for x in items),'new_scientific_demands':0,
              'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
                       for name,data in files.items()}}
    output.mkdir(parents=True,exist_ok=False)
    for name,data in files.items():
        with (output/name).open('xb') as handle:
            handle.write(data)
    with (output/'manifest.json').open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(manifest,handle,indent=2,sort_keys=True)
        handle.write('\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=build(args.native_root,args.output)
    print(json.dumps({key:result[key] for key in ('cases','accept','reject','new_scientific_demands')}))
