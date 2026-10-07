#ifndef WS26_TIME_PROBE_H
#define WS26_TIME_PROBE_H

#include <cstdint>
#include <cstdlib>

namespace ns3 {

// Frozen, already unblinded WS-25 tail flows. Each row is src, dst, sport, dport.
// This diagnostic is never enabled for formal WS-26 demand.
static inline bool Ws26TimeProbeEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS26_TIME_PROBE");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

static inline bool Ws26TimeProbeTarget(uint32_t src, uint32_t dst,
                                       uint32_t sport, uint32_t dport) {
    static const uint32_t target[][4] = {
        {692, 1052, 10001, 102}, {1076, 1040, 10002, 103},
        {408, 1040, 10000, 101}, {1016, 1052, 10000, 101},
        {1016, 1040, 10002, 100}, {28, 1176, 10004, 101},
        {164, 1176, 10002, 104}, {56, 64, 10000, 100},
        {976, 324, 10000, 100}, {292, 1116, 10001, 102},
    };
    for (const auto &row : target) {
        if (src == row[0] && dst == row[1] &&
            sport == row[2] && dport == row[3]) return true;
    }
    return false;
}

}  // namespace ns3

#endif
