#ifndef WS31_ENDPOINT_PROBE_H
#define WS31_ENDPOINT_PROBE_H

// Incomplete integration WIP. This adapter observes actual NS-3 objects, but
// only when explicitly invoked by a later fixture. No normal code includes it.
// SWITCH_STATE is deliberately not certified here: real per-switch reads and
// the default-off channel token hook remain separate integration obligations.
#include "ws31-endpoint-ledger.h"
#include "rdma-hw.h"
#include "rdma-driver.h"
#include "ns3/node-list.h"
#include "ns3/simulator.h"
#include "ns3/loopback-net-device.h"
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
        uintptr_t deviceObject=0, physicalObject=0, egressObject=0, ackObject=0, groupObject=0;
        bool host=false, linkUp=false, physicalQueuePresent=false;
        bool ackQueuePresent=false, qpGroupPresent=false;
        bool busy=false, currentPacket=false;
        uint64_t currentUid=0, currentBytes=0, dataQueueBytes=0, ackQueueBytes=0;
        uint64_t pacingEvents=0, resumeEvents=0, pausedPriorities=0;
        std::vector<RetainedQp> retained;
    };
    class Scope {
        friend class Ws31EndpointProbe;
        struct NodeBinding {
            Ptr<Node> node;
            uint32_t type=0;
            std::vector<Ptr<NetDevice> > devices;
            std::vector<Ptr<BEgressQueue> > physical;
        };
        struct NicBinding {
            Ptr<QbbNetDevice> device;
            Ptr<BEgressQueue> physical;
            Ptr<RdmaEgressQueue> egress;
            Ptr<DropTailQueue> ack;
            Ptr<RdmaQueuePairGroup> group;
        };
        struct HostBinding {
            Ptr<RdmaDriver> driver;
            Ptr<RdmaHw> hw;
            Ptr<Node> node;
            std::vector<NicBinding> nics;
        };
        std::vector<NodeBinding> nodes;
        std::vector<HostBinding> hosts;
    };
    struct Observation {
        ws31::EndpointSnapshot snapshot;
        uintptr_t savedTxObject=0, savedRxObject=0;
        uintptr_t liveTxObject=0, liveRxObject=0;
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
    static const Scope::HostBinding &Host(const Scope &scope,Ptr<RdmaHw> hw) {
        for (const auto &host:scope.hosts) if (host.hw==hw) return host;
        throw std::logic_error("Endpoint hardware was not captured from its actual driver");
    }
    static void ValidateScope(const Scope &scope) {
        Need(!scope.nodes.empty() && !scope.hosts.empty(),"Endpoint scope has no setup provenance");
        uint32_t index=0;
        for (auto it=NodeList::Begin();it!=NodeList::End();++it,++index) {
            Need(index<scope.nodes.size() && *it==scope.nodes[index].node,
                 "NodeList differs from the frozen endpoint scope");
            const auto &record=scope.nodes[index];
            Need(record.node->GetNodeType()==record.type,"Frozen node type changed");
            Need(record.node->GetNDevices()==record.devices.size(),"Frozen device count changed");
            for (uint32_t i=0;i<record.devices.size();++i) {
                Need(record.node->GetDevice(i)==record.devices[i],"Frozen interface identity changed");
                Ptr<QbbNetDevice> device=DynamicCast<QbbNetDevice>(record.devices[i]);
                if (device) Need(device->m_queue==record.physical[i],"Frozen physical queue identity changed");
            }
        }
        Need(index==scope.nodes.size(),"Frozen node is missing from NodeList");
        for (const auto &host:scope.hosts) {
            Need(host.driver && host.hw && host.driver->m_rdma==host.hw &&
                 host.driver->m_node==host.node && host.hw->m_node==host.node,
                 "Captured actual driver/hardware/node binding changed");
            Need(host.hw->m_nic.size()==host.nics.size(),"Captured NIC count changed");
            for (uint32_t i=0;i<host.nics.size();++i) {
                const auto &nic=host.nics[i]; const auto &actual=host.hw->m_nic[i];
                Need(actual.dev==nic.device && actual.qpGrp==nic.group,"Hardware NIC/group binding changed");
                if (!nic.device) {
                    Need(nic.group && nic.group->m_qps.empty(),"Loopback slot has unexpected retained QPs");
                    continue;
                }
                Need(nic.device->GetNode()==host.node && nic.device->GetIfIndex()==i &&
                     nic.device->m_rdmaEQ==nic.egress && nic.device->m_queue==nic.physical &&
                     nic.egress && nic.egress->m_ackQ==nic.ack && nic.egress->m_qpGrp==nic.group,
                     "Actual device/egress/ACK/retained-group binding changed");
            }
        }
    }
public:
    // Setup only: GetObject may change ns-3 aggregate lookup bookkeeping.
    // Call Capture after actual driver Init, before any purity fingerprint.
    // Observation below never calls GetObject or rediscovers driver ownership.
    static Scope Capture(const std::vector<Ptr<RdmaDriver> > &drivers) {
        Scope scope;
        std::set<uintptr_t> devices,physical,egress,ack,groups,hardware,hostNodes;
        for (auto it=NodeList::Begin();it!=NodeList::End();++it) {
            Scope::NodeBinding record; record.node=*it; record.type=record.node->GetNodeType();
            for (uint32_t i=0;i<record.node->GetNDevices();++i) {
                Ptr<NetDevice> device=record.node->GetDevice(i);
                Need(device && device->GetNode()==record.node && device->GetIfIndex()==i &&
                     devices.insert(reinterpret_cast<uintptr_t>(PeekPointer(device))).second,
                     "Duplicate or wrongly indexed device in endpoint scope");
                record.devices.push_back(device);
                Ptr<QbbNetDevice> qbb=DynamicCast<QbbNetDevice>(device);
                record.physical.push_back(qbb ? qbb->m_queue : Ptr<BEgressQueue>());
                if (!qbb) {
                    Need(DynamicCast<LoopbackNetDevice>(device)!=nullptr,
                         "Unknown non-Qbb data-plane device in endpoint scope");
                    continue;
                }
                Need(qbb->m_queue && physical.insert(reinterpret_cast<uintptr_t>(PeekPointer(qbb->m_queue))).second,
                     "Missing or shared physical queue in standard endpoint scope");
            }
            scope.nodes.push_back(record);
        }
        for (auto driver:drivers) {
            Need(driver && driver->m_node && driver->m_rdma,"Incomplete setup driver provenance");
            Scope::HostBinding host;
            host.driver=driver; host.node=driver->m_node; host.hw=driver->m_rdma;
            Need(host.node->GetNodeType()==0 && host.node->GetObject<RdmaDriver>()==driver &&
                 host.hw->m_node==host.node && hardware.insert(reinterpret_cast<uintptr_t>(PeekPointer(host.hw))).second &&
                 hostNodes.insert(reinterpret_cast<uintptr_t>(PeekPointer(host.node))).second,
                 "Setup provenance is not the unique actual host driver/hardware");
            Need(host.hw->m_nic.size()==host.node->GetNDevices(),"Setup NIC vector does not cover all interfaces");
            for (uint32_t i=0;i<host.hw->m_nic.size();++i) {
                Scope::NicBinding nic;
                const auto &actual=host.hw->m_nic[i];
                nic.device=actual.dev; nic.group=actual.qpGrp;
                Ptr<NetDevice> device=host.node->GetDevice(i);
                if (!nic.device) {
                    Need(DynamicCast<LoopbackNetDevice>(device)!=nullptr,"Missing actual Qbb NIC binding");
                } else {
                    Need(device==nic.device && nic.device->m_rdmaEQ && nic.group,
                         "Actual NIC identity/egress/group is absent");
                    nic.physical=nic.device->m_queue; nic.egress=nic.device->m_rdmaEQ;
                    nic.ack=nic.egress->m_ackQ;
                    Need(nic.physical && nic.ack && nic.egress->m_qpGrp==nic.group,
                         "Actual hardware and device do not share the recorded QP group");
                    Need(egress.insert(reinterpret_cast<uintptr_t>(PeekPointer(nic.egress))).second &&
                         ack.insert(reinterpret_cast<uintptr_t>(PeekPointer(nic.ack))).second &&
                         groups.insert(reinterpret_cast<uintptr_t>(PeekPointer(nic.group))).second,
                         "Shared egress, ACK queue, or retained group is outside the standard fixture contract");
                }
                host.nics.push_back(nic);
            }
            scope.hosts.push_back(host);
        }
        for (const auto &node:scope.nodes)
            if (node.node->GetNodeType()==0)
                Need(hostNodes.count(reinterpret_cast<uintptr_t>(PeekPointer(node.node)))==1,
                     "Expected host has no captured actual driver");
        ValidateScope(scope);
        return scope;
    }
    static Device ReadDevice(Ptr<QbbNetDevice> device) {
        Need(device && device->GetNode(),"Endpoint probe requires an attached real device");
        Device result;
        result.node=device->GetNode()->GetId(); result.interface=device->GetIfIndex();
        result.deviceObject=reinterpret_cast<uintptr_t>(PeekPointer(device));
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
        result.physicalObject=reinterpret_cast<uintptr_t>(PeekPointer(device->m_queue));
        if (result.physicalQueuePresent) result.dataQueueBytes=device->m_queue->GetNBytesTotal();
        Need(result.physicalQueuePresent,"Standard endpoint scope has no physical queue");
        if (result.host) {
            Need(device->m_rdmaEQ!=nullptr,"Host has no actual RDMA queue");
            Ptr<RdmaEgressQueue> queue=device->m_rdmaEQ;
            result.egressObject=reinterpret_cast<uintptr_t>(PeekPointer(queue));
            result.ackQueuePresent=queue->m_ackQ!=nullptr;
            result.qpGroupPresent=queue->m_qpGrp!=nullptr;
            result.ackObject=reinterpret_cast<uintptr_t>(PeekPointer(queue->m_ackQ));
            result.groupObject=reinterpret_cast<uintptr_t>(PeekPointer(queue->m_qpGrp));
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
                            Ptr<RdmaQueuePair> savedTx,Ptr<RdmaRxQueuePair> savedRx,
                            const Scope &scope,uint32_t txNic,uint32_t rxNic) {
        ValidateScope(scope);
        const auto &txBinding=Host(scope,tx); const auto &rxBinding=Host(scope,rx);
        Need(txNic<txBinding.nics.size() && rxNic<rxBinding.nics.size() &&
             txBinding.nics[txNic].device && rxBinding.nics[rxNic].device,
             "Selected endpoint NIC is outside its setup binding");
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
        if (!s.txAbsent) {
            Need(liveTx->second!=nullptr,"Live sender map contains an empty QP reference");
            result.liveTxFlowId=liveTx->second->m_flow_id;
            result.liveTxObject=reinterpret_cast<uintptr_t>(PeekPointer(liveTx->second));
        }
        if (!s.rxAbsent) {
            Need(liveRx->second!=nullptr,"Live receiver map contains an empty QP reference");
            result.liveRxFlowId=liveRx->second->m_flow_id;
            result.liveRxObject=reinterpret_cast<uintptr_t>(PeekPointer(liveRx->second));
        }
        s.txTimers=Timers(savedTx); s.rxTimers=savedRx->QcnTimerEvent.IsRunning();
        if (!s.rxAbsent && liveRx->second!=savedRx) s.rxTimers+=liveRx->second->QcnTimerEvent.IsRunning();
        result.txHistory=tx->akashic_Qp.count(txKey)!=0;
        result.rxHistory=rx->akashic_RxQp.count(rxKey)!=0;
        s.completionHistoryReleased=!result.txHistory && !result.rxHistory;
        s.retainedQpsFinished=savedTx->IsFinishedConst();
        s.pendingPayloadBytes=Pending(savedTx);
        bool txNodeSeen=false, rxNodeSeen=false;
        std::set<uintptr_t> timerObjects;
        std::set<uintptr_t> payloadObjects,groupObjects;
        timerObjects.insert(result.savedTxObject);
        payloadObjects.insert(result.savedTxObject);
        uint32_t savedTxOccurrences=0;
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
                    Need(groupObjects.insert(qp.object).second,"Duplicate QP in retained groups or slots");
                    s.retainedQpsFinished &= qp.completed;
                    if (payloadObjects.insert(qp.object).second) s.pendingPayloadBytes+=qp.pendingPayload;
                    if (timerObjects.insert(qp.object).second) s.txTimers+=qp.timers;
                    if (qp.object==result.savedTxObject) {
                        Need(device==txBinding.nics[txNic].device &&
                             device->m_rdmaEQ->m_qpGrp==txBinding.nics[txNic].group,
                             "Saved sender QP is outside its selected actual NIC/group");
                        ++savedTxOccurrences;
                    }
                }
                result.devices.push_back(observation);
            }
        }
        Need(txNodeSeen && rxNodeSeen && !result.devices.empty(),"Actual endpoint device scope was not observed");
        Need(savedTxOccurrences==1,"Saved sender QP missing from its actual retained group");
        s.observedFields=ws31::EndpointSnapshot::MAPS | ws31::EndpointSnapshot::QP_TIMERS |
            ws31::EndpointSnapshot::DEVICE_TIMERS | ws31::EndpointSnapshot::RETAINED_QPS |
            ws31::EndpointSnapshot::QUEUES | ws31::EndpointSnapshot::SERIALIZATION |
            ws31::EndpointSnapshot::HISTORY;
        return result;
    }
};
} // namespace ns3
#endif
