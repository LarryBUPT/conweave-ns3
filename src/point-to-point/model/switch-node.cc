#include "switch-node.h"

#include "assert.h"
#include "ns3/boolean.h"
#include "ns3/channel.h"
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
#include "ws21-heartbeat-header.h"
#include <iostream>
#include <cstdlib>
#include <algorithm>
#include <map>
#include <limits>
#include <tuple>
#include "ppp-header.h"
#include "qbb-net-device.h"

namespace ns3 {

static bool ClassReserveFamilyMode() {
    return Settings::lb_mode == 21 ||
           (Settings::lb_mode >= 25 && Settings::lb_mode <= 27);
}

// -1 preserves every historical code path. 0=C0, 1=C1, 2=C2, 3=STATE-only.
static int32_t ws29_arm = -1;
static uint32_t ws29_fault = 0, ws29_fault_tor = 0, ws29_fault_port = 0;
static uint64_t ws29_fault_start = 0, ws29_fault_end = 0;
static uint64_t ws29_rows = 0, ws29_overflow = 0;
static std::map<std::string, uint64_t> ws29_counts;
static bool Ws29Row() {
    if (ws29_rows >= 500000) { ++ws29_overflow; return false; }
    ++ws29_rows;
    return true;
}

void SwitchNode::ConfigureWs29(int32_t arm, uint32_t fault, uint32_t tor,
                              uint32_t port, uint64_t startNs, uint64_t endNs) {
    ws29_arm = arm;
    ws29_fault = fault; ws29_fault_tor = tor; ws29_fault_port = port;
    ws29_fault_start = startNs; ws29_fault_end = endNs;
}


static bool ClassReserveBackgroundWeight() {
    return Settings::lb_mode != 25 && Settings::lb_mode != 27;
}

static bool ClassReserveBackgroundRouting() {
    return Settings::lb_mode != 25 && Settings::lb_mode != 26;
}

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
static uint64_t ws27_moe_packets = 0, ws27_new_flows = 0, ws27_reused_packets = 0;
static uint64_t ws27_two_candidates = 0, ws27_scored = 0, ws27_diverted = 0;
static uint64_t ws27_gate_activations = 0, ws27_gate_exits = 0;
static uint64_t ws27_fallback_packets = 0;
static uint64_t guard_packets = 0, guard_two_candidates = 0;
static uint64_t guard_scored = 0, guard_diverted = 0;
static uint64_t guard_activations = 0, guard_exits = 0;
static uint64_t guard_queue_violations = 0;
static uint64_t classreserve_moe_packets = 0, classreserve_background_packets = 0;
static uint64_t classreserve_moe_two_choices = 0, classreserve_moe_diverted = 0;
static uint64_t classreserve_moe_flow_new = 0, classreserve_moe_flow_reused = 0;
static uint64_t classreserve_fallback_packets = 0;
static uint64_t classreserve_background_new_flows = 0, classreserve_background_reused = 0;
static uint64_t classreserve_background_queue_avoids = 0;
static uint64_t destspread_moe_packets = 0, destspread_background_packets = 0;
static uint64_t destspread_moe_new = 0, destspread_moe_reused = 0;
static uint64_t destspread_background_new = 0, destspread_background_reused = 0;
static uint64_t destspread_background_ties = 0, destspread_background_all_empty = 0;
static uint64_t destspread_fallback_packets = 0;
static std::map<std::tuple<uint32_t, uint32_t, uint32_t>, uint64_t>
    destspread_source_port_packets;
static std::map<std::tuple<uint32_t, uint32_t, uint32_t>, uint64_t>
    classreserve_source_port_packets;
static uint64_t ws25_choice_events[3] = {0, 0, 0};
static uint64_t ws25_empty_choices[3] = {0, 0, 0};
static uint64_t ws25_first_queue_sum[3] = {0, 0, 0};
static uint64_t ws25_second_queue_sum[3] = {0, 0, 0};
static uint64_t ws25_background_queue_nonzero = 0;
static bool Ws25DiagnosticEnabled();
static bool ws18_path_enabled = false;
static bool ws21_identity_enabled = false;
static bool ws21_feedback_enabled = false;
static uint32_t ws21_feedback_interval_ns = 10000;
static uint64_t ws21_feedback_delivered = 0, ws21_feedback_rejected = 0;
static uint64_t ws21_feedback_expired = 0, ws21_feedback_bytes = 0;
static uint64_t ws21_feedback_cache_peak = 0;
static uint64_t ws21_feedback_age_sum_ns = 0, ws21_feedback_age_max_ns = 0;
static uint64_t ws21_feedback_sample_age_sum_ns = 0, ws21_feedback_sample_age_max_ns = 0;
static uint64_t ws21_feedback_age_bins[5] = {0, 0, 0, 0, 0};
static uint64_t ws21_feedback_sequence_gaps = 0;
static uint64_t ws21_feedback_generated = 0, ws21_feedback_hop_bytes = 0;
static uint64_t ws21_feedback_hop_enqueues = 0, ws21_feedback_hop_rejects = 0;
static uint64_t ws21_feedback_hop_dequeues = 0;
static bool ws21_heartbeat_enabled = false;
static uint32_t ws21_heartbeat_interval_ns = 200000;
static uint32_t ws21_heartbeat_fault_mode = 0, ws21_heartbeat_fault_tor = 0;
static uint32_t ws21_heartbeat_fault_port = 0;
static uint64_t ws21_heartbeat_fault_start_ns = 0, ws21_heartbeat_fault_end_ns = 0;
static uint64_t ws21_heartbeat_hello_generated = 0, ws21_heartbeat_ack_generated = 0;
static uint64_t ws21_heartbeat_hello_received = 0, ws21_heartbeat_ack_received = 0;
static uint64_t ws21_heartbeat_rejected = 0, ws21_heartbeat_injected_drops = 0;
static uint64_t ws21_heartbeat_timeouts = 0, ws21_heartbeat_unknown = 0;
static uint64_t ws21_heartbeat_recovered = 0, ws21_heartbeat_activations = 0;
static uint64_t ws21_heartbeat_ack_rtt_sum_ns = 0, ws21_heartbeat_ack_rtt_max_ns = 0;
static uint64_t ws21_heartbeat_deactivations = 0, ws21_heartbeat_active = 0;
static uint64_t ws21_heartbeat_active_peak = 0;
static uint64_t ws21_heartbeat_hop_enqueues = 0, ws21_heartbeat_hop_dequeues = 0;
static uint64_t ws21_heartbeat_hop_rejects = 0, ws21_heartbeat_hop_bytes = 0;
static uint64_t ws21_heartbeat_hello_hop_bytes = 0, ws21_heartbeat_ack_hop_bytes = 0;
static uint64_t ws21_heartbeat_event_rows = 0, ws21_heartbeat_event_overflow = 0;
static const uint64_t WS21_HEARTBEAT_MAX_EVENT_ROWS = 20000;
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

struct Ws28TailTarget {
    uint32_t seed, src, dst, sport, dport;
};
static const Ws28TailTarget ws28_tail_targets[] = {
    {20262725, 780, 956, 10045, 142}, {20262725, 964, 304, 10020, 139},
    {20262729, 1176, 344, 10010, 165}, {20262729, 320, 528, 10033, 115},
    {20262739, 860, 1160, 10057, 137}, {20262739, 560, 448, 10027, 133},
};
struct Ws28TailQueued {
    uint32_t target, port, seq, bytes;
    uint64_t enqueueNs, queueBytes, backgroundBytes;
};
static std::map<std::pair<uint32_t, uint64_t>, Ws28TailQueued> ws28_tail_queued;
static uint32_t ws28_tail_rows = 0;
static const uint32_t WS28_TAIL_MAX_ROWS = 20000;
static bool Ws28TailDiagnosticEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS28_TAIL_DIAG");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}
static int Ws28TailTargetIndex(const CustomHeader &ch) {
    if (!Ws28TailDiagnosticEnabled() || ch.l3Prot != 0x11) return -1;
    const uint64_t now = uint64_t(Simulator::Now().GetNanoSeconds());
    if (now < 2000000000ULL || now > 2000025000ULL) return -1;
    for (size_t i = 0; i < sizeof(ws28_tail_targets) / sizeof(ws28_tail_targets[0]); ++i) {
        const Ws28TailTarget &t = ws28_tail_targets[i];
        if (ch.udp.sport != t.sport || ch.udp.dport != t.dport) continue;
        auto src = Settings::hostIp2IdMap.find(ch.sip);
        auto dst = Settings::hostIp2IdMap.find(ch.dip);
        if (src != Settings::hostIp2IdMap.end() && dst != Settings::hostIp2IdMap.end() &&
            src->second == t.src && dst->second == t.dst)
            return int(i);
    }
    return -1;
}
static uint64_t Ws28BackgroundQueueBytes(uint32_t switchId, uint32_t port) {
    auto it = guard_queue_stats.find(std::make_tuple(switchId, port, 1U));
    return it == guard_queue_stats.end() ? 0 : it->second.current;
}
static bool Ws28TailReserveRow() {
    if (!Ws28TailDiagnosticEnabled()) return false;
    if (ws28_tail_rows == WS28_TAIL_MAX_ROWS) {
        std::cout << "WS28_TAIL_OVERFLOW limit=" << WS28_TAIL_MAX_ROWS << std::endl;
        ++ws28_tail_rows;
        return false;
    }
    if (ws28_tail_rows > WS28_TAIL_MAX_ROWS) return false;
    ++ws28_tail_rows;
    return true;
}
static void Ws28TailAdmissionDrop(const CustomHeader &ch, uint32_t switchId,
                                  uint32_t port, uint64_t uid, const char *side) {
    const int target = Ws28TailTargetIndex(ch);
    if (target < 0 || !Ws28TailReserveRow()) return;
    std::cout << "WS28_TAIL_ADMISSION_DROP seed=" << ws28_tail_targets[target].seed
              << " target=" << target
              << " time_ns=" << Simulator::Now().GetNanoSeconds()
              << " switch=" << switchId << " port=" << port
              << " uid=" << uid << " seq=" << ch.udp.seq
              << " side=" << side << std::endl;
}

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

static uint8_t Ws21HeartbeatPacketType(Ptr<const Packet> p) {
    Ptr<Packet> copy = p->Copy();
    PppHeader ppp;
    Ipv4Header ipv4;
    if (copy->GetSize() < ppp.GetSerializedSize() + ipv4.GetSerializedSize() +
                              Ws21HeartbeatHeader::SERIALIZED_SIZE)
        return 0;
    copy->RemoveHeader(ppp);
    copy->RemoveHeader(ipv4);
    if (ipv4.GetProtocol() != Ws21FeedbackHeader::IP_PROTOCOL ||
        ipv4.GetPayloadSize() != Ws21HeartbeatHeader::SERIALIZED_SIZE ||
        copy->GetSize() != Ws21HeartbeatHeader::SERIALIZED_SIZE)
        return 0;
    Ws21HeartbeatHeader heartbeat;
    copy->RemoveHeader(heartbeat);
    return heartbeat.IsValid() ? heartbeat.type : 0;
}

struct Ws21PeerInfo {
    uint32_t nodeId, port, nodeType;
};

static void Ws29ControlEvent(Ptr<const Packet> p, uint32_t node, uint32_t port,
                             const char *event) {
    if (ws29_arm < 0) return;
    CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
    p->PeekHeader(ch);
    if (ch.l3Prot != Ws21FeedbackHeader::IP_PROTOCOL) return;
    const uint8_t type = Ws21HeartbeatPacketType(p);
    const std::string kind = type == 2 ? "hello" : (type == 3 ? "ack" : "state");
    ++ws29_counts[kind + "_" + event + "_packets"];
    ws29_counts[kind + "_" + event + "_bytes"] += p->GetSize();
    if (Ws29Row()) std::cout << "WS29_CONTROL time_ns=" << Simulator::Now().GetNanoSeconds()
        << " switch=" << node << " port=" << port << " event=" << event
        << " type=" << kind << " bytes=" << p->GetSize() << std::endl;
}

static Ws21PeerInfo Ws21Peer(Ptr<NetDevice> device) {
    Ptr<Channel> channel = device->GetChannel();
    if (!channel || channel->GetNDevices() != 2)
        NS_FATAL_ERROR("WS-21 heartbeat requires a point-to-point channel");
    for (uint32_t i = 0; i < 2; ++i) {
        Ptr<NetDevice> peer = channel->GetDevice(i);
        if (peer != device)
            return {peer->GetNode()->GetId(), peer->GetIfIndex(),
                    peer->GetNode()->GetNodeType()};
    }
    NS_FATAL_ERROR("WS-21 heartbeat cannot find the neighboring device");
    return {0U, 0U, 0U};
}

static void RecordWs21HeartbeatEvent(uint32_t tor, uint32_t port, const char *event,
                                     uint32_t epoch, uint32_t sequence) {
    if (ws21_heartbeat_event_rows >= WS21_HEARTBEAT_MAX_EVENT_ROWS) {
        ++ws21_heartbeat_event_overflow;
        return;
    }
    ++ws21_heartbeat_event_rows;
    std::cout << "WS21_HEARTBEAT_EVENT time_ns=" << Simulator::Now().GetNanoSeconds()
              << " tor=" << tor << " port=" << port << " event=" << event
              << " epoch=" << epoch << " sequence=" << sequence << std::endl;
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
void SwitchNode::ConfigureWs21Feedback(bool enabled, uint32_t intervalNs) {
    if (intervalNs < 1000 || intervalNs > 60000)
        NS_FATAL_ERROR("WS-21 feedback interval must fit the compact generation delay");
    ws21_feedback_enabled = enabled;
    ws21_feedback_interval_ns = intervalNs;
}

void SwitchNode::ConfigureWs21Heartbeat(bool enabled, uint32_t intervalNs,
                                        uint32_t faultMode, uint32_t faultTor,
                                        uint32_t faultPort, uint64_t faultStartNs,
                                        uint64_t faultEndNs) {
    if (intervalNs < 50000 || intervalNs > 1000000 || faultMode > 2 ||
        (faultMode && faultEndNs <= faultStartNs))
        NS_FATAL_ERROR("WS-21 heartbeat configuration is outside the technical pilot contract");
    ws21_heartbeat_enabled = enabled;
    ws21_heartbeat_interval_ns = intervalNs;
    ws21_heartbeat_fault_mode = faultMode;
    ws21_heartbeat_fault_tor = faultTor;
    ws21_heartbeat_fault_port = faultPort;
    ws21_heartbeat_fault_start_ns = faultStartNs;
    ws21_heartbeat_fault_end_ns = faultEndNs;
}

void SwitchNode::RestartWs29Session() {
    NS_ASSERT_MSG(ws29_arm >= 0, "WS-29 restart requires an enabled experiment");
    NS_ASSERT_MSG(m_ws29StateSession < std::numeric_limits<uint32_t>::max(),
                  "STATE session exhausted; fail closed instead of reusing an identity");
    ++m_ws29StateSession;
    m_ws29RestartNs = Simulator::Now().GetNanoSeconds();
    m_ws21Feedback.clear();
    m_ws21FeedbackWindows.clear();
    m_ws21FeedbackSequence.clear();
    for (auto &item : m_ws21HeartbeatPorts) {
        Ws21HeartbeatPort &state = item.second;
        const bool active = state.active;
        if (active) --ws21_heartbeat_active;
        state.active = false;
        state.outstanding = state.missed = 0;
        // Touch increments epoch, invalidating every scheduled old Tick.
        if (active) TouchWs21Heartbeat(item.first);
    }
    if (Ws29Row()) std::cout << "WS29_SESSION time_ns=" << m_ws29RestartNs
        << " switch=" << m_id << " session=" << m_ws29StateSession << std::endl;
}

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
        Simulator::Schedule(NanoSeconds(ws21_feedback_interval_ns), &SwitchNode::FlushWs21Feedback,
                            this, sourceTor, candidatePort, m_ws29StateSession);
    }
}

