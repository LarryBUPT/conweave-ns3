"""Main compatibility acceptance for the default transport dispatch extraction."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('adapter_default_previous', HERE/'verify_label_default_raw_r1.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
common, identity = previous.common, previous.identity


def verify(base, plan, reference):
    result = common.verify(base, plan)
    meta = json.loads((base/'metadata.json').read_text(encoding='utf-8'))
    cell = next(c for c in plan['cells'] if c['id']==meta['experiment_id'])
    assert cell['lb'] in ('ws30v13-q12','ws31-c2')
    assert meta['parameters']['ws31_label_profile']==0
    config = {line.split()[0]:line.split()[1:] for line in
              (base/'config/config.txt').read_text(encoding='ascii').splitlines() if line.strip()}
    required = {'LB_MODE':[str(cell['lb_mode'])], 'CC_MODE':['1'], 'ENABLE_PFC':['0'],
                'ENABLE_IRN':['1'], 'RANDOM_SEED':['1'], 'PACKET_PAYLOAD_SIZE':['1000'],
                'BUFFER_SIZE':['9'], 'LINK_DOWN':['0','0','0']}
    for key,wanted in required.items():
        assert config[key]==wanted, (key,config[key])
    assert float(config['ERROR_RATE_PER_LINK'][0])==0
    ref = json.loads((reference/'metadata.json').read_text(encoding='utf-8'))
    assert ref['experiment_id']==cell['reference_id'] and ref['git_commit']==cell['reference_sha']
    assert ref['status']=='SUCCEEDED' and ref['algorithm']==cell['lb']
    for rel in ('config/traffic_trace.txt','config/topology.txt'):
        assert common.digest(base/rel)==common.digest(reference/rel)
    expected,_ = identity.trace_rows(base/'config/traffic_trace.txt')
    fct,log = identity.raw_paths(base)
    ref_fct,ref_log = identity.raw_paths(reference)
    assert common.digest(ref_fct)==cell['reference_fct_sha256']
    assert common.digest(ref_log)==cell['reference_log_sha256']
    assert common.digest(fct)==common.digest(ref_fct)
    assert identity.ordered_hashes(log)==identity.ordered_hashes(ref_log)
    for line in log.open(encoding='utf-8'):
        assert not line.startswith(('WS31_LABEL_','WS31_SWITCH_BOUNDARY','WS31_C2_BOUNDARY'))
        if line.startswith('WS30_ROUTE '):
            v = common.values(line)
            key = ((v['sip']>>8)&65535,(v['dip']>>8)&65535,v['sport'],v['dport'])
            assert v['tag']==expected[key]['tag']
        elif line.startswith('WS30_CHOICE '):
            assert common.values(line)['tag']==0
        if cell['lb']=='ws30v13-q12':
            assert not line.startswith(('WS31_C1_','WS31_C2_','WS31_C3_'))
        else:
            assert not line.startswith(('WS31_C1_','WS31_C3_'))
    prefixes = ()
    if cell['lb']=='ws31-c2':
        result['mechanism_replay'] = common.mechanism(base,'ws31-c2')
        prefixes = ('WS31_C2_DEMAND','WS31_C2_LAUNCH','WS31_C2_FINISH','WS31_C2_STATE')
        for prefix in prefixes:
            assert previous.events(base,prefix)==previous.events(reference,prefix),prefix
    result.update({'status':'MAIN_PASS_DEFAULT_DISPATCH_NETWORK_COMPATIBILITY',
                   'regression':{'reference_id':cell['reference_id'],'reference_sha':cell['reference_sha'],
                                 'full_FCT_equal':True,'ordered_CHOICE_ROUTE_remove_uid_only_equal':True,
                                 'dedicated_events_equal':list(prefixes)},
                   'scope':'Default dispatch technical compatibility only; real endpoint lifecycle and independent efficacy/cost remain'})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    parser.add_argument('plan',type=Path)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    assert not args.output.exists(),'Refusing to overwrite main acceptance'
    result = verify(args.results,json.loads(args.plan.read_text(encoding='utf-8')),args.reference)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'id':result['id'],'status':result['status'],'flows':result['flows'],
                      'replay':result.get('mechanism_replay')}))
