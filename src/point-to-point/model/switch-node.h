#ifndef SWITCH_NODE_H
#define SWITCH_NODE_H

#include <ns3/node.h>
#include <ns3/traced-callback.h>

#include <unordered_map>
#include <unordered_set>
#include <tuple>
#include <cstdio>
#include <map>

#include "qbb-net-device.h"
#include "switch-mmu.h"
#include "ws31-budget.h"
#include "ws31-downstream-feedback.h"
#include "ws31-quota.h"
#include "ws31-ofan.h"

namespace ns3 {

class Packet;
class Ipv4Header;
class Ws31C3rControl;

class SwitchNode : public Node {
   public:
    struct Ws31SourceDecision {
        bool fresh;
        uint32_t first, second, chosen;
        uint64_t q1, q2, r1, r2, predicted;
    };

   private:
    friend class Ws31SwitchBoundaryProbe;
    friend class Ws31EndpointSwitchProbe;
    friend class Ws31EndpointSwitchFixture;
    static const unsigned qCnt = 8;    // Number of queues/priorities used
    static const unsigned pCnt = 128;  // port 0 is not used so + 1	// Number of ports used
    uint32_t m_ecmpSeed;
    std::map<uint64_t, bool> m_guardGateActive;
    std::map<uint64_t, bool> m_ws27GateActive;
    std::unordered_map<uint32_t, std::vector<int> >
        m_rtTable;  // map from ip address (u32) to possible ECMP port (index of dev)

    // monitor uplinks
    uint64_t m_txBytes[pCnt];  // counter of tx bytes, for HPCC

   protected:
    bool m_ecnEnabled;
    uint32_t m_ccMode;
    uint32_t m_ackHighPrio;  // set high priority for ACK/NACK

   private:
    int GetOutDev(Ptr<Packet>, CustomHeader &ch);
    void SendToDev(Ptr<Packet> p, CustomHeader &ch);
    void SendToDevContinue(Ptr<Packet> p, CustomHeader &ch);
    static uint32_t EcmpHash(const uint8_t *key, size_t len, uint32_t seed);
    void CheckAndSendPfc(uint32_t inDev, uint32_t qIndex);
    void CheckAndSendResume(uint32_t inDev, uint32_t qIndex);
    void CheckGuardQueue(uint32_t ifIndex);

    /* Sending packet to Egress port */
    void DoSwitchSend(Ptr<Packet> p, CustomHeader &ch, uint32_t outDev, uint32_t qIndex);

