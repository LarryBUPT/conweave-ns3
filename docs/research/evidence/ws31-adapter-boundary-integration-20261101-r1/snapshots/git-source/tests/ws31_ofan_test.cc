#include "../src/point-to-point/model/ws31-ofan.h"
#include <cassert>
#include <iostream>
using namespace ns3::ws31;
int main() {
    // Non-arithmetic IDs: edge -> aggregation -> cores -> mandatory aggregation -> edge -> host.
    std::map<uint32_t,std::vector<uint32_t> > dag={
        {900,{31,47}},{31,{61,73}},{47,{89,97}},
        {61,{501}},{73,{501}},{89,{503}},{97,{503}},
        {501,{777}},{503,{777}},{777,{4}}};
    std::set<uint32_t> switches={900,31,47,61,73,89,97,501,503,777};
    auto g=OfanMandatoryGroups(dag,4,switches);
    assert(g.at(900)==777 && g.at(31)==501 && g.at(47)==503 && g.size()==3);
    auto bad=dag; bad[501]={31}; bool rejected=false;
    try { OfanMandatoryGroups(bad,4,switches); } catch (const std::logic_error &) { rejected=true; }
    assert(rejected);
    OfanScheduler a,b; const std::vector<uint32_t> ports={8,2,5,1};
    std::map<uint32_t,unsigned> counts;
    std::vector<uint32_t> cycle;
    for (unsigned i=0; i<400; ++i) {
        auto d=a.Select(777,1062,ports,123);
        auto e=b.Select(777,1062,ports,123);
        assert(d.port==e.port && d.quantum==1 && d.fresh==(i==0));
        ++counts[d.port];
        if (i<4) cycle.push_back(d.port); else assert(d.port==cycle[i%4]);
        // Interleave a different destination and ACK-size class: neither may advance data pointer.
        a.Select(503,1062,ports,123); a.Select(777,62,ports,123);
    }
    for (uint32_t p : ports) assert(counts[p]==100);
    assert(a.Groups().size()==3 && a.Groups().at({777,1}).packets==400);
    assert(OfanQuantum(128)==0 && OfanQuantum(129)==1);
    rejected=false;
    try { a.Select(777,1062,std::vector<uint32_t>{1,2},123); }
    catch (const std::logic_error &) { rejected=true; }
    assert(rejected);
    OfanScheduler c; c.Select(777,1062,ports,999);
    assert(c.Groups().at({777,1}).order!=a.Groups().at({777,1}).order ||
           c.Groups().at({777,1}).cursor!=a.Groups().at({777,1}).cursor);
    std::cout << "WS31_OFAN_TEST PASS mandatory-groups/cycle-rejection/rotation/independence/seed/static-gate\n";
}
