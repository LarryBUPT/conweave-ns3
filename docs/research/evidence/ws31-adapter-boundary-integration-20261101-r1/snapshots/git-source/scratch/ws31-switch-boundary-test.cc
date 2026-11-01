#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/switch-node.h"
#include "ns3/qbb-net-device.h"
#include "ns3/broadcom-egress-queue.h"
#include "ns3/ppp-header.h"
#include "ns3/seq-ts-header.h"
#include "ns3/workload-tag.h"
#include "ns3/settings.h"
#include "ns3/ws30-observer.h"
#include "ns3/ws30-v13-fixture.h"
#include <functional>
#include <iostream>
#include <vector>

using namespace ns3;

static void Require(bool condition, const char *message) {
    if (!condition) NS_FATAL_ERROR(message);
}

namespace ns3 {
// The probe calls the real adapters. It does not replace queue reads, packet
// parsing, prediction, quota admission or production tuple erasure.
class Ws31SwitchBoundaryProbe {
public:
    static uint32_t Route(Ptr<SwitchNode> sw, Ptr<Packet> p, CustomHeader &ch,
                          const std::vector<int> &ports) {
        return Settings::lb_mode==36 ? sw->DoLbWs31C1(p,ch,ports) : sw->DoLbWs31C3(p,ch,ports);
    }
    static ws31::BudgetLedger &Budget(Ptr<SwitchNode> sw) { return sw->m_ws31Budget; }
    static const ws31::QuotaAdmission &Quota(Ptr<SwitchNode> sw) { return sw->m_ws31Quota; }
    static size_t Pairs(Ptr<SwitchNode> sw) { return sw->m_ws31Pairs.size(); }
    static uint64_t Fresh(Ptr<SwitchNode> sw) { return sw->m_ws31Fresh; }
    static uint64_t Hits(Ptr<SwitchNode> sw) { return sw->m_ws31Hits; }
    static uint32_t First(Ptr<SwitchNode> sw, uint32_t sip, uint32_t dip,
                          uint16_t sport, uint16_t dport, const std::vector<int> &ports) {
        const uint32_t words[3]={sip,dip,uint32_t(sport)|(uint32_t(dport)<<16)};
        return ports[sw->EcmpHash(reinterpret_cast<const uint8_t *>(words),12,sw->m_ecmpSeed)%ports.size()];
    }
};
} // namespace ns3

