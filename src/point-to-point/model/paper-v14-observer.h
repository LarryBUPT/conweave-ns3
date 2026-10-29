#ifndef PAPER_V14_OBSERVER_H
#define PAPER_V14_OBSERVER_H
#include <cstdint>
#include <utility>
#include <vector>
namespace ns3 {
bool Pv14Observe();
void Pv14Choice(uint32_t node, uint32_t sip, uint32_t dip, uint16_t sport,
                uint16_t dport, uint32_t degree, uint32_t first, uint32_t second,
                uint64_t q1, uint64_t q2, uint32_t chosen);
void Pv14Count(const char *kind, uint32_t node, int32_t flow, uint64_t amount = 1);
void Pv14Candidates(uint32_t node, uint32_t sip, uint32_t dip, uint16_t sport,
                    uint16_t dport, const std::vector<std::pair<uint32_t,uint64_t>> &queues);
void Pv14Print();
}
#endif
