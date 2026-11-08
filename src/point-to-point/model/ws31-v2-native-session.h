#ifndef WS31_V2_NATIVE_SESSION_H
#define WS31_V2_NATIVE_SESSION_H

// Current-request policy capability only. No parser, future table or group data.
#include "ns3/rdma-queue-pair.h"
#include "ns3/simulator.h"
#include <limits>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

namespace ns3 {
class Ws31V2NativeSession;
class Ws31V2NativeRequest {
    friend class Ws31V2NativeSession;
    enum State { ISSUED, DEMANDED, BOUND, CANCELLED };
    std::weak_ptr<Ws31V2NativeSession> owner;
    uint32_t node, sip, dip, original, policy;
    int32_t id;
    uint16_t sport, dport, pg;
    uint64_t bytes, demand, launch=0;
    bool present;
    State state=ISSUED;
    Ptr<RdmaQueuePair> actual;
    Ws31V2NativeRequest():node(0),sip(0),dip(0),original(0),policy(0),id(-1),
        sport(0),dport(0),pg(0),bytes(0),demand(0),present(false) {}
public:
    ~Ws31V2NativeRequest()=default;
    Ws31V2NativeRequest(const Ws31V2NativeRequest &)=delete;
    Ws31V2NativeRequest &operator=(const Ws31V2NativeRequest &)=delete;
};

class Ws31V2NativeSession : public std::enable_shared_from_this<Ws31V2NativeSession> {
public:
    typedef std::shared_ptr<Ws31V2NativeRequest> Handle;
    struct Policy { uint32_t value; bool present; };
private:
    friend class Ws31V2NativeEntry;
    friend class Ws31V2NativeBindingFixture;
    std::map<int32_t,Handle> arrived;
    bool failed=false;
    std::string reason;
    uint64_t demandReads=0, bindings=0, packetReads=0, cancellations=0;
    void Need(bool ok,const char *message) {
        RequireHealthy();
        if (!ok) { Fail(message); throw std::logic_error(message); }
    }
    Ws31V2NativeRequest &Owned(const Handle &h) {
        Need(bool(h),"V2 current request handle missing");
        Need(h->owner.lock().get()==this,"V2 foreign session handle");
        auto it=arrived.find(h->id);
        Need(it!=arrived.end() && it->second==h,"V2 request is not actually issued");
        return *h;
    }
    void Fields(const Handle &h,uint32_t node,int32_t id,uint32_t sip,uint32_t dip,
                uint16_t sport,uint16_t dport,uint16_t pg,uint64_t bytes,
                uint32_t original,uint64_t demand) {
        const auto &r=Owned(h);
        Need(r.node==node && r.id==id && r.sip==sip && r.dip==dip &&
             r.sport==sport && r.dport==dport && r.pg==pg && r.bytes==bytes &&
             r.original==original && r.demand==demand,"V2 original request identity changed");
    }
    // Only the driver/fixture may issue, and only at the actual demand event.
    Handle IssueCurrent(uint32_t node,int32_t id,uint32_t sip,uint32_t dip,
                        uint16_t sport,uint16_t dport,uint16_t pg,uint64_t bytes,
                        uint32_t original,uint64_t demand,bool present,uint32_t policy,
                        uint64_t generation=0) {
        Need(Simulator::Now().GetNanoSeconds()>=0 &&
             demand==uint64_t(Simulator::Now().GetNanoSeconds()),"V2 issue is not current demand");
        Need(generation==0 && node<128 && id>=0 && id<=65535 && !arrived.count(id),
             "V2 invalid/repeated current identity or unsupported generation");
        Need(sip && dip && sport && dport && pg<8 && bytes>0 &&
             bytes<=std::numeric_limits<uint32_t>::max() && (original==1 || original==2),
             "V2 current identity range");
        Need(present || policy==0,"V2 absent policy is not canonical zero");
        Handle r(new Ws31V2NativeRequest());
        r->owner=shared_from_this(); r->node=node; r->id=id; r->sip=sip; r->dip=dip;
        r->sport=sport; r->dport=dport; r->pg=pg; r->bytes=bytes;
        r->original=original; r->demand=demand; r->present=present; r->policy=policy;
        arrived.insert(std::make_pair(id,r));
        return r;
    }
public:
    Ws31V2NativeSession()=default;
    Ws31V2NativeSession(const Ws31V2NativeSession &)=delete;
    Ws31V2NativeSession &operator=(const Ws31V2NativeSession &)=delete;
    void Fail(const char *message) { if (!failed) { failed=true; reason=message; } }
    void RequireHealthy() const {
        if (failed) throw std::logic_error("V2 session failed: "+reason);
    }
    static void FailHandle(const Handle &h,const char *message) {
        if (h) { auto owner=h->owner.lock(); if (owner) owner->Fail(message); }
    }
    void CheckIssued(const Handle &h) {
        Need(Owned(h).state==Ws31V2NativeRequest::ISSUED,"V2 handle not awaiting demand");
    }
    Policy Demand(const Handle &h,uint32_t node,int32_t id,uint32_t sip,uint32_t dip,
                  uint16_t sport,uint16_t dport,uint16_t pg,uint64_t bytes,uint32_t original) {
        const uint64_t now=Simulator::Now().GetNanoSeconds();
        Fields(h,node,id,sip,dip,sport,dport,pg,bytes,original,now);
        auto &r=Owned(h);
        Need(r.state==Ws31V2NativeRequest::ISSUED,"V2 demand repeated/out of order");
        r.state=Ws31V2NativeRequest::DEMANDED; ++demandReads;
        return Policy{r.policy,r.present};
    }
    void ValidateLaunch(const Handle &h,uint32_t node,int32_t id,uint32_t sip,uint32_t dip,
                        uint16_t sport,uint16_t dport,uint16_t pg,uint64_t bytes,
                        uint32_t original,uint64_t demand) {
        Fields(h,node,id,sip,dip,sport,dport,pg,bytes,original,demand);
        const auto &r=Owned(h);
        Need(r.state==Ws31V2NativeRequest::DEMANDED &&
             uint64_t(Simulator::Now().GetNanoSeconds())>=r.demand,
             "V2 launch missing demand/cancelled/repeated");
    }
    void BindActual(const Handle &h,uint32_t node,Ptr<RdmaQueuePair> qp) {
        Need(qp!=nullptr,"V2 actual QP missing");
        ValidateLaunch(h,node,qp->m_flow_id,qp->sip.Get(),qp->dip.Get(),qp->sport,
            qp->dport,qp->m_pg,qp->m_size,qp->m_workload_tag,qp->startTime.GetNanoSeconds());
        auto &r=Owned(h); r.launch=Simulator::Now().GetNanoSeconds();
        Need(qp->m_ws31LaunchDelayNs==r.launch-r.demand,"V2 QP launch delay changed");
        r.actual=qp; r.state=Ws31V2NativeRequest::BOUND; ++bindings;
    }
    Policy Packet(uint32_t node,Ptr<RdmaQueuePair> qp) {
        Need(qp!=nullptr,"V2 packet has no actual QP");
        auto it=arrived.find(qp->m_flow_id);
        Need(it!=arrived.end(),"V2 packet QP was not issued");
        const auto h=it->second;
        Fields(h,node,qp->m_flow_id,qp->sip.Get(),qp->dip.Get(),qp->sport,qp->dport,
               qp->m_pg,qp->m_size,qp->m_workload_tag,qp->startTime.GetNanoSeconds());
        const auto &r=Owned(h);
        Need(r.state==Ws31V2NativeRequest::BOUND && r.actual==qp &&
             uint64_t(Simulator::Now().GetNanoSeconds())>=r.launch &&
             qp->m_ws31LaunchDelayNs==r.launch-r.demand,"V2 packet has wrong/unbound QP");
        ++packetReads; return Policy{r.policy,r.present};
    }
    void CancelPending(const Handle &h,uint32_t node,int32_t id,uint32_t sip,uint32_t dip,
                       uint16_t sport,uint16_t dport,uint16_t pg,uint64_t bytes,
                       uint32_t original,uint64_t demand) {
        Fields(h,node,id,sip,dip,sport,dport,pg,bytes,original,demand);
        auto &r=Owned(h);
        Need(r.state==Ws31V2NativeRequest::DEMANDED &&
             uint64_t(Simulator::Now().GetNanoSeconds())>=r.demand,
             "V2 cancellation is not a pending request");
        r.state=Ws31V2NativeRequest::CANCELLED; ++cancellations;
    }
    uint64_t Issued() const { return arrived.size(); }
    uint64_t DemandReads() const { return demandReads; }
    uint64_t Bindings() const { return bindings; }
    uint64_t PacketReads() const { return packetReads; }
    uint64_t Cancellations() const { return cancellations; }
};
} // namespace ns3
#endif
