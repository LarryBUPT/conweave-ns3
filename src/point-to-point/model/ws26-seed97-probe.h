#ifndef WS26_SEED97_PROBE_H
#define WS26_SEED97_PROBE_H

#include <cstdint>
#include <cstdlib>

namespace ns3 {

// Frozen from the already disclosed seed 20262697 pair. The second half of
// each row is a same-class, same-destination-ToR control; one control is reused.
static inline bool Ws26Seed97ProbeEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS26_SEED97_TIME_DIAG");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

static inline bool Ws26Seed97Target(uint32_t src, uint32_t dst,
                                    uint32_t sport, uint32_t dport) {
    static const uint32_t selected[][4] = {
        {268, 628, 10001, 105}, {340, 628, 10000, 101},
        {544, 628, 10000, 103}, {692, 628, 10005, 104},
        {896, 628, 10000, 100}, {1124, 628, 10000, 102},
        {964, 1148, 10059, 136}, {980, 1128, 10059, 156},
        {988, 1120, 10056, 151}, {1076, 1120, 10060, 154},
        {1080, 1148, 10058, 139}, {1116, 1128, 10058, 165},
        {268, 616, 10000, 101}, {840, 616, 10001, 102},
        {868, 628, 10003, 107}, {880, 628, 10004, 106},
        {1176, 616, 10000, 100}, {0, 1144, 10059, 100},
        {8, 1128, 10052, 100}, {8, 1144, 10053, 101},
        {8, 1148, 10054, 100}, {12, 1128, 10058, 101},
        {20, 1128, 10058, 102},
    };
    for (const auto &row : selected) {
        if (src == row[0] && dst == row[1] &&
            sport == row[2] && dport == row[3]) return true;
    }
    return false;
}

}  // namespace ns3

#endif
