#ifndef WS31_ENDPOINT_LEDGER_H
#define WS31_ENDPOINT_LEDGER_H

// Test-only endpoint evidence core. Production adapters must supply real
// endpoint/queue/timer snapshots; this core alone does not prove network drain.
#include <cstdint>
#include <cstddef>
#include <limits>
#include <map>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace ns3 { namespace ws31 {
typedef std::tuple<uint32_t,uint32_t,uint16_t,uint16_t,uint16_t> EndpointKey;
typedef std::tuple<uint32_t,uint32_t,uint32_t,uint32_t> EndpointLink;
typedef std::tuple<uint32_t,uint32_t,uint16_t,uint16_t> EndpointRouteKey;

// Values must come from the actual transport key functions and node mapping.
// This core does not change or reinterpret the production packed-key format.
struct EndpointResources {
    uint32_t sourceNode=0, destinationNode=0;
    uint64_t txKey=0, rxKey=0;
};

struct EndpointSnapshot {
    enum Fields { MAPS=1, QP_TIMERS=2, DEVICE_TIMERS=4, RETAINED_QPS=8,
                  QUEUES=16, SERIALIZATION=32, HISTORY=64, SWITCH_STATE=128, ALL=255 };
    uint32_t observedFields=0;
    int32_t flowId=-1;
    EndpointKey tuple;
    uint64_t generation=0, observedNs=0;
    bool txAbsent=false, rxAbsent=false, retainedQpsFinished=false;
    bool completionHistoryReleased=false;
    uint64_t txTimers=0, rxTimers=0, dataQueueBytes=0, ackQueueBytes=0, transmitting=0;
    uint64_t deviceTimers=0, pendingPayloadBytes=0;
    uint64_t pinnedEntries=0, budgetEntries=0, quotaEntries=0;
    bool Retired() const { return txAbsent && rxAbsent && txTimers==0 && rxTimers==0; }
    bool Quiet() const {
        return Retired() && retainedQpsFinished && deviceTimers==0 && pendingPayloadBytes==0 &&
               dataQueueBytes==0 && ackQueueBytes==0 && transmitting==0;
    }
    bool Reusable() const {
        return Quiet() && completionHistoryReleased && pinnedEntries==0 && budgetEntries==0 && quotaEntries==0;
    }
};

