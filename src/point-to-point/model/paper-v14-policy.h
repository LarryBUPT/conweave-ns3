#ifndef PAPER_V14_POLICY_H
#define PAPER_V14_POLICY_H
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <utility>
#include <vector>
namespace ns3 {
inline uint32_t Pv14TieMatched(uint32_t first, uint32_t second,
                              uint64_t a, uint64_t b, bool bit) {
    return a == b ? first : (bit ? second : first);
}
// Prefer the ECMP candidate whenever it is a minimum. Otherwise the lowest
// port number among the minimum queues wins, independent of route-table order.
inline uint32_t Pv14AllMinimum(uint32_t first,
                              std::vector<std::pair<uint32_t, uint64_t>> queues) {
    if (queues.empty()) throw std::runtime_error("PV14 empty candidate set");
    std::sort(queues.begin(), queues.end());
    bool found = false; uint64_t best = 0; uint32_t selected = first;
    for (const auto &q : queues) if (q.first == first) { best = q.second; found = true; }
    if (!found) throw std::runtime_error("PV14 ECMP outside candidates");
    for (const auto &q : queues) if (q.second < best) { best = q.second; selected = q.first; }
    return selected;
}
}
#endif
