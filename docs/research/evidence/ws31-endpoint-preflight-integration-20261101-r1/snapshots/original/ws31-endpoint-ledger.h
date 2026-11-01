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

namespace ns3 { namespace ws31 {
typedef std::tuple<uint32_t,uint32_t,uint16_t,uint16_t,uint16_t> EndpointKey;

struct EndpointSnapshot {
    bool txAbsent=false, rxAbsent=false, retainedQpsFinished=false;
    uint64_t txTimers=0, rxTimers=0, dataQueueBytes=0, ackQueueBytes=0, transmitting=0;
    bool Retired() const { return txAbsent && rxAbsent && txTimers==0 && rxTimers==0; }
    bool Quiet() const {
        return Retired() && retainedQpsFinished && dataQueueBytes==0 && ackQueueBytes==0 && transmitting==0;
    }
};

class EndpointLedger {
public:
    enum State { CREATED, ACTIVE, ACK_COMPLETE, ENDPOINTS_RETIRED, DRAINED, SWITCH_CLEARED };
    enum TokenKind { CHANNEL, HELD_TEST_COPY };
    struct Entry {
        EndpointKey tuple;
        uint64_t generation=0, bytes=0, demandNs=0, launchNs=0, finishNs=0, lastNs=0;
        uint32_t originalTag=0;
        State state=CREATED;
        uint64_t entered=0, closed=0, outstandingChannel=0, outstandingHeld=0;
    };
    struct Token {
        int32_t flowId=-1;
        uint64_t uid=0, enteredNs=0;
        uint32_t source=0, destination=0;
        TokenKind kind=CHANNEL;
    };
private:
    std::map<int32_t,Entry> history;
    std::map<EndpointKey,int32_t> current;
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
public:
    const Entry &Get(int32_t id) const {
        auto it=history.find(id);
        if (it==history.end()) throw std::logic_error("Unknown WS31 endpoint request");
        return it->second;
    }
    std::size_t Requests() const { return history.size(); }
    std::size_t OutstandingTokens() const { return tokens.size(); }
    void Begin(const EndpointKey &tuple,int32_t id,uint64_t generation,uint64_t bytes,
               uint32_t originalTag,uint64_t demandNs) {
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
        }
        Entry e; e.tuple=tuple; e.generation=generation; e.bytes=bytes; e.originalTag=originalTag;
        e.demandNs=e.lastNs=demandNs;
        history.insert(std::make_pair(id,e)); current[tuple]=id;
    }
    void Launch(int32_t id,uint64_t now) {
        Entry &e=Find(id); Time(e,now);
        Need(e.state==CREATED,"Endpoint launch repeated or out of order");
        e.launchNs=e.lastNs=now; e.state=ACTIVE;
    }
    uint64_t Enter(int32_t id,uint64_t uid,uint32_t source,uint32_t destination,
                   TokenKind kind,uint64_t now) {
        Entry &e=Find(id); Time(e,now);
        Need(e.state==ACTIVE || e.state==ACK_COMPLETE || e.state==ENDPOINTS_RETIRED,
             "Packet token entered outside an open endpoint generation");
        Need(kind==CHANNEL || kind==HELD_TEST_COPY,"Unknown endpoint token kind");
        Need(nextToken<std::numeric_limits<uint64_t>::max(),"Endpoint token identity overflow");
        Token t; t.flowId=id; t.uid=uid; t.source=source; t.destination=destination;
        t.kind=kind; t.enteredNs=now;
        const uint64_t serial=nextToken++;
        tokens.insert(std::make_pair(serial,t));
        ++e.entered;
        if (kind==CHANNEL) ++e.outstandingChannel; else ++e.outstandingHeld;
        e.lastNs=now; return serial;
    }
    void Close(uint64_t serial,int32_t id,uint64_t uid,uint32_t source,uint32_t destination,uint64_t now) {
        auto it=tokens.find(serial);
        Need(it!=tokens.end(),"Unknown or twice-closed endpoint token");
        const Token &t=it->second;
        Need(t.flowId==id && t.uid==uid && t.source==source && t.destination==destination,
             "Endpoint token identity or directed link mismatch");
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
        Entry &e=Find(id); Time(e,now);
        Need(e.state==ACK_COMPLETE,"Endpoint retirement before completion or repeated");
        if (!actual.Retired()) return false;
        e.lastNs=now; e.state=ENDPOINTS_RETIRED; return true;
    }
    bool CertifyDrain(int32_t id,const EndpointSnapshot &actual,uint64_t now) {
        Entry &e=Find(id); Time(e,now);
        Need(e.state==ENDPOINTS_RETIRED,"Drain certification before endpoint retirement or repeated");
        if (!actual.Quiet() || e.outstandingChannel || e.outstandingHeld) return false;
        e.lastNs=now; e.state=DRAINED; return true;
    }
    bool SwitchCleared(int32_t id,const EndpointSnapshot &actual,uint64_t pinnedEntries,
                       uint64_t budgetEntries,uint64_t quotaEntries,uint64_t now) {
        Entry &e=Find(id); Time(e,now);
        Need(e.state==DRAINED,"Switch cleanup before certified drain or repeated");
        if (!actual.Quiet() || e.outstandingChannel || e.outstandingHeld ||
            pinnedEntries || budgetEntries || quotaEntries) return false;
        e.lastNs=now; e.state=SWITCH_CLEARED; return true;
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