struct SwitchFixture {
    Ptr<SwitchNode> sw;
    std::vector<int> ports;
    const Ipv4Address sip=Ipv4Address("11.0.0.1"), dip=Ipv4Address("11.0.1.1");
    const uint16_t dport=100;
    const char *name;
    uint32_t fixed=0, overhead=0;
    explicit SwitchFixture(const char *caseName) : name(caseName) {
        sw=CreateObject<SwitchNode>(); sw->SetEcmpSeed(7);
        sw->m_isToR=true; sw->m_isToR_hostIP.insert(sip.Get());
        for (unsigned i=0; i<8; ++i) {
            Ptr<QbbNetDevice> device=CreateObject<QbbNetDevice>();
            device->SetQueue(CreateObject<BEgressQueue>());
            ports.push_back(sw->AddDevice(device));
        }
    }
    Ptr<BEgressQueue> Queue(uint32_t port) {
        return DynamicCast<QbbNetDevice>(sw->GetDevice(port))->GetQueue();
    }
    uint64_t Pressure(uint32_t port) {
        return Ws31SwitchBoundaryProbe::Budget(sw).Pressure(port,Simulator::Now().GetNanoSeconds());
    }
    uint64_t Expected(uint64_t remaining) const {
        return remaining+((remaining+999)/1000)*overhead;
    }
    uint16_t BorrowerPort() {
        const std::vector<uint32_t> uports(ports.begin(),ports.end());
        for (uint32_t sport=1; sport<65536; ++sport) {
            const uint32_t first=Ws31SwitchBoundaryProbe::First(sw,sip.Get(),dip.Get(),sport,dport,ports);
            if (ws31::QuotaAdmission::Owner(first,uports)==2) return sport;
        }
        NS_FATAL_ERROR("C3 fixture could not find a class1 borrower tuple");
        return 0;
    }
    uint32_t Packet(uint16_t sport, uint32_t seq, uint32_t bytes, uint32_t tag,
                    bool present=true) {
        Ptr<ns3::Packet> p=Create<ns3::Packet>(bytes);
        SeqTsHeader sequence; sequence.SetSeq(seq); sequence.SetPG(3); p->AddHeader(sequence);
        UdpHeader udp; udp.SetSourcePort(sport); udp.SetDestinationPort(dport); p->AddHeader(udp);
        Ipv4Header ip; ip.SetSource(sip); ip.SetDestination(dip); ip.SetProtocol(0x11);
        ip.SetPayloadSize(p->GetSize()); ip.SetTtl(64); ip.SetTos(0); ip.SetIdentification(0); p->AddHeader(ip);
        PppHeader ppp; ppp.SetProtocol(0x0021); p->AddHeader(ppp);
        if (present) { WorkloadTag label; label.SetValue(tag); p->AddPacketTag(label); }
        CustomHeader ch(CustomHeader::L2_Header|CustomHeader::L3_Header|CustomHeader::L4_Header);
        ch.brief=0; p->PeekHeader(ch);
        Require(ch.l3Prot==0x11 && ch.sip==sip.Get() && ch.dip==dip.Get() &&
                ch.udp.sport==sport && ch.udp.dport==dport && ch.udp.seq==seq && ch.udp.pg==3 &&
                ch.udp.payload_size==bytes+CustomHeader::GetUdpHeaderSize(),"Fixture packet did not parse actual UDP payload");
        overhead=p->GetSize()-bytes;
        WorkloadTag actual; const bool actualPresent=p->PeekPacketTag(actual);
        Require(actualPresent==present && (!present || actual.GetValue()==tag),"Fixture tag presence mismatch");
        const uint32_t port=Ws31SwitchBoundaryProbe::Route(sw,p,ch,ports);
        const auto &b=Ws31SwitchBoundaryProbe::Budget(sw);
        const auto &q=Ws31SwitchBoundaryProbe::Quota(sw);
        Require(b.Conserved() && q.Conserved(),"Adapter state is not conserved");
        const size_t budgetEntries=b.Size(); const uint64_t expired=b.expired;
        const uint64_t pressure=Settings::lb_mode==36?Pressure(port):0;
        Require(b.Size()==budgetEntries && b.expired==expired,
                "Pressure observation expired a prediction missed by the production adapter");
        // These snapshots do not expire leases or predictions. In particular,
        // Size/expired are checked before any diagnostic Pressure() call.
        std::cout << "WS31_SWITCH_BOUNDARY_PACKET case=" << name << " mode=" << Settings::lb_mode
                  << " time_ns=" << Simulator::Now().GetNanoSeconds() << " uid=" << p->GetUid()
                  << " sip=" << sip.Get() << " dip=" << dip.Get() << " sport=" << sport
                  << " dport=" << dport << " seq=" << seq << " payload=" << bytes
                  << " wire=" << p->GetSize() << " tag=" << tag << " present=" << present
                  << " chosen=" << port << " pairs=" << Ws31SwitchBoundaryProbe::Pairs(sw)
                  << " queue_bytes=" << Queue(port)->GetNBytesTotal() << " pressure=" << pressure
                  << " budget_entries=" << b.Size() << " unique=" << b.uniquePayload
                  << " duplicate=" << b.duplicatePackets << " expired=" << b.expired
                  << " capacity_fallback=" << b.capacityFallbacks << " range_fallback=" << b.rangeFallbacks
                  << " quota_entries=" << q.Size() << " fresh=" << q.fresh << " hits=" << q.hits
                  << " restricted=" << q.restrictedAdmissions << " borrowed=" << q.borrowedAdmissions
                  << " live_owner2=" << q.liveBorrowed[2] << " residual=" << q.residualPackets
                  << " residual_bytes=" << q.residualWireBytes
                  << " active1=" << q.Active(1,Simulator::Now().GetNanoSeconds())
                  << " active2=" << q.Active(2,Simulator::Now().GetNanoSeconds())
                  << " activation1=" << q.activations[1] << " activation2=" << q.activations[2]
                  << " conserved=1" << std::endl;
        return port;
    }
    void Idle() {
        const auto &q=Ws31SwitchBoundaryProbe::Quota(sw);
        const uint64_t now=Simulator::Now().GetNanoSeconds();
        std::cout << "WS31_SWITCH_BOUNDARY_IDLE case=" << name << " time_ns=" << now
                  << " quota_entries=" << q.Size() << " live_owner2=" << q.liveBorrowed[2]
                  << " active1=" << q.Active(1,now) << " active2=" << q.Active(2,now)
                  << " conserved=" << q.Conserved() << " observer_expires=0" << std::endl;
    }
    void Reset(uint16_t sport) {
        const auto &b=Ws31SwitchBoundaryProbe::Budget(sw);
        const auto &q=Ws31SwitchBoundaryProbe::Quota(sw);
        const size_t pairsBefore=Ws31SwitchBoundaryProbe::Pairs(sw), budgetBefore=b.Size(), quotaBefore=q.Size();
        sw->ResetWs30V13Tuple(sip.Get(),dip.Get(),sport,dport);
        Require(b.Conserved() && q.Conserved(),"Production reset broke state conservation");
        std::cout << "WS31_SWITCH_BOUNDARY_RESET case=" << name
                  << " time_ns=" << Simulator::Now().GetNanoSeconds() << " sip=" << sip.Get()
                  << " dip=" << dip.Get() << " sport=" << sport << " dport=" << dport
                  << " pairs_before=" << pairsBefore << " pairs_after=" << Ws31SwitchBoundaryProbe::Pairs(sw)
                  << " budget_before=" << budgetBefore << " budget_after=" << b.Size()
                  << " quota_before=" << quotaBefore << " quota_after=" << q.Size()
                  << " conserved=1" << std::endl;
    }
};

