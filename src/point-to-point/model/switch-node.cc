#include "switch-node.h"

#include "assert.h"
#include "ns3/boolean.h"
#include "ns3/conweave-routing.h"
#include "ns3/double.h"
#include "ns3/flow-id-tag.h"
#include "ns3/int-header.h"
#include "ns3/ipv4-header.h"
#include "ns3/ipv4.h"
#include "ns3/letflow-routing.h"
#include "ns3/packet.h"
#include "ns3/pause-header.h"
#include "ns3/settings.h"
#include "ns3/uinteger.h"
#include "ns3/workload-tag.h"
#include <iostream>
#include <map>
#include <tuple>
#include "ppp-header.h"
#include "qbb-net-device.h"

namespace ns3 {

static std::map<uint32_t, uint64_t> workload_tag_packets;
static uint64_t missing_workload_tag_packets = 0;
static uint64_t dualtrack_flow_packets = 0;
static uint64_t dualtrack_packet_packets = 0;
static uint64_t dualtrack_packet_multipath = 0;
static uint32_t guard_lambda = 1, guard_tau = 0;
static uint32_t guard_on_bytes = 8192, guard_off_bytes = 4096;
static uint64_t guard_packets = 0, guard_two_candidates = 0;
static uint64_t guard_scored = 0, guard_diverted = 0;
static uint64_t guard_activations = 0, guard_exits = 0;
static uint64_t guard_queue_violations = 0;
struct GuardQueueStat {
    uint64_t enqueued = 0, dequeued = 0, admissionDropped = 0;
    uint64_t queueRejected = 0, queuedDropped = 0, current = 0;
};
static std::map<std::tuple<uint32_t, uint32_t, uint32_t>, GuardQueueStat> guard_queue_stats;

static uint32_t GuardTag(Ptr<const Packet> p) {
    WorkloadTag label;
    if (!p->PeekPacketTag(label)) return 0;
    return label.GetValue() <= 2 ? label.GetValue() : 3;
}

void SwitchNode::ConfigureGuardHash(uint32_t lambda, uint32_t tau,
                                     uint32_t gateOnBytes, uint32_t gateOffBytes) {
    NS_ASSERT_MSG(gateOffBytes < gateOnBytes, "HarmGate exit must be below activation");
    guard_lambda = lambda;
    guard_tau = tau;
    guard_on_bytes = gateOnBytes;
    guard_off_bytes = gateOffBytes;
}

void SwitchNode::PrintWorkloadTagCounts() {
    for (const auto &entry : workload_tag_packets)
        std::cout << "WS06_ROUTING_TAG tag=" << entry.first << " packets=" << entry.second << std::endl;
    std::cout << "WS06_ROUTING_TAG missing=" << missing_workload_tag_packets << std::endl;
    if (Settings::lb_mode == 12)
        std::cout << "WS07_DUALTRACK flow_packets=" << dualtrack_flow_packets
                  << " packet_packets=" << dualtrack_packet_packets
                  << " packet_multipath=" << dualtrack_packet_multipath << std::endl;
    if (Settings::lb_mode >= 13 && Settings::lb_mode <= 15) {
        std::cout << "WS09_CONFIG mode=" << Settings::lb_mode
                  << " lambda=" << guard_lambda << " tau=" << guard_tau
                  << " gate_on=" << guard_on_bytes << " gate_off=" << guard_off_bytes << std::endl;
        std::cout << "WS09_ROUTE packets=" << guard_packets << " two_candidates="
                  << guard_two_candidates << " scored=" << guard_scored
                  << " diverted=" << guard_diverted << " activations="
                  << guard_activations << " exits=" << guard_exits << std::endl;
        for (const auto &entry : guard_queue_stats) {
            const GuardQueueStat &s = entry.second;
            if (s.enqueued != s.dequeued + s.queuedDropped + s.current)
                ++guard_queue_violations;
            std::cout << "WS09_QUEUE switch=" << std::get<0>(entry.first)
                      << " port=" << std::get<1>(entry.first)
                      << " tag=" << std::get<2>(entry.first)
                      << " enqueued=" << s.enqueued << " dequeued=" << s.dequeued
                      << " admission_drop=" << s.admissionDropped
                      << " queue_reject=" << s.queueRejected
                      << " queued_drop=" << s.queuedDropped
                      << " current=" << s.current << std::endl;
        }
        std::cout << "WS09_QUEUE_CHECK violations=" << guard_queue_violations << std::endl;
        NS_ASSERT_MSG(guard_queue_violations == 0, "GuardHash queue counters do not conserve bytes");
    }
}

TypeId SwitchNode::GetTypeId(void) {
    static TypeId tid =
        TypeId("ns3::SwitchNode")
            .SetParent<Node>()
            .AddConstructor<SwitchNode>()
            .AddAttribute("EcnEnabled", "Enable ECN marking.", BooleanValue(false),
                          MakeBooleanAccessor(&SwitchNode::m_ecnEnabled), MakeBooleanChecker())
            .AddAttribute("CcMode", "CC mode.", UintegerValue(0),
                          MakeUintegerAccessor(&SwitchNode::m_ccMode),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("AckHighPrio", "Set high priority for ACK/NACK or not", UintegerValue(0),
                          MakeUintegerAccessor(&SwitchNode::m_ackHighPrio),
                          MakeUintegerChecker<uint32_t>());
    return tid;
}

SwitchNode::SwitchNode() {
    m_ecmpSeed = m_id;
    m_isToR = false;
    m_node_type = 1;
    m_isToR = false;
    m_drill_candidate = 2;
    m_mmu = CreateObject<SwitchMmu>();
    // Conga's Callback for switch functions
    m_mmu->m_congaRouting.SetSwitchSendCallback(MakeCallback(&SwitchNode::DoSwitchSend, this));
    m_mmu->m_congaRouting.SetSwitchSendToDevCallback(
        MakeCallback(&SwitchNode::SendToDevContinue, this));
    // ConWeave's Callback for switch functions
    m_mmu->m_conweaveRouting.SetSwitchSendCallback(MakeCallback(&SwitchNode::DoSwitchSend, this));
    m_mmu->m_conweaveRouting.SetSwitchSendToDevCallback(
        MakeCallback(&SwitchNode::SendToDevContinue, this));

    for (uint32_t i = 0; i < pCnt; i++) {
        m_txBytes[i] = 0;
    }
}

/**
 * @brief Load Balancing
 */
uint32_t SwitchNode::DoLbFlowECMP(Ptr<const Packet> p, const CustomHeader &ch,
                                  const std::vector<int> &nexthops) {
    // pick one next hop based on hash
    union {
        uint8_t u8[4 + 4 + 2 + 2];
        uint32_t u32[3];
    } buf;
    buf.u32[0] = ch.sip;
    buf.u32[1] = ch.dip;
    if (ch.l3Prot == 0x6)
        buf.u32[2] = ch.tcp.sport | ((uint32_t)ch.tcp.dport << 16);
    else if (ch.l3Prot == 0x11)  // XXX RDMA traffic on UDP
        buf.u32[2] = ch.udp.sport | ((uint32_t)ch.udp.dport << 16);
    else if (ch.l3Prot == 0xFC || ch.l3Prot == 0xFD)  // ACK or NACK
        buf.u32[2] = ch.ack.sport | ((uint32_t)ch.ack.dport << 16);
    else {
        std::cout << "[ERROR] Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
                  << "Cannot support other protoocls than TCP/UDP (l3Prot:" << ch.l3Prot << ")"
                  << std::endl;
        assert(false && "Cannot support other protoocls than TCP/UDP");
    }

    uint32_t hashVal = EcmpHash(buf.u8, 12, m_ecmpSeed);
    uint32_t idx = hashVal % nexthops.size();
    return nexthops[idx];
}

// tag=2 uses a deterministic per-packet ECMP hash. tag=0/1 and all control
// traffic retain the original flow hash. No transport or receiver setting changes.
uint32_t SwitchNode::DoLbDualTrack(Ptr<const Packet> p, const CustomHeader &ch,
                                   const std::vector<int> &nexthops) {
    WorkloadTag label;
    if (!p->PeekPacketTag(label) || label.GetValue() != 2) {
        if (m_isToR && m_isToR_hostIP.count(ch.sip)) ++dualtrack_flow_packets;
        return DoLbFlowECMP(p, ch, nexthops);
    }
    if (m_isToR && m_isToR_hostIP.count(ch.sip)) {
        ++dualtrack_packet_packets;
        if (nexthops.size() > 1) ++dualtrack_packet_multipath;
    }
    uint32_t key[4] = {ch.sip, ch.dip,
                       uint32_t(ch.udp.sport) | (uint32_t(ch.udp.dport) << 16),
                       ch.udp.seq};
    return nexthops[EcmpHash(reinterpret_cast<const uint8_t *>(key), sizeof(key), m_ecmpSeed)
                    % nexthops.size()];
}

uint32_t SwitchNode::DoLbGuardHash(Ptr<const Packet> p, const CustomHeader &ch,
                                   const std::vector<int> &nexthops) {
    WorkloadTag label;
    if (ch.l3Prot != 0x11 || !p->PeekPacketTag(label) || label.GetValue() != 2)
        return DoLbFlowECMP(p, ch, nexthops);
    ++guard_packets;
    uint32_t key[4] = {ch.sip, ch.dip,
                       uint32_t(ch.udp.sport) | (uint32_t(ch.udp.dport) << 16),
                       ch.udp.seq};
    uint32_t first = nexthops[EcmpHash(reinterpret_cast<const uint8_t *>(key),
                                       sizeof(key), m_ecmpSeed) % nexthops.size()];
    if (nexthops.size() == 1) return first;
    uint32_t second = nexthops[EcmpHash(reinterpret_cast<const uint8_t *>(key),
                                        sizeof(key), m_ecmpSeed ^ 0x9e3779b9U)
                                % nexthops.size()];
    if (first == second) return first;
    ++guard_two_candidates;
    uint32_t qFirst = CalculateInterfaceLoad(first);
    uint32_t qSecond = CalculateInterfaceLoad(second);
    if (Settings::lb_mode == 15) {
        uint32_t low = std::min(first, second), high = std::max(first, second);
        uint64_t pair = (uint64_t(low) << 32) | high;
        bool &active = m_guardGateActive[pair];
        uint32_t peak = std::max(qFirst, qSecond);
        if (!active && peak >= guard_on_bytes) { active = true; ++guard_activations; }
        else if (active && peak <= guard_off_bytes) { active = false; ++guard_exits; }
        if (!active) return first;
    }
    ++guard_scored;
    uint64_t scoreFirst = qFirst, scoreSecond = qSecond;
    if (Settings::lb_mode != 13) {
        auto a = guard_queue_stats.find(std::make_tuple(m_id, first, 1));
        auto b = guard_queue_stats.find(std::make_tuple(m_id, second, 1));
        if (a != guard_queue_stats.end()) scoreFirst += uint64_t(guard_lambda) * a->second.current;
        if (b != guard_queue_stats.end()) scoreSecond += uint64_t(guard_lambda) * b->second.current;
    }
    if (scoreSecond + guard_tau < scoreFirst) { ++guard_diverted; return second; }
    return first;
}

/*-----------------CONGA-----------------*/
uint32_t SwitchNode::DoLbConga(Ptr<Packet> p, CustomHeader &ch, const std::vector<int> &nexthops) {
    return DoLbFlowECMP(p, ch, nexthops);  // flow ECMP (dummy)
}

/*-----------------Letflow-----------------*/
uint32_t SwitchNode::DoLbLetflow(Ptr<Packet> p, CustomHeader &ch,
                                 const std::vector<int> &nexthops) {
    if (m_isToR && nexthops.size() == 1) {
        if (m_isToR_hostIP.find(ch.sip) != m_isToR_hostIP.end() &&
            m_isToR_hostIP.find(ch.dip) != m_isToR_hostIP.end()) {
            return nexthops[0];  // intra-pod traffic
        }
    }

    /* ONLY called for inter-Pod traffic */
    uint32_t outPort = m_mmu->m_letflowRouting.RouteInput(p, ch);
    if (outPort == LETFLOW_NULL) {
        assert(nexthops.size() == 1);  // Receiver's TOR has only one interface to receiver-server
        outPort = nexthops[0];         // has only one option
    }
    assert(std::find(nexthops.begin(), nexthops.end(), outPort) !=
           nexthops.end());  // Result of Letflow cannot be found in nexthops
    return outPort;
}

/*-----------------DRILL-----------------*/
uint32_t SwitchNode::CalculateInterfaceLoad(uint32_t interface) {
    Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(m_devices[interface]);
    NS_ASSERT_MSG(!!device && !!device->GetQueue(),
                  "Error of getting a egress queue for calculating interface load");
    return device->GetQueue()->GetNBytesTotal();  // also used in HPCC
}

uint32_t SwitchNode::DoLbDrill(Ptr<const Packet> p, const CustomHeader &ch,
                               const std::vector<int> &nexthops) {
    // find the Egress (output) link with the smallest local Egress Queue length
    uint32_t leastLoadInterface = 0;
    uint32_t leastLoad = std::numeric_limits<uint32_t>::max();
    auto rand_nexthops = nexthops;
    std::random_shuffle(rand_nexthops.begin(), rand_nexthops.end());

    std::map<uint32_t, uint32_t>::iterator itr = m_previousBestInterfaceMap.find(ch.dip);
    if (itr != m_previousBestInterfaceMap.end()) {
        leastLoadInterface = itr->second;
        leastLoad = CalculateInterfaceLoad(itr->second);
    }

    uint32_t sampleNum =
        m_drill_candidate < rand_nexthops.size() ? m_drill_candidate : rand_nexthops.size();
    for (uint32_t samplePort = 0; samplePort < sampleNum; samplePort++) {
        uint32_t sampleLoad = CalculateInterfaceLoad(rand_nexthops[samplePort]);
        if (sampleLoad < leastLoad) {
            leastLoad = sampleLoad;
            leastLoadInterface = rand_nexthops[samplePort];
        }
    }
    m_previousBestInterfaceMap[ch.dip] = leastLoadInterface;
    return leastLoadInterface;
}

/*------------------ConWeave Dummy ----------------*/
uint32_t SwitchNode::DoLbConWeave(Ptr<const Packet> p, const CustomHeader &ch,
                                  const std::vector<int> &nexthops) {
    return DoLbFlowECMP(p, ch, nexthops);  // flow ECMP (dummy)
}
/*----------------------------------*/

void SwitchNode::CheckAndSendPfc(uint32_t inDev, uint32_t qIndex) {
    Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(m_devices[inDev]);
    bool pClasses[qCnt] = {0};
    m_mmu->GetPauseClasses(inDev, qIndex, pClasses);
    for (int j = 0; j < qCnt; j++) {
        if (pClasses[j]) {
            uint32_t paused_time = device->SendPfc(j, 0);
            m_mmu->SetPause(inDev, j, paused_time);
            m_mmu->m_pause_remote[inDev][j] = true;
            /** PAUSE SEND COUNT ++ */
        }
    }

    for (int j = 0; j < qCnt; j++) {
        if (!m_mmu->m_pause_remote[inDev][j]) continue;

        if (m_mmu->GetResumeClasses(inDev, j)) {
            device->SendPfc(j, 1);
            m_mmu->SetResume(inDev, j);
            m_mmu->m_pause_remote[inDev][j] = false;
        }
    }
}
void SwitchNode::CheckAndSendResume(uint32_t inDev, uint32_t qIndex) {
    Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(m_devices[inDev]);
    if (m_mmu->GetResumeClasses(inDev, qIndex)) {
        device->SendPfc(qIndex, 1);
        m_mmu->SetResume(inDev, qIndex);
    }
}

/********************************************
 *              MAIN LOGICS                 *
 *******************************************/

// This function can only be called in switch mode
bool SwitchNode::SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet,
                                         CustomHeader &ch) {
    SendToDev(packet, ch);
    return true;
}

void SwitchNode::SendToDev(Ptr<Packet> p, CustomHeader &ch) {
    // Count only data packets as they enter their source ToR, before any LB dispatch.
    if (ch.l3Prot == 0x11 && m_isToR && m_isToR_hostIP.count(ch.sip)) {
        WorkloadTag label;
        if (p->PeekPacketTag(label))
            ++workload_tag_packets[label.GetValue()];
        else
            ++missing_workload_tag_packets;
    }
    /** HIJACK: hijack the packet and run DoSwitchSend internally for Conga and ConWeave.
     * Note that DoLbConWeave() and DoLbConga() are flow-ECMP function for control packets
     * or intra-ToR traffic.
     */

    // Conga
    if (Settings::lb_mode == 3) {
        m_mmu->m_congaRouting.RouteInput(p, ch);
        return;
    }

    // ConWeave
    if (Settings::lb_mode == 9) {
        m_mmu->m_conweaveRouting.RouteInput(p, ch);
        return;
    }

    // Others
    SendToDevContinue(p, ch);
}

void SwitchNode::SendToDevContinue(Ptr<Packet> p, CustomHeader &ch) {
    int idx = GetOutDev(p, ch);
    if (idx >= 0) {
        NS_ASSERT_MSG(m_devices[idx]->IsLinkUp(),
                      "The routing table look up should return link that is up");

        // determine the qIndex
        uint32_t qIndex;
        if (ch.l3Prot == 0xFF || ch.l3Prot == 0xFE ||
            (m_ackHighPrio &&
             (ch.l3Prot == 0xFD ||
              ch.l3Prot == 0xFC))) {  // QCN or PFC or ACK/NACK, go highest priority
            qIndex = 0;               // high priority
        } else {
            qIndex = (ch.l3Prot == 0x06 ? 1 : ch.udp.pg);  // if TCP, put to queue 1. Otherwise, it
                                                           // would be 3 (refer to trafficgen)
        }

        DoSwitchSend(p, ch, idx, qIndex);  // m_devices[idx]->SwitchSend(qIndex, p, ch);
        return;
    }
    std::cout << "WARNING - Drop occurs in SendToDevContinue()" << std::endl;
    return;  // Drop otherwise
}

int SwitchNode::GetOutDev(Ptr<Packet> p, CustomHeader &ch) {
    // look up entries
    auto entry = m_rtTable.find(ch.dip);

    // no matching entry
    if (entry == m_rtTable.end()) {
        std::cout << "[ERROR] Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
                  << "No matching entry, so drop this packet at SwitchNode (l3Prot:" << ch.l3Prot
                  << ")" << std::endl;
        assert(false);
    }

    // entry found
    const auto &nexthops = entry->second;
    bool control_pkt =
        (ch.l3Prot == 0xFF || ch.l3Prot == 0xFE || ch.l3Prot == 0xFD || ch.l3Prot == 0xFC);

    if (Settings::lb_mode == 0 || control_pkt) {  // control packet (ACK, NACK, PFC, QCN)
        return DoLbFlowECMP(p, ch, nexthops);     // ECMP routing path decision (4-tuple)
    }

    switch (Settings::lb_mode) {
        case 2:
            return DoLbDrill(p, ch, nexthops);
        case 3:
            return DoLbConga(p, ch, nexthops); /** DUMMY: Do ECMP */
        case 6:
            return DoLbLetflow(p, ch, nexthops);
        case 9:
            return DoLbConWeave(p, ch, nexthops); /** DUMMY: Do ECMP */
        case 12:
            return DoLbDualTrack(p, ch, nexthops);
        case 13:
        case 14:
        case 15:
            return DoLbGuardHash(p, ch, nexthops);
        default:
            std::cout << "Unknown lb_mode(" << Settings::lb_mode << ")" << std::endl;
            assert(false);
    }
}

/*
 * The (possible) callback point when conweave dequeues packets from buffer
 */
void SwitchNode::DoSwitchSend(Ptr<Packet> p, CustomHeader &ch, uint32_t outDev, uint32_t qIndex) {
    // admission control
    FlowIdTag t;
    p->PeekPacketTag(t);
    uint32_t inDev = t.GetFlowId();

    /** NOTE:
     * ConWeave control packets have the high priority as ACK/NACK/PFC/etc with qIndex = 0.
     */
    if (inDev == Settings::CONWEAVE_CTRL_DUMMY_INDEV) { // sanity check
        // ConWeave reply is on ACK protocol with high priority, so qIndex should be 0
        assert(qIndex == 0 && m_ackHighPrio == 1 && "ConWeave's reply packet follows ACK, so its qIndex should be 0");
    }

    if (qIndex != 0) {  // not highest priority
        if (m_mmu->CheckEgressAdmission(outDev, qIndex,
                                        p->GetSize())) {  // Egress Admission control
            if (m_mmu->CheckIngressAdmission(inDev, qIndex,
                                             p->GetSize())) {  // Ingress Admission control
                m_mmu->UpdateIngressAdmission(inDev, qIndex, p->GetSize());
                m_mmu->UpdateEgressAdmission(outDev, qIndex, p->GetSize());
            } else { /** DROP: At Ingress */
#if (0)
                // /** NOTE: logging dropped pkts */
                // std::cout << "LostPkt ingress - Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
                //           << "L3Prot:" << ch.l3Prot
                //           << ",Size:" << p->GetSize()
                //           << ",At " << Simulator::Now() << std::endl;
#endif
                Settings::dropped_pkt_sw_ingress++;
                if (Settings::lb_mode >= 13 && Settings::lb_mode <= 15)
                    SwitchNotifyAdmissionDrop(outDev, p);
                return;  // drop
            }
        } else { /** DROP: At Egress */
#if (0)
            // /** NOTE: logging dropped pkts */
            // std::cout << "LostPkt egress - Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
            //           << "L3Prot:" << ch.l3Prot << ",Size:" << p->GetSize() << ",At "
            //           << Simulator::Now() << std::endl;
#endif
            Settings::dropped_pkt_sw_egress++;
            if (Settings::lb_mode >= 13 && Settings::lb_mode <= 15)
                SwitchNotifyAdmissionDrop(outDev, p);
            return;  // drop
        }

        CheckAndSendPfc(inDev, qIndex);
    }

    m_devices[outDev]->SwitchSend(qIndex, p, ch);
}

void SwitchNode::CheckGuardQueue(uint32_t ifIndex) {
    uint64_t counted = 0;
    for (uint32_t tag = 0; tag <= 3; ++tag) {
        auto it = guard_queue_stats.find(std::make_tuple(m_id, ifIndex, tag));
        if (it != guard_queue_stats.end()) counted += it->second.current;
    }
    Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[ifIndex]);
    NS_ASSERT_MSG(dev && dev->GetQueue(), "GuardHash missing egress queue");
    if (counted != dev->GetQueue()->GetNBytesTotal()) {
        ++guard_queue_violations;
        NS_ASSERT_MSG(false, "GuardHash queue bytes differ from BEgressQueue");
    }
}

