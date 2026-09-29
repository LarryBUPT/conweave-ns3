#include "switch-node.h"

#include "assert.h"
#include "ns3/boolean.h"
#include "ns3/conweave-routing.h"
#include "ns3/double.h"
#include "ns3/flow-id-tag.h"
#include "ns3/flow-id-num-tag.h"
#include "ns3/int-header.h"
#include "ns3/ipv4-header.h"
#include "ns3/ipv4.h"
#include "ns3/letflow-routing.h"
#include "ns3/packet.h"
#include "ns3/pause-header.h"
#include "ns3/settings.h"
#include "ns3/uinteger.h"
#include "ns3/workload-tag.h"
#include "ws21-feedback-header.h"
#include <iostream>
#include <cstdlib>
#include <algorithm>
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
static uint64_t ws12_moe_packets = 0, ws12_background_packets = 0;
static uint64_t ws12_multipath_packets = 0;
static std::map<std::pair<uint32_t, uint32_t>, uint64_t> ws12_source_port_choices;
static uint32_t guard_lambda = 1, guard_tau = 0;
static uint32_t guard_on_bytes = 8192, guard_off_bytes = 4096;
static uint64_t guard_packets = 0, guard_two_candidates = 0;
static uint64_t guard_scored = 0, guard_diverted = 0;
static uint64_t guard_activations = 0, guard_exits = 0;
static uint64_t guard_queue_violations = 0;
static bool ws18_path_enabled = false;
static bool ws21_identity_enabled = false;
static bool ws21_feedback_enabled = false;
static uint64_t ws21_feedback_delivered = 0, ws21_feedback_rejected = 0;
static uint64_t ws21_feedback_expired = 0, ws21_feedback_bytes = 0;
static uint64_t ws21_feedback_cache_peak = 0;
static uint64_t ws21_feedback_age_sum_ns = 0, ws21_feedback_age_max_ns = 0;
static uint64_t ws21_feedback_age_bins[5] = {0, 0, 0, 0, 0};
static uint64_t ws21_feedback_sequence_gaps = 0;
static uint64_t ws21_feedback_generated = 0, ws21_feedback_hop_bytes = 0;
static uint64_t ws21_feedback_hop_enqueues = 0, ws21_feedback_hop_rejects = 0;
static uint64_t ws21_feedback_hop_dequeues = 0;
static const size_t WS21_FEEDBACK_MAX_KEYS_PER_TOR = 16384;
static std::map<uint32_t, uint32_t> ws21_host_tor;
static FILE *ws21_port_events = NULL;
static uint64_t ws21_port_max_bytes = 0, ws21_port_bytes = 0;
static uint64_t ws21_port_count = 0, ws21_port_overflow = 0;
static uint64_t ws18_path_flows = 0, ws18_path_alternate = 0;
static uint64_t ws18_path_packets = 0, ws18_path_multipath = 0;
struct GuardQueueStat {
    uint64_t enqueued = 0, dequeued = 0, admissionDropped = 0;
    uint64_t queueRejected = 0, queuedDropped = 0, current = 0;
};
static std::map<std::tuple<uint32_t, uint32_t, uint32_t>, GuardQueueStat> guard_queue_stats;

// WS-13 legacy cells retain their two frozen destinations. WS-19 opt-in cells
// observe all background destinations because each independent demand redraws them.
struct Ws13Packet {
    uint32_t src, dst, sport, dport, outDev, queuedBytes;
    uint64_t enqueueNs;
};
struct Ws13FlowHop {
    uint64_t packets = 0, bytes = 0, queuedBytesSum = 0, waitNsSum = 0;
    uint64_t maxQueuedBytes = 0, maxWaitNs = 0;
};
static std::map<std::pair<uint32_t, uint64_t>, Ws13Packet> ws13_inflight;
static std::map<std::tuple<uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t>,
                Ws13FlowHop> ws13_hops;
static bool Ws13DiagnosticEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS13_DIAG");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

static bool Ws21FeedbackEnabled() {
    return ws21_feedback_enabled;
}

