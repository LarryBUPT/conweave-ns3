#ifndef WS31_BUDGET_H
#define WS31_BUDGET_H

// Simulator-independent accounting core. Budgets predict unseen local arrivals;
// they are not physical queue occupancy or bandwidth reservations.
#include <algorithm>
#include <cstdint>
#include <limits>
#include <map>
#include <stdexcept>
#include <tuple>
#include <utility>
#include <vector>

namespace ns3 { namespace ws31 {
typedef std::tuple<uint32_t, uint32_t, uint16_t, uint16_t> Key;

inline uint64_t Add(uint64_t a, uint64_t b) {
    return b > std::numeric_limits<uint64_t>::max() - a
               ? std::numeric_limits<uint64_t>::max() : a + b;
}
inline uint64_t Framed(uint64_t payload, uint32_t mtu, uint32_t overhead) {
    if (!mtu) throw std::invalid_argument("WS31 MTU must be positive");
    const uint64_t packets = payload / mtu + (payload % mtu != 0);
    if (overhead && packets > std::numeric_limits<uint64_t>::max() / overhead)
        return std::numeric_limits<uint64_t>::max();
    return Add(payload, packets * overhead);
}

class BudgetLedger {
    typedef std::multimap<uint64_t, Key> Deadlines;
    struct Entry {
        uint32_t port, mtu, overhead;
        uint64_t remaining;
        Deadlines::iterator deadline;
        std::vector<std::pair<uint64_t, uint64_t> > ranges;
    };
    std::map<Key, Entry> entries;
    Deadlines deadlines;
    std::map<uint32_t, uint64_t> totals;
    size_t capacity, maxRanges;
    void Remove(std::map<Key, Entry>::iterator it) {
        const Entry &e = it->second;
        totals[e.port] -= Framed(e.remaining, e.mtu, e.overhead);
        deadlines.erase(e.deadline);
        entries.erase(it);
    }
  public:
    uint64_t expired = 0, capacityFallbacks = 0, rangeFallbacks = 0;
    uint64_t duplicatePackets = 0, uniquePayload = 0, peakEntries = 0;
    explicit BudgetLedger(size_t cap = 65536, size_t ranges = 32)
        : capacity(cap), maxRanges(ranges) {}
    void Limits(size_t cap, size_t ranges) {
        if (!entries.empty()) throw std::logic_error("Cannot reconfigure live WS31 state");
        capacity = cap; maxRanges = ranges;
    }
    void Expire(uint64_t now) {
        while (!deadlines.empty() && deadlines.begin()->first <= now) {
            typename std::map<Key, Entry>::iterator it = entries.find(deadlines.begin()->second);
            Remove(it); ++expired;
        }
    }
    bool Insert(const Key &key, uint32_t port, uint64_t payload,
                uint32_t mtu, uint32_t overhead, uint64_t now, uint64_t ttl) {
        Expire(now);
        // An existing tuple is never re-armed by a duplicate or retransmission.
        if (entries.count(key)) return false;
        if (!payload || !ttl) return false;
        if (entries.size() >= capacity) { ++capacityFallbacks; return false; }
        const uint64_t wire = Framed(payload, mtu, overhead);
        if (wire > std::numeric_limits<uint64_t>::max() - totals[port]) {
            ++capacityFallbacks; return false;
        }
        Entry entry;
        entry.port = port; entry.remaining = payload;
        entry.mtu = mtu; entry.overhead = overhead;
        entry.deadline = deadlines.insert(std::make_pair(Add(now, ttl), key));
        entries.insert(std::make_pair(key, entry));
        totals[port] += wire;
        peakEntries = std::max<uint64_t>(peakEntries, entries.size());
        return true;
    }
    void Observe(const Key &key, uint64_t seq, uint32_t bytes, uint64_t now,
                 bool deduct = true) {
        Expire(now);
        typename std::map<Key, Entry>::iterator it = entries.find(key);
        if (it == entries.end() || !deduct || !bytes) return;
        Entry &e = it->second;
        // The simulator uses a 32-bit sequence domain. Retire prediction on wrap;
        // never change a pinned route or infer that holes have been delivered.
        if (seq + bytes > (uint64_t(1) << 32)) {
            Remove(it); ++rangeFallbacks; return;
        }
        const uint64_t end = seq + bytes;
        uint64_t covered = 0;
        for (size_t i = 0; i < e.ranges.size(); ++i) {
            const uint64_t lo = std::max(seq, e.ranges[i].first);
            const uint64_t hi = std::min(end, e.ranges[i].second);
            if (hi > lo) covered += hi - lo;
        }
        const uint64_t novel = bytes - covered;
        if (!novel) { ++duplicatePackets; return; }
        std::vector<std::pair<uint64_t,uint64_t> > joined;
        uint64_t lo = seq, hi = end;
        bool emitted = false;
        for (size_t i = 0; i < e.ranges.size(); ++i) {
            const std::pair<uint64_t,uint64_t> r = e.ranges[i];
            if (r.second < lo) joined.push_back(r);
            else if (hi < r.first) {
                if (!emitted) { joined.push_back(std::make_pair(lo,hi)); emitted = true; }
                joined.push_back(r);
            } else { lo = std::min(lo,r.first); hi = std::max(hi,r.second); }
        }
        if (!emitted) joined.push_back(std::make_pair(lo,hi));
        if (joined.size() > maxRanges) { Remove(it); ++rangeFallbacks; return; }
        const uint64_t before = Framed(e.remaining,e.mtu,e.overhead);
        e.remaining -= std::min(e.remaining,novel);
        totals[e.port] -= before - Framed(e.remaining,e.mtu,e.overhead);
        e.ranges.swap(joined);
        uniquePayload = Add(uniquePayload,novel);
        if (!e.remaining) Remove(it);
    }
    uint64_t Pressure(uint32_t port, uint64_t now) {
        Expire(now); return totals[port];
    }
    void Erase(const Key &key) {
        typename std::map<Key, Entry>::iterator it = entries.find(key);
        if (it != entries.end()) Remove(it);
    }
    size_t Size() const { return entries.size(); }
    bool Contains(const Key &key) const { return entries.count(key)!=0; }
    bool Conserved() const {
        std::map<uint32_t,uint64_t> sum;
        for (typename std::map<Key,Entry>::const_iterator i=entries.begin(); i!=entries.end(); ++i)
            sum[i->second.port] += Framed(i->second.remaining,i->second.mtu,i->second.overhead);
        for (std::map<uint32_t,uint64_t>::const_iterator i=totals.begin(); i!=totals.end(); ++i)
            if (sum[i->first] != i->second) return false;
        return deadlines.size() == entries.size();
    }
};

class ObservedMemory {
    struct State { uint64_t bytes = 0, time = 0; };
    std::map<uint32_t,State> ports;
  public:
    size_t PortCount() const { return ports.size(); }
    uint64_t Value(uint32_t port, uint64_t now, uint64_t ttl) {
        State &s=ports[port];
        const uint64_t elapsed=now>=s.time ? now-s.time : 0;
        if (!ttl || elapsed>=ttl) return 0;
        // ttl is bounded to 1e9 ns by the adapter, avoiding product overflow.
        const uint64_t remain=ttl-elapsed;
        return (s.bytes/ttl)*remain + ((s.bytes%ttl)*remain)/ttl;
    }
    void Observe(uint32_t port, uint32_t bytes, uint64_t now, uint64_t ttl) {
        const uint64_t previous=Value(port,now,ttl);
        State &s=ports[port]; s.bytes=Add(previous,bytes); s.time=now;
    }
};
} }
#endif