static void Invoke(std::function<void()> action) { action(); }
static void At(uint64_t ns, std::function<void()> action) {
    Simulator::Schedule(NanoSeconds(ns),&Invoke,action);
}
static void Run(const char *name) {
    Simulator::Run(); Simulator::Destroy();
    std::cout << "WS31_SWITCH_BOUNDARY PASS case=" << name << std::endl;
}

static void C1Ranges() {
    SwitchFixture f("c1-ranges"); auto &b=Ws31SwitchBoundaryProbe::Budget(f.sw);
    At(0,[&] { f.fixed=f.Packet(1000,0,100,2); Require(b.uniquePayload==100 && b.Size()==1 && f.Pressure(f.fixed)==f.Expected(8092),"C1 first parsed payload deduction failed"); });
    At(1,[&] {
        Require(f.Queue(f.fixed)->Enqueue(Create<ns3::Packet>(5000),3),"Actual egress queue fill failed");
        Require(f.Queue(f.fixed)->GetNBytesTotal()==5000,"Real queue load not installed");
        Require(f.Packet(1000,0,100,1)==f.fixed && b.uniquePayload==100 && b.duplicatePackets==1 && f.Pressure(f.fixed)==f.Expected(8092),"C1 duplicate/label/queue change altered budget or route");
    });
    At(2,[&] { Require(f.Packet(1000,300,100,1)==f.fixed && b.uniquePayload==200 && f.Pressure(f.fixed)==f.Expected(7992),"C1 hole was falsely delivered"); });
    At(3,[&] { Require(f.Packet(1000,50,300,1)==f.fixed && b.uniquePayload==400 && f.Pressure(f.fixed)==f.Expected(7792),"C1 partial overlap deducted more than unique payload"); });
    At(4,[&] { Require(f.Packet(1000,400,100,1)==f.fixed && b.uniquePayload==500 && Ws31SwitchBoundaryProbe::Fresh(f.sw)==1 && Ws31SwitchBoundaryProbe::Hits(f.sw)==4 && f.Pressure(f.fixed)==f.Expected(7692),"C1 changed tag rearmed a template"); });
    Run(f.name);
}