static void FactorialAdmissionDrop(const char *reason, uint32_t switchId,
                                   const CustomHeader &ch, uint32_t inDev,
                                   uint32_t outDev, uint32_t size) {
    static const bool enabled = []() {
        const char *value = std::getenv("IRN_PFC_DROP_DIAG");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    if (!enabled || ch.l3Prot != 0x11) return;
    auto source = Settings::hostIp2IdMap.find(ch.sip);
    auto destination = Settings::hostIp2IdMap.find(ch.dip);
    std::cout << "FACTORIAL_ADMISSION_DROP reason=" << reason
              << " time_ns=" << Simulator::Now().GetTimeStep()
              << " switch=" << switchId
              << " src=" << (source == Settings::hostIp2IdMap.end() ? -1 : int(source->second))
              << " dst=" << (destination == Settings::hostIp2IdMap.end() ? -1 : int(destination->second))
              << " seq=" << ch.udp.seq << " bytes=" << size
              << " in_dev=" << inDev << " out_dev=" << outDev << std::endl;
}

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

void SwitchNode::ConfigureWs18Path(bool enabled) { ws18_path_enabled = enabled; }
void SwitchNode::ConfigureWs21Feedback(bool enabled) { ws21_feedback_enabled = enabled; }

void SwitchNode::ConfigureWs21Identity(bool enabled) { ws21_identity_enabled = enabled; }

void SwitchNode::ConfigureWs21PortEvents(FILE *out, uint64_t maxBytes) {
    NS_ASSERT_MSG(!out || maxBytes >= 1024, "WS-21 port log cap is too small");
    ws21_port_events = out;
    ws21_port_max_bytes = maxBytes;
    ws21_port_bytes = ws21_port_count = ws21_port_overflow = 0;
    if (out) {
        const char *header = "time_ns tor port event queue_bytes\n";
        const int written = fprintf(out, "%s", header);
        NS_ASSERT_MSG(written > 0, "WS-21 port log header write failed");
        ws21_port_bytes += written;
    }
}

void SwitchNode::FinishWs21PortEvents() {
    if (!ws21_port_events) return;
    fprintf(ws21_port_events, "# events=%lu bytes=%lu overflow=%lu\n",
            ws21_port_count, ws21_port_bytes, ws21_port_overflow);
    std::cout << "WS21_PORT_EVENTS events=" << ws21_port_count
              << " bytes=" << ws21_port_bytes
              << " overflow=" << ws21_port_overflow << std::endl;
    fflush(ws21_port_events);
    ws21_port_events = NULL;
}

void SwitchNode::AddWs21HostPort(uint32_t port) { m_ws21HostPorts.insert(port); }

void SwitchNode::RecordWs21PortEvent(uint32_t port, char event) {
    if (!ws21_port_events || !m_ws21HostPorts.count(port)) return;
    if (ws21_port_overflow) { ++ws21_port_overflow; return; }
    Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(m_devices[port]);
    NS_ASSERT_MSG(device && device->GetQueue(), "WS-21 host egress queue absent");
    char line[128];
    const int length = snprintf(line, sizeof(line), "%lu %u %u %c %u\n",
                                uint64_t(Simulator::Now().GetNanoSeconds()), m_id, port,
                                event, device->GetQueue()->GetNBytesTotal());
    NS_ASSERT_MSG(length > 0 && length < int(sizeof(line)), "WS-21 event row too long");
    if (ws21_port_bytes + uint64_t(length) > ws21_port_max_bytes) {
        ++ws21_port_overflow;
        return;
    }
    const size_t written = fwrite(line, 1, length, ws21_port_events);
    if (written != size_t(length)) NS_FATAL_ERROR("WS-21 port log write failed");
    ws21_port_bytes += length;
    ++ws21_port_count;
}

void SwitchNode::RecordWs21PortBoundary(char event) {
    for (uint32_t port : m_ws21HostPorts) RecordWs21PortEvent(port, event);
}

void SwitchNode::SetWs21HostTor(uint32_t hostIp, uint32_t torId) {
    auto inserted = ws21_host_tor.insert(std::make_pair(hostIp, torId));
    NS_ASSERT_MSG(inserted.second || inserted.first->second == torId,
                  "WS-21 host cannot have two ToRs");
}

bool SwitchNode::AddWs21IngressMapping(uint32_t sourceTor, uint32_t ingressPort,
                                       uint32_t firstPort) {
    auto inserted = m_ws21IngressToFirst.insert(
        std::make_pair(std::make_pair(sourceTor, ingressPort), firstPort));
    return inserted.second || inserted.first->second == firstPort;
}

void SwitchNode::ObserveWs21Source(const CustomHeader &ch, uint32_t port) {
    if (!ws21_identity_enabled || !m_isToR || !m_isToR_hostIP.count(ch.sip)) return;
    auto destination = ws21_host_tor.find(ch.dip);
    if (destination == ws21_host_tor.end() || destination->second == m_id) return;
    const auto key = std::make_tuple(ch.sip, ch.dip, ch.udp.sport, ch.udp.dport);
    Ws21PathObservation &item = m_ws21Source[key];
    if (item.packets && item.port != port) ++item.inconsistent;
    if (!item.packets) { item.port = port; item.firstNs = Simulator::Now().GetNanoSeconds(); }
    ++item.packets;
    item.lastNs = Simulator::Now().GetNanoSeconds();
}

void SwitchNode::ObserveWs21Destination(Ptr<const Packet> p, const CustomHeader &ch) {
    if (!ws21_identity_enabled || !m_isToR || !m_isToR_hostIP.count(ch.dip) ||
        ch.l3Prot != 0x11) return;
    auto source = ws21_host_tor.find(ch.sip);
    if (source == ws21_host_tor.end() || source->second == m_id) return;
    FlowIdTag tag;
    const bool hasIngressTag = p->PeekPacketTag(tag);
    if (!hasIngressTag) NS_FATAL_ERROR("WS-21 destination has no ingress tag");
    const uint32_t ingress = tag.GetFlowId();
    auto route = m_ws21IngressToFirst.find(std::make_pair(source->second, ingress));
    const auto key = std::make_tuple(ch.sip, ch.dip, ch.udp.sport, ch.udp.dport);
    Ws21PathObservation &item = m_ws21Destination[key];
    if (route == m_ws21IngressToFirst.end()) ++item.unmapped;
    else if (item.packets && item.port != route->second) ++item.inconsistent;
    if (!item.packets) {
        item.port = route == m_ws21IngressToFirst.end() ? 0 : route->second;
        item.firstNs = Simulator::Now().GetNanoSeconds();
    }
    ++item.packets;
    item.cePackets += ch.GetIpv4EcnBits() == 3;
    item.lastNs = Simulator::Now().GetNanoSeconds();
    if (route != m_ws21IngressToFirst.end())
        AccumulateWs21Feedback(source->second, route->second, ch,
                               ch.GetIpv4EcnBits() == 3);
}

void SwitchNode::AccumulateWs21Feedback(uint32_t sourceTor, uint32_t candidatePort,
                                        const CustomHeader &ch, bool ce) {
    if (!Ws21FeedbackEnabled() || !m_isToR || sourceTor == m_id) return;
    const auto key = std::make_pair(sourceTor, candidatePort);
    if (!m_ws21FeedbackWindows.count(key) &&
        m_ws21FeedbackWindows.size() >= WS21_FEEDBACK_MAX_KEYS_PER_TOR) {
        ++ws21_feedback_rejected;
        return;
    }
    Ws21FeedbackWindow &window = m_ws21FeedbackWindows[key];
    const uint64_t nowNs = Simulator::Now().GetNanoSeconds();
    if (!window.samplePackets) {
        window.sourceHostIp = ch.sip;
        window.destinationHostIp = ch.dip;
        window.startNs = nowNs;
    }
    ++window.samplePackets;
    if (ce) ++window.cePackets;
    window.endNs = nowNs;
    if (!window.scheduled) {
        window.scheduled = true;
        Simulator::Schedule(NanoSeconds(10000), &SwitchNode::FlushWs21Feedback,
                            this, sourceTor, candidatePort);
    }
}

void SwitchNode::FlushWs21Feedback(uint32_t sourceTor, uint32_t candidatePort) {
    const auto key = std::make_pair(sourceTor, candidatePort);
    auto found = m_ws21FeedbackWindows.find(key);
    if (found == m_ws21FeedbackWindows.end()) return;
    const Ws21FeedbackWindow window = found->second;
    m_ws21FeedbackWindows.erase(found);
    if (!window.samplePackets) return;

    Ws21FeedbackHeader report;
    report.sourceTor = sourceTor;
    report.destinationTor = m_id;
    report.candidatePort = candidatePort;
    report.windowStartNs = window.startNs;
    report.windowEndNs = window.endNs;
    report.cePackets = window.cePackets;
    report.samplePackets = window.samplePackets;
    report.sequence = ++m_ws21FeedbackSequence[key];
    report.generatedNs = Simulator::Now().GetNanoSeconds();
    NS_ASSERT_MSG(report.IsValid(), "WS-21 generated an invalid feedback report");

    Ptr<Packet> packet = Create<Packet>();
    packet->AddHeader(report);
    Ipv4Header ipv4;
    ipv4.SetSource(Ipv4Address(window.destinationHostIp));
    ipv4.SetDestination(Ipv4Address(window.sourceHostIp));
    ipv4.SetProtocol(Ws21FeedbackHeader::IP_PROTOCOL);
    ipv4.SetTtl(64);
    ipv4.SetPayloadSize(packet->GetSize());
    ipv4.SetIdentification(uint16_t(report.sequence));
    packet->AddHeader(ipv4);
    PppHeader ppp;
    ppp.SetProtocol(0x0021);
    packet->AddHeader(ppp);
    packet->AddPacketTag(FlowIdTag(Settings::CONWEAVE_CTRL_DUMMY_INDEV));

    CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header |
                    CustomHeader::L4_Header);
    packet->PeekHeader(ch);
    ++ws21_feedback_generated;
    SendToDevContinue(packet, ch);
}

