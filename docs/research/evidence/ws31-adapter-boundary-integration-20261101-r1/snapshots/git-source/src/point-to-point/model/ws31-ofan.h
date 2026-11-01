#ifndef WS31_OFAN_H
#define WS31_OFAN_H

#include <algorithm>
#include <cstdint>
#include <functional>
#include <iterator>
#include <map>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

namespace ns3 { namespace ws31 {
inline uint32_t OfanQuantum(uint64_t wireBytes) { return wireBytes<=128 ? 0 : 1; }

// Compute the first mandatory downstream switch from the ACTUAL shortest-path
// DAG. On a regular 3-tier fat-tree this is destination edge at a source edge,
// and destination aggregation at a source aggregation. No ID arithmetic.
inline std::map<uint32_t,uint32_t> OfanMandatoryGroups(
    const std::map<uint32_t,std::vector<uint32_t> > &dag, uint32_t target,
    const std::set<uint32_t> &switches) {
    std::map<uint32_t,std::set<uint32_t> > required;
    std::map<uint32_t,uint32_t> distance;
    std::set<uint32_t> visiting;
    std::function<void(uint32_t)> visit = [&](uint32_t u) {
        if (required.count(u)) return;
        if (!visiting.insert(u).second) throw std::logic_error("Ofan route DAG contains a cycle");
        if (u==target) { required[u].insert(u); distance[u]=0; visiting.erase(u); return; }
        auto row=dag.find(u);
        if (row==dag.end() || row->second.empty())
            throw std::logic_error("Ofan route does not reach target");
        bool first=true; std::set<uint32_t> common; uint32_t depth=0;
        for (uint32_t v : row->second) {
            visit(v);
            if (first) { common=required.at(v); depth=distance.at(v)+1; first=false; }
            else {
                if (depth!=distance.at(v)+1) throw std::logic_error("Ofan requires equal-hop routes");
                std::set<uint32_t> intersection;
                std::set_intersection(common.begin(),common.end(),required.at(v).begin(),
                                      required.at(v).end(),std::inserter(intersection,intersection.end()));
                common.swap(intersection);
            }
        }
        common.insert(u); required[u]=common; distance[u]=depth; visiting.erase(u);
    };
    for (const auto &row : dag) visit(row.first);
    std::map<uint32_t,uint32_t> result;
    for (const auto &row : dag) {
        if (row.second.size()<2) continue;
        bool found=false; uint32_t best=0;
        for (uint32_t v : required.at(row.first))
            if (v!=row.first && switches.count(v) && (!found || distance.at(v)>distance.at(best))) {
                best=v; found=true;
            }
        if (!found) throw std::logic_error("Ofan branch has no mandatory downstream switch");
        result[row.first]=best;
    }
    return result;
}

class OfanScheduler {
public:
    typedef std::pair<uint32_t,uint32_t> Group;
    struct State {
        std::vector<uint32_t> canonical, order;
        size_t cursor=0;
        uint64_t packets=0, wireBytes=0, wraps=0;
    };
    struct Decision { uint32_t port, quantum; size_t position; bool fresh; };
    Decision Select(uint32_t mandatory, uint64_t wireBytes, const std::vector<uint32_t> &ports,
                    uint64_t seed) {
        if (ports.empty()) throw std::invalid_argument("Ofan has no reachable uplink");
        const uint32_t quantum=OfanQuantum(wireBytes);
        const Group group(mandatory,quantum);
        std::vector<uint32_t> canonical=ports;
        std::sort(canonical.begin(),canonical.end());
        if (std::adjacent_find(canonical.begin(),canonical.end())!=canonical.end())
            throw std::logic_error("Ofan route set contains duplicate ports");
        auto it=states.find(group); const bool fresh=it==states.end();
        if (fresh) {
            State s; s.canonical=canonical; s.order=canonical;
            uint64_t rng=seed ^ (uint64_t(mandatory)<<32) ^ (uint64_t(quantum)*0xd6e8feb86659fd93ULL);
            for (size_t i=s.order.size(); i>1; --i) std::swap(s.order[i-1],s.order[Bound(rng,i)]);
            s.cursor=Bound(rng,s.order.size());
            it=states.insert(std::make_pair(group,s)).first;
        }
        State &s=it->second;
        if (s.canonical!=canonical)
            throw std::logic_error("Ofan static equal-path group changed; weighted/dynamic mode not implemented");
        const size_t position=s.cursor;
        const uint32_t port=s.order[position];
        s.cursor=(s.cursor+1)%s.order.size(); if (!s.cursor) ++s.wraps;
        ++s.packets; s.wireBytes+=wireBytes;
        return Decision{port,quantum,position,fresh};
    }
    const std::map<Group,State> &Groups() const { return states; }
private:
    std::map<Group,State> states;
    static uint64_t Next(uint64_t &state) {
        uint64_t z=(state+=0x9e3779b97f4a7c15ULL);
        z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL; z=(z^(z>>27))*0x94d049bb133111ebULL;
        return z^(z>>31);
    }
    static uint64_t Bound(uint64_t &state, uint64_t n) {
        const uint64_t threshold=(uint64_t(0)-n)%n;
        uint64_t r; do { r=Next(state); } while (r<threshold);
        return r%n;
    }
};
}} // namespace ns3::ws31
#endif