static void C1ExpiryReset() {
    SwitchFixture f("c1-expiry-reset"); auto &b=Ws31SwitchBoundaryProbe::Budget(f.sw);
    At(0,[&] { f.fixed=f.Packet(1000,0,1000,1); Require(f.Pressure(f.fixed)==f.Expected(64536),"C1 class1 template missing"); });
    At(19999,[&] { Require(f.Packet(1000,0,1000,2)==f.fixed && b.Size()==1 && b.expired==0 && b.uniquePayload==1000,"C1 prediction expired too early"); });
    At(20000,[&] { Require(f.Packet(1000,1000,500,2)==f.fixed && b.Size()==0 && b.expired==1 && b.uniquePayload==1000,"C1 exact expiry or late no-rearm failed"); });
    At(20001,[&] { Require(f.Packet(1000,1500,500,1)==f.fixed && b.Size()==0 && b.expired==1 && Ws31SwitchBoundaryProbe::Fresh(f.sw)==1,"C1 late arrival rebuilt prediction"); });
    At(20002,[&] {
        f.Reset(1000); Require(Ws31SwitchBoundaryProbe::Pairs(f.sw)==0 && b.Size()==0 && Ws31SwitchBoundaryProbe::Quota(f.sw).Size()==0,"C1 explicit reset did not clear actual tables");
        f.Packet(1000,0,100,2); Require(b.Size()==1 && b.uniquePayload==1100 && b.expired==1 && Ws31SwitchBoundaryProbe::Fresh(f.sw)==2,"C1 explicit reset prevented fresh admission");
    });
    Run(f.name);
}

static void C1Capacity() {
    SwitchFixture f("c1-capacity"); auto &b=Ws31SwitchBoundaryProbe::Budget(f.sw); b.Limits(1,32);
    uint32_t second=0;
    At(0,[&] { f.Packet(1000,0,100,2); Require(b.Size()==1,"C1 capacity fixture failed initial insertion"); });
    At(1,[&] { second=f.Packet(1001,0,100,2); Require(b.Size()==1 && b.capacityFallbacks==1 && b.uniquePayload==100 && Ws31SwitchBoundaryProbe::Pairs(f.sw)==2,"C1 capacity fallback lost route or budget accounting"); });
    At(2,[&] { f.Reset(1000); Require(b.Size()==0 && f.Packet(1001,100,100,1)==second && b.Size()==0 && b.uniquePayload==100 && b.capacityFallbacks==1,"C1 capacity fallback was silently rearmed"); });
    At(3,[&] { f.Reset(1001); f.Packet(1001,0,100,2); Require(b.Size()==1 && b.uniquePayload==200 && Ws31SwitchBoundaryProbe::Fresh(f.sw)==3,"C1 capacity reset did not permit new admission"); });
    Run(f.name);
}

static void C1Fallback(bool wrap) {
    SwitchFixture f(wrap?"c1-wrap":"c1-range-limit"); auto &b=Ws31SwitchBoundaryProbe::Budget(f.sw); b.Limits(8,1);
    At(0,[&] { f.fixed=f.Packet(1000,0,100,2); Require(b.Size()==1 && b.uniquePayload==100,"C1 fallback setup failed"); });
    At(1,[&] { Require(f.Packet(1000,wrap?0xfffffff0U:200,wrap?32:100,1)==f.fixed && b.Size()==0 && b.rangeFallbacks==1 && b.uniquePayload==100,"C1 range/wrap fallback lost pinning or overcounted payload"); });
    At(2,[&] { Require(f.Packet(1000,100,100,2)==f.fixed && b.Size()==0 && b.rangeFallbacks==1 && Ws31SwitchBoundaryProbe::Fresh(f.sw)==1,"C1 retired prediction was rearmed by later packet"); });
    Run(f.name);
}

