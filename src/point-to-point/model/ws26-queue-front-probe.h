#ifndef WS26_QUEUE_FRONT_PROBE_H
#define WS26_QUEUE_FRONT_PROBE_H

#include <cstdint>
#include <cstdlib>

namespace ns3 {

// Opt-in observation of the already disclosed seed-97 queue windows.
// This predicate never schedules an event or changes a packet.
static inline bool Ws26QueueFrontProbeEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS26_QUEUE_FRONT_DIAG");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

static inline bool Ws26QueueFrontWindow(uint32_t switchId, uint32_t port,
                                         uint64_t nowNs) {
    const uint64_t start = 2000000000ULL;
    if (nowNs < start) return false;
    if (switchId == 1347 && port == 6)
        return nowNs <= start + 50000ULL;
    if (nowNs > start + 25000ULL) return false;
    return (switchId == 1382 && port == 16) ||
           (switchId == 1543 && port == 10) ||
           (switchId == 1657 && port == 5) ||
           (switchId == 1575 && port == 4);
}

}  // namespace ns3

#endif