class EndpointLedger {
public:
    enum State { CREATED, ACTIVE, ACK_COMPLETE, ENDPOINTS_RETIRED, DRAINED, SWITCH_CLEARED };
    enum TokenKind { CHANNEL, HELD_TEST_COPY };
    enum CloseReason { RECEIVE_RETURNED, HELD_DISCARDED };
    struct Entry {
        EndpointKey tuple;
        EndpointResources resources;
        uint64_t generation=0, bytes=0, demandNs=0, launchNs=0, finishNs=0, lastNs=0;
        uint32_t originalTag=0;
        State state=CREATED;
        uint64_t entered=0, closed=0, outstandingChannel=0, outstandingHeld=0;
    };
    struct Token {
        int32_t flowId=-1;
        uint64_t uid=0, enteredNs=0;
        EndpointLink link;
        TokenKind kind=CHANNEL;
    };
private:
    std::map<int32_t,Entry> history;
    std::map<EndpointKey,int32_t> current;
    std::map<std::pair<uint32_t,uint64_t>,int32_t> txOwners, rxOwners;
    std::map<EndpointRouteKey,int32_t> routeOwners;
    std::map<uint64_t,Token> tokens;
    uint64_t nextToken=1;
    Entry &Find(int32_t id) {
        auto it=history.find(id);
        if (it==history.end()) throw std::logic_error("Unknown WS31 endpoint request");
        return it->second;
    }
    static void Time(const Entry &e,uint64_t now) {
        if (now<e.lastNs) throw std::logic_error("WS31 endpoint evidence moves backwards");
    }
    static void Need(bool ok,const char *message) { if (!ok) throw std::logic_error(message); }
    static EndpointRouteKey RouteKey(const EndpointKey &tuple) {
        return EndpointRouteKey(std::get<0>(tuple),std::get<1>(tuple),std::get<2>(tuple),std::get<3>(tuple));
    }
    template<class K> void Available(const std::map<K,int32_t> &owners,const K &key,
                                     const EndpointKey &tuple) const {
        auto it=owners.find(key);
        // This minimal fixture rejects cross-tuple aliases permanently, even
        // after cleanup, rather than borrowing an unrelated drain certificate.
        Need(it==owners.end() || (Get(it->second).tuple==tuple && Get(it->second).state==SWITCH_CLEARED),
             "Actual transport key or switch fourtuple aliases another request domain");
    }
    void Snapshot(const Entry &e,int32_t id,const EndpointSnapshot &actual,uint64_t now) const {
        Time(e,now);
        Need(actual.observedFields==EndpointSnapshot::ALL && actual.flowId==id &&
             actual.generation==e.generation && actual.tuple==e.tuple && actual.observedNs==now,
             "Endpoint snapshot is incomplete, stale, or belongs to another generation");
        auto tx=txOwners.find(std::make_pair(e.resources.sourceNode,e.resources.txKey));
        auto rx=rxOwners.find(std::make_pair(e.resources.destinationNode,e.resources.rxKey));
        auto route=routeOwners.find(RouteKey(e.tuple));
        Need(tx!=txOwners.end() && tx->second==id && rx!=rxOwners.end() && rx->second==id &&
             route!=routeOwners.end() && route->second==id,"Endpoint evidence lost actual resource ownership");
    }
public:
    const Entry &Get(int32_t id) const {
        auto it=history.find(id);
        if (it==history.end()) throw std::logic_error("Unknown WS31 endpoint request");
        return it->second;
    }
    std::size_t Requests() const { return history.size(); }
    std::size_t OutstandingTokens() const { return tokens.size(); }
    void Begin(const EndpointKey &tuple,const EndpointResources &resources,int32_t id,
               uint64_t generation,uint64_t bytes,uint32_t originalTag,uint64_t demandNs,
               const EndpointSnapshot *prior=nullptr) {
        Need(id>=0 && bytes>0 && !history.count(id),"Invalid or reused WS31 request identity");
        auto old=current.find(tuple);
        if (old==current.end()) Need(generation==0,"First endpoint generation must be zero");
        else {
            const Entry &e=Get(old->second);
            Need(e.state==SWITCH_CLEARED && e.outstandingChannel==0 && e.outstandingHeld==0,
                 "Same tuple reused before certified drain and switch cleanup");
            Need(e.generation<std::numeric_limits<uint64_t>::max() && generation==e.generation+1,
                 "Endpoint generation must advance exactly once");
            Need(demandNs>=e.lastNs,"Next demand precedes prior cleanup");
            // This completion-only fixture admits new demand after old cleanup.
            // Recheck actual resources in the same event as the new creation.
            Need(prior!=nullptr,"Tuple reuse requires a fresh prior-generation snapshot");
            Snapshot(e,old->second,*prior,demandNs);
            Need(prior->Reusable(),"Endpoint resources revived or histories/switch state remain");
            Need(resources.sourceNode==e.resources.sourceNode && resources.destinationNode==e.resources.destinationNode &&
                 resources.txKey==e.resources.txKey && resources.rxKey==e.resources.rxKey,
                 "Same endpoint tuple changed its actual resource identity");
        }
        const auto tx=std::make_pair(resources.sourceNode,resources.txKey);
        const auto rx=std::make_pair(resources.destinationNode,resources.rxKey);
        Available(txOwners,tx,tuple); Available(rxOwners,rx,tuple); Available(routeOwners,RouteKey(tuple),tuple);
        Entry e; e.tuple=tuple; e.resources=resources; e.generation=generation; e.bytes=bytes; e.originalTag=originalTag;
        e.demandNs=e.lastNs=demandNs;
        history.insert(std::make_pair(id,e)); current[tuple]=id;
        txOwners[tx]=id; rxOwners[rx]=id; routeOwners[RouteKey(tuple)]=id;
    }
    void Launch(int32_t id,uint64_t now) {
        Entry &e=Find(id); Time(e,now);
        Need(e.state==CREATED,"Endpoint launch repeated or out of order");
        e.launchNs=e.lastNs=now; e.state=ACTIVE;
    }
    uint64_t Enter(int32_t id,uint64_t uid,const EndpointLink &link,
                   TokenKind kind,uint64_t now) {
        Entry &e=Find(id); Time(e,now);
        Need(e.state==ACTIVE || e.state==ACK_COMPLETE || e.state==ENDPOINTS_RETIRED,
             "Packet token entered outside an open endpoint generation");
        Need(kind==CHANNEL || kind==HELD_TEST_COPY,"Unknown endpoint token kind");
        Need(nextToken<std::numeric_limits<uint64_t>::max(),"Endpoint token identity overflow");
        Need(e.entered<std::numeric_limits<uint64_t>::max(),"Endpoint token count overflow");
        Token t; t.flowId=id; t.uid=uid; t.link=link;
        t.kind=kind; t.enteredNs=now;
        const uint64_t serial=nextToken++;
        tokens.insert(std::make_pair(serial,t));
        ++e.entered;
        if (kind==CHANNEL) ++e.outstandingChannel; else ++e.outstandingHeld;
        e.lastNs=now; return serial;
    }
    void Close(uint64_t serial,int32_t id,uint64_t uid,const EndpointLink &link,
               TokenKind expectedKind,CloseReason reason,uint64_t now) {
        auto it=tokens.find(serial);
        Need(it!=tokens.end(),"Unknown or twice-closed endpoint token");
        const Token &t=it->second;
        Need(t.flowId==id && t.uid==uid && t.link==link,
             "Endpoint token identity or directed link mismatch");
        Need(t.kind==expectedKind &&
             ((expectedKind==CHANNEL && reason==RECEIVE_RETURNED) ||
              (expectedKind==HELD_TEST_COPY && reason==HELD_DISCARDED)),
             "Endpoint token closed by the wrong handler or reason");
        Entry &e=Find(id); Time(e,now);
        Need(now>=t.enteredNs,"Endpoint token closed before entry");
        if (t.kind==CHANNEL) --e.outstandingChannel; else --e.outstandingHeld;
        ++e.closed; e.lastNs=now; tokens.erase(it);
    }
    void AckComplete(int32_t id,uint64_t cumulativeAck,uint64_t now) {
        Entry &e=Find(id); Time(e,now);
        Need(e.state==ACTIVE && cumulativeAck==e.bytes,"Endpoint completion lacks exact cumulative ACK");
        e.finishNs=e.lastNs=now; e.state=ACK_COMPLETE;
    }
    bool Retire(int32_t id,const EndpointSnapshot &actual,uint64_t now) {
        Entry &e=Find(id); Snapshot(e,id,actual,now);
        Need(e.state==ACK_COMPLETE,"Endpoint retirement before completion or repeated");
        e.lastNs=now; // Valid false observations also advance the evidence clock.
        if (!actual.Retired()) return false;
        e.state=ENDPOINTS_RETIRED; return true;
    }
    bool CertifyDrain(int32_t id,const EndpointSnapshot &actual,uint64_t now) {
        Entry &e=Find(id); Snapshot(e,id,actual,now);
        Need(e.state==ENDPOINTS_RETIRED,"Drain certification before endpoint retirement or repeated");
        e.lastNs=now;
        if (!actual.Quiet() || e.outstandingChannel || e.outstandingHeld) return false;
        e.state=DRAINED; return true;
    }
    bool SwitchCleared(int32_t id,const EndpointSnapshot &actual,uint64_t now) {
        Entry &e=Find(id); Snapshot(e,id,actual,now);
        Need(e.state==DRAINED,"Switch cleanup before certified drain or repeated");
        e.lastNs=now;
        if (!actual.Reusable() || e.outstandingChannel || e.outstandingHeld) return false;
        e.state=SWITCH_CLEARED; return true;
    }
    bool Conserved() const {
        std::map<int32_t,uint64_t> channel,held;
        for (const auto &p:tokens) {
            if (!history.count(p.second.flowId)) return false;
            if (p.second.kind==CHANNEL) ++channel[p.second.flowId];
            else if (p.second.kind==HELD_TEST_COPY) ++held[p.second.flowId];
            else return false;
        }
        for (const auto &p:history) {
            const Entry &e=p.second;
            if (e.closed>e.entered || e.entered-e.closed!=e.outstandingChannel+e.outstandingHeld ||
                e.outstandingChannel!=channel[p.first] || e.outstandingHeld!=held[p.first]) return false;
        }
        return true;
    }
};
}} // namespace ns3::ws31
#endif