static void C3BorrowReset() {
    SwitchFixture f("c3-borrow-expiry-reset"); const auto &q=Ws31SwitchBoundaryProbe::Quota(f.sw);
    const uint16_t borrower=f.BorrowerPort(), owner=borrower==65535?1:borrower+1;
    uint64_t residualWire=0;
    At(0,[&] { f.fixed=f.Packet(borrower,0,100,1); Require(q.fresh==1 && q.borrowedAdmissions==1 && q.liveBorrowed[2]==1 && q.Active(1,0) && !q.Active(2,0),"C3 borrowed admission not reached"); });
    At(100,[&] { Require(f.Packet(borrower,100,100,2)==f.fixed && q.activations[2]==0 && q.fresh==1 && q.hits==1,"C3 changed label replaced first policy"); });
    At(200,[&] { f.Packet(owner,0,100,2); Require(q.activations[2]==1 && q.borrowedAtActivation[2]==1 && q.restrictedAdmissions==1 && q.fresh==2,"C3 owner activation did not observe live borrower"); });
    At(201,[&] { Require(f.Packet(borrower,200,100,0,false)==f.fixed && q.residualPackets==1 && q.residualWireBytes==100+f.overhead && q.hits==2,"C3 residual or missing later tag changed pinned flow"); residualWire=q.residualWireBytes; });
    At(20199,[&] { Require(q.Active(2,20199) && q.Size()==2,"C3 activity ended before exact boundary"); f.Idle(); });
    At(20200,[&] { Require(!q.Active(2,20200) && q.Active(1,20200) && q.Size()==2 && q.liveBorrowed[2]==1,"C3 exact owner activity boundary or idle route retention failed"); f.Idle(); });
    At(20201,[&] { Require(!q.Active(1,20201) && q.Size()==2 && q.liveBorrowed[2]==1,"C3 lazy lease observation unexpectedly purged routes/state"); f.Idle(); });
    At(20202,[&] { Require(f.Packet(borrower,300,100,2)==f.fixed && q.Size()==2 && q.fresh==2 && q.hits==3 && q.activations[1]==2 && q.activations[2]==1 && q.liveBorrowed[2]==1 && q.residualPackets==1 && q.residualWireBytes==residualWire,"C3 expired borrower did not retain cached identity/path on late return"); });
    At(20203,[&] {
        f.Reset(borrower); Require(q.Size()==1 && q.liveBorrowed[2]==0,"C3 borrower reset did not release live accounting");
        f.Reset(owner); Require(q.Size()==0 && Ws31SwitchBoundaryProbe::Pairs(f.sw)==0 && Ws31SwitchBoundaryProbe::Budget(f.sw).Size()==0,"C3 reset did not clear actual tables");
        f.Packet(borrower,0,100,2); Require(q.Size()==1 && q.fresh==3 && q.activations[2]==2 && q.restrictedAdmissions==2 && q.borrowedAdmissions==1 && q.liveBorrowed[2]==0 && q.residualPackets==1,"C3 same tuple fresh admission failed after reset");
    });
    Run(f.name);
}

static void C3UnknownReset() {
    SwitchFixture f("c3-unknown-reset"); const auto &q=Ws31SwitchBoundaryProbe::Quota(f.sw);
    At(0,[&] { f.fixed=f.Packet(1000,0,100,0,false); Require(q.fresh==1 && !q.activations[1] && !q.activations[2],"C3 missing first tag activated category"); });
    At(1,[&] { Require(f.Packet(1000,100,100,1)==f.fixed && q.fresh==1 && q.hits==1 && !q.activations[1] && !q.activations[2],"C3 later label replaced cached unknown policy"); });
    At(2,[&] { f.Reset(1000); Require(q.Size()==0,"C3 unknown tuple not erased"); f.Packet(1000,0,100,1); Require(q.fresh==2 && q.activations[1]==1 && q.Size()==1,"C3 unknown reset prevented new known admission"); });
    Run(f.name);
}

int main(int argc, char *argv[]) {
    std::string candidate;
    CommandLine command; command.AddValue("candidate","Run exactly c1 or c3 adapter cases",candidate);
    command.Parse(argc,argv);
    Require(candidate=="c1" || candidate=="c3","Select exactly one candidate adapter: c1 or c3");
    Require(ws31::LabelProfile()==0 && Ws30V13TagTransform()==0 && Ws30V13Life()==0,
            "Switch adapter fixture requires label/transform/legacy lifecycle off");
    Require(Ws30Level()==2,"Switch adapter fixture requires full production observation WS30_OBSERVE=2");
    Settings::packet_payload=1000; IntHeader::mode=1;
    if (candidate=="c1") {
        Settings::lb_mode=36;
        C1Ranges(); C1ExpiryReset(); C1Capacity(); C1Fallback(false); C1Fallback(true);
    } else {
        Settings::lb_mode=47;
        C3BorrowReset(); C3UnknownReset();
    }
    std::cout << "WS31_SWITCH_BOUNDARY_SUMMARY PASS candidate=" << candidate
              << " cases=" << (candidate=="c1"?5:2) << " network_runs=0 endpoint_generations=0" << std::endl;
    return 0;
}