bool SwitchNode::ReceiveWs21Feedback(Ptr<Packet> p, const CustomHeader &ch) {
    if (!Ws21FeedbackEnabled() || ch.l3Prot != Ws21FeedbackHeader::IP_PROTOCOL || !m_isToR)
        return false;
    auto localSource = ws21_host_tor.find(ch.dip);
    auto remoteDestination = ws21_host_tor.find(ch.sip);
    if (localSource == ws21_host_tor.end() || localSource->second != m_id ||
        remoteDestination == ws21_host_tor.end()) {
        ++ws21_feedback_rejected;
        return true;
    }

    const uint32_t packetBytes = p->GetSize();
    PppHeader ppp;
    Ipv4Header ipv4;
    Ws21FeedbackHeader report;
    if (p->RemoveHeader(ppp) != ppp.GetSerializedSize() ||
        p->RemoveHeader(ipv4) != ipv4.GetSerializedSize() ||
        p->RemoveHeader(report) != report.GetSerializedSize()) {
        ++ws21_feedback_rejected;
        return true;
    }

    const uint64_t nowNs = Simulator::Now().GetNanoSeconds();
    if (!report.IsValid() || ipv4.GetProtocol() != Ws21FeedbackHeader::IP_PROTOCOL ||
        ipv4.GetSource().Get() != ch.sip || ipv4.GetDestination().Get() != ch.dip ||
        report.sourceTor != m_id || report.destinationTor != remoteDestination->second ||
        report.generatedNs > nowNs) {
        ++ws21_feedback_rejected;
        return true;
    }
    const uint64_t ageNs = nowNs - report.generatedNs;
    ws21_feedback_age_sum_ns += ageNs;
    ws21_feedback_age_max_ns = std::max(ws21_feedback_age_max_ns, ageNs);
    if (ageNs < 1000) ++ws21_feedback_age_bins[0];
    else if (ageNs < 2000) ++ws21_feedback_age_bins[1];
    else if (ageNs < 5000) ++ws21_feedback_age_bins[2];
    else if (ageNs <= 10000) ++ws21_feedback_age_bins[3];
    else ++ws21_feedback_age_bins[4];
    if (ageNs > 10000) {
        ++ws21_feedback_expired;
        return true;
    }

    auto routes = m_rtTable.find(ch.sip);
    if (routes == m_rtTable.end() ||
        std::find(routes->second.begin(), routes->second.end(), report.candidatePort) ==
            routes->second.end()) {
        ++ws21_feedback_rejected;
        return true;
    }

    const auto key = std::make_pair(report.destinationTor, report.candidatePort);
    if (!m_ws21Feedback.count(key) && m_ws21Feedback.size() >= WS21_FEEDBACK_MAX_KEYS_PER_TOR) {
        ++ws21_feedback_rejected;
        return true;
    }
    Ws21FeedbackState &state = m_ws21Feedback[key];
    if (report.sequence <= state.sequence) {
        ++ws21_feedback_rejected;
        return true;
    }
    if (state.sequence && report.sequence > state.sequence + 1)
        ws21_feedback_sequence_gaps += report.sequence - state.sequence - 1;
    state.sequence = report.sequence;
    state.windowEndNs = report.windowEndNs;
    state.generatedNs = report.generatedNs;
    state.cePackets = report.cePackets;
    state.samplePackets = report.samplePackets;
    ++ws21_feedback_delivered;
    ws21_feedback_bytes += packetBytes;
    ws21_feedback_cache_peak = std::max<uint64_t>(ws21_feedback_cache_peak,
                                                   m_ws21Feedback.size());
    return true;
}

