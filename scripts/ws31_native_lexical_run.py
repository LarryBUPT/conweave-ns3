"""Python3.5-compatible bounded compiler/codec runner. No SSH or ns-3 launch."""
from __future__ import print_function
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import time


def sha(path):
    with open(path,'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--corpus',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    source=os.path.realpath(args.source)
    corpus=os.path.realpath(args.corpus)
    output=os.path.realpath(args.output)
    if os.path.exists(output):
        raise ValueError('refuse existing output')
    os.makedirs(output)
    events=[]
    def run(name,command,expected=0,timeout=60):
        start=time.time()
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=source)
        try:
            stdout,stderr=process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout,stderr=process.communicate()
            with open(os.path.join(output,name+'.stdout'),'wb') as handle: handle.write(stdout)
            with open(os.path.join(output,name+'.stderr'),'wb') as handle: handle.write(stderr)
            raise RuntimeError(name+' timeout')
        for suffix,data in [('stdout',stdout),('stderr',stderr)]:
            with open(os.path.join(output,name+'.'+suffix),'wb') as handle: handle.write(data)
        events.append({'name':name,'command':command,'expected_exit':expected,'actual_exit':process.returncode,
                       'started_epoch_s':start,'elapsed_s':time.time()-start,
                       'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
                       'stderr_sha256':hashlib.sha256(stderr).hexdigest()})
        with open(os.path.join(output,'commands.json'),'w') as handle:
            json.dump(events,handle,indent=2,sort_keys=True)
        if process.returncode!=expected:
            raise RuntimeError(name+' unexpected exit '+str(process.returncode))
        return stdout
    with open(os.path.join(corpus,'manifest.json')) as handle:
        manifest=json.load(handle)
    for name,item in manifest['files'].items():
        if '/' in name or '\\' in name or name in ('.','..'):
            raise ValueError('unsafe corpus name')
        path=os.path.join(corpus,name)
        if os.path.islink(path) or sha(path)!=item['sha256'] or os.path.getsize(path)!=item['bytes']:
            raise ValueError('corpus identity '+name)
    run('compiler-version',['g++','--version'])
    flags=['-std=c++11','-O2','-Wall','-Wextra','-Werror','-pedantic']
    binaries={}
    for revision,relative in [('r1','validation/r1/scratch/ws31-v2-native-declarations-check.cc'),
                              ('r2','scratch/ws31-v2-native-declarations-check.cc')]:
        binaries[revision]=os.path.join(output,'codec-'+revision)
        run('compile-'+revision,['g++']+flags+[os.path.join(source,relative),'-o',binaries[revision]])
    for name in ('witness-vt-offset302.native','witness-us-offset238.native'):
        run('r1-'+name,[binaries['r1'],'--parse',os.path.join(corpus,name)],expected=2,timeout=10)
        run('r2-'+name,[binaries['r2'],'--parse',os.path.join(corpus,name)],expected=2,timeout=10)
    for family in ('D1','D2'):
        for seed in range(5310001,5310009):
            name='valid-{}-{}'.format(family,seed)
            run('r2-self-'+name,[binaries['r2'],'--self-check',os.path.join(corpus,name+'.native')],timeout=10)
    run('r2-corpus',[binaries['r2'],'--corpus',os.path.join(corpus,'cases.tsv')],timeout=30)
    receipt={'status':'PASS_DECLARATION_LEXICAL_ONLY','finished_utc':datetime.datetime.utcnow().isoformat()+'Z',
             'corpus_manifest_sha256':sha(os.path.join(corpus,'manifest.json')),
             'cases':manifest['cases'],'accept':manifest['accept'],'reject':manifest['reject'],
             'actual_compilations':2,'commands':len(events),'binaries':{r:sha(p) for r,p in binaries.items()},
             'native_objects':0,'ns3_builds':0,'network_runs':0,'new_scientific_demands':0}
    with open(os.path.join(output,'receipt.json'),'w') as handle:
        json.dump(receipt,handle,sort_keys=True,indent=2)
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':
    main()
