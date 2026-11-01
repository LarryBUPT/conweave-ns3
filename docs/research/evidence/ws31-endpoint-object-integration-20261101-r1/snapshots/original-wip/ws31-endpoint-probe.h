#ifndef WS31_ENDPOINT_PROBE_H
#define WS31_ENDPOINT_PROBE_H

// Incomplete integration WIP. This adapter observes actual NS-3 objects, but
// only when explicitly invoked by a later fixture. No normal code includes it.
// SWITCH_STATE is deliberately not certified here: real per-switch reads and
// the default-off channel token hook remain separate integration obligations.
#include "ws31-endpoint-ledger.h"
#include "rdma-hw.h"
#include "ns3/node-list.h"
#include "ns3/simulator.h"
#include <set>
#include <vector>

namespace ns3 {

class Ws31EndpointProbe {
public:
    struct RetainedQp {
        int32_t flowId=-1;
        uintptr_t object=0;
        uint64_t size=0, next=0, acknowledged=0, pendingPayload=0, timers=0;
        bool completed=false, finishedBit=false;
    };
    struct Device {
        uint32_t node=0, interface=0;
        bool host=false, linkUp=false, physicalQueuePresent=false;
        bool ackQueuePresent=false, qpGroupPresent=false;
        bool busy=false, currentPacket=false;
        uint64_t currentUid=0, currentBytes=0, dataQueueBytes=0, ackQueueBytes=0;
        uint64_t pacingEvents=0, resumeEvents=0, pausedPriorities=0;
        std::vector<RetainedQp> retained;
    };
    struct Observation {
        ws31::EndpointSnapshot snapshot;
        uintptr_t savedTxObject=0, savedRxObject=0;
        int32_t liveTxFlowId=-1, liveRxFlowId=-1;
        bool txHistory=false, rxHistory=false;
        uint32_t nodes=0;
        std::vector<Device> devices;
    };
private:
    static void Need(bool ok,const char *message) {
        if (!ok) throw std::logic_error(message);
    }
    static uint64_t Timers(Ptr<RdmaQueuePair> qp) {
        return uint64_t(qp->mlx.m_eventUpdateAlpha.IsRunning())+
               uint64_t(qp->mlx.m_eventDecreaseRate.IsRunning())+
               uint64_t(qp->mlx.m_rpTimer.IsRunning())+
               uint64_t(qp->m_retransmit.IsRunning());
    }
    static uint64_t Pending(Ptr<RdmaQueuePair> qp) {
        // GetBytesLeft() is NOT a pure getter under IRN: it may advance
        // snd_nxt and discard SACK entries. Read a conservative field bound.
        const uint64_t limit=qp->m_ws30Persistent ? qp->m_ws30Released : qp->m_size;
        return limit>=qp->snd_nxt ? limit-qp->snd_nxt : 0;
    }
public:
    static Device ReadDevice(Ptr<QbbNetDevice> device) {
        Need(device && device->GetNode(),"Endpoint probe requires an attached real device");
        Device result;
        result.node=device->GetNode()->GetId(); result.interface=device->GetIfIndex();
        result.host=device->GetNode()->GetNodeType()==0;
        result.linkUp=device->m_linkUp;
        result.busy=device->m_txMachineState==QbbNetDevice::BUSY;
        result.currentPacket=device->m_currentPkt!=nullptr;
        if (result.currentPacket) {
            result.currentUid=device->m_currentPkt->GetUid();
            result.currentBytes=device->m_currentPkt->GetSize();
        }
        result.pacingEvents=device->m_nextSend.IsRunning();
        for (uint32_t i=0;i<QbbNetDevice::qCnt;++i) {
            result.resumeEvents+=device->m_resumeEvt[i].IsRunning();
            result.pausedPriorities+=device->m_paused[i];
        }
        result.physicalQueuePresent=device->m_queue!=nullptr;
        if (result.physicalQueuePresent) result.dataQueueBytes=device->m_queue->GetNBytesTotal();
        Need(result.host || result.physicalQueuePresent,"Switch queue scope has no physical queue");
        if (result.host) {
            Need(device->m_rdmaEQ!=nullptr,"Host has no actual RDMA queue");
            Ptr<RdmaEgressQueue> queue=device->m_rdmaEQ;
            result.ackQueuePresent=queue->m_ackQ!=nullptr;
            result.qpGroupPresent=queue->m_qpGrp!=nullptr;
            Need(result.ackQueuePresent && result.qpGroupPresent,"Host queue setup is incomplete");
            result.ackQueueBytes=queue->m_ackQ->GetNBytes();
            for (uint32_t i=0;i<queue->m_qpGrp->m_qps.size();++i) {
                Ptr<RdmaQueuePair> qp=queue->m_qpGrp->m_qps[i];
                Need(qp!=nullptr,"Retained group has an empty QP reference");
                RetainedQp retained;
                retained.flowId=qp->m_flow_id;
                retained.object=reinterpret_cast<uintptr_t>(PeekPointer(qp));
                retained.size=qp->m_size; retained.next=qp->snd_nxt;
                retained.acknowledged=qp->snd_una;
                retained.pendingPayload=Pending(qp); retained.timers=Timers(qp);
                retained.completed=qp->IsFinishedConst();
                // IsQpFinished only reads the existing bit; do not call
                // GetNextQindex, IsFinished, GetNBytes, or GetBytesLeft here.
                retained.finishedBit=queue->m_qpGrp->IsQpFinished(i);
                result.retained.push_back(retained);
            }
        }
        return result;
    }

