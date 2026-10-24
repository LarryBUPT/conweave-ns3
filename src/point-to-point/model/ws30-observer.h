#ifndef WS30_OBSERVER_H
#define WS30_OBSERVER_H

#include <cstdlib>
#include <iostream>
#include <map>
#include <tuple>
#include "ns3/custom-header.h"
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include "ns3/workload-tag.h"

namespace ns3 {
// Environment-only observation: no events, packets, RNG draws or routing writes.
inline uint32_t Ws30Level() {
    static const uint32_t level = []() {
        const char *p = std::getenv("WS30_OBSERVE");
        return p && p[0] >= '1' && p[0] <= '2' && p[1] == '\0' ? uint32_t(p[0]-'0') : 0U;
    }();
    return level;
}
struct Ws30RouteState { uint32_t first=0, last=0; uint64_t packets=0, changes=0; };
struct Ws30ChoiceStat {
    uint64_t events=0, same=0, empty=0, background=0, equal=0, near=0;
    uint64_t composition=0, aDisagrees=0, choseSecond=0;
};
struct Ws30Observation {
    typedef std::tuple<uint32_t,uint32_t,uint32_t,uint16_t,uint16_t> RouteKey;
    std::map<RouteKey,Ws30RouteState> routes;
    Ws30ChoiceStat choice[3];
    uint64_t routeRows=0, rejected=0;
};
inline Ws30Observation &Ws30Data() { static Ws30Observation d; return d; }
inline void Ws30Reject(uint32_t sw, Ptr<const Packet> p, const CustomHeader &ch,
                       uint32_t port, const char *reason) {
    if (!Ws30Level() || ch.l3Prot!=0x11) return;
    ++Ws30Data().rejected;
    if (Ws30Level()==2)
        std::cout << "WS30_REJECT time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " switch=" << sw << " sip=" << ch.sip << " dip=" << ch.dip
                  << " sport=" << ch.udp.sport << " dport=" << ch.udp.dport
                  << " seq=" << ch.udp.seq << " port=" << port
                  << " bytes=" << p->GetSize() << " reason=" << reason << std::endl;
}
inline void Ws30Choice(uint32_t sw, const CustomHeader &ch, uint32_t tag,
                       uint32_t first, uint32_t second, uint64_t q1, uint64_t q2,
                       uint64_t b1, uint64_t b2, uint32_t chosen, uint32_t packetBytes) {
    if (!Ws30Level()) return;
    Ws30ChoiceStat &s=Ws30Data().choice[tag<=2?tag:0];
    ++s.events;
    if (first==second) ++s.same;
    else {
        // Pair-composition frequencies are defined only for distinct ports.
        // Legacy pinning skips queue reads on a collision; zeros are placeholders.
        if (!q1 && !q2) ++s.empty;
        if (b1 || b2) ++s.background;
        if (q1==q2) ++s.equal;
        const uint64_t diff=q1>q2?q1-q2:q2-q1;
        if (diff<=packetBytes) { ++s.near; if (b1!=b2) ++s.composition; }
        if ((q2<q1) != (q2+b2<q1+b1)) ++s.aDisagrees;
    }
    if (chosen==second && second!=first) ++s.choseSecond;
    if (Ws30Level()==2)
        std::cout << "WS30_CHOICE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " switch=" << sw << " sip=" << ch.sip << " dip=" << ch.dip
                  << " sport=" << ch.udp.sport << " dport=" << ch.udp.dport
                  << " seq=" << ch.udp.seq << " tag=" << tag << " first=" << first
                  << " second=" << second << " q1=" << q1 << " q2=" << q2
                  << " b1=" << b1 << " b2=" << b2 << " chosen=" << chosen << std::endl;
}
inline void Ws30Route(uint32_t sw, Ptr<const Packet> p, const CustomHeader &ch,
                      uint32_t port, bool accepted) {
    if (!Ws30Level() || ch.l3Prot!=0x11) return;
    Ws30Observation &d=Ws30Data();
    if (!accepted) { Ws30Reject(sw,p,ch,port,"queue_rejected"); return; }
    auto key=std::make_tuple(sw,ch.sip,ch.dip,ch.udp.sport,ch.udp.dport);
    Ws30RouteState &s=d.routes[key];
    if (!s.packets) s.first=port;
    else if (s.last!=port) ++s.changes;
    s.last=port; ++s.packets;
    if (Ws30Level()==2) {
        if (++d.routeRows>1000000) { std::cerr << "WS30_OBSERVATION_OVERFLOW\n"; std::abort(); }
        WorkloadTag tag;
        const uint32_t label=p->PeekPacketTag(tag)?tag.GetValue():0;
        std::cout << "WS30_ROUTE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " switch=" << sw << " sip=" << ch.sip << " dip=" << ch.dip
                  << " sport=" << ch.udp.sport << " dport=" << ch.udp.dport
                  << " seq=" << ch.udp.seq << " tag=" << label << " port=" << port
                  << " uid=" << p->GetUid() << std::endl;
    }
}
inline void Ws30Print() {
    if (!Ws30Level()) return;
    const Ws30Observation &d=Ws30Data();
    uint64_t packets=0,changed=0,changes=0;
    for (const auto &r:d.routes) {
        packets+=r.second.packets; changes+=r.second.changes;
        if (r.second.changes) ++changed;
    }
    std::cout << "WS30_PATH switch_qps=" << d.routes.size() << " data_hops=" << packets
              << " changed_qps=" << changed << " port_changes=" << changes
              << " rejected=" << d.rejected << " full_rows=" << d.routeRows << std::endl;
    for (uint32_t tag=0;tag<=2;++tag) {
        const Ws30ChoiceStat &s=d.choice[tag];
        std::cout << "WS30_CHOICES tag=" << tag << " events=" << s.events
                  << " same=" << s.same << " empty=" << s.empty
                  << " background_nonzero=" << s.background << " equal=" << s.equal
                  << " near=" << s.near << " composition=" << s.composition
                  << " a_disagrees=" << s.aDisagrees << " chose_second=" << s.choseSecond
                  << std::endl;
    }
}
} // namespace ns3
#endif
