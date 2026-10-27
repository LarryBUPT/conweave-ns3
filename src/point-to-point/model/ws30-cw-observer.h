#ifndef WS30_CW_OBSERVER_H
#define WS30_CW_OBSERVER_H
#include "ws30-observer.h"
#include "ns3/fatal-error.h"
#include <sstream>
#include <string>
#include <limits>

namespace ns3 {
struct Ws30CwStat {
    uint64_t count=0,samples=0,flags[4]={},first=0,last=0,known=0,missing=0,minAge=0,maxAge=0,bins[64]={};
};
struct Ws30CwObservation {
    typedef std::tuple<uint32_t,uint64_t> Key;
    typedef std::tuple<uint32_t,uint32_t,uint32_t,uint32_t> Signature;
    typedef std::tuple<uint32_t,uint64_t,uint32_t,uint32_t> Request;
    std::map<Key,Signature> last;
    std::map<Request,uint64_t> requests;
    std::map<Key,uint64_t> buffered;
    Ws30CwStat stats[7];
    uint64_t bytes=0,total=0,pathChanges=0,epochChanges=0,phaseChanges=0;
    uint64_t matches=0,missing=0,replaced=0,bufferMatches=0,bufferMissing=0,flushPackets=0,maxBuffered=0;
    uint64_t requestPeak=0,keyPeak=0,bufferPeak=0;
    bool finalized=false;
};
inline Ws30CwObservation &Ws30CwData() { static Ws30CwObservation d;return d; }
inline const char *Ws30CwName(uint32_t i) {
    static const char *names[]={"tx","rx_mark","rx_buffer","reply_rx","reply_after","notify_rx","flush"};
    return names[i];
}
inline void Ws30CwAdd(uint64_t &n,uint64_t value=1) {
    if (value>std::numeric_limits<uint64_t>::max()-n) NS_FATAL_ERROR("WS30_CW counter overflow");
    n+=value;
}
template<class Map,class Key,class Value>
inline void Ws30CwPut(Map &m,const Key &key,const Value &value) {
    if (!m.count(key) && m.size()>=65536) NS_FATAL_ERROR("WS30_CW state bound exceeded");
    m[key]=value;
}
inline void Ws30CwEmit(const std::string &line) {
    Ws30CwObservation &d=Ws30CwData();
    if (line.size()+1>67108864ULL || d.bytes>67108864ULL-line.size()-1)
        NS_FATAL_ERROR("WS30_CW observation overflow");
    d.bytes+=line.size()+1;std::cout << line << '\n';
}
// Observer-owned maps only. Never schedule events, draw RNG, mutate routing,
// create packets, or call QP methods with stateful side effects.
inline void Ws30CwEvent(const char *event, uint32_t sw, uint64_t flow,
                       uint32_t epoch, uint32_t phase, uint32_t path,
                       uint32_t flag, uint32_t seq, uint64_t stamp, uint64_t aux) {
    if (!Ws30Level()) return;
    typedef std::tuple<uint32_t,uint64_t> Key;
    typedef std::tuple<uint32_t,uint32_t,uint32_t,uint32_t> Signature;
    typedef std::tuple<uint32_t,uint64_t,uint32_t,uint32_t> Request;
    Ws30CwObservation &d=Ws30CwData();
    if (d.finalized) NS_FATAL_ERROR("WS30_CW event after terminal summary");
    auto &last=d.last;auto &requests=d.requests;auto &buffered=d.buffered;
    const uint64_t now=Simulator::Now().GetNanoSeconds();
    const std::string kind(event);
    uint32_t index=7;
    for (uint32_t i=0;i<7;++i) if (kind==Ws30CwName(i)) {index=i;break;}
    if (index==7 || flag>3) NS_FATAL_ERROR("WS30_CW unknown event/flag");
    int64_t age=-1;
    if (kind=="tx") {
        Signature signature(epoch,phase,path,flag);
        auto it=last.find(Key(sw,flow));
        if (it!=last.end()) {
            if (std::get<2>(it->second)!=path) Ws30CwAdd(d.pathChanges);
            if (std::get<0>(it->second)!=epoch) Ws30CwAdd(d.epochChanges);
            if (std::get<1>(it->second)!=phase) Ws30CwAdd(d.phaseChanges);
        }
        Ws30CwPut(last,Key(sw,flow),signature);
        if (flag==2 || flag==3) {
            Request key(sw,flow,epoch,flag==3?1:0);
            if (requests.count(key)) Ws30CwAdd(d.replaced);
            Ws30CwPut(requests,key,now);
        }
    } else if (kind=="reply_rx") {
        auto it=requests.find(Request(sw,flow,epoch,phase));
        if (it!=requests.end()) {
            if (now<it->second || now-it->second>uint64_t(std::numeric_limits<int64_t>::max()))
                NS_FATAL_ERROR("WS30_CW invalid request age");
            age=int64_t(now-it->second);
            requests.erase(it);
            Ws30CwAdd(d.matches);
        } else Ws30CwAdd(d.missing);
    } else if (kind=="flush") {
        auto it=buffered.find(Key(sw,flow));
        if (it!=buffered.end()) {
            if (now<it->second || now-it->second>uint64_t(std::numeric_limits<int64_t>::max()))
                NS_FATAL_ERROR("WS30_CW invalid buffer age");
            age=int64_t(now-it->second);buffered.erase(it);Ws30CwAdd(d.bufferMatches);
        } else Ws30CwAdd(d.bufferMissing);
        Ws30CwAdd(d.flushPackets,aux);
    } else {
        if (stamp && stamp<=now) {
            if (now-stamp>uint64_t(std::numeric_limits<int64_t>::max())) NS_FATAL_ERROR("WS30_CW invalid packet age");
            age=int64_t(now-stamp);
        }
        if (kind=="rx_buffer") {
            if (!buffered.count(Key(sw,flow))) Ws30CwPut(buffered,Key(sw,flow),now);
            if (aux>d.maxBuffered) d.maxBuffered=aux;
        }
    }
    if (requests.size()>d.requestPeak) d.requestPeak=requests.size();
    if (last.size()>d.keyPeak) d.keyPeak=last.size();
    if (buffered.size()>d.bufferPeak) d.bufferPeak=buffered.size();
    Ws30CwStat &s=d.stats[index];Ws30CwAdd(s.count);Ws30CwAdd(s.flags[flag]);Ws30CwAdd(d.total);
    if (s.count==1) s.first=now;
    s.last=now;
    if (age>=0) {
        if (!s.known || uint64_t(age)<s.minAge) s.minAge=uint64_t(age);
        if (!s.known || uint64_t(age)>s.maxAge) s.maxAge=uint64_t(age);
        Ws30CwAdd(s.known);uint32_t bin=0;uint64_t value=uint64_t(age);
        while (value>1 && bin<63) {value>>=1;++bin;}
        Ws30CwAdd(s.bins[bin]);
    } else Ws30CwAdd(s.missing);
    // Prefix examples are intentionally biased; all totals above are complete.
    if (s.samples>=32) return;
    Ws30CwAdd(s.samples);
    std::ostringstream o;
    o << "WS30_CW_SAMPLE schema=2 event=" << event << " time_ns=" << now << " switch=" << sw
      << " flow=" << flow << " epoch=" << epoch << " phase=" << phase
      << " path=" << path << " flag=" << flag << " seq=" << seq
      << " stamp_ns=" << stamp << " age_ns=" << age << " aux=" << aux;
    Ws30CwEmit(o.str());
}
inline void Ws30CwPrint() {
    if (!Ws30Level()) return;
    Ws30CwObservation &d=Ws30CwData();
    if (d.finalized) NS_FATAL_ERROR("WS30_CW duplicate terminal summary");
    uint64_t total=0,samples=0;
    for (uint32_t i=0;i<7;++i) {
        const Ws30CwStat &s=d.stats[i];uint64_t flags=0,ages=0;
        for (uint32_t j=0;j<4;++j) Ws30CwAdd(flags,s.flags[j]);
        for (uint32_t j=0;j<64;++j) Ws30CwAdd(ages,s.bins[j]);
        if (flags!=s.count || s.known>s.count || s.missing!=s.count-s.known || ages!=s.known || s.samples>s.count)
            NS_FATAL_ERROR("WS30_CW summary conservation failure");
        Ws30CwAdd(total,s.count);Ws30CwAdd(samples,s.samples);
        std::ostringstream o;
        o << "WS30_CW_COUNT schema=2 event=" << Ws30CwName(i) << " count=" << s.count
          << " samples=" << s.samples << " omitted=" << s.count-s.samples
          << " first_ns=" << s.first << " last_ns=" << s.last
          << " age_known=" << s.known << " age_missing=" << s.missing
          << " age_min_ns=" << s.minAge << " age_max_ns=" << s.maxAge;
        for (uint32_t j=0;j<4;++j) o << " flag" << j << '=' << s.flags[j];
        for (uint32_t j=0;j<64;++j) o << " age_b" << j << '=' << s.bins[j];
        Ws30CwEmit(o.str());
    }
    if (total!=d.total) NS_FATAL_ERROR("WS30_CW total conservation failure");
    std::ostringstream o;
    o << "WS30_CW_TOTAL schema=2 complete=1 total_events=" << total << " samples=" << samples
      << " omitted=" << total-samples << " sample_policy=first32_per_kind"
      << " path_changes=" << d.pathChanges << " epoch_changes=" << d.epochChanges << " phase_changes=" << d.phaseChanges
      << " request_matches=" << d.matches << " request_missing=" << d.missing << " request_replaced=" << d.replaced
      << " requests_pending=" << d.requests.size() << " request_peak=" << d.requestPeak
      << " buffer_matches=" << d.bufferMatches << " buffer_missing=" << d.bufferMissing
      << " buffers_pending=" << d.buffered.size() << " buffer_peak=" << d.bufferPeak
      << " flush_packets=" << d.flushPackets << " max_buffered=" << d.maxBuffered
      << " tx_keys=" << d.last.size() << " tx_key_peak=" << d.keyPeak
      << " state_bound=65536 bytes_before_total=" << d.bytes << " byte_bound=67108864";
    Ws30CwEmit(o.str());d.finalized=true;
}
}
#endif