void SwitchNode::SwitchNotifyEnqueue(uint32_t ifIndex, Ptr<const Packet> p) {
    GuardQueueStat &s = guard_queue_stats[std::make_tuple(m_id, ifIndex, GuardTag(p))];
    s.enqueued += p->GetSize();
    s.current += p->GetSize();
    CheckGuardQueue(ifIndex);
}

void SwitchNode::SwitchNotifyAdmissionDrop(uint32_t ifIndex, Ptr<const Packet> p) {
    guard_queue_stats[std::make_tuple(m_id, ifIndex, GuardTag(p))].admissionDropped += p->GetSize();
    CheckGuardQueue(ifIndex);
}

void SwitchNode::SwitchNotifyQueueDrop(uint32_t ifIndex, uint32_t qIndex,
                                       Ptr<const Packet> p, bool wasQueued) {
    GuardQueueStat &s = guard_queue_stats[std::make_tuple(m_id, ifIndex, GuardTag(p))];
    if (wasQueued) {
        s.queuedDropped += p->GetSize();
        NS_ASSERT_MSG(s.current >= p->GetSize(), "GuardHash queue drop underflow");
        s.current -= p->GetSize();
    } else s.queueRejected += p->GetSize();
    if (qIndex != 0) {
        FlowIdTag t;
        p->PeekPacketTag(t);
        uint32_t inDev = t.GetFlowId();
        if (inDev != Settings::CONWEAVE_CTRL_DUMMY_INDEV)
            m_mmu->RemoveFromIngressAdmission(inDev, qIndex, p->GetSize());
        m_mmu->RemoveFromEgressAdmission(ifIndex, qIndex, p->GetSize());
    }
    CheckGuardQueue(ifIndex);
}

