"""Read complete adapter logs and check raw case clocks, counters and state."""
import json,pathlib
def fields(line):
    return {k:int(v) if v.isdigit() else v for k,v in (t.split('=',1) for t in line.split() if '=' in t)}
def framed(n):return n+((n+999)//1000)*56
def parse(path,prefix):return [fields(line) for line in path.read_text(encoding='utf-8').splitlines() if line.startswith(prefix)]
def switch(log,candidate):
    packets=parse(log,'WS31_SWITCH_BOUNDARY_PACKET ');resets=parse(log,'WS31_SWITCH_BOUNDARY_RESET ');idle=parse(log,'WS31_SWITCH_BOUNDARY_IDLE ')
    for p in packets:
        assert p['wire']==p['payload']+56 and p['conserved']==1 and p['present'] in (0,1)
    grouped={case:[p for p in packets if p['case']==case] for case in dict.fromkeys(p['case'] for p in packets)}
    if candidate=='C1':
        assert list(grouped)==['c1-ranges','c1-expiry-reset','c1-capacity','c1-range-limit','c1-wrap']
        assert len(packets)==20 and len(resets)==3 and not idle
        p=grouped['c1-ranges'];assert [x['time_ns'] for x in p]==[0,1,2,3,4]
        assert [x['seq'] for x in p]==[0,0,300,50,400] and [x['payload'] for x in p]==[100,100,100,300,100]
        assert [x['unique'] for x in p]==[100,100,200,400,500] and [x['duplicate'] for x in p]==[0,1,1,1,1]
        assert [x['pressure'] for x in p]==[framed(x) for x in [8092,8092,7992,7792,7692]]
        assert [x['queue_bytes'] for x in p]==[0,5000,5000,5000,5000] and len({x['chosen'] for x in p})==1
        p=grouped['c1-expiry-reset'];assert [x['time_ns'] for x in p]==[0,19999,20000,20001,20002]
        assert [x['budget_entries'] for x in p]==[1,1,0,0,1] and [x['expired'] for x in p]==[0,0,1,1,1]
        assert [x['unique'] for x in p]==[1000,1000,1000,1000,1100] and [x['pressure'] for x in p]==[framed(64536),framed(64536),0,0,framed(8092)]
        assert len({x['chosen'] for x in p[:4]})==1
        p=grouped['c1-capacity'];assert [x['time_ns'] for x in p]==[0,1,2,3]
        assert [x['budget_entries'] for x in p]==[1,1,0,1] and [x['capacity_fallback'] for x in p]==[0,1,1,1]
        assert [x['unique'] for x in p]==[100,100,100,200] and p[1]['chosen']==p[2]['chosen']
        for case in ('c1-range-limit','c1-wrap'):
            p=grouped[case];assert [x['time_ns'] for x in p]==[0,1,2]
            assert [x['budget_entries'] for x in p]==[1,0,0] and [x['range_fallback'] for x in p]==[0,1,1]
            assert [x['unique'] for x in p]==[100,100,100] and len({x['chosen'] for x in p})==1
        assert grouped['c1-wrap'][1]['seq']==0xfffffff0 and grouped['c1-wrap'][1]['payload']==32
        for x in resets:assert x['pairs_after']==x['budget_after']==x['quota_after']==0 or x['case']=='c1-capacity' and x['pairs_after']==1 and x['budget_after']==0
    else:
        assert list(grouped)==['c3-borrow-expiry-reset','c3-unknown-reset'] and len(packets)==9 and len(resets)==3 and len(idle)==3
        p=grouped['c3-borrow-expiry-reset'];assert [x['time_ns'] for x in p]==[0,100,200,201,20202,20203]
        assert [x['fresh'] for x in p]==[1,1,2,2,2,3] and [x['hits'] for x in p]==[0,1,1,2,3,3]
        assert [x['borrowed'] for x in p]==[1,1,1,1,1,1] and [x['restricted'] for x in p]==[0,0,1,1,1,2]
        assert [x['residual'] for x in p]==[0,0,0,1,1,1] and [x['residual_bytes'] for x in p]==[0,0,0,156,156,156]
        assert [x['activation1'] for x in p]==[1,1,1,1,2,2] and [x['activation2'] for x in p]==[0,0,1,1,1,2]
        assert len({p[i]['chosen'] for i in (0,1,3,4)})==1 and p[3]['present']==0
        assert [x['time_ns'] for x in idle]==[20199,20200,20201] and all(x['observer_expires']==0 and x['quota_entries']==2 and x['live_owner2']==1 and x['conserved']==1 for x in idle)
        assert [(x['active1'],x['active2']) for x in idle]==[(1,1),(1,0),(0,0)]
        p=grouped['c3-unknown-reset'];assert [x['time_ns'] for x in p]==[0,1,2] and [x['fresh'] for x in p]==[1,1,2]
        assert [x['activation1'] for x in p]==[0,0,1] and all(x['activation2']==0 for x in p)
        assert p[0]['present']==0 and p[1]['chosen']==p[0]['chosen']
        assert [(x['quota_before'],x['quota_after']) for x in resets]==[(2,1),(1,0),(1,0)]
    return {'status':'PASS','candidate':candidate,'cases':list(grouped),'packet_rows':len(packets),'reset_rows':len(resets),'idle_rows':len(idle),
        'packets':packets,'resets':resets,'idle':idle,'framing_bytes':56,'scope':'Actual adapter calls with real packets/egress queues; no network endpoint generations'}
def start_hash(v):
    h=2166136261^0x43c2a517
    for word in (v['sip'],v['dip'],v['sport']|(v['dport']<<16)):
        for shift in range(0,32,8):h=((h^((word>>shift)&255))*16777619)&0xffffffff
    h^=h>>16;h=(h*0x85ebca6b)&0xffffffff;h^=h>>13;return h
def c2(log):
    cases=parse(log,'WS31_C2_BOUNDARY PASS ');assert len(cases)==10
    assert [(x['kind'],x['phase']) for x in cases]==[(kind,phase) for kind in ('stop','dispose') for phase in ('before','same-control-first','same-launch-first','after','zero')]
    for v in cases:
        phase=v['phase'];cancelled=phase in ('before','same-control-first');wait=0 if phase=='zero' else start_hash(v)%501
        assert (phase=='zero' or wait>1) and v['wait_ns']==wait and v['demand_ns']==10 and v['size']==8192
        assert v['demanded']==1 and v['demand_bytes']==8192 and v['launched']==int(not cancelled) and v['cancelled']==int(cancelled)
        assert v['calls']==v['launched'] and v['launch_bytes']==8192*v['launched'] and v['cancel_bytes']==8192*v['cancelled']
        assert v['finished']==v['pending']==0 and v['transport']=='fixture'
        assert v['control_ns']==10+wait+(-1 if phase=='before' else 1 if phase=='after' else 0)
        assert v['waited']==int(not cancelled and wait>0) and v['delay_sum_ns']==v['delay_max_ns']==(0 if cancelled else wait)
        assert (v['launch_ns'],v['dispatch_demand_ns'])==((0,0) if cancelled else (10+wait,10))
        if phase=='same-control-first':assert v['control_uid']<v['launch_uid']
        if phase=='same-launch-first':assert v['launch_uid']<v['control_uid']
    demands=parse(log,'WS31_C2_DEMAND ');launches=parse(log,'WS31_C2_LAUNCH ');cancels=parse(log,'WS31_C2_CANCEL ')
    assert len(demands)==10 and len(launches)==6 and len(cancels)==4
    assert {x['flow_id'] for x in demands}==set(range(10))
    assert {x['flow_id'] for x in launches}=={2,3,4,7,8,9} and {x['flow_id'] for x in cancels}=={0,1,5,6}
    return {'status':'PASS','candidate':'C2','cases':cases,'case_count':10,'demand_events':10,'launch_events':6,'cancel_events':4,'finished':0,'real_QPs':0,'scope':'Original timing/cancel adapter; transport dispatch fixture only'}
def verify(folder):
    return {'status':'PASS_17_NEW_ADAPTER_CASES','C1':switch(folder/'logs/adapter-C1.log','C1'),'C2':c2(folder/'logs/adapter-C2.log'),'C3':switch(folder/'logs/adapter-C3.log','C3')}
if __name__=='__main__':
    import sys
    print(json.dumps(verify(pathlib.Path(sys.argv[1])),indent=2))