void SwitchNode::FlushWs21Feedback(uint32_t sourceTor, uint32_t candidatePort,
                                  uint32_t session) {
    if (session != m_ws29StateSession) {
        if (ws29_arm >= 0) {
            ++ws29_counts["state_old_timer_ignored"];
            if (Ws29Row()) std::cout << "WS29_TIMER time_ns=" << Simulator::Now().GetNanoSeconds()
                << " switch=" << m_id << " port=" << candidatePort << " kind=state outcome=ignored"
                << " scheduled=" << session << " current=" << m_ws29StateSession << std::endl;
        }
        return; // old session timer owns no new window
    }
    const auto key = std::make_pair(sourceTor, candidatePort);
    auto found = m_ws21FeedbackWindows.find(key);
    if (found == m_ws21FeedbackWindows.end()) return;
    const Ws21FeedbackWindow window = found->second;
    m_ws21FeedbackWindows.erase(found);
    if (!window.samplePackets) return;

    Ws21FeedbackHeader report;
    report.candidatePort = candidatePort;
    report.windowEndNs = window.endNs;
    report.cePackets = window.cePackets;
    report.samplePackets = window.samplePackets;
    if (ws29_arm >= 0) {
        report.version = 3;
        report.session = session;
        report.windowStartNs = window.startNs;
    }
    uint32_t &sequence = m_ws21FeedbackSequence[key];
    if (sequence == std::numeric_limits<uint32_t>::max()) {
        if (ws29_arm < 0) NS_FATAL_ERROR("WS-21 compact feedback sequence exhausted");
        // Session rollover invalidates old timers; this window is already copied.
        RestartWs29Session();
        ++ws29_counts["state_sequence_rollover"];
        report.session = m_ws29StateSession;
        m_ws21FeedbackSequence[key] = 0;
        report.sequence = ++m_ws21FeedbackSequence[key];
    } else report.sequence = ++sequence;
    const uint64_t nowNs = Simulator::Now().GetNanoSeconds();
    if (nowNs < window.endNs ||
        nowNs - window.endNs > std::numeric_limits<uint16_t>::max())
        NS_FATAL_ERROR("WS-21 compact generation delay overflow");
    report.generationDelayNs = static_cast<uint16_t>(nowNs - window.endNs);
    if (!report.IsValid())
        NS_FATAL_ERROR("WS-21 generated an invalid feedback report");

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
    if (ws29_arm >= 0 && Ws29Row())
        std::cout << "WS29_STATE_SEND time_ns=" << nowNs << " switch=" << m_id
                  << " source_tor=" << sourceTor << " candidate=" << candidatePort
                  << " session=" << report.session << " sequence=" << report.sequence
                  << " start_ns=" << window.startNs << " end_ns=" << window.endNs
                  << " ce=" << window.cePackets << " samples=" << window.samplePackets
                  << " bytes=" << packet->GetSize() << std::endl;
    SendToDevContinue(packet, ch);
}