    static Observation Read(int32_t id,const ws31::EndpointLedger::Entry &entry,
                            Ptr<RdmaHw> tx,Ptr<RdmaHw> rx,
                            Ptr<RdmaQueuePair> savedTx,Ptr<RdmaRxQueuePair> savedRx) {
        Need(tx && rx && tx->m_node && rx->m_node && savedTx && savedRx,
             "Endpoint observation needs saved actual TX/RX objects");
        const auto &tuple=entry.tuple;
        const uint32_t sip=std::get<0>(tuple), dip=std::get<1>(tuple);
        const uint16_t sport=std::get<2>(tuple), dport=std::get<3>(tuple), pg=std::get<4>(tuple);
        const uint64_t txKey=RdmaHw::GetQpKey(dip,sport,dport,pg);
        const uint64_t rxKey=RdmaHw::GetRxQpKey(sip,sport,dport,pg);
        Need(tx->m_node->GetId()==entry.resources.sourceNode && rx->m_node->GetId()==entry.resources.destinationNode &&
             txKey==entry.resources.txKey && rxKey==entry.resources.rxKey,
             "Endpoint resource keys differ from actual transport functions");
        Need(savedTx->m_flow_id==id && savedTx->sip.Get()==sip && savedTx->dip.Get()==dip &&
             savedTx->sport==sport && savedTx->dport==dport && savedTx->m_pg==pg &&
             savedTx->m_size==entry.bytes && savedTx->m_workload_tag==entry.originalTag &&
             uint64_t(savedTx->startTime.GetNanoSeconds())==entry.demandNs &&
             entry.launchNs>=entry.demandNs && savedTx->m_ws31LaunchDelayNs==entry.launchNs-entry.demandNs,
             "Saved sender object does not belong to the requested generation");
        Need(savedRx->m_flow_id==id && savedRx->sip==dip && savedRx->dip==sip &&
             savedRx->sport==dport && savedRx->dport==sport && savedRx->m_ecn_source.qIndex==pg,
             "Saved receiver object has the wrong reversed endpoint identity");
        Observation result;
        result.savedTxObject=reinterpret_cast<uintptr_t>(PeekPointer(savedTx));
        result.savedRxObject=reinterpret_cast<uintptr_t>(PeekPointer(savedRx));
        auto &s=result.snapshot;
        s.flowId=id; s.tuple=tuple; s.generation=entry.generation;
        s.observedNs=Simulator::Now().GetNanoSeconds();
        auto liveTx=tx->m_qpMap.find(txKey);
        auto liveRx=rx->m_rxQpMap.find(rxKey);
        s.txAbsent=liveTx==tx->m_qpMap.end(); s.rxAbsent=liveRx==rx->m_rxQpMap.end();
        if (!s.txAbsent) result.liveTxFlowId=liveTx->second->m_flow_id;
        if (!s.rxAbsent) result.liveRxFlowId=liveRx->second->m_flow_id;
        s.txTimers=Timers(savedTx); s.rxTimers=savedRx->QcnTimerEvent.IsRunning();
        if (!s.rxAbsent && liveRx->second!=savedRx) s.rxTimers+=liveRx->second->QcnTimerEvent.IsRunning();
        result.txHistory=tx->akashic_Qp.count(txKey)!=0;
        result.rxHistory=rx->akashic_RxQp.count(rxKey)!=0;
        s.completionHistoryReleased=!result.txHistory && !result.rxHistory;
        s.retainedQpsFinished=true;
        bool txNodeSeen=false, rxNodeSeen=false;
        std::set<uintptr_t> timerObjects;
        timerObjects.insert(result.savedTxObject);
        if (!s.txAbsent) {
            const uintptr_t object=reinterpret_cast<uintptr_t>(PeekPointer(liveTx->second));
            if (timerObjects.insert(object).second) s.txTimers+=Timers(liveTx->second);
        }
        for (auto it=NodeList::Begin();it!=NodeList::End();++it) {
            Ptr<Node> node=*it; ++result.nodes;
            for (uint32_t i=0;i<node->GetNDevices();++i) {
                Ptr<QbbNetDevice> device=DynamicCast<QbbNetDevice>(node->GetDevice(i));
                if (!device) continue;
                Device observation=ReadDevice(device);
                Need(observation.linkUp && observation.pausedPriorities==0,
                     "Endpoint fixture scope contains a down or paused device");
                txNodeSeen|=observation.node==entry.resources.sourceNode;
                rxNodeSeen|=observation.node==entry.resources.destinationNode;
                s.deviceTimers+=observation.pacingEvents+observation.resumeEvents;
                s.dataQueueBytes+=observation.dataQueueBytes;
                s.ackQueueBytes+=observation.ackQueueBytes;
                s.transmitting+=observation.busy || observation.currentPacket;
                for (const auto &qp:observation.retained) {
                    s.retainedQpsFinished &= qp.completed;
                    s.pendingPayloadBytes+=qp.pendingPayload;
                    if (timerObjects.insert(qp.object).second) s.txTimers+=qp.timers;
                }
                result.devices.push_back(observation);
            }
        }
        Need(txNodeSeen && rxNodeSeen && !result.devices.empty(),"Actual endpoint device scope was not observed");
        s.observedFields=ws31::EndpointSnapshot::MAPS | ws31::EndpointSnapshot::QP_TIMERS |
            ws31::EndpointSnapshot::DEVICE_TIMERS | ws31::EndpointSnapshot::RETAINED_QPS |
            ws31::EndpointSnapshot::QUEUES | ws31::EndpointSnapshot::SERIALIZATION |
            ws31::EndpointSnapshot::HISTORY;
        return result;
    }
};
} // namespace ns3
#endif