    /*----- Load balancer -----*/
    // Flow ECMP (lb_mode = 0)
    uint32_t DoLbFlowECMP(Ptr<const Packet> p, const CustomHeader &ch,
                          const std::vector<int> &nexthops);
    uint32_t DoLbDualTrack(Ptr<const Packet> p, const CustomHeader &ch,
                           const std::vector<int> &nexthops);
    uint32_t DoLbPacketStrategy(Ptr<const Packet> p, const CustomHeader &ch,
                                const std::vector<int> &nexthops);
    uint32_t DoLbClassReserve(Ptr<const Packet> p, const CustomHeader &ch,
                              const std::vector<int> &nexthops);
    struct Ws30Pair { uint32_t first=0, second=0, chosen=0; };
    std::map<std::tuple<uint32_t,uint32_t,uint16_t,uint16_t>,Ws30Pair> m_ws30Pairs;
    // v13 arms are isolated from every historical mode and table.
    std::map<std::tuple<uint32_t,uint32_t,uint16_t,uint16_t>,Ws30Pair> m_ws30V13Pairs;
    uint64_t m_ws30V13Hits{0}, m_ws30V13Misses{0}, m_ws30V13Peak{0};
    uint32_t DoLbWs30V13(Ptr<const Packet> p, const CustomHeader &ch,
                         const std::vector<int> &nexthops);
    using Ws31M1FlowKey = std::tuple<uint32_t,uint32_t,uint16_t,uint16_t>;
    std::map<Ws31M1FlowKey,Ws30Pair> m_ws31M1Pairs;
    uint64_t m_ws31M1PeakPairs{0};
    uint64_t m_ws31M1Packets[3]{0,0,0};
    uint64_t m_ws31M1Distinct[3]{0,0,0};
    uint64_t m_ws31M1Switches[3]{0,0,0};
    uint64_t m_ws31M1QueueReads[3]{0,0,0};
    uint64_t m_ws31M1WireBytes[3]{0,0,0};
    uint32_t DoLbWs31M1(Ptr<const Packet> p, const CustomHeader &ch,
                        const std::vector<int> &nexthops);
    std::map<ws31::Key,Ws30Pair> m_ws31Pairs;
    ws31::BudgetLedger m_ws31Budget;
    ws31::ObservedMemory m_ws31Observed;
    uint64_t m_ws31Fresh{0}, m_ws31Hits{0};
    uint32_t DoLbWs31C1(Ptr<const Packet> p, const CustomHeader &ch,
                        const std::vector<int> &nexthops);
    TracedCallback<Ptr<const Packet>, const Ws31SourceDecision &> m_ws31SourceDecision;
    void TraceWs31Source(Ptr<const Packet> p, const CustomHeader &ch,
                         const Ws31SourceDecision &decision);
    ws31::QuotaAdmission m_ws31Quota;
    typedef std::tuple<uint32_t,uint32_t,uint16_t,uint16_t,uint16_t,uint32_t>
        Ws31C3rKey;
    struct Ws31C3rRoute {
        uint32_t category=0, owner=0, oldPort=0, newPort=0, epoch=0;
        uint64_t size=0, cut=0, lastArrivalNs=0, deadlineNs=0, admissionSerial=0;
        bool borrowed=false, pending=false, committed=false;
    };
    std::map<Ws31C3rKey,Ws31C3rRoute> m_ws31C3rRoutes;
    std::map<ws31::QuotaKey,uint32_t> m_ws31C3rCurrentGeneration;
    uint64_t m_ws31C3rAdmissions=0, m_ws31C3rPeakRoutes=0;
    uint64_t m_ws31C3rPausePackets=0, m_ws31C3rSkippedAtActivation=0;
    uint32_t DoLbWs31C3r(Ptr<const Packet> p, const CustomHeader &ch,
                          const std::vector<int> &nexthops);
    bool ReceiveWs31C3rControl(Ptr<NetDevice> device, Ptr<Packet> p,
                                const CustomHeader &ch);
    void SendWs31C3rControl(const Ws31C3rKey &key, uint8_t type,
                            uint32_t epoch, uint64_t cut);
    void ExpireWs31C3rPause(Ws31C3rKey key, uint32_t epoch);
    ws31::OfanScheduler m_ws31Ofan;
    std::map<uint32_t,uint32_t> m_ws31OfanDestination;
    std::map<uint32_t,std::vector<uint32_t> > m_ws31OfanGroupPorts;
    std::map<std::vector<uint32_t>,uint32_t> m_ws31OfanRrGroups;
    uint64_t m_ws31OfanData=0, m_ws31OfanAck=0;
    uint32_t DoLbWs31Ofan(Ptr<const Packet> p, const CustomHeader &ch,
                          const std::vector<int> &nexthops);
    uint32_t DoLbWs31C3(Ptr<const Packet> p, const CustomHeader &ch,
                        const std::vector<int> &nexthops);
    uint32_t DoLbWs30(Ptr<const Packet> p, const CustomHeader &ch,
                      const std::vector<int> &nexthops);
    uint32_t DoLbDestSpread(Ptr<const Packet> p, const CustomHeader &ch,
                            const std::vector<int> &nexthops);
    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t>, uint32_t>
        m_classReserveBackgroundPort;
    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t>, uint32_t>
        m_classReserveMoePort;
    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t>, uint32_t>
        m_destSpreadBackgroundPort;
    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t>, uint32_t>
        m_destSpreadMoePort;
    std::map<uint32_t, uint32_t> m_destSpreadNextByDestination;
    std::map<uint32_t, uint32_t> m_packetRoundRobinNext;  // destination IP -> next index
    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t>, uint32_t> m_ws18FlowPort;
    struct Ws21PathObservation {
        uint32_t port = 0;
        uint64_t packets = 0, cePackets = 0, firstNs = 0, lastNs = 0;
        uint64_t inconsistent = 0, unmapped = 0;
    };
    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t>, Ws21PathObservation>
        m_ws21Source, m_ws21Destination;
    std::map<std::pair<uint32_t, uint32_t>, uint32_t> m_ws21IngressToFirst;
    struct Ws21FeedbackState {
        uint64_t windowEndNs = 0, generatedNs = 0;
        uint32_t sequence = 0;
        uint32_t cePackets = 0, samplePackets = 0;
    };
    struct Ws21FeedbackWindow {
        uint32_t sourceHostIp = 0, destinationHostIp = 0;
        uint64_t endNs = 0;
        uint32_t cePackets = 0, samplePackets = 0;
        bool scheduled = false;
    };
    std::map<std::pair<uint32_t, uint32_t>, Ws21FeedbackState> m_ws21Feedback;
    std::map<std::pair<uint32_t, uint32_t>, Ws21FeedbackWindow> m_ws21FeedbackWindows;
    std::map<std::pair<uint32_t, uint32_t>, uint32_t> m_ws21FeedbackSequence;
    struct Ws31DownstreamState {
        Ws31DownstreamPath path;
        uint64_t sampleNs = 0;
        uint32_t queueBytes = 0;
        bool present = false;
        bool ambiguous = false;
    };
    std::map<std::pair<uint32_t, uint32_t>, Ws31DownstreamState> m_ws31Downstream;
    struct Ws31DownstreamPeer {
        uint32_t node = 0, ingressPort = 0;
        uint64_t rate = 0;
    };
    struct Ws31ObservedEgress {
        Ws31DownstreamPath path;
        uint32_t returnPort = 0;
        uint64_t lastDataNs = 0;
        uint64_t lastReportNs = 0, nextLegacyNs = 0;
        uint32_t lastQueueBytes = 0;
        bool reported = false;
    };
    std::map<uint32_t, Ws31DownstreamPeer> m_ws31DownstreamPeers;
    std::map<Ws31M1FlowKey, Ws31ObservedEgress> m_ws31ObservedEgresses;
    std::map<Ws31M1FlowKey, std::map<uint32_t, Ws31DownstreamState>> m_ws31ObservedSamples;
    uint64_t m_ws31ObservedPeriodNs = 0, m_ws31ObservedIdleNs = 0;
    uint64_t m_ws31EventDelta = 0, m_ws31EventWater = 0, m_ws31EventInterval = 0;
    uint64_t m_ws31PersistNs = 0, m_ws31PressureAgeNs = 0;
    uint64_t m_ws31EventSentBytes = 0, m_ws31EventWireBytes = 0, m_ws31ShadowBytes = 0;
    struct Ws31Rc2Flow {
        uint64_t highSinceNs = 0, lowSinceNs = 0, pressureNs = 0, lastDecisionNs = 0;
        uint32_t betterPort = 0, pinnedPort = 0;
        uint16_t pressureId = 0;
        bool high = false, low = false, pressureSeen = false, pressure = false;
        bool receiverPin = false;
    };
    std::map<Ws31M1FlowKey, Ws31Rc2Flow> m_ws31Rc2Flows;
    void ObserveWs31Rc2Pressure(const CustomHeader &ch);
    uint32_t SelectWs31Rc2(const Ws31M1FlowKey &flow, uint32_t first, uint32_t second,
                          uint32_t local, const Ws31DownstreamState *a,
                          const Ws31DownstreamState *b, uint64_t now);
    void ObserveWs31Downstream(Ptr<const Packet> frame, const CustomHeader &ch, uint32_t chosen);
    void TickWs31ObservedEgress(Ws31M1FlowKey flow);
    Ws31DownstreamState *FindWs31ObservedSample(const Ws31DownstreamFeedback &report,
                                                const Ipv4Header &ipv4, uint32_t ingress);
    const Ws31DownstreamState *FindWs31DownstreamSample(const Ws31M1FlowKey &flow,
                                                         uint32_t destinationLeaf,
                                                         uint32_t candidate) const;
    struct Ws31NarrowPath {
        uint32_t port = 0;
        bool low = false;
        uint64_t lowSinceSampleNs = 0;
        uint64_t lastLowSampleNs = 0;
    };
    std::map<Ws31M1FlowKey, Ws31NarrowPath> m_ws31NarrowPaths;
    uint64_t m_ws31NarrowBytes = 0, m_ws31ReopenBytes = 0, m_ws31ReopenNs = 0;
    uint64_t m_ws31DownstreamAgeNs = 0;
    bool m_ws31DownstreamSends = false;
    void SendWs31DownstreamFeedback(Ws31DownstreamFeedback report, uint32_t returnPort,
                                    uint32_t sourceHost, uint32_t destinationHost);
    void ReceiveWs31DownstreamFeedback(Ptr<NetDevice> ingress, Ptr<const Packet> frame);
    uint32_t SelectWs31Downstream(const Ws31M1FlowKey &flow, uint32_t first, uint32_t second,
                                  uint64_t localFirst, uint64_t localSecond);
    uint32_t ConstrainWs31DownstreamWidth(const Ws31M1FlowKey &flow, uint32_t chosen,
                                          bool fresh, uint64_t spread, uint64_t sampleNs,
                                          uint64_t nowNs);
    std::unordered_set<uint32_t> m_ws21HostPorts;
    struct Ws21HeartbeatPort {
        uint32_t epoch = 0, nextSequence = 0, outstanding = 0, missed = 0;
        uint64_t lastActivityNs = 0, sentNs = 0, lastAckNs = 0;
        bool active = false, unknown = false;
    };
    std::map<uint32_t, Ws21HeartbeatPort> m_ws21HeartbeatPorts;
    void TouchWs21Heartbeat(uint32_t port);
    void TickWs21Heartbeat(uint32_t port, uint32_t epoch);
    bool SendWs21Heartbeat(uint32_t port, uint8_t type, uint32_t epoch,
                           uint32_t sequence);
    bool ReceiveWs21Heartbeat(Ptr<NetDevice> device, Ptr<Packet> p,
                              const CustomHeader &ch);
    void ObserveWs21Source(const CustomHeader &ch, uint32_t port);
    void ObserveWs21Destination(Ptr<const Packet> p, const CustomHeader &ch);
    bool ReceiveWs21Feedback(Ptr<Packet> p, const CustomHeader &ch);
    void AccumulateWs21Feedback(uint32_t sourceTor, uint32_t candidatePort,
                                const CustomHeader &ch, bool ce);
    void FlushWs21Feedback(uint32_t sourceTor, uint32_t candidatePort);
    uint32_t DoLbWs18(Ptr<const Packet> p, const CustomHeader &ch,
                      const std::vector<int> &nexthops);
    uint32_t DoLbGuardHash(Ptr<const Packet> p, const CustomHeader &ch,
                           const std::vector<int> &nexthops);
    uint32_t DoLbWs27Guard(Ptr<const Packet> p, const CustomHeader &ch,
                           const std::vector<int> &nexthops);
    std::map<std::tuple<uint32_t, uint32_t, uint16_t, uint16_t>, uint32_t>
        m_ws27MoePort;
    // DRILL (lb_mode = 2)
    uint32_t DoLbDrill(Ptr<const Packet> p, const CustomHeader &ch,
                       const std::vector<int> &nexthops);     // choose egress port
    uint32_t m_drill_candidate;                               // always 2 (power of two)
    std::map<uint32_t, uint32_t> m_previousBestInterfaceMap;  // <dip, previousBestInterface>
    uint32_t CalculateInterfaceLoad(uint32_t interface);      // Get the load of a interface
    // Conga (lb_mode = 3)
    uint32_t DoLbConga(Ptr<Packet> p, CustomHeader &ch, const std::vector<int> &nexthops);
    // Conga (lb_mode = 6)
    uint32_t DoLbLetflow(Ptr<Packet> p, CustomHeader &ch, const std::vector<int> &nexthops);
    // ConWeave (lb_mode = 9)
    uint32_t DoLbConWeave(Ptr<const Packet> p, const CustomHeader &ch,
                           const std::vector<int> &nexthops);  // dummy

