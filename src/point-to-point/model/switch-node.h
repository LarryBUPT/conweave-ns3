#ifndef SWITCH_NODE_H
#define SWITCH_NODE_H

#include <ns3/node.h>

#include <unordered_map>
#include <unordered_set>
#include <tuple>
#include <cstdio>

#include "qbb-net-device.h"
#include "switch-mmu.h"

namespace ns3 {

class Packet;

class SwitchNode : public Node {
    static const unsigned qCnt = 8;    // Number of queues/priorities used
    static const unsigned pCnt = 128;  // port 0 is not used so + 1	// Number of ports used
    uint32_t m_ecmpSeed;
    std::map<uint64_t, bool> m_guardGateActive;
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
    void ObserveWs21Source(const CustomHeader &ch, uint32_t port);
    void ObserveWs21Destination(Ptr<const Packet> p, const CustomHeader &ch);
    uint32_t DoLbWs18(Ptr<const Packet> p, const CustomHeader &ch,
                      const std::vector<int> &nexthops);
    uint32_t DoLbGuardHash(Ptr<const Packet> p, const CustomHeader &ch,
                           const std::vector<int> &nexthops);
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
    static void ConfigureWs21Identity(bool enabled);
    static void SetWs21HostTor(uint32_t hostIp, uint32_t torId);
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
