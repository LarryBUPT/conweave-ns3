#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "../src/point-to-point/model/ws31-endpoint-probe.h"
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <cstring>

using namespace ns3;
using namespace ns3::ws31;

namespace ns3 {
// Test setup and explicit protocol fingerprints only. Normal code never calls
// these setters. The production probe itself provides no mutation interface.
class Ws31EndpointSnapshotFixture {
public:
    static void Activity(Ptr<QbbNetDevice> d,EventId pacing,EventId resume,Ptr<Packet> packet) {
        d->m_nextSend=pacing; d->m_resumeEvt[1]=resume;
        d->m_txMachineState=QbbNetDevice::BUSY; d->m_currentPkt=packet;
    }
    static void Pause(Ptr<QbbNetDevice> d,bool value) { d->m_paused[1]=value; }
    static void Link(Ptr<QbbNetDevice> d,bool value) { d->m_linkUp=value; }
    static void Event(std::ostream &out,const EventId &e) {
        out << e.GetUid() << ':' << e.GetTs() << ':' << e.GetContext() << ':' << e.IsRunning() << ';';
    }
    static void QpState(std::ostream &out,Ptr<RdmaQueuePair> qp) {
        out << PeekPointer(qp) << ':' << qp->sip.Get() << ':' << qp->dip.Get() << ':'
            << qp->sport << ':' << qp->dport << ':' << qp->m_pg << ':' << qp->m_flow_id << ':'
            << qp->m_workload_tag << ':' << qp->startTime.GetTimeStep() << ':' << qp->m_ws31LaunchDelayNs << ':'
            << qp->snd_nxt << ':' << qp->snd_una << ':' << qp->m_size << ':' << qp->irn.m_enabled << ':'
            << qp->m_nextAvail.GetTimeStep() << ':' << qp->m_ws30Persistent << ':' << qp->m_ws30Released << ':'
            << qp->irn.m_sack;
        Event(out,qp->m_retransmit); Event(out,qp->mlx.m_eventUpdateAlpha);
        Event(out,qp->mlx.m_eventDecreaseRate); Event(out,qp->mlx.m_rpTimer);
    }
    static void DeviceState(std::ostream &out,Ptr<QbbNetDevice> d) {
        out << d->GetNode()->GetId() << ':' << d->GetIfIndex() << ':' << d->m_linkUp << ':'
            << d->m_txMachineState << ':' << PeekPointer(d->m_currentPkt) << ':';
        if (d->m_currentPkt) out << d->m_currentPkt->GetUid() << ':' << d->m_currentPkt->GetSize();
        Event(out,d->m_nextSend);
        for (uint32_t i=0;i<QbbNetDevice::qCnt;++i) {
            out << d->m_paused[i] << ':'; Event(out,d->m_resumeEvt[i]);
        }
        out << PeekPointer(d->m_queue) << ':';
        if (d->m_queue) out << d->m_queue->GetNBytesTotal();
        Ptr<RdmaEgressQueue> eq=d->m_rdmaEQ;
        out << ':' << PeekPointer(eq) << ':' << eq->m_rrlast << ':' << eq->m_qlast << ':'
            << eq->current_pause_time.size() << ':' << PeekPointer(eq->m_ackQ) << ':'
            << eq->m_ackQ->GetNBytes() << ':' << eq->m_ackQ->GetNPackets() << ':' << PeekPointer(eq->m_qpGrp);
        Ptr<RdmaQueuePairGroup> group=eq->m_qpGrp;
        out << ':' << group->m_qps.size() << ':';
        // Only the protocol bitmap, not the bytes of an entire C++ object.
        out.write(group->m_qp_finished,sizeof(group->m_qp_finished));
        for (auto qp:group->m_qps) QpState(out,qp);
        for (const auto &paused:eq->current_pause_time)
            out << paused.first << ':' << paused.second.GetTimeStep() << ';';
    }
};
}

static void Require(bool ok,const char *message) { if (!ok) throw std::runtime_error(message); }
static uint32_t eventCalls=0,reads=0,refusals=0;
static void Noop() { ++eventCalls; }
template<class F> static std::string Reject(F action) {
    bool rejected=false; std::string reason;
    try { action(); } catch (const std::logic_error &error) { rejected=true; reason=error.what(); }
    Require(rejected,"Object coverage refusal was not enforced"); ++refusals;
    return reason;
}
static uint64_t Fingerprint(const std::string &s) {
    uint64_t hash=14695981039346656037ULL;
    for (unsigned char c:s) { hash^=c; hash*=1099511628211ULL; }
    return hash;
}

