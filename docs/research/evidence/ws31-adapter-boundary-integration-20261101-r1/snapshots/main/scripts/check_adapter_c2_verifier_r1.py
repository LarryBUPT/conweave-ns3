"""Literal timing/byte corruption checks; no simulator or experiment execution."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('main_adapter_check', HERE/'verify_adapter_boundary_raw_r1.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def fixture():
    out = []
    phases = ('before','same-control-first','same-launch-first','after','zero')
    # Frozen independently before any execution: first tuple sport1 has wait376.
    assert v.start_wait(1) == 376
    for i,(kind,phase) in enumerate((k,p) for k in ('stop','dispose') for p in phases):
        n = phases.index(phase)
        delay = 0 if n==4 else 376
        tag = 1 if n==4 else 2
        launch = int(n>=2)
        cancel = 1-launch
        control = 10+delay+(-1 if n==0 else 1 if n==3 else 0)
        out.append(('WS31_C2_DEMAND', {'flow_id':i,'demand_ns':10,'size':8192,'tag':tag,
                    'delay_ns':delay,'policy_tag':tag,'tag_transform':0}))
        if launch:
            out.append(('WS31_C2_LAUNCH', {'flow_id':i,'demand_ns':10,'launch_ns':10+delay,'wait_ns':delay,'size':8192}))
        else:
            out.append(('WS31_C2_CANCEL', {'flow_id':i,'demand_ns':10,'time_ns':control,'size':8192}))
        out.append(('WS31_C2_BOUNDARY PASS', {'kind':kind,'phase':phase,'demand_ns':10,'wait_ns':delay,
                    'sip':v.SIP,'dip':v.DIP,'sport':1,'dport':100,'tag':tag,'size':8192,
                    'launch_uid':0 if n==4 else 100+10*i+(1 if n==1 else 0),
                    'control_uid':100+10*i+(0 if n==1 else 1),'control_ns':control,
                    'launched':launch,'cancelled':cancel,'launch_ns':10+delay if launch else 0,
                    'dispatch_demand_ns':10 if launch else 0,'calls':launch,'demanded':1,
                    'demand_bytes':8192,'launch_bytes':8192*launch,'cancel_bytes':8192*cancel,
                    'waited':int(bool(launch and delay)),'delay_sum_ns':delay*launch,
                    'delay_max_ns':delay*launch,'finished':0,'pending':0,'transport':'fixture'}))
    out.append(('WS31_C2_BOUNDARY_SUMMARY PASS',{'cases':10,'network_runs':0,'completions':0}))
    return out


def render(out):
    return ''.join(p+' '+' '.join('{}={}'.format(k,x) for k,x in d.items())+'\n' for p,d in out)


def main():
    original = fixture()
    tests = []
    def summary(out, phase):
        return next(d for p,d in out if p=='WS31_C2_BOUNDARY PASS' and d['phase']==phase)
    bad = copy.deepcopy(original); summary(bad,'same-control-first')['launch_uid']=1; tests.append(('control uid order',bad))
    bad = copy.deepcopy(original); summary(bad,'same-launch-first')['control_ns']+=1; tests.append(('same-time timestamp',bad))
    bad = copy.deepcopy(original); summary(bad,'zero')['launch_uid']=42; tests.append(('zero synchronous launch',bad))
    bad = copy.deepcopy(original); summary(bad,'after')['dispatch_demand_ns']=386; tests.append(('demand clock reset',bad))
    bad = copy.deepcopy(original); summary(bad,'before')['cancel_bytes']=0; tests.append(('cancel byte conservation',bad))
    bad = copy.deepcopy(original); summary(bad,'after')['cancelled']=1; tests.append(('postlaunch falsely cancelled',bad))
    bad = copy.deepcopy(original); bad.append(('WS31_C2_FINISH',{'flow_id':2})); tests.append(('fabricated completion',bad))
    bad = copy.deepcopy(original); bad.pop(0); tests.append(('missing demand',bad))
    bad = copy.deepcopy(original); launch = next(copy.deepcopy(x) for x in bad if x[0]=='WS31_C2_LAUNCH'); bad.append(launch); tests.append(('duplicate production launch',bad))
    bad = copy.deepcopy(original); bad[-1]=(bad[-1][0].replace('PASS','FAIL'),bad[-1][1]); tests.append(('failed completion marker',bad))
    with tempfile.TemporaryDirectory(prefix='adapter-verifier-',dir=HERE.parent/'evidence') as folder:
        path = Path(folder)/'synthetic.log'
        path.write_text(render(original),encoding='ascii')
        positive = v.verify_c2(path)
        for name,bad in tests:
            path.write_text(render(bad),encoding='ascii')
            try:
                v.verify_c2(path)
            except (AssertionError,KeyError):
                continue
            raise AssertionError('Verifier accepted corrupt fixture: '+name)
    print(json.dumps({'status':'PASS_LOCAL_VERIFIER_PREPARATION','positive_synthetic_C2_cases':positive['cases'],
                      'corrupt_fixtures_rejected':[name for name,_ in tests],
                      'scope':'Log verifier preparation only; no CXX, adapter acceptance or simulator execution'}))


if __name__ == '__main__':
    main()
