#ifndef WS30_COMPOSITION_FIXTURE_H
#define WS30_COMPOSITION_FIXTURE_H

// An explicit experimental intervention, separate from the passive observer.
// Prefill packets originate in real RDMA QPs. No queue/score value is written.
#include "ns3/custom-header.h"
#include "ns3/seq-ts-header.h"
#include "ns3/workload-tag.h"
#include <cstdlib>
#include <map>

#define WS30_COMPOSITION_REQUIRE(condition, message) \
    do { if (!(condition)) NS_FATAL_ERROR(message); } while (0)
namespace ns3 {
struct Ws30CompositionLedger {
    uint64_t bytes=0, background=0, afterProbeBackground=0;
};
static std::map<uint32_t, Ws30CompositionLedger> ws30CompositionLedger;
static uint32_t ws30CompositionSnapshots=0;
static Ptr<QbbNetDevice> ws30CompositionPorts[2];

static bool Ws30CompositionEnabled() {
    const char *p=std::getenv("WS30_COMPOSITION");
    return p && p[0]=='1' && p[1]=='\0';
}

static void Ws30CompositionQueue(uint32_t port, bool enqueue,
                                  Ptr<const Packet> p, uint32_t qIndex) {
    WorkloadTag tag;
    const uint32_t label=p->PeekPacketTag(tag)?tag.GetValue():0;
    WS30_COMPOSITION_REQUIRE(qIndex==3 && (label==1 || label==2),
                  "Unexpected packet in composition output queue");
    Ws30CompositionLedger &ledger=ws30CompositionLedger[port];
    const uint64_t bytes=p->GetSize();
    if (enqueue) {
        ledger.bytes+=bytes;
        if (label==1) {
            ledger.background+=bytes;
            if (ws30CompositionSnapshots) ledger.afterProbeBackground+=bytes;
        }
    } else {
        WS30_COMPOSITION_REQUIRE(ledger.bytes>=bytes && (label!=1 || ledger.background>=bytes),
                      "Composition queue ledger underflow");
        ledger.bytes-=bytes;
        if (label==1) ledger.background-=bytes;
    }
    std::cout << "WS30_COMPOSITION_QUEUE time_ns=" << Simulator::Now().GetNanoSeconds()
              << " port=" << port << " enqueue=" << enqueue << " bytes=" << bytes
              << " tag=" << label << " total=" << ledger.bytes
              << " background=" << ledger.background << std::endl;
}

static void Ws30CompositionProbe(Ptr<const Packet> p) {
    CustomHeader ch(CustomHeader::L2_Header|CustomHeader::L3_Header|CustomHeader::L4_Header);
    ch.getInt=1;
    p->PeekHeader(ch);
    if (ch.l3Prot!=0x11 || ch.dip!=Settings::node_id_to_ip(3).Get() || ch.udp.seq!=0) return;
    WS30_COMPOSITION_REQUIRE(ch.udp.sport==10004 && ch.udp.dport==100,
                  "Composition probe identity changed");
    WS30_COMPOSITION_REQUIRE(++ws30CompositionSnapshots==1, "Repeated composition probe first packet");
    const auto &a=ws30CompositionLedger[2], &b=ws30CompositionLedger[3];
    const uint64_t q1=ws30CompositionPorts[0]->GetQueue()->GetNBytesTotal();
    const uint64_t q2=ws30CompositionPorts[1]->GetQueue()->GetNBytesTotal();
    WS30_COMPOSITION_REQUIRE(q1==65536 && q2==65536 && a.bytes==q1 && b.bytes==q2,
                  "Composition ports must each contain exactly 64 KiB before the probe");
    WS30_COMPOSITION_REQUIRE((a.background==65536 && b.background==0) ||
                  (a.background==0 && b.background==65536), "Composition was not exchanged");
    WS30_COMPOSITION_REQUIRE(ws30CompositionPorts[0]->IsPaused(3) &&
                  ws30CompositionPorts[1]->IsPaused(3), "Prefill leaked before probe");
    std::cout << "WS30_COMPOSITION_PROBE time_ns=" << Simulator::Now().GetNanoSeconds()
              << " switch=4 port1=2 port2=3 q1=" << q1 << " q2=" << q2
              << " b1=" << a.background << " b2=" << b.background
              << " sport=" << ch.udp.sport << " dport=" << ch.udp.dport << std::endl;
}

static void Ws30CompositionHold(bool hold) {
    for (const auto &port:ws30CompositionPorts) port->Ws30FixtureHold(3,hold);
    std::cout << "WS30_COMPOSITION_HOLD time_ns=" << Simulator::Now().GetNanoSeconds()
              << " hold=" << hold << std::endl;
}

static void Ws30CompositionInstall(NodeContainer nodes, double origin) {
    if (!Ws30CompositionEnabled()) return;
    const char *observe=std::getenv("WS30_OBSERVE");
    WS30_COMPOSITION_REQUIRE(nodes.GetN()==8 && Settings::host_num==4 && origin==2.0 &&
                  observe && observe[0]=='2' && observe[1]=='\0', "Invalid composition fixture setup");
    WS30_COMPOSITION_REQUIRE(30+SeqTsHeader::GetHeaderSize()==36,
                  "Composition trace assumes 36 on-wire header bytes per data packet");
    for (uint32_t i=0;i<2;++i) {
        auto port=DynamicCast<QbbNetDevice>(nodes.Get(4)->GetDevice(2+i));
        WS30_COMPOSITION_REQUIRE(port && port->GetDataRate().GetBitRate()==40000000000ULL,
                      "Composition output must be 40 Gbps");
        const auto channel=port->GetChannel();
        uint32_t peer=channel->GetDevice(0)==port?1:0;
        WS30_COMPOSITION_REQUIRE(channel->GetDevice(peer)->GetNode()->GetId()==5+i,
                      "Composition output ordering changed");
        ws30CompositionPorts[i]=port;
        WS30_COMPOSITION_REQUIRE(port->TraceConnectWithoutContext("QbbEnqueue",
            MakeBoundCallback(&Ws30CompositionQueue,2+i,true)), "Missing enqueue trace");
        WS30_COMPOSITION_REQUIRE(port->TraceConnectWithoutContext("QbbDequeue",
            MakeBoundCallback(&Ws30CompositionQueue,2+i,false)), "Missing dequeue trace");
    }
    WS30_COMPOSITION_REQUIRE(nodes.Get(4)->GetDevice(1)->TraceConnectWithoutContext("MacRx",
                  MakeCallback(&Ws30CompositionProbe)), "Missing pre-routing receive trace");
    Simulator::Schedule(Seconds(origin)-NanoSeconds(1000),&Ws30CompositionHold,true);
    Simulator::Schedule(Seconds(origin)+NanoSeconds(22000),&Ws30CompositionHold,false);
}

static void Ws30CompositionFinish() {
    if (!Ws30CompositionEnabled()) return;
    WS30_COMPOSITION_REQUIRE(ws30CompositionSnapshots==1, "Composition probe never arrived");
    for (const auto &port:ws30CompositionPorts) {
        const auto &ledger=ws30CompositionLedger[port->GetIfIndex()];
        WS30_COMPOSITION_REQUIRE(ledger.bytes==0 && ledger.background==0 &&
                      port->GetQueue()->GetNBytesTotal()==0, "Composition queue did not drain");
        std::cout << "WS30_COMPOSITION_FINAL port=" << port->GetIfIndex()
                  << " total=" << ledger.bytes << " background=" << ledger.background
                  << " after_probe_background=" << ledger.afterProbeBackground << std::endl;
    }
}
}  // namespace ns3
#undef WS30_COMPOSITION_REQUIRE
#endif
