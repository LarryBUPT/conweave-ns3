#ifndef WS31_QUOTA_H
#define WS31_QUOTA_H

#include <algorithm>
#include <cstdint>
#include <limits>
#include <map>
#include <stdexcept>
#include <tuple>
#include <vector>

namespace ns3 { namespace ws31 {
typedef std::tuple<uint32_t,uint32_t,uint16_t,uint16_t> QuotaKey;

inline uint32_t QuotaClass(uint32_t tag) { return tag==1 || tag==2 ? tag : 0; }
inline uint32_t QuotaSizeClass(uint64_t size) { return size==8192 ? 2 : size==8388608 ? 1 : 0; }

// Quotas constrain NEW admission only. Entries retain their first route even
// after an activity lease expires or a borrowed lane's owner becomes active.
class QuotaAdmission {
public:
    struct Decision {
        uint32_t category=0, first=0, second=0, chosen=0, owner=0, eligible=0;
        uint64_t q1=0, q2=0;
        bool fresh=false, restricted=false, borrowed=false, residual=false;
    };
    uint64_t fresh=0, hits=0, borrowedAdmissions=0, restrictedAdmissions=0;
    uint64_t residualPackets=0, residualWireBytes=0;
    uint64_t activations[3]={0,0,0}, liveBorrowed[3]={0,0,0};
    uint64_t borrowedAtActivation[3]={0,0,0}, maxBorrowedAtActivation[3]={0,0,0};
    explicit QuotaAdmission(uint64_t windowNs=20000) : window(windowNs) {
        if (!window) throw std::invalid_argument("WS31 activity window must be positive");
    }
    static uint32_t Owner(uint32_t port, const std::vector<uint32_t> &ports) {
        if (ports.size()<2) return 0;
        std::vector<uint32_t> sorted=ports;
        std::sort(sorted.begin(),sorted.end());
        const size_t reserved=(sorted.size()+3)/4;
        return std::find(sorted.begin(),sorted.begin()+reserved,port)!=sorted.begin()+reserved ? 2 : 1;
    }
    bool Active(uint32_t category, uint64_t now) const {
        return category>=1 && category<=2 && seen[category] &&
               now>=last[category] && now-last[category]<window;
    }
    void Expire(uint64_t now) {
        while (!deadlines.empty() && deadlines.begin()->first<=now) {
            auto it=entries.find(deadlines.begin()->second);
            Entry &e=it->second;
            if (e.d.borrowed) --liveBorrowed[e.d.owner];
            e.live=false;
            deadlines.erase(deadlines.begin());
        }
    }
    template<class Load>
    Decision Admit(const QuotaKey &key, uint32_t category, const std::vector<uint32_t> &ports,
                   uint32_t h1, uint32_t h2, uint64_t now, uint64_t wireBytes,
                   bool hard, Load load) {
        if (ports.empty()) throw std::invalid_argument("WS31 quota has no route");
        Expire(now);
        auto it=entries.find(key);
        const bool isNew=it==entries.end();
        category=isNew ? QuotaClass(category) : it->second.d.category;
        if (category) {
            if (!Active(category,now)) {
                ++activations[category];
                borrowedAtActivation[category]+=liveBorrowed[category];
                maxBorrowedAtActivation[category]=std::max(maxBorrowedAtActivation[category],liveBorrowed[category]);
            }
            seen[category]=true; last[category]=now;
        }
        if (isNew) {
            Decision d; d.category=category;
            d.restricted=category && ports.size()>1 && (hard || Active(3-category,now));
            std::vector<uint32_t> eligible;
            for (uint32_t p : ports)
                if (!d.restricted || Owner(p,ports)==category) eligible.push_back(p);
            if (eligible.empty()) throw std::logic_error("WS31 quota produced empty route set");
            d.eligible=eligible.size();
            d.first=eligible[h1%eligible.size()]; d.second=eligible[h2%eligible.size()];
            d.q1=load(d.first); d.q2=load(d.second);
            d.chosen=d.q2<d.q1 ? d.second : d.first;
            d.owner=Owner(d.chosen,ports);
            d.borrowed=category && d.owner && d.owner!=category;
            Entry e; e.d=d;
            it=entries.insert(std::make_pair(key,e)).first;
            ++fresh; borrowedAdmissions+=d.borrowed; restrictedAdmissions+=d.restricted;
        } else ++hits;
        Entry &e=it->second;
        if (e.live) {
            deadlines.erase(e.expiry);
            if (e.d.borrowed) --liveBorrowed[e.d.owner];
        }
        const uint64_t end=window>std::numeric_limits<uint64_t>::max()-now ?
                           std::numeric_limits<uint64_t>::max() : now+window;
        e.expiry=deadlines.insert(std::make_pair(end,key)); e.live=true;
        if (e.d.borrowed) ++liveBorrowed[e.d.owner];
        Decision result=e.d;
        result.fresh=isNew;
        result.residual=e.d.borrowed && Active(e.d.owner,now);
        if (result.residual) { ++residualPackets; residualWireBytes+=wireBytes; }
        return result;
    }
    void Erase(const QuotaKey &key) {
        auto it=entries.find(key); if (it==entries.end()) return;
        if (it->second.live) {
            deadlines.erase(it->second.expiry);
            if (it->second.d.borrowed) --liveBorrowed[it->second.d.owner];
        }
        entries.erase(it);
    }
    size_t Size() const { return entries.size(); }
    bool Conserved() const {
        uint64_t count[3]={0,0,0}; size_t live=0;
        for (const auto &p : entries) if (p.second.live) {
            ++live;
            if (p.second.d.borrowed) ++count[p.second.d.owner];
        }
        return live==deadlines.size() && count[1]==liveBorrowed[1] && count[2]==liveBorrowed[2];
    }
private:
    typedef std::multimap<uint64_t,QuotaKey> Deadlines;
    struct Entry { Decision d; bool live=false; Deadlines::iterator expiry; };
    uint64_t window;
    bool seen[3]={false,false,false}; uint64_t last[3]={0,0,0};
    std::map<QuotaKey,Entry> entries;
    Deadlines deadlines;
};
}} // namespace ns3::ws31
#endif
