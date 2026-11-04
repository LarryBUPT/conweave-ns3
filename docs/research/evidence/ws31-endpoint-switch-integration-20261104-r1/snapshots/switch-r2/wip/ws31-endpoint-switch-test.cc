#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "../src/point-to-point/model/ws31-endpoint-switch-probe.h"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <type_traits>

using namespace ns3;
using namespace ns3::ws31;

static void Require(bool ok,const char *reason) {
    if (!ok) throw std::runtime_error(reason);
}

namespace ns3 {
// Only this test's setup/fingerprint code has access. No production caller uses
// these methods. Serialization is semantic, not padding/object-byte comparison.
class Ws31EndpointSwitchFixture {
    static void KeyState(std::ostream &o,const ws31::Key &k) {
        o << std::get<0>(k) << ',' << std::get<1>(k) << ','
          << std::get<2>(k) << ',' << std::get<3>(k) << ';';
    }
    static void Decision(std::ostream &o,const ws31::QuotaAdmission::Decision &d) {
        o << d.category << ',' << d.first << ',' << d.second << ',' << d.chosen << ','
          << d.owner << ',' << d.eligible << ',' << d.q1 << ',' << d.q2 << ','
          << d.fresh << ',' << d.restricted << ',' << d.borrowed << ',' << d.residual << ';';
    }
    static void BudgetEntry(std::ostream &o,const ws31::BudgetLedger::Entry &e) {
        o << e.port << ',' << e.mtu << ',' << e.overhead << ',' << e.remaining << ','
          << e.deadline->first << ';'; KeyState(o,e.deadline->second);
        for (const auto &range:e.ranges) o << range.first << ',' << range.second << ';';
    }
    static void QuotaEntry(std::ostream &o,const ws31::QuotaAdmission::Entry &e) {
        Decision(o,e.d); o << e.live << ';';
        if (e.live) { o << e.expiry->first << ';'; KeyState(o,e.expiry->second); }
    }
public:
    static void Seed(Ptr<SwitchNode> s,const ws31::Key &k,const ws31::Key &other) {
        SwitchNode::Ws30Pair a; a.first=1; a.second=2; a.chosen=1;
        SwitchNode::Ws30Pair b; b.first=3; b.second=4; b.chosen=4;
        s->m_ws30V13Pairs[k]=a; s->m_ws30V13Pairs[other]=b;
        s->m_ws31Pairs[k]=a; s->m_ws31Pairs[other]=b;
        Require(s->m_ws31Budget.Insert(k,1,1024,512,16,0,1),"Target budget setup failed");
        Require(s->m_ws31Budget.Insert(other,4,2048,1024,32,0,1000),"Other budget setup failed");
        s->m_ws31Budget.Observe(k,0,128,0);
        s->m_ws31Budget.Observe(k,0,128,0); // Nonzero duplicate counter and ranges.
        s->m_ws31Quota=ws31::QuotaAdmission(10); // Empty object only, before entries.
        std::vector<uint32_t> ports{1,2,3,4};
        auto load=[](uint32_t port) { return uint64_t(port*3); };
        auto target=s->m_ws31Quota.Admit(k,1,ports,0,0,0,64,false,load);
        auto unrelated=s->m_ws31Quota.Admit(other,1,ports,1,1,0,96,false,load);
        Require(target.borrowed && target.owner==2 && !unrelated.borrowed,
                "Quota setup did not create one borrowed and one own entry");
        s->m_ws31Observed.Observe(1,73,0,1000);
        s->m_ws31Observed.Observe(4,91,0,1000);
    }
    static std::string Shared(Ptr<SwitchNode> s) {
        std::ostringstream o; const auto &q=s->m_ws31Quota;
        o << q.window << ';';
        for (unsigned i=0;i<3;++i) o << q.seen[i] << ',' << q.last[i] << ';';
        for (const auto &p:s->m_ws31Observed.ports)
            o << p.first << ',' << p.second.bytes << ',' << p.second.time << ';';
        return o.str();
    }
    static std::string Other(Ptr<SwitchNode> s,const ws31::Key &k) {
        std::ostringstream o;
        const auto &p=s->m_ws30V13Pairs.at(k), &c=s->m_ws31Pairs.at(k);
        o << p.first << ',' << p.second << ',' << p.chosen << ';'
          << c.first << ',' << c.second << ',' << c.chosen << ';';
        BudgetEntry(o,s->m_ws31Budget.entries.at(k));
        QuotaEntry(o,s->m_ws31Quota.entries.at(k)); return o.str();
    }
    static std::string State(Ptr<SwitchNode> s) {
        std::ostringstream o;
        for (const auto &p:s->m_ws30V13Pairs) {
            KeyState(o,p.first); o << p.second.first << ',' << p.second.second << ',' << p.second.chosen << ';';
        }
        o << '|';
        for (const auto &p:s->m_ws31Pairs) {
            KeyState(o,p.first); o << p.second.first << ',' << p.second.second << ',' << p.second.chosen << ';';
        }
        const auto &b=s->m_ws31Budget;
        o << '|' << b.capacity << ',' << b.maxRanges << ',' << b.expired << ',' << b.capacityFallbacks
          << ',' << b.rangeFallbacks << ',' << b.duplicatePackets << ',' << b.uniquePayload << ',' << b.peakEntries << ';';
        for (const auto &p:b.entries) { KeyState(o,p.first); BudgetEntry(o,p.second); }
        o << '|'; for (const auto &p:b.deadlines) { o << p.first << ';'; KeyState(o,p.second); }
        o << '|'; for (const auto &p:b.totals) o << p.first << ',' << p.second << ';';
        const auto &q=s->m_ws31Quota;
        o << '|' << q.fresh << ',' << q.hits << ',' << q.borrowedAdmissions << ',' << q.restrictedAdmissions
          << ',' << q.residualPackets << ',' << q.residualWireBytes << ';';
        for (unsigned i=0;i<3;++i) o << q.activations[i] << ',' << q.liveBorrowed[i] << ','
          << q.borrowedAtActivation[i] << ',' << q.maxBorrowedAtActivation[i] << ';';
        for (const auto &p:q.entries) { KeyState(o,p.first); QuotaEntry(o,p.second); }
        o << '|'; for (const auto &p:q.deadlines) { o << p.first << ';'; KeyState(o,p.second); }
        o << '|' << Shared(s) << '|' << s->m_ws30V13Hits << ',' << s->m_ws30V13Misses << ','
          << s->m_ws30V13Peak << ',' << s->m_ws31Fresh << ',' << s->m_ws31Hits;
        return o.str();
    }
    static void VerifyOverdue(Ptr<SwitchNode> s,const ws31::Key &k) {
        const auto &b=s->m_ws31Budget; const auto &q=s->m_ws31Quota;
        Require(b.entries.at(k).deadline->first==1 && b.expired==0 && b.duplicatePackets==1,
                "Read expired or changed budget contents");
        Require(q.entries.at(k).live && q.entries.at(k).expiry->first==10 &&
                q.liveBorrowed[2]==1 && !q.Active(1,20),
                "Read expired quota or rewrote shared activity");
    }
    static void VerifyCleanup(Ptr<SwitchNode> s,const ws31::Key &k,const ws31::Key &other) {
        Require(!s->m_ws30V13Pairs.count(k) && !s->m_ws31Pairs.count(k) &&
                !s->m_ws31Budget.Contains(k) && !s->m_ws31Quota.Contains(k),"Target cleanup missed a table");
        Require(s->m_ws31Budget.totals.at(1)==0 && s->m_ws31Budget.totals.at(4)==2112 &&
                s->m_ws31Budget.deadlines.size()==1 && s->m_ws31Quota.deadlines.size()==1 &&
                s->m_ws31Budget.Contains(other) && s->m_ws31Quota.Contains(other) &&
                s->m_ws31Quota.liveBorrowed[2]==0 && s->m_ws31Budget.Conserved() && s->m_ws31Quota.Conserved(),
                "Original targeted cleanup changed unrelated accounting incorrectly");
    }
};

// The existing narrow Qbb fixture friendship also supplies endpoint fingerprints.
class Ws31EndpointSnapshotFixture {
public:
    static void Event(std::ostream &o,const EventId &e) {
        o << e.GetUid() << ',' << e.GetTs() << ',' << e.GetContext() << ',' << e.IsRunning() << ';';
    }
    static void Device(std::ostream &o,Ptr<QbbNetDevice> d) {
        o << d->m_linkUp << ',' << d->m_txMachineState << ',' << PeekPointer(d->m_currentPkt) << ';';
        if (d->m_currentPkt) o << d->m_currentPkt->GetUid() << ',' << d->m_currentPkt->GetSize() << ';';
        Event(o,d->m_nextSend);
        for (uint32_t i=0;i<QbbNetDevice::qCnt;++i) { o << d->m_paused[i] << ';'; Event(o,d->m_resumeEvt[i]); }
        o << PeekPointer(d->m_queue) << ';';
        if (d->m_queue) for (uint32_t i=0;i<BEgressQueue::qCnt;++i) o << d->m_queue->GetNBytes(i) << ';';
        if (d->GetNode()->GetNodeType()!=0) return;
        const auto eq=d->m_rdmaEQ;
        o << PeekPointer(eq) << ',' << eq->m_rrlast << ',' << eq->m_qlast << ','
          << PeekPointer(eq->m_ackQ) << ',' << eq->m_ackQ->GetNBytes() << ',' << eq->m_ackQ->GetNPackets()
          << ',' << PeekPointer(eq->m_qpGrp) << ';';
        o.write(eq->m_qpGrp->m_qp_finished,sizeof(eq->m_qpGrp->m_qp_finished));
        for (const auto &p:eq->current_pause_time) o << p.first << ',' << p.second.GetTimeStep() << ';';
        for (auto qp:eq->m_qpGrp->m_qps) {
            o << PeekPointer(qp) << ',' << qp->m_flow_id << ',' << qp->sip.Get() << ',' << qp->dip.Get() << ','
              << qp->sport << ',' << qp->dport << ',' << qp->m_pg << ',' << qp->m_size << ','
              << qp->snd_nxt << ',' << qp->snd_una << ',' << qp->m_workload_tag << ','
              << qp->startTime.GetTimeStep() << ',' << qp->m_ws31LaunchDelayNs << ','
              << qp->m_ws30Persistent << ',' << qp->m_ws30Released << ',' << qp->irn.m_enabled << ',' << qp->irn.m_sack << ';';
            Event(o,qp->m_retransmit); Event(o,qp->mlx.m_eventUpdateAlpha);
            Event(o,qp->mlx.m_eventDecreaseRate); Event(o,qp->mlx.m_rpTimer);
        }
    }
};

class Ws31RoleNode : public Node {
public:
    void Role(uint32_t type) { m_node_type=type; }
};
class Ws31DerivedSwitch : public SwitchNode {};
}