void SwitchNode::SwitchNotifyDequeue(uint32_t ifIndex, uint32_t qIndex, Ptr<Packet> p) {
    if (Settings::lb_mode >= 13 && Settings::lb_mode <= 15) {
        GuardQueueStat &s = guard_queue_stats[std::make_tuple(m_id, ifIndex, GuardTag(p))];
        NS_ASSERT_MSG(s.current >= p->GetSize(), "GuardHash dequeue underflow");
        s.current -= p->GetSize();
        s.dequeued += p->GetSize();
        CheckGuardQueue(ifIndex);
    }
    FlowIdTag t;
    p->PeekPacketTag(t);
    if (qIndex != 0) {
        uint32_t inDev = t.GetFlowId();
        if (inDev != Settings::CONWEAVE_CTRL_DUMMY_INDEV) {
            // NOTE: ConWeave's probe/reply does not need to pass inDev interface,
            // so skip for conweave's queued packets
            m_mmu->RemoveFromIngressAdmission(inDev, qIndex, p->GetSize());
        }
        m_mmu->RemoveFromEgressAdmission(ifIndex, qIndex, p->GetSize());
        if (m_ecnEnabled) {
            bool egressCongested = m_mmu->ShouldSendCN(ifIndex, qIndex);
            if (egressCongested) {
                PppHeader ppp;
                Ipv4Header h;
                p->RemoveHeader(ppp);
                p->RemoveHeader(h);
                h.SetEcn((Ipv4Header::EcnType)0x03);
                p->AddHeader(h);
                p->AddHeader(ppp);
            }
        }
        // NOTE: ConWeave's probe/reply does not need to pass inDev interface
        if (inDev != Settings::CONWEAVE_CTRL_DUMMY_INDEV) {
            CheckAndSendResume(inDev, qIndex);
        }
    }

    // HPCC's INT
    if (1) {
        uint8_t *buf = p->GetBuffer();
        if (buf[PppHeader::GetStaticSize() + 9] == 0x11) {  // udp packet
            IntHeader *ih = (IntHeader *)&buf[PppHeader::GetStaticSize() + 20 + 8 +
                                              6];  // ppp, ip, udp, SeqTs, INT
            Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[ifIndex]);
            if (m_ccMode == 3) {  // HPCC
                ih->PushHop(Simulator::Now().GetTimeStep(), m_txBytes[ifIndex],
                            dev->GetQueue()->GetNBytesTotal(), dev->GetDataRate().GetBitRate());
            }
        }
    }
    m_txBytes[ifIndex] += p->GetSize();
}

