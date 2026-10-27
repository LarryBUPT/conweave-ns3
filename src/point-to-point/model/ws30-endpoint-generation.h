#ifndef WS30_ENDPOINT_GENERATION_H
#define WS30_ENDPOINT_GENERATION_H

#include <cstdint>
#include <map>

namespace ns3 {
// Explicit synthetic endpoint incarnation bookkeeping. Flow IDs are neutral
// trace identities, never workload classes, route labels, or packet sequences.
class Ws30EndpointGeneration {
  public:
    struct Entry { int32_t flow; bool active; };
    std::map<uint64_t, Entry> entries;

    bool Begin(uint64_t key, int32_t flow) {
        auto it = entries.find(key);
        if (flow < 0 || (it != entries.end() && (it->second.active || flow <= it->second.flow)))
            return false;
        entries[key] = {flow, true};
        return true;
    }
    bool Accept(uint64_t key, int32_t flow) const {
        auto it = entries.find(key);
        return it != entries.end() && it->second.active && it->second.flow == flow;
    }
    bool Close(uint64_t key, int32_t flow) {
        if (!Accept(key, flow)) return false;
        entries.find(key)->second.active = false;
        return true;
    }
    int32_t Current(uint64_t key) const {
        auto it = entries.find(key);
        return it == entries.end() ? -1 : it->second.flow;
    }
};
} // namespace ns3
#endif