void SwitchNode::WriteWs21Identity(FILE *out) const {
    for (const auto &group : {&m_ws21Source, &m_ws21Destination}) {
        const char *side = group == &m_ws21Source ? "source" : "destination";
        for (const auto &entry : *group) {
            const auto &key = entry.first;
            const auto &s = entry.second;
            fprintf(out, "%s %u %u %u %u %u %u %lu %lu %lu %lu %lu %lu\n",
                    side, m_id, Settings::hostIp2IdMap.at(std::get<0>(key)),
                    Settings::hostIp2IdMap.at(std::get<1>(key)),
                    std::get<2>(key), std::get<3>(key), s.port, s.packets,
                    s.cePackets, s.firstNs, s.lastNs, s.inconsistent, s.unmapped);
        }
    }
}

void SwitchNode::PrintWorkloadTagCounts() {
    if (Ws21FeedbackEnabled())
        std::cout << "WS21_FEEDBACK generated=" << ws21_feedback_generated
                  << " delivered=" << ws21_feedback_delivered
                  << " rejected=" << ws21_feedback_rejected
                  << " expired=" << ws21_feedback_expired
                  << " delivered_bytes=" << ws21_feedback_bytes
                  << " age_sum_ns=" << ws21_feedback_age_sum_ns
                  << " age_max_ns=" << ws21_feedback_age_max_ns
                  << " age_lt_1us=" << ws21_feedback_age_bins[0]
                  << " age_1_2us=" << ws21_feedback_age_bins[1]
                  << " age_2_5us=" << ws21_feedback_age_bins[2]
                  << " age_5_10us=" << ws21_feedback_age_bins[3]
                  << " age_gt_10us=" << ws21_feedback_age_bins[4]
                  << " sequence_gaps=" << ws21_feedback_sequence_gaps
                  << " hop_enqueues=" << ws21_feedback_hop_enqueues
                  << " hop_rejects=" << ws21_feedback_hop_rejects
                  << " hop_dequeues=" << ws21_feedback_hop_dequeues
                  << " hop_bytes=" << ws21_feedback_hop_bytes
                  << " cache_peak=" << ws21_feedback_cache_peak << std::endl;
    if (Settings::lb_mode == 20)
        std::cout << "WS18_PATH flows=" << ws18_path_flows
                  << " alternate=" << ws18_path_alternate
                  << " packets=" << ws18_path_packets
                  << " multipath_packets=" << ws18_path_multipath << std::endl;
    if (Ws13DiagnosticEnabled()) {
        for (const auto &entry : ws13_hops) {
            const auto &key = entry.first;
            const Ws13FlowHop &s = entry.second;
            std::cout << "WS13_HOP src=" << std::get<0>(key)
                      << " dst=" << std::get<1>(key)
                      << " sport=" << std::get<2>(key)
                      << " dport=" << std::get<3>(key)
                      << " switch=" << std::get<4>(key)
                      << " port=" << std::get<5>(key)
                      << " packets=" << s.packets << " bytes=" << s.bytes
                      << " queued_bytes_sum=" << s.queuedBytesSum
                      << " queued_bytes_max=" << s.maxQueuedBytes
                      << " wait_ns_sum=" << s.waitNsSum
                      << " wait_ns_max=" << s.maxWaitNs << std::endl;
        }
        std::cout << "WS13_INFLIGHT unpaired=" << ws13_inflight.size() << std::endl;
    }
    for (const auto &entry : workload_tag_packets)
        std::cout << "WS06_ROUTING_TAG tag=" << entry.first << " packets=" << entry.second << std::endl;
    std::cout << "WS06_ROUTING_TAG missing=" << missing_workload_tag_packets << std::endl;
    if (Settings::lb_mode == 12)
        std::cout << "WS07_DUALTRACK flow_packets=" << dualtrack_flow_packets
                  << " packet_packets=" << dualtrack_packet_packets
                  << " packet_multipath=" << dualtrack_packet_multipath << std::endl;
    if (Settings::lb_mode >= 16 && Settings::lb_mode <= 19) {
        std::cout << "WS12_ROUTE mode=" << Settings::lb_mode
                  << " moe_packets=" << ws12_moe_packets
                  << " background_packets=" << ws12_background_packets
                  << " moe_multipath=" << ws12_multipath_packets << std::endl;
        for (const auto &entry : ws12_source_port_choices)
            std::cout << "WS12_PORT switch=" << entry.first.first
                      << " port=" << entry.first.second
                      << " packets=" << entry.second << std::endl;
    }
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
    else if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL)
        buf.u32[2] = Ws21FeedbackHeader::IP_PROTOCOL;
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