bool SwitchNode::ReceiveWs21Feedback(Ptr<Packet> p, const CustomHeader &ch) {
    if (!Ws21FeedbackEnabled() || ch.l3Prot != Ws21FeedbackHeader::IP_PROTOCOL || !m_isToR)
        return false;
    auto localSource = ws21_host_tor.find(ch.dip);
    auto remoteDestination = ws21_host_tor.find(ch.sip);
    Ws21FeedbackHeader report;
    const auto reject = [&](const char *reason, bool expired = false) {
        if (expired) ++ws21_feedback_expired;
        else ++ws21_feedback_rejected;
        const uint32_t destination = remoteDestination == ws21_host_tor.end() ? UINT32_MAX : remoteDestination->second;
        const auto high = m_ws29StateHighWater.find(std::make_pair(destination, report.candidatePort));
        if (ws29_arm >= 0 && Ws29Row()) std::cout << "WS29_STATE_REJECT time_ns=" << Simulator::Now().GetNanoSeconds()
            << " switch=" << m_id << " destination=" << destination << " candidate=" << report.candidatePort
            << " session=" << report.session << " sequence=" << report.sequence
            << " start_ns=" << report.windowStartNs << " end_ns=" << report.windowEndNs
            << " high_water=" << (high == m_ws29StateHighWater.end() ? 0 : high->second)
            << " outcome=" << (expired ? "expired" : "rejected") << " reason=" << reason << std::endl;
        return true;
    };
    if (localSource == ws21_host_tor.end() || localSource->second != m_id ||
        remoteDestination == ws21_host_tor.end()) {
        return reject("endpoint");
    }

    const uint32_t packetBytes = p->GetSize();
    PppHeader ppp;
    Ipv4Header ipv4;
    if (p->GetSize() != ppp.GetSerializedSize() + ipv4.GetSerializedSize() +
                           (ws29_arm >= 0 ? 38U : 26U)) {
        return reject("wire_size");
    }
    if (ws29_arm >= 0) report.version = 3;
    if (p->RemoveHeader(ppp) != ppp.GetSerializedSize() ||
        p->RemoveHeader(ipv4) != ipv4.GetSerializedSize() ||
        p->RemoveHeader(report) != report.GetSerializedSize()) {
        return reject("decode");
    }

    const uint64_t nowNs = Simulator::Now().GetNanoSeconds();
    if (!report.IsValid() || report.version != (ws29_arm >= 0 ? 3 : 2) ||
        ipv4.GetProtocol() != Ws21FeedbackHeader::IP_PROTOCOL ||
        ipv4.GetPayloadSize() != report.GetSerializedSize() ||
        ipv4.GetSource().Get() != ch.sip || ipv4.GetDestination().Get() != ch.dip ||
        report.GetGeneratedNs() > nowNs) {
        return reject("header");
    }
    const uint64_t ageNs = nowNs - report.GetGeneratedNs();
    const uint64_t sampleAgeNs = nowNs - report.windowEndNs;
    if (ws29_arm >= 0 && report.windowStartNs < m_ws29RestartNs) {
        ++ws29_counts["state_before_receiver_restart"];
        return reject("before_restart");
    }
    ws21_feedback_age_sum_ns += ageNs;
    ws21_feedback_age_max_ns = std::max(ws21_feedback_age_max_ns, ageNs);
    ws21_feedback_sample_age_sum_ns += sampleAgeNs;
    ws21_feedback_sample_age_max_ns = std::max(ws21_feedback_sample_age_max_ns,
                                               sampleAgeNs);
    if (ageNs < 1000) ++ws21_feedback_age_bins[0];
    else if (ageNs < 2000) ++ws21_feedback_age_bins[1];
    else if (ageNs < 5000) ++ws21_feedback_age_bins[2];
    else if (ageNs <= 10000) ++ws21_feedback_age_bins[3];
    else ++ws21_feedback_age_bins[4];
    if (ageNs > 10000) {
        return reject("age", true);
    }

    auto routes = m_rtTable.find(ch.sip);
    if (routes == m_rtTable.end() ||
        std::find(routes->second.begin(), routes->second.end(), report.candidatePort) ==
            routes->second.end()) {
        return reject("candidate");
    }

    const auto key = std::make_pair(remoteDestination->second, report.candidatePort);
    if (ws29_arm >= 0 && !m_ws29StateHighWater.count(key) &&
        m_ws29StateHighWater.size() >= WS21_FEEDBACK_MAX_KEYS_PER_TOR) {
        return reject("highwater_capacity");
    }
    if (!m_ws21Feedback.count(key) && m_ws21Feedback.size() >= WS21_FEEDBACK_MAX_KEYS_PER_TOR) {
        return reject("cache_capacity");
    }
    Ws21FeedbackState &state = m_ws21Feedback[key];
    if (ws29_arm >= 0 && report.session < m_ws29StateHighWater[key]) {
        ++ws29_counts["state_old_session"];
        return reject("old_session");
    }
    const bool sameSession = ws29_arm < 0 || report.session == state.session;
    if (sameSession && report.sequence <= state.sequence) {
        return reject("sequence");
    }
    if (sameSession && state.sequence && report.sequence > state.sequence + 1)
        ws21_feedback_sequence_gaps += report.sequence - state.sequence - 1;
    state.sequence = report.sequence;
    state.windowEndNs = report.windowEndNs;
    state.generatedNs = report.GetGeneratedNs();
    state.cePackets = report.cePackets;
    state.samplePackets = report.samplePackets;
    state.session = report.session;
    if (ws29_arm >= 0) m_ws29StateHighWater[key] = report.session;
    state.windowStartNs = report.windowStartNs;
    ++ws21_feedback_delivered;
    ws21_feedback_bytes += packetBytes;
    ws21_feedback_cache_peak = std::max<uint64_t>(ws21_feedback_cache_peak,
                                                   m_ws21Feedback.size());
    if (ws29_arm >= 0 && Ws29Row())
        std::cout << "WS29_STATE_CACHE time_ns=" << nowNs << " switch=" << m_id
                  << " destination=" << remoteDestination->second
                  << " candidate=" << report.candidatePort << " session=" << state.session
                  << " sequence=" << state.sequence << " start_ns=" << state.windowStartNs
                  << " end_ns=" << state.windowEndNs << " ce=" << state.cePackets
                  << " samples=" << state.samplePackets << " bytes=" << packetBytes << std::endl;
    return true;
}

bool SwitchNode::SendWs21Heartbeat(uint32_t port, uint8_t type, uint32_t epoch,
                                   uint32_t sequence) {
    if (port == 0 || port >= m_devices.size() || !m_devices[port]->IsLinkUp())
        return false;
    const auto peer = Ws21Peer(m_devices[port]);
    if (peer.nodeType != 1)
        NS_FATAL_ERROR("WS-21 heartbeat attempted on a host-facing port");
    Ws21HeartbeatHeader header;
    header.type = type;
    header.epoch = epoch;
    header.sequence = sequence;
    if (!header.IsValid()) NS_FATAL_ERROR("WS-21 generated an invalid heartbeat");

    Ptr<Packet> packet = Create<Packet>();
    packet->AddHeader(header);
    Ipv4Header ipv4;
    // These IDs are validated against the actual directly connected device.
    // No IP route lookup is used for local HELLO/ACK delivery.
    ipv4.SetSource(Ipv4Address(m_id + 1));
    ipv4.SetDestination(Ipv4Address(peer.nodeId + 1));
    ipv4.SetProtocol(Ws21FeedbackHeader::IP_PROTOCOL);
    ipv4.SetTtl(1);
    ipv4.SetPayloadSize(packet->GetSize());
    packet->AddHeader(ipv4);
    PppHeader ppp;
    ppp.SetProtocol(0x0021);
    packet->AddHeader(ppp);
    packet->AddPacketTag(FlowIdTag(Settings::CONWEAVE_CTRL_DUMMY_INDEV));
    CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header |
                    CustomHeader::L4_Header);
    packet->PeekHeader(ch);
    if (type == Ws21HeartbeatHeader::HELLO) ++ws21_heartbeat_hello_generated;
    else ++ws21_heartbeat_ack_generated;
    DoSwitchSend(packet, ch, port, 3);
    return true;
}

void SwitchNode::TouchWs21Heartbeat(uint32_t port) {
    if (!ws21_heartbeat_enabled || !m_isToR || port == 0 ||
        m_ws21HostPorts.count(port) || port >= m_devices.size()) return;
    Ws21HeartbeatPort &state = m_ws21HeartbeatPorts[port];
    state.lastActivityNs = Simulator::Now().GetNanoSeconds();
    if (state.active) return;
    if (state.epoch == std::numeric_limits<uint32_t>::max())
        NS_FATAL_ERROR("WS-21 heartbeat epoch exhausted");
    ++state.epoch;
    state.nextSequence = state.outstanding = state.missed = 0;
    state.sentNs = state.lastAckNs = 0;
    state.unknown = false;
    state.active = true;
    ++ws21_heartbeat_activations;
    ++ws21_heartbeat_active;
    ws21_heartbeat_active_peak = std::max(ws21_heartbeat_active_peak,
                                           ws21_heartbeat_active);
    RecordWs21HeartbeatEvent(m_id, port, "activate", state.epoch, 0);
    TickWs21Heartbeat(port, state.epoch);
}

void SwitchNode::TickWs21Heartbeat(uint32_t port, uint32_t epoch) {
    auto found = m_ws21HeartbeatPorts.find(port);
    if (found == m_ws21HeartbeatPorts.end() || !found->second.active ||
        found->second.epoch != epoch) {
        if (ws29_arm >= 0 && found != m_ws21HeartbeatPorts.end() && found->second.epoch != epoch) {
            ++ws29_counts["hb_old_timer_ignored"];
            if (Ws29Row()) std::cout << "WS29_TIMER time_ns=" << Simulator::Now().GetNanoSeconds()
                << " switch=" << m_id << " port=" << port << " kind=hb outcome=ignored"
                << " scheduled=" << epoch << " current=" << found->second.epoch << std::endl;
        }
        return;
    }
    Ws21HeartbeatPort &state = found->second;
    const uint64_t nowNs = Simulator::Now().GetNanoSeconds();
    const uint64_t idleNs = 4ULL * ws21_heartbeat_interval_ns;
    if (nowNs - state.lastActivityNs >= idleNs) {
        state.active = false;
        state.outstanding = 0;
        --ws21_heartbeat_active;
        ++ws21_heartbeat_deactivations;
        RecordWs21HeartbeatEvent(m_id, port, "deactivate", epoch, 0);
        return;
    }
    if (state.outstanding) {
        ++ws21_heartbeat_timeouts;
        ++state.missed;
        state.outstanding = 0;
        if (state.missed >= 3 && !state.unknown) {
            state.unknown = true;
            ++ws21_heartbeat_unknown;
            RecordWs21HeartbeatEvent(m_id, port, "unknown_timeout", epoch,
                                     state.nextSequence);
        }
    }
    if (!m_devices[port]->IsLinkUp() && !state.unknown) {
        state.unknown = true;
        ++ws21_heartbeat_unknown;
        RecordWs21HeartbeatEvent(m_id, port, "unknown_link_down", epoch,
                                 state.nextSequence);
    }
    if (m_devices[port]->IsLinkUp()) {
        if (state.nextSequence == std::numeric_limits<uint32_t>::max()) {
            if (ws29_arm < 0) NS_FATAL_ERROR("WS-21 heartbeat sequence exhausted");
            state.active = false;
            --ws21_heartbeat_active;
            TouchWs21Heartbeat(port);
            ++ws29_counts["hb_sequence_rollover"];
            return;
        }
        const uint32_t sequence = ++state.nextSequence;
        if (SendWs21Heartbeat(port, Ws21HeartbeatHeader::HELLO, epoch, sequence)) {
            state.outstanding = sequence;
            state.sentNs = nowNs;
            if (ws29_arm >= 0 && ws29_fault >= 3 && ws29_fault <= 8 &&
                m_id == ws29_fault_tor && port == ws29_fault_port &&
                nowNs >= ws29_fault_start && nowNs < ws29_fault_end &&
                !ws29_counts["fault_injected"])
                Simulator::Schedule(NanoSeconds(1), &SwitchNode::Ws29Fault,
                                    this, ws29_fault, port);
        }
    }
    Simulator::Schedule(NanoSeconds(ws21_heartbeat_interval_ns),
                        &SwitchNode::TickWs21Heartbeat, this, port, epoch);
}