typedef Ws31EndpointSwitchProbe Probe;
typedef Probe::Observation (*CompositeRead)(int32_t,const EndpointLedger::Entry &,
    Ptr<RdmaHw>,Ptr<RdmaHw>,Ptr<RdmaQueuePair>,Ptr<RdmaRxQueuePair>,const Probe::Scope &,uint32_t,uint32_t);
static_assert(std::is_same<decltype(&Probe::Read),CompositeRead>::value,
              "Only the fresh composite endpoint/switch read entry is permitted");

static uint32_t reads=0,refusals=0,pairs=0,clockEvents=0;
static void Advance() { ++clockEvents; }
static uint64_t Hash(const std::string &s) {
    uint64_t h=14695981039346656037ULL;
    for (unsigned char c:s) { h^=c; h*=1099511628211ULL; } return h;
}
template<class F> static void Deny(const char *name,F action,const std::string &expected="") {
    bool refused=false; std::string reason;
    try { action(); } catch (const std::logic_error &e) { refused=true; reason=e.what(); }
    Require(refused,"Expected switch fixture refusal was accepted");
    Require(expected.empty() || reason==expected,"Refusal came from an unexpected guard");
    ++refusals;
    std::cout << "WS31_ENDPOINT_SWITCH_REFUSE case=" << name << " reason=\"" << reason << "\"" << std::endl;
}