   public:
    void AddWs31OfanDestination(uint32_t dip, uint32_t mandatory,
                                const std::vector<uint32_t> &ports);
    void ResetWs30V13Tuple(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport);
    void WriteWs30V13State();
    // Ptr<BroadcomNode> m_broadcom;
    Ptr<SwitchMmu> m_mmu;
    bool m_isToR;                                 // true if ToR switch
    std::unordered_set<uint32_t> m_isToR_hostIP;  // host's IP connected to this ToR

    static TypeId GetTypeId(void);
    SwitchNode();
    void SetEcmpSeed(uint32_t seed);
    void AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx);
    void ClearTable();
    bool SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch);
    static void PrintWorkloadTagCounts();
    static void ConfigureGuardHash(uint32_t lambda, uint32_t tau,
                                   uint32_t gateOnBytes, uint32_t gateOffBytes);
    static void ConfigureWs18Path(bool enabled);
    static void ConfigureWs21Feedback(bool enabled, uint32_t intervalNs);
    static void ConfigureWs21Heartbeat(bool enabled, uint32_t intervalNs,
                                       uint32_t faultMode, uint32_t faultTor,
                                       uint32_t faultPort, uint64_t faultStartNs,
                                       uint64_t faultEndNs);
    static void ConfigureWs21Identity(bool enabled);
    void ConfigureWs31Downstream(uint64_t maximumAgeNs);
    void ConfigureWs31ObservedDownstream(uint64_t periodNs, uint64_t idleNs);
    void ConfigureWs31Rc2(uint64_t delta, uint64_t water, uint64_t interval,
                          uint64_t persistNs, uint64_t pressureAgeNs);
    void AddWs31DownstreamPeer(uint32_t port, uint32_t node, uint32_t receiverPort, uint64_t rate);
    void FinishWs31ObservedFlow(uint32_t source, uint32_t destination, uint16_t sport,
                                uint16_t dport);
    void ConfigureWs31DownstreamWidth(uint64_t narrowBytes, uint64_t reopenBytes,
                                      uint64_t reopenNs);
    void FinishWs31DownstreamWidth(uint32_t source, uint32_t destination, uint16_t sport,
                                   uint16_t dport);
    void AddWs31DownstreamPath(const Ws31DownstreamPath &path);
    void SampleWs31Downstream(const Ws31DownstreamPath &path, uint32_t returnPort,
                              uint32_t sourceHost, uint32_t destinationHost, Time sendDelay);
    static void ConfigureWs21PortEvents(FILE *out, uint64_t maxBytes);
    static void FinishWs21PortEvents();
    static void SetWs21HostTor(uint32_t hostIp, uint32_t torId);
    void AddWs21HostPort(uint32_t port);
    void RecordWs21PortEvent(uint32_t port, char event);
    void RecordWs21PortBoundary(char event);
    bool AddWs21IngressMapping(uint32_t sourceTor, uint32_t ingressPort,
                               uint32_t firstPort);
    void WriteWs21Identity(FILE *out) const;
    void SwitchNotifyEnqueue(uint32_t ifIndex, Ptr<const Packet> p);
    void SwitchNotifyAdmissionDrop(uint32_t ifIndex, Ptr<const Packet> p);
    void SwitchNotifyQueueDrop(uint32_t ifIndex, uint32_t qIndex,
                               Ptr<const Packet> p, bool wasQueued);
    void SwitchNotifyDequeue(uint32_t ifIndex, uint32_t qIndex, Ptr<Packet> p);
    uint64_t GetTxBytesOutDev(uint32_t outdev);
};

} /* namespace ns3 */

#endif /* SWITCH_NODE_H */