bool SwitchNode::ReceiveWs21Heartbeat(Ptr<NetDevice> device, Ptr<Packet> p,
                                      const CustomHeader &ch) {
    if (!ws21_heartbeat_enabled || ch.l3Prot != Ws21FeedbackHeader::IP_PROTOCOL)
        return false;
    const uint32_t port = device->GetIfIndex();
    const auto initial = m_ws21HeartbeatPorts.find(port);
    const Ws21HeartbeatPort before = initial == m_ws21HeartbeatPorts.end() ? Ws21HeartbeatPort() : initial->second;
    Ws21HeartbeatHeader heartbeat;
    const auto auditAck = [&](bool accepted, const char *reason) {
        const auto current = m_ws21HeartbeatPorts.find(port);
        const Ws21HeartbeatPort after = current == m_ws21HeartbeatPorts.end() ? Ws21HeartbeatPort() : current->second;
        if (ws29_arm >= 0 && Ws29Row()) std::cout << "WS29_ACK_CHECK time_ns=" << Simulator::Now().GetNanoSeconds()
            << " switch=" << m_id << " port=" << port << " accepted=" << int(accepted)
            << " reason=" << reason << " packet_type=" << int(heartbeat.type)
            << " packet_epoch=" << heartbeat.epoch << " packet_sequence=" << heartbeat.sequence
            << " last_ack_before=" << before.lastAckNs << " last_ack_after=" << after.lastAckNs
            << " missed_before=" << before.missed << " missed_after=" << after.missed
            << " outstanding_before=" << before.outstanding << " outstanding_after=" << after.outstanding
            << " epoch_before=" << before.epoch << " epoch_after=" << after.epoch << std::endl;
    };
    const auto reject = [&](const char *reason) {
        ++ws21_heartbeat_rejected;
        auditAck(false, reason);
        return true;
    };
    PppHeader ppp;
    Ipv4Header ipv4;
    if (p->GetSize() < ppp.GetSerializedSize() + ipv4.GetSerializedSize()) {
        return reject("short_header");
    }
    Ptr<Packet> copy = p->Copy();
    copy->RemoveHeader(ppp);
    copy->RemoveHeader(ipv4);
    if (ipv4.GetPayloadSize() == (ws29_arm >= 0 ? 38U : 26U) &&
        ws21_feedback_enabled)
        return false;  // Existing multi-hop STATE report.
    if (ipv4.GetPayloadSize() != Ws21HeartbeatHeader::SERIALIZED_SIZE ||
        copy->GetSize() != Ws21HeartbeatHeader::SERIALIZED_SIZE) {
        return reject("wire_size");
    }
    copy->RemoveHeader(heartbeat);
    const auto peer = Ws21Peer(device);
    if (!heartbeat.IsValid() || peer.nodeType != 1 ||
        ipv4.GetSource().Get() != peer.nodeId + 1 ||
        ipv4.GetDestination().Get() != m_id + 1 ||
        ch.sip != ipv4.GetSource().Get() || ch.dip != ipv4.GetDestination().Get()) {
        return reject("peer_or_header");
    }
    const uint64_t nowNs = Simulator::Now().GetNanoSeconds();
    const bool inFaultWindow = ws21_heartbeat_fault_mode &&
        nowNs >= ws21_heartbeat_fault_start_ns &&
        nowNs < ws21_heartbeat_fault_end_ns;
    const bool ws29Single = ws29_arm >= 0 && (ws29_fault == 1 || ws29_fault == 2) &&
        nowNs >= ws29_fault_start && nowNs < ws29_fault_end &&
        !ws29_counts["fault_injected"];
    if (ws29Single &&
        ((ws29_fault == 1 && heartbeat.type == Ws21HeartbeatHeader::HELLO &&
          peer.nodeId == ws29_fault_tor && peer.port == ws29_fault_port) ||
         (ws29_fault == 2 && heartbeat.type == Ws21HeartbeatHeader::ACK &&
          m_id == ws29_fault_tor && port == ws29_fault_port))) {
        ++ws29_counts["fault_injected"];
        ++ws21_heartbeat_injected_drops;
        RecordWs21HeartbeatEvent(ws29_fault_tor, ws29_fault_port,
            ws29_fault == 1 ? "single_drop_hello" : "single_drop_ack",
            heartbeat.epoch, heartbeat.sequence);
        return true;
    }
    if (heartbeat.type == Ws21HeartbeatHeader::HELLO) {
        if (inFaultWindow && ws21_heartbeat_fault_mode == 1 &&
            peer.nodeId == ws21_heartbeat_fault_tor &&
            (ws21_heartbeat_fault_port == 0 ||
             peer.port == ws21_heartbeat_fault_port)) {
            ++ws21_heartbeat_injected_drops;
            RecordWs21HeartbeatEvent(peer.nodeId, peer.port, "drop_hello", heartbeat.epoch,
                                     heartbeat.sequence);
            return true;
        }
        ++ws21_heartbeat_hello_received;
        if (ws29_arm >= 0 && Ws29Row()) std::cout << "WS29_HELLO time_ns=" << nowNs
            << " switch=" << m_id << " port=" << port << " epoch=" << heartbeat.epoch
            << " sequence=" << heartbeat.sequence << std::endl;
        if (!SendWs21Heartbeat(port, Ws21HeartbeatHeader::ACK,
                               heartbeat.epoch, heartbeat.sequence)) {
            ++ws21_heartbeat_hop_rejects;
            if (ws29_arm >= 0) {
                ++ws29_counts["ack_unsent_packets"];
                if (Ws29Row()) std::cout << "WS29_CONTROL_UNSENT time_ns=" << nowNs
                    << " switch=" << m_id << " port=" << port << " type=ack reason=unavailable bytes=0" << std::endl;
            }
        }
        return true;
    }
    if (inFaultWindow && ws21_heartbeat_fault_mode == 2 &&
        m_id == ws21_heartbeat_fault_tor &&
        (ws21_heartbeat_fault_port == 0 || port == ws21_heartbeat_fault_port)) {
        ++ws21_heartbeat_injected_drops;
        RecordWs21HeartbeatEvent(m_id, port, "drop_ack", heartbeat.epoch,
                                 heartbeat.sequence);
        return true;
    }
    auto found = m_ws21HeartbeatPorts.find(port);
    if (!m_isToR || found == m_ws21HeartbeatPorts.end() || !found->second.active ||
        found->second.epoch != heartbeat.epoch ||
        found->second.outstanding != heartbeat.sequence ||
        !m_devices[port]->IsLinkUp()) {
        return reject("session_or_sequence_or_link");
    }
    Ws21HeartbeatPort &state = found->second;
    const uint64_t rttNs = nowNs - state.sentNs;
    state.lastAckNs = nowNs;
    ws21_heartbeat_ack_rtt_sum_ns += rttNs;
    ws21_heartbeat_ack_rtt_max_ns = std::max(ws21_heartbeat_ack_rtt_max_ns, rttNs);
    state.outstanding = 0;
    state.missed = 0;
    if (state.unknown) {
        state.unknown = false;
        ++ws21_heartbeat_recovered;
        RecordWs21HeartbeatEvent(m_id, port, "recovered", heartbeat.epoch,
                                 heartbeat.sequence);
    }
    ++ws21_heartbeat_ack_received;
    auditAck(true, "current_probe");
    if (ws29_arm >= 0 && Ws29Row())
        std::cout << "WS29_ACK time_ns=" << nowNs << " switch=" << m_id
                  << " port=" << port << " epoch=" << heartbeat.epoch
                  << " sequence=" << heartbeat.sequence << " rtt_ns=" << rttNs << std::endl;
    return true;
}

void SwitchNode::Ws29LinkState(uint32_t port, bool up) {
    NS_ASSERT_MSG(ws29_arm >= 0 && port > 0 && port < m_devices.size(), "invalid link target");
    Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[port]);
    NS_ASSERT_MSG(dev && Ws21Peer(dev).nodeType == 1, "switch-switch faults only");
    if (up) dev->Ws29BringUp();
    else dev->Ws29TakeDown();
    // No route recomputation: this experiment changes the directly attached link.
    // All arms filter live physical ports and invalidate cached QPs identically.
    for (auto it = m_ws21Feedback.begin(); it != m_ws21Feedback.end(); ) {
        if (it->first.second == port) it = m_ws21Feedback.erase(it);
        else ++it;
    }
    auto h = m_ws21HeartbeatPorts.find(port);
    if (h != m_ws21HeartbeatPorts.end()) {
        const bool wasActive = h->second.active;
        h->second.active = false;
        if (wasActive) --ws21_heartbeat_active;
        h->second.lastAckNs = 0;
        h->second.outstanding = 0;
        h->second.unknown = !up;
        if (up) TouchWs21Heartbeat(port);
    }
    if (Ws29Row()) std::cout << "WS29_LINK time_ns=" << Simulator::Now().GetNanoSeconds()
        << " switch=" << m_id << " port=" << port << " up=" << int(up) << std::endl;
}