// The two candidates are determined by the immutable 4-tuple. Queue load is
// sampled once at the source ToR; every later packet stays on that flow's port.
uint32_t SwitchNode::DoLbWs18(Ptr<const Packet> p, const CustomHeader &ch,
                               const std::vector<int> &nexthops) {
    WorkloadTag label;
    if (!ws18_path_enabled || ch.l3Prot != 0x11 || !m_isToR ||
        !m_isToR_hostIP.count(ch.sip) || !p->PeekPacketTag(label) ||
        label.GetValue() != 2 || nexthops.size() < 2)
        return DoLbFlowECMP(p, ch, nexthops);
    ++ws18_path_packets;
    ++ws18_path_multipath;
    const auto key = std::make_tuple(ch.sip, ch.dip, ch.udp.sport, ch.udp.dport);
    auto found = m_ws18FlowPort.find(key);
    if (found != m_ws18FlowPort.end()) return found->second;
    uint32_t words[3] = {ch.sip, ch.dip,
                         uint32_t(ch.udp.sport) | (uint32_t(ch.udp.dport) << 16)};
    uint32_t first = EcmpHash(reinterpret_cast<const uint8_t *>(words),
                              sizeof(words), m_ecmpSeed) % nexthops.size();
    uint32_t second = EcmpHash(reinterpret_cast<const uint8_t *>(words),
                               sizeof(words), m_ecmpSeed ^ 0x9e3779b9U) % nexthops.size();
    if (second == first) second = (first + 1) % nexthops.size();
    uint32_t selected = CalculateInterfaceLoad(nexthops[second]) <
                                CalculateInterfaceLoad(nexthops[first])
                            ? second : first;
    ++ws18_path_flows;
    if (selected != first) ++ws18_path_alternate;
    m_ws18FlowPort[key] = nexthops[selected];
    return nexthops[selected];
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

// WS-12: isolate each packet strategy to tag=2 UDP data.  Background and
// control traffic use the original flow ECMP hash on the same next-hop set.
uint32_t SwitchNode::DoLbPacketStrategy(Ptr<const Packet> p, const CustomHeader &ch,
                                        const std::vector<int> &nexthops) {
    WorkloadTag label;
    const bool moe = ch.l3Prot == 0x11 && p->PeekPacketTag(label) &&
                     label.GetValue() == 2;
    const bool sourceTor = m_isToR && m_isToR_hostIP.count(ch.sip);
    if (!moe) {
        if (sourceTor && ch.l3Prot == 0x11) ++ws12_background_packets;
        return DoLbFlowECMP(p, ch, nexthops);
    }
    uint32_t chosen = nexthops[0];
    switch (Settings::lb_mode) {
        case 16: {  // round robin per switch and destination, reset with the switch
            uint32_t &next = m_packetRoundRobinNext[ch.dip];
            chosen = nexthops[next % nexthops.size()];
            next = (next + 1) % nexthops.size();
            break;
        }
        case 17:  // uniform random spray, matching hybrid-ss's effective rule
            chosen = nexthops[std::rand() % nexthops.size()];
            break;
        case 18: {  // hybrid-as effective path: local queue, no probes in mode 13
            double totalWeight = 0.0;
            for (int port : nexthops)
                totalWeight += 1.0 / (static_cast<double>(CalculateInterfaceLoad(port)) + 8193.0);
            const double draw = (static_cast<double>(std::rand()) / RAND_MAX) * totalWeight;
            double cumulative = 0.0;
            chosen = nexthops.back();
            for (int port : nexthops) {
                cumulative += 1.0 / (static_cast<double>(CalculateInterfaceLoad(port)) + 8193.0);
                if (draw < cumulative) { chosen = port; break; }
            }
            break;
        }
        case 19:  // original DRILL's local queue + per-destination cached best
            chosen = DoLbDrill(p, ch, nexthops);
            break;
        default:
            NS_ASSERT_MSG(false, "Unknown WS-12 packet strategy");
    }
    if (sourceTor) {
        ++ws12_moe_packets;
        if (nexthops.size() > 1) ++ws12_multipath_packets;
        ++ws12_source_port_choices[std::make_pair(m_id, chosen)];
    }
    return chosen;
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
    if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL && ReceiveWs21Feedback(packet, ch))
        return true;
    ObserveWs21Destination(packet, ch);
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
        } else if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL) {
            qIndex = 3;  // normal data priority; feedback competes for queue service
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
        (ch.l3Prot == 0xFF || ch.l3Prot == 0xFE || ch.l3Prot == 0xFD || ch.l3Prot == 0xFC ||
         ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL);

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
        case 16:
        case 17:
        case 18:
        case 19:
            return DoLbPacketStrategy(p, ch, nexthops);
        case 20:
        {
            const uint32_t port = DoLbWs18(p, ch, nexthops);
            if (ws21_identity_enabled && ch.l3Prot == 0x11)
                ObserveWs21Source(ch, port);
            return port;
        }
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
    const bool locallyGenerated = inDev == Settings::CONWEAVE_CTRL_DUMMY_INDEV;
    if (locallyGenerated) { // sanity check
        // ConWeave reply is on ACK protocol with high priority, so qIndex should be 0
        assert((qIndex == 0 && m_ackHighPrio == 1) ||
               (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL && qIndex == 3));
    }

    if (qIndex != 0) {  // not highest priority
        if (m_mmu->CheckEgressAdmission(outDev, qIndex,
                                        p->GetSize())) {  // Egress Admission control
            if (locallyGenerated || m_mmu->CheckIngressAdmission(inDev, qIndex,
                                                                  p->GetSize())) {
                if (!locallyGenerated)
                    m_mmu->UpdateIngressAdmission(inDev, qIndex, p->GetSize());
                m_mmu->UpdateEgressAdmission(outDev, qIndex, p->GetSize());
            } else { /** DROP: At Ingress */
                FactorialAdmissionDrop("ingress", m_id, ch, inDev, outDev, p->GetSize());
#if (0)
                // /** NOTE: logging dropped pkts */
                // std::cout << "LostPkt ingress - Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
                //           << "L3Prot:" << ch.l3Prot
                //           << ",Size:" << p->GetSize()
                //           << ",At " << Simulator::Now() << std::endl;
#endif
                Settings::dropped_pkt_sw_ingress++;
                if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL)
                    ++ws21_feedback_hop_rejects;
                if (Settings::lb_mode >= 13 && Settings::lb_mode <= 15)
                    SwitchNotifyAdmissionDrop(outDev, p);
                return;  // drop
            }
        } else { /** DROP: At Egress */
            FactorialAdmissionDrop("egress", m_id, ch, inDev, outDev, p->GetSize());
#if (0)
            // /** NOTE: logging dropped pkts */
            // std::cout << "LostPkt egress - Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
            //           << "L3Prot:" << ch.l3Prot << ",Size:" << p->GetSize() << ",At "
            //           << Simulator::Now() << std::endl;
#endif
            Settings::dropped_pkt_sw_egress++;
            if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL)
                ++ws21_feedback_hop_rejects;
            if (Settings::lb_mode >= 13 && Settings::lb_mode <= 15)
                SwitchNotifyAdmissionDrop(outDev, p);
            return;  // drop
        }

        if (!locallyGenerated) CheckAndSendPfc(inDev, qIndex);
    }

    if (Ws13DiagnosticEnabled() && ch.l3Prot == 0x11) {
        WorkloadTag tag;
        auto destination = Settings::hostIp2IdMap.find(ch.dip);
        auto source = Settings::hostIp2IdMap.find(ch.sip);
        if (p->PeekPacketTag(tag) && tag.GetValue() == 1 &&
            destination != Settings::hostIp2IdMap.end() &&
            (Settings::lb_mode == 20 || destination->second == 856 ||
             destination->second == 576) &&
            source != Settings::hostIp2IdMap.end()) {
            Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[outDev]);
            NS_ASSERT_MSG(dev && dev->GetQueue(), "WS-13 diagnostic egress queue absent");
            Ws13Packet item = {source->second, destination->second,
                               ch.udp.sport, ch.udp.dport, outDev,
                               dev->GetQueue()->GetNBytesTotal(),
                               uint64_t(Simulator::Now().GetNanoSeconds())};
            auto key = std::make_pair(m_id, p->GetUid());
            NS_ASSERT_MSG(ws13_inflight.count(key) == 0, "WS-13 duplicate packet UID at switch");
            ws13_inflight[key] = item;
        }
    }
    const bool accepted = m_devices[outDev]->SwitchSend(qIndex, p, ch);
    if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL) {
        if (accepted) {
            ++ws21_feedback_hop_enqueues;
            ws21_feedback_hop_bytes += p->GetSize();
        } else {
            ++ws21_feedback_hop_rejects;
        }
    }
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
    bool feedbackPacket = false;
    if (Ws21FeedbackEnabled()) {
        CustomHeader feedback(CustomHeader::L2_Header | CustomHeader::L3_Header |
                              CustomHeader::L4_Header);
        if (p->PeekHeader(feedback) && feedback.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL) {
            feedbackPacket = true;
            ++ws21_feedback_hop_dequeues;
        }
    }
    RecordWs21PortEvent(ifIndex, 'D');
    if (Ws13DiagnosticEnabled()) {
        auto hit = ws13_inflight.find(std::make_pair(m_id, p->GetUid()));
        if (hit != ws13_inflight.end()) {
            const Ws13Packet &item = hit->second;
            NS_ASSERT_MSG(item.outDev == ifIndex, "WS-13 diagnostic port mismatch");
            uint64_t waited = uint64_t(Simulator::Now().GetNanoSeconds()) - item.enqueueNs;
            auto key = std::make_tuple(item.src, item.dst, item.sport, item.dport, m_id, ifIndex);
            Ws13FlowHop &s = ws13_hops[key];
            ++s.packets;
            s.bytes += p->GetSize();
            s.queuedBytesSum += item.queuedBytes;
            s.waitNsSum += waited;
            s.maxQueuedBytes = std::max(s.maxQueuedBytes, uint64_t(item.queuedBytes));
            s.maxWaitNs = std::max(s.maxWaitNs, waited);
            ws13_inflight.erase(hit);
        }
    }
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
    if (feedbackPacket) {
        FlowIdTag ingress;
        if (p->PeekPacketTag(ingress) &&
            ingress.GetFlowId() == Settings::CONWEAVE_CTRL_DUMMY_INDEV)
            p->RemovePacketTag(ingress);
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
