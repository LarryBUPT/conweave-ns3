"""Static/source/input checks only. Explicitly not native compilation or simulation."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from make_ws30_v14_inputs import generate,ecmp,pair

ROOT=Path(__file__).resolve().parents[1]
BASE='2c9f3a50bafad0740b461496ba24fa81941a9bc7'
def original(path):return subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'show',BASE+':'+path],cwd=ROOT).decode()
def body(s,marker):
    start=s.index(marker);a=s.index('{',start);depth=1;i=a+1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return re.sub(r'\s+','',s[start:i])
def main():
    manifests=[generate(),generate()];assert manifests[0]==manifests[1]
    for name in ('run.py','scripts/remote_experiment.py','scripts/remote_worker.py','scripts/make_ws30_v14_inputs.py','scripts/prepare_ws30_v14.py','scripts/verify_ws30_v14_raw.py','scripts/run_ws30_v14.py'):
        ast.parse((ROOT/name).read_text())
    ast.parse((ROOT/'scripts/remote_worker.py').read_text(),feature_version=(3,5))
    sw='src/point-to-point/model/switch-node.cc'
    for function in ('uint32_t SwitchNode::DoLbDrill','uint32_t SwitchNode::DoLbWs30(','uint32_t SwitchNode::DoLbClassReserve'):
        assert body(original(sw),function)==body((ROOT/sw).read_text(),function),function
    cw='src/point-to-point/model/conweave-routing.cc'
    text=(ROOT/cw).read_text().replace('#include "ws30-cw-observer.h"','')
    text=re.sub(r'\s*const uint32_t observedOldPath=txEntry\._pathId;','',text)
    text=re.sub(r'if \(conweaveDataTag.GetFlagData\(\)!=ConWeaveDataTag::DATA\)\s*Ws30CwEvent\(.*?;','',text,flags=re.S)
    text=re.sub(r'Ws30CwEvent\(.*?;','',text,flags=re.S)
    assert re.sub(r'\s+','',text)==re.sub(r'\s+','',original(cw)),'Non-observer ConWeave edit'
    helper=(ROOT/'src/point-to-point/model/ws30-cw-observer.h').read_text()
    for bad in ('Simulator::Schedule','rand(','UniformVariable','Create<Packet>','AddPacketTag','SendToDev','IsFinished(','GetBytesLeft('):assert bad not in helper,bad
    rdma=(ROOT/'src/point-to-point/model/rdma-hw.cc').read_text()
    state=body(rdma,'static void Ws30V14State')
    for bad in ('Schedule(','Cancel(','rand(','GetBytesLeft(','IsFinished('):assert bad not in state,bad
    # Strip only known observation-only additions, then compare actual protocol
    # functions. Generalized round constants retain the old profile's values.
    stripped=rdma.replace('Ws30RoundBytes()','8192').replace('Ws30RoundIntervalNs()','100000')
    stripped=re.sub(r'if \(Ws30V14Enabled\(\) && Ws30Level\(\) && qp->m_ws30Serial\) \{\s*\+\+qp->m_ws30(?:Sack|Recovery)Events;\s*Ws30V14State\([^;]+;\s*\}','',stripped)
    stripped=re.sub(r'if \(Ws30V14Enabled\(\) && Ws30Level\(\) && qp->m_ws30Serial\) \+\+qp->m_ws30CnpEvents;','',stripped)
    stripped=re.sub(r'if \(Ws30V14Enabled\(\) && Ws30Level\(\) && ch.sip==0x0b000001 && ch.dip==0x0b000301 &&\s*\(ecnbits \|\| cnp_check \|\| ch.udp.seq%8192==0\)\)\s*std::cout << "WS30V14_RX_STATE.*?std::endl;','',stripped,flags=re.S)
    stripped=re.sub(r'if \(cnp \|\| ch.ack.irnNackSize \|\| \(Ws30V14Enabled\(\) && qp->irn.m_recovery\)\)\s*Ws30V14State\([^;]+;','',stripped)
    stripped=re.sub(r'Ws30V14State\([^;]+;','',stripped[stripped.index('struct Ws25QpDiagnostic'):])
    checked=[]
    for marker in ('int RdmaHw::ReceiveUdp','int RdmaHw::ReceiveAck','void RdmaHw::PktSent','void RdmaHw::UpdateAlphaMlx','void RdmaHw::cnp_received_mlx','void RdmaHw::CheckRateDecreaseMlx'):
        assert body(stripped,marker)==body(original('src/point-to-point/model/rdma-hw.cc'),marker),marker
        checked.append(marker)
    routing=(ROOT/sw).read_text().replace('Ws30RoundBytes()','8192')
    routing=re.sub(r'auto observePair = .*?\n    \};','',routing,flags=re.S)
    routing=routing.replace('{ observePair(hit->second); return hit->second.chosen; }','return hit->second.chosen;').replace('observePair(pair);','')
    assert body(routing,'uint32_t SwitchNode::DoLbWs30V13(')==body(original(sw),'uint32_t SwitchNode::DoLbWs30V13(')
    assert [p for p in range(10000,10009) if len(set(pair(p)))==2]==[10003,10006,10008]
    assert pair(10001)==[2,2] # observed original fixture collision
    for seed in (20263101,20263102):
        files=[ROOT/'config'/('ws30w5_seed%d_%s.txt'%(seed,t)) for t in ('concurrent','lead20us')]
        identities=[]
        for p in files:
            rows=[l.split() for l in p.read_text().splitlines()[1:]]
            identities.append(sorted(tuple(a[:4]+a[5:]) for a in rows))
            assert sum(int(a[3]) for a in rows)==2281701376
        assert identities[0]==identities[1]
    report={'scope':'static only; no native compiler or simulation invoked','analysis_model':'gpt-6.1-sol / medium','source_baseline':BASE,'native_historical_functions_equal':True,'ConWeave_equal_after_removing_passive_hooks':True,'observer_no_rng_events_packets':True,'generator_repeat_bytes_equal':True,'input_manifest':manifests[0],'pending':['native optimized build','all 18 regression cells','24 lifecycle and 6 observation controls','four ConWeave invariance cells','all W5 performance and formal cells']}
    names=['.gitattributes','run.py','scratch/network-load-balance.cc','scripts/remote_experiment.py','scripts/remote_worker.py','scripts/make_ws30_v14_inputs.py','scripts/prepare_ws30_v14.py','scripts/verify_ws30_v14_raw.py','scripts/audit_ws30_v14_static.py','src/point-to-point/model/ws30-cw-observer.h','src/point-to-point/model/ws30-v13-fixture.h','src/point-to-point/model/rdma-hw.cc','src/point-to-point/model/rdma-queue-pair.h','src/point-to-point/model/switch-node.cc','src/point-to-point/model/conweave-routing.cc','src/point-to-point/wscript']
    report['source_file_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    report['remote_worker_python35_syntax']=True
    report['transport_protocol_functions_equal_after_removing_hooks']=checked
    report['strict_classless_routing_equal_after_removing_hooks']=True
    report['analysis_turn_context']={'model':'gpt-6.1-sol','effort':'medium','turn_id':'01a1758b-1da9-7c23-a858-775b233fe8c9'}
    report['execution_entrypoint_sha256']=hashlib.sha256((ROOT/'scripts/run_ws30_v14.py').read_bytes()).hexdigest()
    path=ROOT/'docs/research/evidence/ws30-v14-static-audit-r5.json'
    data=json.dumps(report,indent=2)+'\n'
    if path.exists():assert json.loads(path.read_text())==report
    else:path.write_text(data,encoding='utf-8')
    print('Static source/input audit passed; native build and dynamic checks remain pending.')
if __name__=='__main__':main()
