#ifndef WS30_CW_OBSERVER_H
#define WS30_CW_OBSERVER_H
#include "ws30-observer.h"
#include "ns3/fatal-error.h"
#include <sstream>
#include <string>

namespace ns3 {
// Observer-owned maps only. Never schedule events, draw RNG, mutate routing,
// create packets, or call QP methods with stateful side effects.
inline void Ws30CwEvent(const char *event, uint32_t sw, uint64_t flow,
                       uint32_t epoch, uint32_t phase, uint32_t path,
                       uint32_t flag, uint32_t seq, uint64_t stamp, uint64_t aux) {
    if (!Ws30Level()) return;
    typedef std::tuple<uint32_t,uint64_t> Key;
    typedef std::tuple<uint32_t,uint32_t,uint32_t,uint32_t> Signature;
    typedef std::tuple<uint32_t,uint64_t,uint32_t,uint32_t> Request;
    static std::map<Key,Signature> last;
    static std::map<Request,uint64_t> requests;
    static std::map<Key,uint64_t> buffered;
    static uint64_t bytes=0;
    const uint64_t now=Simulator::Now().GetNanoSeconds();
    const std::string kind(event);
    int64_t age=-1;
    if (kind=="tx") {
        Signature signature(epoch,phase,path,flag);
        auto it=last.find(Key(sw,flow));
        if (flag==1 && it!=last.end() && it->second==signature) return;
        last[Key(sw,flow)]=signature;
        if (flag==2 || flag==3) requests[Request(sw,flow,epoch,flag==3?1:0)]=now;
    } else if (kind=="reply_rx") {
        auto it=requests.find(Request(sw,flow,epoch,phase));
        if (it!=requests.end()) {
            age=int64_t(now-it->second);
            requests.erase(it);
        }
    } else if (kind=="flush") {
        auto it=buffered.find(Key(sw,flow));
        if (it!=buffered.end()) { age=int64_t(now-it->second); buffered.erase(it); }
    } else {
        if (stamp && stamp<=now) age=int64_t(now-stamp);
        if (kind=="rx_buffer") buffered.insert(std::make_pair(Key(sw,flow),now));
    }
    std::ostringstream o;
    o << "WS30_CW event=" << event << " time_ns=" << now << " switch=" << sw
      << " flow=" << flow << " epoch=" << epoch << " phase=" << phase
      << " path=" << path << " flag=" << flag << " seq=" << seq
      << " stamp_ns=" << stamp << " age_ns=" << age << " aux=" << aux;
    bytes+=o.str().size()+1;
    if (bytes>67108864ULL || requests.size()>1000000 || last.size()>1000000)
        NS_FATAL_ERROR("WS30_CW observation overflow");
    std::cout << o.str() << std::endl;
}
}
#endif