int main() {
    Settings::lb_mode=36;
    Deny("no-switch",[]{ Probe::Capture({}); },"WS31 switch scope has no actual switch");
    NodeContainer hosts; hosts.Create(2);
    Ptr<SwitchNode> left=CreateObject<SwitchNode>(),right=CreateObject<SwitchNode>();
    NodeContainer all; all.Add(hosts); all.Add(left); all.Add(right);
    InternetStackHelper internet; internet.Install(all);
    QbbHelper qbb;
    auto aLink=qbb.Install(hosts.Get(0),left);
    auto middle=qbb.Install(left,right);
    auto bLink=qbb.Install(right,hosts.Get(1));
    Ptr<QbbNetDevice> a=DynamicCast<QbbNetDevice>(aLink.Get(0));
    Ptr<QbbNetDevice> b=DynamicCast<QbbNetDevice>(bLink.Get(1));
    Ptr<QbbNetDevice> swDevice=DynamicCast<QbbNetDevice>(middle.Get(0));
    std::vector<Ptr<RdmaDriver> > drivers;
    for (uint32_t i=0;i<2;++i) {
        auto d=CreateObject<RdmaDriver>(); d->SetNode(hosts.Get(i)); d->SetRdmaHw(CreateObject<RdmaHw>());
        hosts.Get(i)->AggregateObject(d); d->Init(); drivers.push_back(d);
    }
    auto tx=drivers[0]->m_rdma,rx=drivers[1]->m_rdma;
    const uint32_t sip=0x0a000001,dip=0x0a000002;
    const uint16_t sport=1000,dport=100,pg=3;
    const ws31::Key key(sip,dip,sport,dport),other(sip,dip,sport+1,dport);
    EndpointResources resources;
    resources.sourceNode=hosts.Get(0)->GetId(); resources.destinationNode=hosts.Get(1)->GetId();
    resources.txKey=RdmaHw::GetQpKey(dip,sport,dport,pg);
    resources.rxKey=RdmaHw::GetRxQpKey(sip,sport,dport,pg);
    EndpointLedger ledger; ledger.Begin(EndpointKey(sip,dip,sport,dport,pg),resources,0,0,8192,1,0); ledger.Launch(0,0);
    auto qp=CreateObject<RdmaQueuePair>(pg,Ipv4Address(sip),Ipv4Address(dip),sport,dport);
    qp->SetSize(8192); qp->SetFlowId(0); qp->m_workload_tag=1; qp->snd_nxt=qp->snd_una=8192;
    auto receiver=CreateObject<RdmaRxQueuePair>(); receiver->m_flow_id=0;
    receiver->sip=dip; receiver->dip=sip; receiver->sport=dport; receiver->dport=sport;
    receiver->m_ecn_source.qIndex=pg;
    const uint32_t txNic=a->GetIfIndex(),rxNic=b->GetIfIndex();
    tx->m_nic[txNic].qpGrp->AddQp(qp); tx->m_nic[txNic].qpGrp->SetQpFinished(0);
    auto scope=Probe::Capture(drivers); // Setup GetObject before all fingerprints.
    auto state=[&]() {
        std::ostringstream o; o << Settings::lb_mode << ':' << Simulator::Now().GetTimeStep() << ':';
        for (auto it=NodeList::Begin();it!=NodeList::End();++it) {
            Ptr<Node> n=*it; o << PeekPointer(n) << ',' << n->GetId() << ',' << n->GetNodeType() << ',' << n->GetNDevices() << ';';
            for (uint32_t i=0;i<n->GetNDevices();++i) {
                auto d=n->GetDevice(i); o << PeekPointer(d) << ',' << PeekPointer(d->GetNode()) << ',' << d->GetIfIndex() << ';';
                auto q=DynamicCast<QbbNetDevice>(d); if (q) Ws31EndpointSnapshotFixture::Device(o,q);
            }
        }
        for (auto driver:drivers) {
            auto hw=driver->m_rdma;
            o << PeekPointer(driver) << ',' << PeekPointer(driver->m_node) << ',' << PeekPointer(hw) << ',' << PeekPointer(hw->m_node) << ';';
            for (const auto &nic:hw->m_nic) o << PeekPointer(nic.dev) << ',' << PeekPointer(nic.qpGrp) << ';';
            for (const auto &p:hw->m_qpMap) o << p.first << ',' << PeekPointer(p.second) << ';';
            for (const auto &p:hw->m_rxQpMap) o << p.first << ',' << PeekPointer(p.second) << ';';
            for (auto k:hw->akashic_Qp) o << k << ';';
            for (auto k:hw->akashic_RxQp) o << k << ';';
        }
        o << receiver->m_flow_id << ',' << receiver->sip << ',' << receiver->dip << ','
          << receiver->sport << ',' << receiver->dport << ',' << receiver->m_ipid << ','
          << receiver->ReceiverNextExpectedSeq << ',' << receiver->m_nackTimer.GetTimeStep() << ','
          << receiver->m_milestone_rx << ',' << receiver->m_lastNACK << ','
          << receiver->m_ecn_source.qIndex << ',' << uint32_t(receiver->m_ecn_source.ecnbits) << ','
          << receiver->m_ecn_source.qfb << ',' << receiver->m_ecn_source.total << ',' << receiver->m_irn_sack_ << ';';
        Ws31EndpointSnapshotFixture::Event(o,receiver->QcnTimerEvent);
        o << Ws31EndpointSwitchFixture::State(left) << '|' << Ws31EndpointSwitchFixture::State(right);
        return o.str();
    };
    auto observe=[&]() { ++reads; return Probe::Read(0,ledger.Get(0),tx,rx,qp,receiver,scope,txNic,rxNic); };
    auto pair=[&](const char *name) {
        const auto before=state(); const auto x=observe(); const auto between=state(); const auto y=observe();
        Require(before==between && between==state(),"Composite read changed semantic protocol/switch state");
        Require(x.snapshot.observedFields==255 && x.endpoint.snapshot.observedFields==127 &&
                x.switches.size()==2 && x.endpoint.nodes==4 && x.endpoint.devices.size()==6 &&
                x.snapshot.pinnedEntries==y.snapshot.pinnedEntries && x.snapshot.budgetEntries==y.snapshot.budgetEntries &&
                x.snapshot.quotaEntries==y.snapshot.quotaEntries,"Composite observation omitted actual scope or changed counts");
        ++pairs;
        std::cout << "WS31_ENDPOINT_SWITCH_PAIR case=" << name << " mask=" << x.snapshot.observedFields
          << " endpoint_mask=" << x.endpoint.snapshot.observedFields << " switches=" << x.switches.size()
          << " pins=" << x.snapshot.pinnedEntries << " budget=" << x.snapshot.budgetEntries << " quota=" << x.snapshot.quotaEntries
          << " data=" << x.snapshot.dataQueueBytes << " quiet=" << x.snapshot.Quiet() << " reusable=" << x.snapshot.Reusable()
          << " before=" << Hash(before) << " after=" << Hash(state()) << " semantic_bytes_equal=1" << std::endl;
        for (const auto &s:x.switches) std::cout << "WS31_ENDPOINT_SWITCH_ROW case=" << name << " node=" << s.node
          << " object=" << s.object << " q12=" << s.q12Pins << " c1=" << s.ws31Pins << " budget=" << s.budget << " quota=" << s.quota
          << " all_q12=" << s.allQ12Pins << " all_c1=" << s.allWs31Pins << " all_budget=" << s.allBudget << " all_quota=" << s.allQuota
          << " observed_ports=" << s.observedPorts << " live_borrowed2=" << s.liveBorrowed[2]
          << " window=" << s.sharedActivity.windowNs << " seen1=" << s.sharedActivity.seen[1] << " last1=" << s.sharedActivity.last[1] << std::endl;
        return x;
    };
    auto denyRead=[&](const char *name) {
        const auto before=state(); Deny(name,[&]{ observe(); });
        Require(before==state(),"Rejected composite read changed semantic state");
        std::cout << "WS31_ENDPOINT_SWITCH_REFUSE_PURITY case=" << name << " semantic_bytes_equal=1" << std::endl;
    };
    auto empty=pair("empty-miss-no-insertion");
    Require(empty.snapshot.Reusable(),"Actually empty scope was not reusable");
    Ws31EndpointSwitchFixture::Seed(left,key,other); Ws31EndpointSwitchFixture::Seed(right,key,other);
    Simulator::Schedule(NanoSeconds(20),&Advance); Simulator::Run();
    Require(Simulator::Now().GetNanoSeconds()==20 && clockEvents==1,"Fixture clock did not reach expiry boundary");
    auto overdue=pair("overdue-stored-not-expired");
    Require(overdue.snapshot.pinnedEntries==4 && overdue.snapshot.budgetEntries==2 && overdue.snapshot.quotaEntries==2,
            "Two-switch target counts do not add up");
    for (auto s:{left,right}) Ws31EndpointSwitchFixture::VerifyOverdue(s,key);
    // PG is part of endpoint identity, not part of the switch fourtuple.
    auto pgEntry=ledger.Get(0); std::get<4>(pgEntry.tuple)=4;
    pgEntry.resources.txKey=RdmaHw::GetQpKey(dip,sport,dport,4); pgEntry.resources.rxKey=RdmaHw::GetRxQpKey(sip,sport,dport,4);
    qp->m_pg=4; receiver->m_ecn_source.qIndex=4;
    const auto beforePg=state(); auto changedPg=Probe::Read(0,pgEntry,tx,rx,qp,receiver,scope,txNic,rxNic); ++reads;
    Require(beforePg==state() && changedPg.snapshot.pinnedEntries==4 && changedPg.snapshot.budgetEntries==2 && changedPg.snapshot.quotaEntries==2,
            "Switch key incorrectly includes endpoint PG");
    qp->m_pg=pg; receiver->m_ecn_source.qIndex=pg;
    auto savedScope=scope; scope=Probe::Scope(); denyRead("default-scope"); scope=savedScope;
    Settings::lb_mode=37; denyRead("supported-mode-changed"); Settings::lb_mode=36;
    Settings::lb_mode=0; Deny("unsupported-mode-capture",[&]{ Probe::Capture(drivers); }); Settings::lb_mode=36;
    // All supported table modes retain the same target counters. Fresh Capture
    // is setup, and is deliberately outside each paired purity fingerprint.
    for (uint32_t mode=33;mode<=50;++mode) {
        Settings::lb_mode=mode; scope=Probe::Capture(drivers);
        const std::string label="mode-"+std::to_string(mode); auto modeResult=pair(label.c_str());
        Require(modeResult.snapshot.pinnedEntries==4 && modeResult.snapshot.budgetEntries==2 &&
                modeResult.snapshot.quotaEntries==2,"A supported mode lost target table coverage");
    }
    Settings::lb_mode=36; scope=Probe::Capture(drivers);
    const auto owner=swDevice->GetNode(); const auto slot=swDevice->GetIfIndex();
    swDevice->SetIfIndex(slot+10); denyRead("switch-index-changed");
    Deny("bad-index-capture",[&]{ Probe::Capture(drivers); }); swDevice->SetIfIndex(slot);
    swDevice->SetNode(hosts.Get(0)); denyRead("switch-owner-changed");
    Deny("bad-owner-capture",[&]{ Probe::Capture(drivers); }); swDevice->SetNode(owner);
    qp->m_flow_id=7; denyRead("wrong-saved-identity"); qp->m_flow_id=0;
    ++receiver->dip; denyRead("wrong-saved-rx"); --receiver->dip;
    auto wrong=ledger.Get(0); ++wrong.resources.txKey;
    const auto beforeWrong=state();
    Deny("wrong-resource-key",[&]{ ++reads; Probe::Read(0,wrong,tx,rx,qp,receiver,scope,txNic,rxNic); });
    Require(beforeWrong==state(),"Wrong-resource rejection changed semantic state");
    tx->akashic_Qp.insert(resources.txKey); rx->akashic_RxQp.insert(resources.rxKey);
    Require(!pair("history-blocks-reuse").snapshot.completionHistoryReleased,"History was omitted");
    tx->akashic_Qp.erase(resources.txKey); rx->akashic_RxQp.erase(resources.rxKey);
    // Reproduce S1's stale-queue sequence at exactly the same nanosecond. E is
    // deliberately retained but cannot be supplied to the new composite API.
    auto oldEndpoint=Ws31EndpointProbe::Read(0,ledger.Get(0),tx,rx,qp,receiver,Ws31EndpointProbe::Capture(drivers),txNic,rxNic);
    Require(oldEndpoint.snapshot.dataQueueBytes==0,"Old endpoint observation was not empty");
    auto physical=swDevice->GetQueue(); Require(physical->Enqueue(Create<Packet>(32),1),"Switch queue setup failed");
    auto queued=pair("same-nanosecond-fresh-queue");
    Require(queued.snapshot.observedNs==oldEndpoint.snapshot.observedNs && queued.snapshot.dataQueueBytes==32 && !queued.snapshot.Quiet(),
            "Composite read upgraded stale queue state");
    ledger.AckComplete(0,8192,20); Require(ledger.Retire(0,queued.snapshot,20),"Endpoint retirement failed");
    Require(!ledger.CertifyDrain(0,queued.snapshot,20),"Complete coverage falsely certified a queued scope");
    bool paused[BEgressQueue::qCnt]={false}; Require(physical->DequeueRR(paused)!=nullptr,"Test queue removal failed");
    EndpointLink link(hosts.Get(0)->GetId(),txNic,left->GetId(),aLink.Get(1)->GetIfIndex());
    auto c=ledger.Enter(0,100,link,EndpointLedger::CHANNEL,20),h=ledger.Enter(0,101,link,EndpointLedger::HELD_TEST_COPY,20);
    auto quiet=pair("complete-mask-with-manual-open-tokens");
    Require(quiet.snapshot.Quiet() && !ledger.CertifyDrain(0,quiet.snapshot,20),"Mask bypassed channel/held ledger");
    ledger.Close(c,0,100,link,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,20);
    Require(!ledger.CertifyDrain(0,observe().snapshot,20),"Mask bypassed held token");
    ledger.Close(h,0,101,link,EndpointLedger::HELD_TEST_COPY,EndpointLedger::HELD_DISCARDED,20);
    Require(ledger.CertifyDrain(0,observe().snapshot,20),"Quiet manually closed fixture failed drain gate");
    const auto unrelatedLeft=Ws31EndpointSwitchFixture::Other(left,other),unrelatedRight=Ws31EndpointSwitchFixture::Other(right,other);
    const auto sharedLeft=Ws31EndpointSwitchFixture::Shared(left),sharedRight=Ws31EndpointSwitchFixture::Shared(right);
    left->ResetWs30V13Tuple(sip,dip,sport,dport); right->ResetWs30V13Tuple(sip,dip,sport,dport);
    Require(unrelatedLeft==Ws31EndpointSwitchFixture::Other(left,other) && unrelatedRight==Ws31EndpointSwitchFixture::Other(right,other) &&
            sharedLeft==Ws31EndpointSwitchFixture::Shared(left) && sharedRight==Ws31EndpointSwitchFixture::Shared(right),
            "Original target cleanup changed K2 or shared history");
    for (auto s:{left,right}) Ws31EndpointSwitchFixture::VerifyCleanup(s,key,other);
    auto cleared=pair("target-cleared-unrelated-shared-retained");
    Require(cleared.snapshot.Reusable() && ledger.SwitchCleared(0,cleared.snapshot,20),"Target cleanup did not satisfy fixture ledger");
    for (const auto &s:cleared.switches) Require(s.allQ12Pins==1 && s.allWs31Pins==1 && s.allBudget==1 &&
        s.allQuota==1 && s.observedPorts==2 && s.liveBorrowed[2]==0,"Global/shared state was treated as target state");
    // S1's interface mutation: stale endpoint scope cannot be combined with a
    // fresh switch scope. Both are private parts of a single captured Scope.
    auto loop=CreateObject<LoopbackNetDevice>(); left->AddDevice(loop);
    denyRead("same-nanosecond-interface-added");
    scope=Probe::Capture(drivers); Require(pair("recaptured-composite-scope").snapshot.Reusable(),"Composite recapture failed");
    left->AddDevice(swDevice); denyRead("duplicate-device-added");
    Deny("duplicate-device-capture",[&]{ Probe::Capture(drivers); });
    auto extra=CreateObject<Node>(); denyRead("node-count-changed");
    Simulator::Destroy();
    // Fresh isolated malformed scopes. Nothing is repaired by Capture/Read.
    auto role=CreateObject<Ws31RoleNode>(); role->Role(9);
    Deny("unknown-role",[]{ Probe::Capture({}); }); role->Role(1);
    Deny("false-switch-role",[]{ Probe::Capture({}); }); Simulator::Destroy();
    auto unknownDeviceNode=CreateObject<Node>(); unknownDeviceNode->AddDevice(CreateObject<PointToPointNetDevice>());
    Deny("unknown-interface",[]{ Probe::Capture({}); },"Unsupported interface in WS31 switch scope");
    Simulator::Destroy();
    auto derived=CreateObject<Ws31DerivedSwitch>();
    Deny("switch-subclass",[]{ Probe::Capture({}); },"WS31 switch observation requires an exact SwitchNode");
    Simulator::Destroy();
    std::cout << "WS31_ENDPOINT_SWITCH_SUMMARY PASS pairs=" << pairs << " reads=" << reads << " refusals=" << refusals
      << " network_runs=0 clock_events=" << clockEvents << " natural_network_completions=0 manual_tokens=2"
      << " actual_switches=2 manually_assigned_states=1" << std::endl;
    return 0;
}
