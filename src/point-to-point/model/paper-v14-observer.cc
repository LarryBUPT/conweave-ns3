#include "paper-v14-observer.h"
#include "ns3/simulator.h"
#include <cstdlib>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <tuple>
namespace ns3 {
namespace {
typedef std::tuple<std::string,uint32_t,int32_t> CounterKey;
std::map<CounterKey,uint64_t> counters;
uint64_t choices = 0;
const uint64_t rowLimit = 500000;
}
bool Pv14Observe() {
    static const bool enabled = []() {
        const char *v = std::getenv("PAPER_V14_OBSERVE");
        if (!v) return false;
        if ((v[0]!='0' && v[0]!='1') || v[1])
            throw std::runtime_error("PV14 invalid observation switch");
        return v[0]=='1';
    }();
    return enabled;
}
void Pv14Choice(uint32_t node, uint32_t sip, uint32_t dip, uint16_t sport,
                uint16_t dport, uint32_t degree, uint32_t first, uint32_t second,
                uint64_t q1, uint64_t q2, uint32_t chosen) {
    if (!Pv14Observe()) return;
    if (++choices > rowLimit) throw std::runtime_error("PV14 first-choice overflow");
    std::cout << "PV14_CHOICE time_ns=" << Simulator::Now().GetNanoSeconds()
              << " switch=" << node << " sip=" << sip << " dip=" << dip
              << " sport=" << sport << " dport=" << dport << " degree=" << degree
              << " first=" << first << " second=" << second
              << " q1=" << q1 << " q2=" << q2 << " chosen=" << chosen << '\n';
}
void Pv14Count(const char *kind, uint32_t node, int32_t flow, uint64_t amount) {
    if (!Pv14Observe()) return;
    CounterKey key(kind,node,flow);
    if (!counters.count(key) && counters.size() >= rowLimit)
        throw std::runtime_error("PV14 counter overflow");
    counters[key] += amount;
}
void Pv14Candidates(uint32_t node, uint32_t sip, uint32_t dip, uint16_t sport,
                    uint16_t dport, const std::vector<std::pair<uint32_t,uint64_t>> &queues) {
    if (!Pv14Observe()) return;
    std::cout << "PV14_CANDIDATES switch=" << node << " sip=" << sip << " dip=" << dip
              << " sport=" << sport << " dport=" << dport << " samples=";
    for (const auto &q : queues) std::cout << q.first << ':' << q.second << ',';
    std::cout << '\n';
}
void Pv14Print() {
    if (!Pv14Observe()) return;
    for (const auto &c : counters)
        std::cout << "PV14_COUNT kind=" << std::get<0>(c.first)
                  << " node=" << std::get<1>(c.first) << " flow=" << std::get<2>(c.first)
                  << " value=" << c.second << '\n';
    std::cout << "PV14_TERMINAL schema=1 first_choices=" << choices
              << " counter_rows=" << counters.size() << " complete=1" << std::endl;
}
}