int main() {
    NodeContainer nodes; nodes.Create(2);
    InternetStackHelper internet; internet.Install(nodes);
    QbbHelper qbb;
    NetDeviceContainer link=qbb.Install(nodes.Get(0),nodes.Get(1));
    Ptr<QbbNetDevice> a=DynamicCast<QbbNetDevice>(link.Get(0));
    Ptr<QbbNetDevice> b=DynamicCast<QbbNetDevice>(link.Get(1));
    std::vector<Ptr<RdmaDriver> > drivers;
    for (uint32_t i=0;i<2;++i) {
        Ptr<RdmaDriver> driver=CreateObject<RdmaDriver>();
        driver->SetNode(nodes.Get(i)); driver->SetRdmaHw(CreateObject<RdmaHw>());
        nodes.Get(i)->AggregateObject(driver); driver->Init(); drivers.push_back(driver);
    }
    Ptr<RdmaHw> tx=drivers[0]->m_rdma,rx=drivers[1]->m_rdma;
    const uint32_t txNic=a->GetIfIndex(),rxNic=b->GetIfIndex();
    const uint32_t sip=0x0a000001,dip=0x0a000002;
    const uint16_t sport=1000,dport=100,pg=3;
    const EndpointKey tuple(sip,dip,sport,dport,pg);
    EndpointResources resources;
    resources.sourceNode=nodes.Get(0)->GetId(); resources.destinationNode=nodes.Get(1)->GetId();
    resources.txKey=RdmaHw::GetQpKey(dip,sport,dport,pg);
    resources.rxKey=RdmaHw::GetRxQpKey(sip,sport,dport,pg);
    EndpointLedger ledger; ledger.Begin(tuple,resources,0,0,8192,1,0); ledger.Launch(0,0);
    Ptr<RdmaQueuePair> qp=CreateObject<RdmaQueuePair>(pg,Ipv4Address(sip),Ipv4Address(dip),sport,dport);
    qp->SetSize(8192); qp->SetFlowId(0); qp->m_workload_tag=1; qp->snd_nxt=qp->snd_una=8192;
    Ptr<RdmaRxQueuePair> receiver=CreateObject<RdmaRxQueuePair>();
    receiver->m_flow_id=0; receiver->sip=dip; receiver->dip=sip;
    receiver->sport=dport; receiver->dport=sport; receiver->m_ecn_source.qIndex=pg;
    Ptr<RdmaQueuePairGroup> group=tx->m_nic[txNic].qpGrp;
    group->AddQp(qp);
    // Capture performs setup-only aggregate lookups. Initialize Now/NodeList
    // before fingerprints; never run events between the two observations.
    Ws31EndpointProbe::Scope scope=Ws31EndpointProbe::Capture(drivers);
    (void)Simulator::Now();
    auto state=[&]() {
        std::ostringstream out;
        out << Simulator::Now().GetTimeStep() << ':' << NodeList::GetNNodes() << ':'
            << tx->m_qpMap.size() << ':' << rx->m_rxQpMap.size() << ':'
            << tx->akashic_Qp.size() << ':' << rx->akashic_RxQp.size() << ':'
            << receiver->m_flow_id << ':' << receiver->sip << ':' << receiver->dip << ':'
            << receiver->sport << ':' << receiver->dport << ':' << receiver->m_ipid << ':'
            << receiver->ReceiverNextExpectedSeq << ':' << receiver->m_nackTimer.GetTimeStep() << ':'
            << receiver->m_milestone_rx << ':' << receiver->m_lastNACK << ':'
            << receiver->m_ecn_source.qIndex << ':' << uint32_t(receiver->m_ecn_source.ecnbits) << ':'
            << receiver->m_ecn_source.qfb << ':' << receiver->m_ecn_source.total << ':' << receiver->m_irn_sack_;
        Ws31EndpointSnapshotFixture::QpState(out,qp);
        for (const auto &p:tx->m_qpMap) out << p.first << ':' << PeekPointer(p.second) << ';';
        for (const auto &p:rx->m_rxQpMap) out << p.first << ':' << PeekPointer(p.second) << ';';
        for (auto key:tx->akashic_Qp) out << key << ';';
        for (auto key:rx->akashic_RxQp) out << key << ';';
        for (auto driver:drivers) {
            out << PeekPointer(driver) << ':' << PeekPointer(driver->m_node) << ':' << PeekPointer(driver->m_rdma) << ':';
            for (const auto &nic:driver->m_rdma->m_nic)
                out << PeekPointer(nic.dev) << ':' << PeekPointer(nic.qpGrp) << ':' << nic.qpGrp->m_qps.size() << ';';
        }
        Ws31EndpointSnapshotFixture::Event(out,receiver->QcnTimerEvent);
        Ws31EndpointSnapshotFixture::DeviceState(out,a);
        Ws31EndpointSnapshotFixture::DeviceState(out,b);
        return out.str();
    };
    auto observe=[&]() { ++reads; return Ws31EndpointProbe::Read(0,ledger.Get(0),tx,rx,qp,receiver,scope,txNic,rxNic); };
    auto pair=[&](const char *name) {
        const std::string before=state(); auto first=observe(); const std::string middle=state();
        auto second=observe(); const std::string after=state();
        Require(before==middle && middle==after,"Probe changed explicit protocol state");
        const auto &s=first.snapshot; const auto &t=second.snapshot;
        Require(s.observedNs==t.observedNs && s.observedFields==127 && t.observedFields==127 &&
            s.pendingPayloadBytes==t.pendingPayloadBytes && s.retainedQpsFinished==t.retainedQpsFinished &&
            s.txTimers==t.txTimers && s.rxTimers==t.rxTimers && s.deviceTimers==t.deviceTimers &&
            s.dataQueueBytes==t.dataQueueBytes && s.ackQueueBytes==t.ackQueueBytes && s.transmitting==t.transmitting,
            "Repeated same-event probe output differs");
        std::cout << "WS31_ENDPOINT_OBJECT case=" << name << " mask=" << s.observedFields
            << " finished=" << s.retainedQpsFinished << " pending=" << s.pendingPayloadBytes
            << " tx_timers=" << s.txTimers << " rx_timers=" << s.rxTimers << " device_timers=" << s.deviceTimers
            << " data=" << s.dataQueueBytes << " ack=" << s.ackQueueBytes << " transmitting=" << s.transmitting
            << " history_released=" << s.completionHistoryReleased << " before=" << Fingerprint(before)
            << " after=" << Fingerprint(after) << " full_protocol_bytes_equal=1"
            << " nodes=" << first.nodes << " devices=" << first.devices.size()
            << " saved_tx=" << first.savedTxObject << " saved_rx=" << first.savedRxObject
            << " live_tx=" << first.liveTxObject << " live_rx=" << first.liveRxObject << std::endl;
        for (const auto &device:first.devices) {
            std::cout << "WS31_ENDPOINT_OBJECT_DEVICE case=" << name << " node=" << device.node
                << " interface=" << device.interface << " object=" << device.deviceObject
                << " physical=" << device.physicalObject << " egress=" << device.egressObject
                << " ack=" << device.ackObject << " group=" << device.groupObject << std::endl;
            for (uint32_t i=0;i<device.retained.size();++i) {
                const auto &retained=device.retained[i];
                std::cout << "WS31_ENDPOINT_OBJECT_SLOT case=" << name << " node=" << device.node
                    << " interface=" << device.interface << " slot=" << i << " object=" << retained.object
                    << " flow_id=" << retained.flowId << " finished_bit=" << retained.finishedBit
                    << " completed=" << retained.completed << " next=" << retained.next
                    << " acknowledged=" << retained.acknowledged << " size=" << retained.size
                    << " pending=" << retained.pendingPayload << " timers=" << retained.timers << std::endl;
            }
        }
        std::cout << "WS31_ENDPOINT_OBJECT_SACK case=" << name << " next=" << qp->snd_nxt
            << " acknowledged=" << qp->snd_una << " state=\"" << qp->irn.m_sack << "\"" << std::endl;
        return first;
    };
    auto deny=[&](const char *name) {
        const std::string before=state(); const std::string reason=Reject([&]{ observe(); });
        Require(before==state(),"Rejected probe changed protocol state");
        std::cout << "WS31_ENDPOINT_OBJECT_REFUSE case=" << name << " full_protocol_bytes_equal=1 reason=\""
            << reason << "\"" << std::endl;
    };
    Require(pair("complete-unmarked").snapshot.Quiet(),"Completed unmarked QP not quiet");
    ledger.AckComplete(0,8192,0);
    std::cout << "WS31_ENDPOINT_OBJECT_REFUSE case=incomplete-mask reason=\""
        << Reject([&]{ ledger.Retire(0,observe().snapshot,0); }) << "\"" << std::endl;
    group->SetQpFinished(0);
    Require(pair("complete-marked").snapshot.Quiet(),"Completed marked retained QP not quiet");
    qp->irn.m_enabled=true; qp->snd_nxt=qp->snd_una=0;
    qp->irn.m_sack.sack(0,1024); qp->irn.m_sack.sack(2048,1024);
    auto pending=pair("irn-two-sack-blocks");
    Require(!pending.snapshot.retainedQpsFinished && pending.snapshot.pendingPayloadBytes==8192,
            "Finished bit hid unfinished QP or mutable SACK getter changed pending");
    qp->snd_nxt=qp->snd_una=8192;
    Ptr<RdmaQueuePair> next=CreateObject<RdmaQueuePair>(pg,Ipv4Address(sip),Ipv4Address(dip),sport+1,dport);
    next->SetSize(4096); next->SetFlowId(1); group->AddQp(next);
    Require(pair("retain-old-append-new").snapshot.pendingPayloadBytes==4096,"New slot payload omitted or double counted");
    group->m_qps.erase(group->m_qps.begin()); deny("missing-saved-qp"); group->m_qps.insert(group->m_qps.begin(),qp);
    group->m_qps.push_back(qp); deny("duplicate-qp-slot"); group->m_qps.pop_back();
    a->m_rdmaEQ->m_qpGrp=CreateObject<RdmaQueuePairGroup>(); deny("device-group-binding"); a->m_rdmaEQ->m_qpGrp=group;
    tx->m_nic[txNic].qpGrp=CreateObject<RdmaQueuePairGroup>(); deny("hardware-group-binding"); tx->m_nic[txNic].qpGrp=group;
    Ptr<BEgressQueue> physical=a->GetQueue(); a->SetQueue(Ptr<BEgressQueue>()); deny("missing-physical-queue"); a->SetQueue(physical);
    tx->m_qpMap[resources.txKey]=Ptr<RdmaQueuePair>(); deny("empty-live-tx"); tx->m_qpMap.erase(resources.txKey);
    rx->m_rxQpMap[resources.rxKey]=Ptr<RdmaRxQueuePair>(); deny("empty-live-rx"); rx->m_rxQpMap.erase(resources.rxKey);
    qp->m_flow_id=99; deny("wrong-saved-flow"); qp->m_flow_id=0;
    ++receiver->dip; deny("wrong-reversed-rx"); --receiver->dip;
    qp->startTime=NanoSeconds(1); deny("wrong-original-clock"); qp->startTime=NanoSeconds(0);
    tx->akashic_Qp.insert(resources.txKey); rx->akashic_RxQp.insert(resources.rxKey);
    Require(!pair("completion-history-present").snapshot.completionHistoryReleased,"Completion histories not observed");
    rx->m_rxQpMap[resources.rxKey]=receiver;
    Require(!pair("live-rx").snapshot.rxAbsent,"Live RX treated as absent"); rx->m_rxQpMap.erase(resources.rxKey);
    Require(physical->Enqueue(Create<Packet>(32),1),"Physical queue setup failed");
    Require(a->m_rdmaEQ->m_ackQ->Enqueue(Create<Packet>(48)),"ACK queue setup failed");
    auto queued=pair("physical-and-ack-queues");
    Require(queued.snapshot.dataQueueBytes==32 && queued.snapshot.ackQueueBytes==48,"Physical/ACK byte accounting wrong");
    qp->m_retransmit=Simulator::Schedule(NanoSeconds(100),&Noop);
    receiver->QcnTimerEvent=Simulator::Schedule(NanoSeconds(100),&Noop);
    Ws31EndpointSnapshotFixture::Activity(a,Simulator::Schedule(NanoSeconds(100),&Noop),
        Simulator::Schedule(NanoSeconds(100),&Noop),Create<Packet>(20));
    auto active=pair("events-and-serialization");
    Require(active.snapshot.txTimers==1 && active.snapshot.rxTimers==1 && active.snapshot.deviceTimers==2 &&
            active.snapshot.transmitting==1,"QP/device events or current serialization omitted");
    Ws31EndpointSnapshotFixture::Pause(a,true); deny("paused-device"); Ws31EndpointSnapshotFixture::Pause(a,false);
    Ws31EndpointSnapshotFixture::Link(a,false); deny("down-device"); Ws31EndpointSnapshotFixture::Link(a,true);
    Ptr<BEgressQueue> physicalB=b->GetQueue(); b->SetQueue(physical); deny("changed-shared-queue"); b->SetQueue(physicalB);
    // Last setup deliberately adds an unexpected non-Qbb data-plane device.
    nodes.Get(1)->AddDevice(CreateObject<PointToPointNetDevice>()); deny("changed-device-scope");
    std::cout << "WS31_ENDPOINT_OBJECT_REFUSE case=unknown-non-qbb reason=\""
        << Reject([&]{ Ws31EndpointProbe::Capture(drivers); }) << "\"" << std::endl;
    Require(eventCalls==0,"Object fixture unexpectedly advanced scheduled events");
    Simulator::Destroy();
    Require(eventCalls==0,"Scheduled protocol fixture events executed");
    std::cout << "WS31_ENDPOINT_OBJECT_SUMMARY PASS reads=" << reads << " refusals=" << refusals
        << " network_runs=0 event_calls=0 actual_network_completions=0" << std::endl;
    return 0;
}