uint32_t SwitchNode::EcmpHash(const uint8_t *key, size_t len, uint32_t seed) {
    uint32_t h = seed;
    if (len > 3) {
        const uint32_t *key_x4 = (const uint32_t *)key;
        size_t i = len >> 2;
        do {
            uint32_t k = *key_x4++;
            k *= 0xcc9e2d51;
            k = (k << 15) | (k >> 17);
            k *= 0x1b873593;
            h ^= k;
            h = (h << 13) | (h >> 19);
            h += (h << 2) + 0xe6546b64;
        } while (--i);
        key = (const uint8_t *)key_x4;
    }
    if (len & 3) {
        size_t i = len & 3;
        uint32_t k = 0;
        key = &key[i - 1];
        do {
            k <<= 8;
            k |= *key--;
        } while (--i);
        k *= 0xcc9e2d51;
        k = (k << 15) | (k >> 17);
        k *= 0x1b873593;
        h ^= k;
    }
    h ^= len;
    h ^= h >> 16;
    h *= 0x85ebca6b;
    h ^= h >> 13;
    h *= 0xc2b2ae35;
    h ^= h >> 16;
    return h;
}

void SwitchNode::SetEcmpSeed(uint32_t seed) { m_ecmpSeed = seed; }

void SwitchNode::AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx) {
    uint32_t dip = dstAddr.Get();
    m_rtTable[dip].push_back(intf_idx);
}

void SwitchNode::ClearTable() { m_rtTable.clear(); }

uint64_t SwitchNode::GetTxBytesOutDev(uint32_t outdev) {
    assert(outdev < pCnt);
    return m_txBytes[outdev];
}

} /* namespace ns3 */