void SwitchNode::Ws29Fault(uint32_t fault, uint32_t port) {
    NS_ASSERT_MSG(ws29_arm >= 0, "WS-29 faults are disabled for historical runs");
    if (fault == 23 || fault == 24) {
        for (uint32_t i = 1; i < m_devices.size(); ++i)
            if (!m_ws21HostPorts.count(i)) Ws29Fault(fault == 23 ? 21 : 22, i);
        return;
    }
    if (fault == 20 || fault == 21 || fault == 22) {
        Ptr<NetDevice> dev = m_devices.at(port);
        const auto peer = Ws21Peer(dev);
        Ptr<Channel> channel = dev->GetChannel();
        Ptr<SwitchNode> other;
        for (uint32_t i = 0; i < channel->GetNDevices(); ++i)
            if (channel->GetDevice(i) != dev)
                other = DynamicCast<SwitchNode>(channel->GetDevice(i)->GetNode());
        NS_ASSERT_MSG(other, "missing switch neighbor");
        Ws29LinkState(port, fault == 22);
        other->Ws29LinkState(peer.port, fault == 22);
        ++ws29_counts["physical_link_events"];
        return;
    }
    if (fault == 9) { RestartWs29Session(); ++ws29_counts["session_restart_injected"]; return; }
    if (fault == 11) {
        for (auto &item : m_ws21FeedbackSequence)
            item.second = std::numeric_limits<uint32_t>::max();
        ++ws29_counts["state_sequence_boundary_injected"];
        return;
    }
    if (fault == 10) {
        NS_ASSERT_MSG(!m_ws21Feedback.empty(), "old STATE test needs an actual cached report");
        const auto key = m_ws21Feedback.begin()->first;
        const auto previous = m_ws21Feedback.begin()->second;
        uint32_t sourceHost = 0, remoteHost = 0;
        bool haveSource = false, haveRemote = false;
        for (const auto &host : ws21_host_tor) {
            if (host.second == m_id) { sourceHost = host.first; haveSource = true; }
            if (host.second == key.first) { remoteHost = host.first; haveRemote = true; }
        }
        NS_ASSERT_MSG(haveSource && haveRemote && previous.session < UINT32_MAX,
                      "STATE test identity/session missing");
        const auto inject = [&](uint32_t session, uint32_t sequence) {
            Ws21FeedbackHeader h; h.version = 3; h.session = session; h.sequence = sequence;
            h.candidatePort = key.second; h.samplePackets = 1; h.cePackets = 0;
            h.windowStartNs = h.windowEndNs = Simulator::Now().GetNanoSeconds();
            Ptr<Packet> p = Create<Packet>(); p->AddHeader(h);
            Ipv4Header ip; ip.SetSource(Ipv4Address(remoteHost));
            ip.SetDestination(Ipv4Address(sourceHost)); ip.SetProtocol(Ws21FeedbackHeader::IP_PROTOCOL);
            ip.SetTtl(64); ip.SetPayloadSize(p->GetSize()); p->AddHeader(ip);
            PppHeader ppp; ppp.SetProtocol(0x0021); p->AddHeader(ppp);
            CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
            p->PeekHeader(ch); ReceiveWs21Feedback(p, ch);
        };
        const uint64_t before = ws21_feedback_rejected;
        inject(previous.session + 1, 1);
        inject(previous.session, previous.sequence);
        ++ws29_counts["synthetic_state_test"];
        if (Ws29Row()) std::cout << "WS29_SYNTHETIC time_ns=" << Simulator::Now().GetNanoSeconds()
            << " fault=10 rejected_delta=" << ws21_feedback_rejected - before << std::endl;
        return;
    }
    if (fault >= 15 && fault <= 17) {
        // Explicit oracle injection is ONLY permitted in labelled state-machine cells.
        // The runner must reject these fault modes in any natural-demand effect cell.
        const uint64_t now = Simulator::Now().GetNanoSeconds();
        for (const auto &route : m_rtTable) {
            auto dest = ws21_host_tor.find(route.first);
            if (dest == ws21_host_tor.end() || dest->second == m_id) continue;
            for (size_t i = 0; i < route.second.size(); ++i) {
                const uint32_t candidate = route.second[i];
                auto key = std::make_pair(dest->second, candidate);
                if (fault == 17) { m_ws21Feedback.erase(key); continue; }
                Ws21FeedbackState &s = m_ws21Feedback[key];
                s.session = 1; s.sequence = 1; s.samplePackets = 10;
                s.cePackets = i % 2 ? 0 : 10;
                s.windowStartNs = s.windowEndNs = fault == 16 ? now - 20001 : now;
                s.generatedNs = s.windowEndNs;
                TouchWs21Heartbeat(candidate);
                auto &h = m_ws21HeartbeatPorts[candidate];
                h.lastAckNs = now; h.unknown = false;
            }
        }
        ++ws29_counts["synthetic_state_test"];
        if (Ws29Row()) std::cout << "WS29_SYNTHETIC time_ns=" << now
            << " fault=" << fault << " switch=" << m_id << std::endl;
        return;
    }
    if (fault < 3 || fault > 8 || ws29_counts["fault_injected"]) return;
    auto found = m_ws21HeartbeatPorts.find(port);
    if (found == m_ws21HeartbeatPorts.end() || !found->second.outstanding) return;
    Ws21HeartbeatHeader h;
    h.type = Ws21HeartbeatHeader::ACK;
    h.epoch = found->second.epoch;
    h.sequence = found->second.outstanding;
    const auto peer = Ws21Peer(m_devices[port]);
    const auto inject = [&](uint32_t ingress, uint32_t sender) {
        Ptr<Packet> packet = Create<Packet>();
        packet->AddHeader(h);
        Ipv4Header ip;
        ip.SetSource(Ipv4Address(sender)); ip.SetDestination(Ipv4Address(m_id + 1));
        ip.SetProtocol(Ws21FeedbackHeader::IP_PROTOCOL); ip.SetTtl(1);
        ip.SetPayloadSize(packet->GetSize()); packet->AddHeader(ip);
        PppHeader ppp; ppp.SetProtocol(0x0021); packet->AddHeader(ppp);
        CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
        packet->PeekHeader(ch);
        ReceiveWs21Heartbeat(m_devices[ingress], packet, ch);
    };
    const uint64_t rejected = ws21_heartbeat_rejected;
    const uint64_t accepted = ws21_heartbeat_ack_received;
    const uint32_t outstanding = found->second.outstanding;
    if (fault == 3) {
        NS_ASSERT_MSG(outstanding > 1, "old-sequence test requires a real earlier probe");
        h.sequence = outstanding - 1;
    }
    if (fault == 4) { inject(port, peer.nodeId + 1); } // then duplicate the accepted ACK
    if (fault == 5) { ++h.sequence; } // out-of-order future reply cannot confirm current probe
    if (fault == 8) {
        // Replay a valid old-session reply after a real local session restart.
        RestartWs29Session();
    }
    uint32_t ingress = port;
    if (fault == 7) {
        for (uint32_t i = 1; i < m_devices.size(); ++i)
            if (i != port && !m_ws21HostPorts.count(i)) { ingress = i; break; }
        NS_ASSERT_MSG(ingress != port, "wrong-port test needs a second switch uplink");
    }
    const Ws21HeartbeatPort beforeInvalid = found->second;
    inject(ingress, fault == 6 ? peer.nodeId + 2 : peer.nodeId + 1);
    const Ws21HeartbeatPort afterInvalid = found->second;
    ++ws29_counts["fault_injected"];
    if (Ws29Row()) std::cout << "WS29_ACK_INJECT time_ns=" << Simulator::Now().GetNanoSeconds()
        << " fault=" << fault << " switch=" << m_id << " port=" << port
        << " rejected_delta=" << ws21_heartbeat_rejected - rejected
        << " accepted_delta=" << ws21_heartbeat_ack_received - accepted
        << " outstanding_before=" << outstanding
        << " outstanding_after=" << found->second.outstanding
        << " invalid_last_ack_before=" << beforeInvalid.lastAckNs << " invalid_last_ack_after=" << afterInvalid.lastAckNs
        << " invalid_missed_before=" << beforeInvalid.missed << " invalid_missed_after=" << afterInvalid.missed
        << " invalid_outstanding_before=" << beforeInvalid.outstanding << " invalid_outstanding_after=" << afterInvalid.outstanding
        << " invalid_epoch_before=" << beforeInvalid.epoch << " invalid_epoch_after=" << afterInvalid.epoch << std::endl;
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
    if (ws29_arm >= 0) {
        std::cout << "WS29_SUMMARY arm=" << ws29_arm << " rows=" << ws29_rows
                  << " overflow=" << ws29_overflow << std::endl;
        for (const auto &item : ws29_counts)
            std::cout << "WS29_COUNT name=" << item.first << " count=" << item.second << std::endl;
    }
    if (ws21_heartbeat_enabled)
        std::cout << "WS21_HEARTBEAT hello_generated=" << ws21_heartbeat_hello_generated
                  << " ack_generated=" << ws21_heartbeat_ack_generated
                  << " hello_received=" << ws21_heartbeat_hello_received
                  << " ack_received=" << ws21_heartbeat_ack_received
                  << " ack_rtt_sum_ns=" << ws21_heartbeat_ack_rtt_sum_ns
                  << " ack_rtt_max_ns=" << ws21_heartbeat_ack_rtt_max_ns
                  << " rejected=" << ws21_heartbeat_rejected
                  << " injected_drops=" << ws21_heartbeat_injected_drops
                  << " timeouts=" << ws21_heartbeat_timeouts
                  << " unknown=" << ws21_heartbeat_unknown
                  << " recovered=" << ws21_heartbeat_recovered
                  << " activations=" << ws21_heartbeat_activations
                  << " deactivations=" << ws21_heartbeat_deactivations
                  << " active=" << ws21_heartbeat_active
                  << " active_peak=" << ws21_heartbeat_active_peak
                  << " event_rows=" << ws21_heartbeat_event_rows
                  << " event_overflow=" << ws21_heartbeat_event_overflow
                  << " hop_enqueues=" << ws21_heartbeat_hop_enqueues
                  << " hop_dequeues=" << ws21_heartbeat_hop_dequeues
                  << " hop_rejects=" << ws21_heartbeat_hop_rejects
                  << " hop_bytes=" << ws21_heartbeat_hop_bytes
                  << " hello_hop_bytes=" << ws21_heartbeat_hello_hop_bytes
                  << " ack_hop_bytes=" << ws21_heartbeat_ack_hop_bytes << std::endl;
    if (Ws21FeedbackEnabled())
        std::cout << "WS21_FEEDBACK generated=" << ws21_feedback_generated
                  << " delivered=" << ws21_feedback_delivered
                  << " rejected=" << ws21_feedback_rejected
                  << " expired=" << ws21_feedback_expired
                  << " delivered_bytes=" << ws21_feedback_bytes
                  << " age_sum_ns=" << ws21_feedback_age_sum_ns
                  << " age_max_ns=" << ws21_feedback_age_max_ns
                  << " sample_age_sum_ns=" << ws21_feedback_sample_age_sum_ns
                  << " sample_age_max_ns=" << ws21_feedback_sample_age_max_ns
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
    if (Ws13DiagnosticEnabled() || Ws25DiagnosticEnabled()) {
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
    if (Settings::lb_mode == 23 || Settings::lb_mode == 24) {
        for (const auto &entry : guard_queue_stats) {
            const GuardQueueStat &s = entry.second;
            if (s.enqueued != s.dequeued + s.queuedDropped + s.current)
                ++guard_queue_violations;
        }
        std::cout << "WS27_GUARD mode=" << Settings::lb_mode
                  << " moe_packets=" << ws27_moe_packets
                  << " new_flows=" << ws27_new_flows
                  << " reused_packets=" << ws27_reused_packets
                  << " two_candidates=" << ws27_two_candidates
                  << " scored=" << ws27_scored
                  << " diverted=" << ws27_diverted
                  << " gate_activations=" << ws27_gate_activations
                  << " gate_exits=" << ws27_gate_exits
                  << " fallback_packets=" << ws27_fallback_packets
                  << " queue_violations=" << guard_queue_violations << std::endl;
        NS_ASSERT_MSG(guard_queue_violations == 0, "WS27 queue counters do not conserve bytes");
    }
    if (ClassReserveFamilyMode() || Settings::lb_mode == 22) {
        uint64_t enqueued = 0, dequeued = 0, queuedDropped = 0, current = 0;
        for (const auto &entry : guard_queue_stats) {
            const GuardQueueStat &s = entry.second;
            enqueued += s.enqueued;
            dequeued += s.dequeued;
            queuedDropped += s.queuedDropped;
            current += s.current;
            if (s.enqueued != s.dequeued + s.queuedDropped + s.current)
                ++guard_queue_violations;
        }
        if (ClassReserveFamilyMode()) {
            std::cout << "WS25_CLASSRESERVE moe_packets=" << classreserve_moe_packets
                      << " background_packets=" << classreserve_background_packets
                      << " moe_two_choices=" << classreserve_moe_two_choices
                      << " moe_diverted=" << classreserve_moe_diverted
                      << " moe_flow_new=" << classreserve_moe_flow_new
                      << " moe_flow_reused=" << classreserve_moe_flow_reused
                      << " fallback_packets=" << classreserve_fallback_packets
                      << " background_new_flows=" << classreserve_background_new_flows
                      << " background_reused=" << classreserve_background_reused
                      << " background_queue_avoids=" << classreserve_background_queue_avoids
                      << " queue_violations=" << guard_queue_violations << std::endl;
            std::cout << "WS28_FACTOR mode=" << Settings::lb_mode
                      << " background_weight=" << int(ClassReserveBackgroundWeight())
                      << " background_routing=" << int(ClassReserveBackgroundRouting())
                      << std::endl;
        } else {
            std::cout << "WS25_DESTSPREAD moe_packets=" << destspread_moe_packets
                      << " background_packets=" << destspread_background_packets
                      << " background_new=" << destspread_background_new
                      << " background_reused=" << destspread_background_reused
                      << " moe_new=" << destspread_moe_new
                      << " moe_reused=" << destspread_moe_reused
                      << " background_ties=" << destspread_background_ties
                      << " background_all_empty=" << destspread_background_all_empty
                      << " fallback_packets=" << destspread_fallback_packets
                      << " queue_violations=" << guard_queue_violations << std::endl;
        }
        std::cout << "WS25_QUEUE enqueued=" << enqueued << " dequeued=" << dequeued
                  << " queued_drop=" << queuedDropped << " current=" << current << std::endl;
        if (ClassReserveFamilyMode() && Ws25DiagnosticEnabled()) {
            for (uint32_t tag = 1; tag <= 2; ++tag)
                std::cout << "WS25_CHOICE tag=" << tag
                          << " events=" << ws25_choice_events[tag]
                          << " both_queues_empty=" << ws25_empty_choices[tag]
                          << " first_queue_sum=" << ws25_first_queue_sum[tag]
                          << " second_queue_sum=" << ws25_second_queue_sum[tag]
                          << " background_queue_nonzero="
                          << (tag == 2 ? ws25_background_queue_nonzero : 0) << std::endl;
        }
        if (ClassReserveFamilyMode()) {
            for (const auto &entry : classreserve_source_port_packets)
                std::cout << "WS25_PORT switch=" << std::get<0>(entry.first)
                          << " port=" << std::get<1>(entry.first)
                          << " tag=" << std::get<2>(entry.first)
                          << " packets=" << entry.second << std::endl;
        } else {
            for (const auto &entry : destspread_source_port_packets)
                std::cout << "WS25_DESTSPREAD_PORT switch=" << std::get<0>(entry.first)
                          << " port=" << std::get<1>(entry.first)
                          << " tag=" << std::get<2>(entry.first)
                          << " packets=" << entry.second << std::endl;
        }
        NS_ASSERT_MSG(guard_queue_violations == 0, "WS-25 queue counters do not conserve bytes");
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
    const uint32_t chosen = nexthops[idx];
    const int ws28Target = Ws28TailTargetIndex(ch);
    if (Settings::lb_mode == 0 && ws28Target >= 0 && m_isToR &&
        m_isToR_hostIP.count(ch.sip) && Ws28TailReserveRow()) {
        std::cout << "WS28_TAIL_CHOICE seed=" << ws28_tail_targets[ws28Target].seed
                  << " target=" << ws28Target
                  << " time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " switch=" << m_id << " chosen=" << chosen
                  << " uid=" << p->GetUid() << std::endl;
    }
    return chosen;
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

static bool Ws25DiagnosticEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS25_DIAG");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

// WS-25 v1 corrected candidate: long background flows and short MoE flows each
// keep one path at each switch.  A new MoE flow uses two deterministic
// candidates, counting queued background bytes twice.  This sees only the
// local egress queue; it cannot avoid the unique destination-host port or infer
// downstream congestion.
uint32_t SwitchNode::ChooseWs29Feedback(const CustomHeader &ch, uint32_t first,
                                        uint32_t second, uint32_t local, bool background) {
    const uint64_t now = Simulator::Now().GetNanoSeconds();
    auto destination = ws21_host_tor.find(ch.dip);
    if (destination == ws21_host_tor.end() || destination->second == m_id) return local;
    const uint32_t tor = destination->second;
    const auto a = m_ws21Feedback.find(std::make_pair(tor, first));
    const auto b = m_ws21Feedback.find(std::make_pair(tor, second));
    const Ws21FeedbackState empty;
    const auto &sa = a == m_ws21Feedback.end() ? empty : a->second;
    const auto &sb = b == m_ws21Feedback.end() ? empty : b->second;
    const auto valid = [&](uint32_t port, const Ws21FeedbackState &s) -> std::string {
        if (!s.samplePackets) return "no_sample";
        if (s.windowEndNs > now || now - s.windowEndNs > 20000) return "stale";
        if (s.windowStartNs < m_ws29RestartNs) return "old_session";
        if (!m_devices[port]->IsLinkUp()) return "link_down";
        auto hb = m_ws21HeartbeatPorts.find(port);
        if (hb == m_ws21HeartbeatPorts.end() || !hb->second.active ||
            !hb->second.lastAckNs) return "unconfirmed";
        if (hb->second.unknown) return "unknown";
        if (now - hb->second.lastAckNs > 4ULL * ws21_heartbeat_interval_ns) return "hb_stale";
        return "valid";
    };
    const std::string va = valid(first, sa), vb = valid(second, sb);
    std::string reason = "off";
    uint32_t proposed = local;
    bool eligible = false;
    if (ws29_arm == 1 || ws29_arm == 2) {
        if (first == second) reason = "same_candidate";
        else if (va != "valid") reason = "a_" + va;
        else if (vb != "valid") reason = "b_" + vb;
        else {
            eligible = true;
            const uint64_t ca = uint64_t(sa.cePackets) * sb.samplePackets;
            const uint64_t cb = uint64_t(sb.cePackets) * sa.samplePackets;
            reason = ca == cb ? "equal_ce" : "distinct_ce";
            if (ca != cb) proposed = ca < cb ? first : second;
        }
    }
    const uint32_t chosen = ws29_arm == 2 ? proposed : local;
    ++ws29_counts["decisions"];
    ++ws29_counts[reason];
    if (eligible) ++ws29_counts["two_fresh"];
    if (proposed != local) ++ws29_counts["would_change"];
    if (chosen != local) ++ws29_counts["adopted_changed"];
    if (Ws29Row())
        std::cout << "WS29_DECISION time_ns=" << now << " switch=" << m_id
                  << " src=" << Settings::hostIp2IdMap.at(ch.sip)
                  << " dst=" << Settings::hostIp2IdMap.at(ch.dip)
                  << " sport=" << ch.udp.sport << " dport=" << ch.udp.dport
                  << " tag=" << (background ? 1 : 2) << " first=" << first
                  << " second=" << second << " local=" << local << " chosen=" << chosen
                  << " proposed=" << proposed << " reason=" << reason
                  << " a_status=" << va << " b_status=" << vb
                  << " a_session=" << sa.session << " b_session=" << sb.session
                  << " a_sequence=" << sa.sequence << " b_sequence=" << sb.sequence
                  << " a_start=" << sa.windowStartNs << " a_end=" << sa.windowEndNs
                  << " b_start=" << sb.windowStartNs << " b_end=" << sb.windowEndNs
                  << " a_ce=" << sa.cePackets << " a_samples=" << sa.samplePackets
                  << " b_ce=" << sb.cePackets << " b_samples=" << sb.samplePackets << std::endl;
    return chosen;
}

uint32_t SwitchNode::DoLbClassReserve(Ptr<const Packet> p, const CustomHeader &ch,
                                      const std::vector<int> &nexthops) {
    WorkloadTag label;
    if (ch.l3Prot != 0x11 || !p->PeekPacketTag(label) ||
        (label.GetValue() != 1 && label.GetValue() != 2)) {
        ++classreserve_fallback_packets;
        return DoLbFlowECMP(p, ch, nexthops);
    }

    const uint32_t flowKey[3] = {ch.sip, ch.dip,
        uint32_t(ch.udp.sport) | (uint32_t(ch.udp.dport) << 16)};
    const uint32_t packetKey[4] = {flowKey[0], flowKey[1], flowKey[2], ch.udp.seq};
    const bool background = label.GetValue() == 1;
    const uint8_t *key = reinterpret_cast<const uint8_t *>(background ? flowKey : packetKey);
    const size_t keyBytes = background ? sizeof(flowKey) : sizeof(packetKey);
    const uint32_t first = nexthops[EcmpHash(key, keyBytes, m_ecmpSeed) % nexthops.size()];
    const auto flow = std::make_tuple(ch.sip, ch.dip, ch.udp.sport, ch.udp.dport);
    if (background) {
        ++classreserve_background_packets;
        auto it = m_classReserveBackgroundPort.find(flow);
        if (ws29_arm >= 0 && it != m_classReserveBackgroundPort.end() &&
            std::find(nexthops.begin(), nexthops.end(), it->second) == nexthops.end()) {
            m_classReserveBackgroundPort.erase(it);
            it = m_classReserveBackgroundPort.end();
            ++ws29_counts["qp_invalidated"];
        }
        if (it != m_classReserveBackgroundPort.end()) {
            ++classreserve_background_reused;
            if (m_isToR && m_isToR_hostIP.count(ch.sip))
                ++classreserve_source_port_packets[std::make_tuple(m_id, it->second, 1U)];
            return it->second;
        }
    } else {
        ++classreserve_moe_packets;
        auto it = m_classReserveMoePort.find(flow);
        if (ws29_arm >= 0 && it != m_classReserveMoePort.end() &&
            std::find(nexthops.begin(), nexthops.end(), it->second) == nexthops.end()) {
            m_classReserveMoePort.erase(it);
            it = m_classReserveMoePort.end();
            ++ws29_counts["qp_invalidated"];
        }
        if (it != m_classReserveMoePort.end()) {
            ++classreserve_moe_flow_reused;
            if (m_isToR && m_isToR_hostIP.count(ch.sip))
                ++classreserve_source_port_packets[std::make_tuple(m_id, it->second, 2U)];
            return it->second;
        }
        ++classreserve_moe_flow_new;
    }
    uint32_t chosen = first;
    uint32_t second = first;
    uint64_t firstQueue = 0, secondQueue = 0;
    uint64_t firstBackground = 0, secondBackground = 0;
    if (nexthops.size() > 1) {
        second = nexthops[EcmpHash(key, keyBytes,
            m_ecmpSeed ^ 0x9e3779b9U) % nexthops.size()];
        if (second != first) {
            firstQueue = CalculateInterfaceLoad(first);
            secondQueue = CalculateInterfaceLoad(second);
            if (Ws25DiagnosticEnabled()) {
                const uint32_t tag = background ? 1 : 2;
                ++ws25_choice_events[tag];
                if (firstQueue == 0 && secondQueue == 0) ++ws25_empty_choices[tag];
                ws25_first_queue_sum[tag] += firstQueue;
                ws25_second_queue_sum[tag] += secondQueue;
            }
            if (background) {
                if (ClassReserveBackgroundRouting() && secondQueue < firstQueue) {
                    chosen = second;
                    ++classreserve_background_queue_avoids;
                }
            } else {
                ++classreserve_moe_two_choices;
                const auto a = guard_queue_stats.find(std::make_tuple(m_id, first, 1));
                const auto b = guard_queue_stats.find(std::make_tuple(m_id, second, 1));
                firstBackground = a == guard_queue_stats.end() ? 0 : a->second.current;
                secondBackground = b == guard_queue_stats.end() ? 0 : b->second.current;
                if (Ws25DiagnosticEnabled() && (firstBackground || secondBackground))
                    ++ws25_background_queue_nonzero;
                const uint64_t firstScore = firstQueue +
                    (ClassReserveBackgroundWeight() ? firstBackground : 0);
                const uint64_t secondScore = secondQueue +
                    (ClassReserveBackgroundWeight() ? secondBackground : 0);
                if (secondScore < firstScore) {
                    chosen = second;
                    ++classreserve_moe_diverted;
                }
            }
        }
    }
    if (ws29_arm >= 0 && m_isToR && m_isToR_hostIP.count(ch.sip))
        chosen = ChooseWs29Feedback(ch, first, second, chosen, background);
    const int ws28Target = Ws28TailTargetIndex(ch);
    if (!background && ws28Target >= 0 && m_isToR && m_isToR_hostIP.count(ch.sip) &&
        Ws28TailReserveRow()) {
        std::cout << "WS28_TAIL_CHOICE seed=" << ws28_tail_targets[ws28Target].seed
                  << " target=" << ws28Target
                  << " time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " switch=" << m_id << " first=" << first
                  << " second=" << second << " chosen=" << chosen
                  << " first_queue=" << firstQueue
                  << " second_queue=" << secondQueue
                  << " first_background=" << firstBackground
                  << " second_background=" << secondBackground << std::endl;
    }
    if (background) {
        m_classReserveBackgroundPort[flow] = chosen;
        ++classreserve_background_new_flows;
    } else {
        m_classReserveMoePort[flow] = chosen;
    }
    if (m_isToR && m_isToR_hostIP.count(ch.sip))
        ++classreserve_source_port_packets[std::make_tuple(m_id, chosen,
                                                            background ? 1U : 2U)];
    return chosen;
}

// WS-25 v2 diagnostic correction. A MoE QP uses the existing DRILL decision
// only for its first packet at this switch, then retains that next hop. A
// background flow also chooses once and keeps its next hop at this switch.
// When instantaneous egress queues tie, rotate assignments for this
// destination instead of letting a fixed hash choose every long flow.
uint32_t SwitchNode::DoLbDestSpread(Ptr<const Packet> p, const CustomHeader &ch,
                                    const std::vector<int> &nexthops) {
    WorkloadTag label;
    if (ch.l3Prot != 0x11 || !p->PeekPacketTag(label) ||
        (label.GetValue() != 1 && label.GetValue() != 2)) {
        ++destspread_fallback_packets;
        return DoLbFlowECMP(p, ch, nexthops);
    }
    if (label.GetValue() == 2) {
        ++destspread_moe_packets;
        const auto flow = std::make_tuple(ch.sip, ch.dip, ch.udp.sport, ch.udp.dport);
        auto cached = m_destSpreadMoePort.find(flow);
        uint32_t chosen;
        if (cached != m_destSpreadMoePort.end()) {
            ++destspread_moe_reused;
            chosen = cached->second;
        } else {
            ++destspread_moe_new;
            chosen = DoLbDrill(p, ch, nexthops);
            m_destSpreadMoePort[flow] = chosen;
        }
        if (m_isToR && m_isToR_hostIP.count(ch.sip))
            ++destspread_source_port_packets[std::make_tuple(m_id, chosen, 2U)];
        return chosen;
    }

    ++destspread_background_packets;
    const auto flow = std::make_tuple(ch.sip, ch.dip, ch.udp.sport, ch.udp.dport);
    auto cached = m_destSpreadBackgroundPort.find(flow);
    if (cached != m_destSpreadBackgroundPort.end()) {
        ++destspread_background_reused;
        if (m_isToR && m_isToR_hostIP.count(ch.sip))
            ++destspread_source_port_packets[std::make_tuple(m_id, cached->second, 1U)];
        return cached->second;
    }
    NS_ASSERT_MSG(!nexthops.empty(), "DestSpread has no next hop");
    ++destspread_background_new;
    uint32_t minimum = std::numeric_limits<uint32_t>::max();
    std::vector<uint32_t> tied;
    for (int port : nexthops) {
        const uint32_t load = CalculateInterfaceLoad(port);
        if (load < minimum) {
            minimum = load;
            tied.clear();
        }
        if (load == minimum) tied.push_back(port);
    }
    std::sort(tied.begin(), tied.end());
    uint32_t chosen = tied.front();
    if (tied.size() > 1) {
        ++destspread_background_ties;
        if (minimum == 0 && tied.size() == nexthops.size())
            ++destspread_background_all_empty;
        uint32_t &turn = m_destSpreadNextByDestination[ch.dip];
        chosen = tied[turn % tied.size()];
        ++turn;
    }
    m_destSpreadBackgroundPort[flow] = chosen;
    if (m_isToR && m_isToR_hostIP.count(ch.sip))
        ++destspread_source_port_packets[std::make_tuple(m_id, chosen, 1U)];
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

// WS-27 keeps GuardHash scoring and HarmGate hysteresis, but pins each MoE
// QP to its first selected next hop at this switch. Modes 14/15 stay intact.
uint32_t SwitchNode::DoLbWs27Guard(Ptr<const Packet> p, const CustomHeader &ch,
                                   const std::vector<int> &nexthops) {
    WorkloadTag label;
    if (ch.l3Prot != 0x11 || !p->PeekPacketTag(label) || label.GetValue() != 2) {
        ++ws27_fallback_packets;
        return DoLbFlowECMP(p, ch, nexthops);
    }
    ++ws27_moe_packets;
    const auto flow = std::make_tuple(ch.sip, ch.dip, ch.udp.sport, ch.udp.dport);
    auto cached = m_ws27MoePort.find(flow);
    if (cached != m_ws27MoePort.end()) {
        ++ws27_reused_packets;
        return cached->second;
    }
    ++ws27_new_flows;
    NS_ASSERT_MSG(!nexthops.empty(), "WS27 has no next hop");
    const uint32_t key[4] = {ch.sip, ch.dip,
        uint32_t(ch.udp.sport) | (uint32_t(ch.udp.dport) << 16), ch.udp.seq};
    const uint32_t first = nexthops[EcmpHash(reinterpret_cast<const uint8_t *>(key),
                                            sizeof(key), m_ecmpSeed) % nexthops.size()];
    uint32_t chosen = first;
    if (nexthops.size() > 1) {
        const uint32_t second = nexthops[EcmpHash(reinterpret_cast<const uint8_t *>(key),
            sizeof(key), m_ecmpSeed ^ 0x9e3779b9U) % nexthops.size()];
        if (second != first) {
            ++ws27_two_candidates;
            const uint32_t qFirst = CalculateInterfaceLoad(first);
            const uint32_t qSecond = CalculateInterfaceLoad(second);
            bool score = true;
            if (Settings::lb_mode == 24) {
                const uint32_t low = std::min(first, second);
                const uint32_t high = std::max(first, second);
                const uint64_t pair = (uint64_t(low) << 32) | high;
                bool &active = m_ws27GateActive[pair];
                const uint32_t peak = std::max(qFirst, qSecond);
                if (!active && peak >= guard_on_bytes) {
                    active = true;
                    ++ws27_gate_activations;
                } else if (active && peak <= guard_off_bytes) {
                    active = false;
                    ++ws27_gate_exits;
                }
                score = active;
            }
            if (score) {
                ++ws27_scored;
                const auto a = guard_queue_stats.find(std::make_tuple(m_id, first, 1));
                const auto b = guard_queue_stats.find(std::make_tuple(m_id, second, 1));
                const uint64_t firstBackground = a == guard_queue_stats.end() ? 0 : a->second.current;
                const uint64_t secondBackground = b == guard_queue_stats.end() ? 0 : b->second.current;
                const uint64_t scoreFirst = uint64_t(qFirst) + uint64_t(guard_lambda) * firstBackground;
                const uint64_t scoreSecond = uint64_t(qSecond) + uint64_t(guard_lambda) * secondBackground;
                if (scoreSecond + guard_tau < scoreFirst) {
                    chosen = second;
                    ++ws27_diverted;
                }
            }
        }
    }
    m_ws27MoePort[flow] = chosen;
    return chosen;
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
    if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL &&
        ReceiveWs21Heartbeat(device, packet, ch)) return true;
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
        if (ws29_arm >= 0) { ++ws29_counts["no_route_drop"]; return -1; }
        assert(false);
    }

    // entry found
    std::vector<int> usable;
    if (ws29_arm >= 0) {
        for (int port : entry->second)
            if (port > 0 && uint32_t(port) < m_devices.size() && m_devices[port]->IsLinkUp())
                usable.push_back(port);
        if (usable.empty()) {
            ++ws29_counts["no_live_port_drop"];
            ws29_counts["no_live_port_drop_bytes"] += p->GetSize();
            if (Ws29Row()) std::cout << "WS29_DROP time_ns=" << Simulator::Now().GetNanoSeconds()
                << " switch=" << m_id << " reason=no_live_port bytes=" << p->GetSize() << std::endl;
            return -1;
        }
    }
    const auto &nexthops = ws29_arm >= 0 ? usable : entry->second;
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
            if (ch.l3Prot == 0x11 && m_isToR && m_isToR_hostIP.count(ch.sip)) {
                if (ws21_identity_enabled) ObserveWs21Source(ch, port);
                TouchWs21Heartbeat(port);
            }
            return port;
        }
        case 21:
        case 25:
        case 26:
        case 27:
        {
            const uint32_t port = DoLbClassReserve(p, ch, nexthops);
            if (ws29_arm >= 0 && ch.l3Prot == 0x11 && m_isToR && m_isToR_hostIP.count(ch.sip)) {
                ObserveWs21Source(ch, port);
                TouchWs21Heartbeat(port);
            }
            return port;
        }
        case 22:
            return DoLbDestSpread(p, ch, nexthops);
        case 23:
        case 24:
            return DoLbWs27Guard(p, ch, nexthops);
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
    const uint8_t heartbeatType = ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL &&
                                          ws21_heartbeat_enabled ?
                                      Ws21HeartbeatPacketType(p) : 0;
    const bool heartbeatPacket = heartbeatType != 0;
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
                Ws28TailAdmissionDrop(ch, m_id, outDev, p->GetUid(), "ingress");
#if (0)
                // /** NOTE: logging dropped pkts */
                // std::cout << "LostPkt ingress - Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
                //           << "L3Prot:" << ch.l3Prot
                //           << ",Size:" << p->GetSize()
                //           << ",At " << Simulator::Now() << std::endl;
#endif
                Settings::dropped_pkt_sw_ingress++;
                if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL) {
                    Ws29ControlEvent(p, m_id, outDev, "admission_reject");
                    if (heartbeatPacket) ++ws21_heartbeat_hop_rejects;
                    else ++ws21_feedback_hop_rejects;
                }
                if ((Settings::lb_mode >= 13 && Settings::lb_mode <= 15) || ClassReserveFamilyMode() || Settings::lb_mode == 22 || Settings::lb_mode == 23 || Settings::lb_mode == 24)
                    SwitchNotifyAdmissionDrop(outDev, p);
                return;  // drop
            }
        } else { /** DROP: At Egress */
            FactorialAdmissionDrop("egress", m_id, ch, inDev, outDev, p->GetSize());
            Ws28TailAdmissionDrop(ch, m_id, outDev, p->GetUid(), "egress");
#if (0)
            // /** NOTE: logging dropped pkts */
            // std::cout << "LostPkt egress - Sw(" << m_id << ")," << PARSE_FIVE_TUPLE(ch)
            //           << "L3Prot:" << ch.l3Prot << ",Size:" << p->GetSize() << ",At "
            //           << Simulator::Now() << std::endl;
#endif
            Settings::dropped_pkt_sw_egress++;
            if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL) {
                Ws29ControlEvent(p, m_id, outDev, "admission_reject");
                if (heartbeatPacket) ++ws21_heartbeat_hop_rejects;
                else ++ws21_feedback_hop_rejects;
            }
            if ((Settings::lb_mode >= 13 && Settings::lb_mode <= 15) || ClassReserveFamilyMode() || Settings::lb_mode == 22 || Settings::lb_mode == 23 || Settings::lb_mode == 24)
                SwitchNotifyAdmissionDrop(outDev, p);
            return;  // drop
        }

        if (!locallyGenerated) CheckAndSendPfc(inDev, qIndex);
    }

    if ((Ws13DiagnosticEnabled() || Ws25DiagnosticEnabled()) && ch.l3Prot == 0x11) {
        WorkloadTag tag;
        auto destination = Settings::hostIp2IdMap.find(ch.dip);
        auto source = Settings::hostIp2IdMap.find(ch.sip);
        if (p->PeekPacketTag(tag) && tag.GetValue() == 1 &&
            destination != Settings::hostIp2IdMap.end() &&
            (Ws25DiagnosticEnabled() || Settings::lb_mode == 20 || destination->second == 856 ||
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
    const int ws28Target = Ws28TailTargetIndex(ch);
    if (ws28Target >= 0) {
        Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[outDev]);
        NS_ASSERT_MSG(dev && dev->GetQueue(), "WS-28 target egress queue absent");
        const auto packetKey = std::make_pair(m_id, p->GetUid());
        NS_ASSERT_MSG(ws28_tail_queued.count(packetKey) == 0,
                      "WS-28 target packet already tracked at this switch");
        Ws28TailQueued item = {uint32_t(ws28Target), outDev, ch.udp.seq,
                               p->GetSize(), uint64_t(Simulator::Now().GetNanoSeconds()),
                               dev->GetQueue()->GetNBytesTotal(),
                               Ws28BackgroundQueueBytes(m_id, outDev)};
        ws28_tail_queued[packetKey] = item;
        if (Ws28TailReserveRow())
            std::cout << "WS28_TAIL_OFFER seed=" << ws28_tail_targets[ws28Target].seed
                      << " target=" << ws28Target << " time_ns=" << item.enqueueNs
                      << " switch=" << m_id << " port=" << outDev
                      << " qindex=" << qIndex << " uid=" << p->GetUid()
                      << " seq=" << item.seq << " bytes=" << item.bytes
                      << " queue_before=" << item.queueBytes
                      << " background_before=" << item.backgroundBytes
                      << " background_valid=" << int(ClassReserveFamilyMode())
                      << std::endl;
    }
    const bool accepted = m_devices[outDev]->SwitchSend(qIndex, p, ch);
    // ECMP does not invoke SwitchNotifyEnqueue; record its successful queue
    // acceptance here. A synchronous dequeue may already have been logged.
    if (accepted && ws28Target >= 0 && !ClassReserveFamilyMode() &&
        Ws28TailReserveRow())
        std::cout << "WS28_TAIL_ENQUEUE seed=" << ws28_tail_targets[ws28Target].seed
                  << " target=" << ws28Target
                  << " time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " switch=" << m_id << " port=" << outDev
                  << " uid=" << p->GetUid() << std::endl;
    if (!accepted && ws28Target >= 0) {
        ws28_tail_queued.erase(std::make_pair(m_id, p->GetUid()));
        if (Ws28TailReserveRow())
            std::cout << "WS28_TAIL_REJECT seed=" << ws28_tail_targets[ws28Target].seed
                      << " target=" << ws28Target
                      << " time_ns=" << Simulator::Now().GetNanoSeconds()
                      << " switch=" << m_id << " port=" << outDev
                      << " uid=" << p->GetUid() << std::endl;
    }
    if (ch.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL) {
        if (accepted) {
            if (heartbeatPacket) {
                ++ws21_heartbeat_hop_enqueues;
                ws21_heartbeat_hop_bytes += p->GetSize();
                if (heartbeatType == Ws21HeartbeatHeader::HELLO)
                    ws21_heartbeat_hello_hop_bytes += p->GetSize();
                else if (heartbeatType == Ws21HeartbeatHeader::ACK)
                    ws21_heartbeat_ack_hop_bytes += p->GetSize();
            } else {
                ++ws21_feedback_hop_enqueues;
                ws21_feedback_hop_bytes += p->GetSize();
            }
        } else {
            // Non-Guard modes do not call SwitchNotifyQueueDrop on queue refusal.
            // Release the admission reservation made above for this packet.
            if (qIndex != 0 && !((Settings::lb_mode >= 13 && Settings::lb_mode <= 15) || ClassReserveFamilyMode() || Settings::lb_mode == 22 || Settings::lb_mode == 23 || Settings::lb_mode == 24)) {
                if (!locallyGenerated)
                    m_mmu->RemoveFromIngressAdmission(inDev, qIndex, p->GetSize());
                m_mmu->RemoveFromEgressAdmission(outDev, qIndex, p->GetSize());
            }
            if (heartbeatPacket) ++ws21_heartbeat_hop_rejects;
            else ++ws21_feedback_hop_rejects;
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
    Ws29ControlEvent(p, m_id, ifIndex, "enqueue");
    auto ws28Hit = ws28_tail_queued.find(std::make_pair(m_id, p->GetUid()));
    if (ws28Hit != ws28_tail_queued.end() && Ws28TailReserveRow()) {
        const Ws28TailQueued &item = ws28Hit->second;
        std::cout << "WS28_TAIL_ENQUEUE seed=" << ws28_tail_targets[item.target].seed
                  << " target=" << item.target
                  << " time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " switch=" << m_id << " port=" << ifIndex
                  << " uid=" << p->GetUid() << std::endl;
    }
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
    Ws29ControlEvent(p, m_id, ifIndex, wasQueued ? "queued_drop" : "queue_reject");
    auto ws28Hit = ws28_tail_queued.find(std::make_pair(m_id, p->GetUid()));
    if (ws28Hit != ws28_tail_queued.end()) {
        const uint32_t target = ws28Hit->second.target;
        if (Ws28TailReserveRow())
            std::cout << "WS28_TAIL_DROP seed=" << ws28_tail_targets[target].seed
                      << " target=" << target
                      << " time_ns=" << Simulator::Now().GetNanoSeconds()
                      << " switch=" << m_id << " port=" << ifIndex
                      << " uid=" << p->GetUid()
                      << " was_queued=" << int(wasQueued) << std::endl;
        ws28_tail_queued.erase(ws28Hit);
    }
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
    Ws29ControlEvent(p, m_id, ifIndex, "dequeue");
    auto ws28Hit = ws28_tail_queued.find(std::make_pair(m_id, p->GetUid()));
    if (ws28Hit != ws28_tail_queued.end()) {
        const Ws28TailQueued item = ws28Hit->second;
        NS_ASSERT_MSG(item.port == ifIndex, "WS-28 target dequeue port mismatch");
        const uint64_t now = uint64_t(Simulator::Now().GetNanoSeconds());
        Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[ifIndex]);
        NS_ASSERT_MSG(dev && dev->GetQueue(), "WS-28 target dequeue queue absent");
        if (Ws28TailReserveRow())
            std::cout << "WS28_TAIL_DEQUEUE seed=" << ws28_tail_targets[item.target].seed
                      << " target=" << item.target << " time_ns=" << now
                      << " switch=" << m_id << " port=" << ifIndex
                      << " qindex=" << qIndex << " uid=" << p->GetUid()
                      << " seq=" << item.seq << " bytes=" << item.bytes
                      << " enqueue_ns=" << item.enqueueNs
                      << " wait_ns=" << (now - item.enqueueNs)
                      << " queue_at_enqueue=" << item.queueBytes
                      << " background_at_enqueue=" << item.backgroundBytes
                      << " queue_after_dequeue=" << dev->GetQueue()->GetNBytesTotal()
                      << " background_valid=" << int(ClassReserveFamilyMode())
                      << std::endl;
        ws28_tail_queued.erase(ws28Hit);
    }
    bool controlPacket = false;
    if (Ws21FeedbackEnabled() || ws21_heartbeat_enabled) {
        CustomHeader feedback(CustomHeader::L2_Header | CustomHeader::L3_Header |
                              CustomHeader::L4_Header);
        if (p->PeekHeader(feedback) && feedback.l3Prot == Ws21FeedbackHeader::IP_PROTOCOL) {
            controlPacket = true;
            if (ws21_heartbeat_enabled && Ws21HeartbeatPacketType(p))
                ++ws21_heartbeat_hop_dequeues;
            else
                ++ws21_feedback_hop_dequeues;
        }
    }
    RecordWs21PortEvent(ifIndex, 'D');
    if (Ws13DiagnosticEnabled() || Ws25DiagnosticEnabled()) {
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
    if ((Settings::lb_mode >= 13 && Settings::lb_mode <= 15) || ClassReserveFamilyMode() || Settings::lb_mode == 22 || Settings::lb_mode == 23 || Settings::lb_mode == 24) {
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
    if (controlPacket) {
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
