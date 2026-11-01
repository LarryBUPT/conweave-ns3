#ifndef WS31_ENDPOINT_CHANNEL_H
#define WS31_ENDPOINT_CHANNEL_H

// Fixture-only adapter. The network entry must validate its parsed G1 context
// before constructing/binding it. Normal simulation code never includes it.
#include "qbb-channel.h"
#include "qbb-net-device.h"
#include "ws31-endpoint-ledger.h"
#include "ns3/flow-id-num-tag.h"
#include "ns3/node.h"
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include <memory>
#include <limits>
#include <vector>
#include <map>
#include <stdexcept>

namespace ns3 {

class Ws31EndpointChannel {
public:
    struct Delivery {
        uint64_t serial=0, generation=0, uid=0, enteredNs=0, returnedNs=0;
        int32_t flowId=-1;
        uint32_t channelId=0, destinationContext=0;
        ws31::EndpointLink link;
        bool receiveReturned=false;
    };
private:
    struct State {
        std::shared_ptr<ws31::EndpointLedger> ledger;
        std::map<int32_t,uint64_t> registered;
        std::vector<Delivery> history;
        std::map<uint64_t,std::size_t> open;
    };
    std::shared_ptr<State> state;
    // State and callbacks do not own channels/devices; avoid reference cycles.
    std::vector<Ptr<QbbChannel>> channels;
    bool finished=false;
    static void Need(bool ok,const char *message) {
        if (!ok) throw std::logic_error(message);
    }
    static uint64_t Now() {
        const int64_t now=Simulator::Now().GetNanoSeconds();
        Need(now>=0,"Negative WS31 channel evidence time");
        return static_cast<uint64_t>(now);
    }
    static ws31::EndpointLink Link(Ptr<QbbNetDevice> source,Ptr<QbbNetDevice> destination) {
        Need(source!=nullptr && destination!=nullptr && source->GetNode()!=nullptr &&
             destination->GetNode()!=nullptr,"Missing WS31 directed channel endpoint");
        return ws31::EndpointLink(source->GetNode()->GetId(),source->GetIfIndex(),
                                  destination->GetNode()->GetId(),destination->GetIfIndex());
    }
    static uint64_t Enter(const std::shared_ptr<State> &s,uint32_t channelId,
                          const ws31::EndpointLink &forward,const ws31::EndpointLink &reverse,
                          Ptr<const Packet> packet,Ptr<QbbNetDevice> source,
                          Ptr<QbbNetDevice> destination) {
        Need(packet!=nullptr,"Missing WS31 channel packet");
        const auto link=Link(source,destination);
        Need(link==forward || link==reverse,"WS31 directed channel binding changed");
        FlowIDNUMTag tag;
        Need(packet->PeekPacketTag(tag) && tag.GetId()>=0,
             "WS31 observed channel packet lacks a valid flow identity");
        const int32_t id=tag.GetId();
        const auto registered=s->registered.find(id);
        Need(registered!=s->registered.end(),"Unregistered WS31 channel request");
        const auto &entry=s->ledger->Get(id);
        Need(entry.generation==registered->second,"WS31 channel generation changed");
        Delivery record;
        record.flowId=id; record.generation=entry.generation; record.uid=packet->GetUid();
        record.link=link; record.channelId=channelId;
        record.destinationContext=std::get<2>(link); record.enteredNs=Now();
        record.serial=s->ledger->Enter(id,record.uid,link,ws31::EndpointLedger::CHANNEL,record.enteredNs);
        s->history.push_back(record);
        Need(s->open.insert(std::make_pair(record.serial,s->history.size()-1)).second,
             "Repeated WS31 channel token serial");
        return record.serial;
    }
    static void Leave(const std::shared_ptr<State> &s,uint64_t serial) {
        auto open=s->open.find(serial);
        Need(open!=s->open.end(),"Unknown or twice-returned WS31 channel delivery");
        Delivery &record=s->history.at(open->second);
        Need(!record.receiveReturned && Simulator::GetContext()==record.destinationContext,
             "WS31 receive returned in the wrong context or more than once");
        Need(s->ledger->Get(record.flowId).generation==record.generation,
             "WS31 delivery returned to another generation");
        const uint64_t now=Now();
        s->ledger->Close(record.serial,record.flowId,record.uid,record.link,
                         ws31::EndpointLedger::CHANNEL,ws31::EndpointLedger::RECEIVE_RETURNED,now);
        record.returnedNs=now; record.receiveReturned=true;
        s->open.erase(open);
    }
public:
    explicit Ws31EndpointChannel(std::shared_ptr<ws31::EndpointLedger> ledger):state(new State) {
        Need(static_cast<bool>(ledger),"Missing WS31 endpoint ledger owner");
        state->ledger=ledger;
    }
    Ws31EndpointChannel(const Ws31EndpointChannel &)=delete;
    Ws31EndpointChannel &operator=(const Ws31EndpointChannel &)=delete;
    // No destructor cleanup: an unfinished owner must not discard open evidence.
    // Bound callbacks retain State/ledger without capturing this. Finish is explicit.
    void Register(int32_t id,uint64_t generation) {
        Need(!finished,"WS31 channel session already finished");
        Need(state->ledger->Get(id).generation==generation,"Wrong WS31 registration generation");
        Need(!state->registered.count(id),"Repeated WS31 channel registration");
        state->registered.insert(std::make_pair(id,generation));
    }
    void Bind(Ptr<QbbChannel> channel) {
        Need(!finished && channel!=nullptr,"Invalid WS31 channel binding session");
        // Remote/MPI and unknown overriding subclasses bypass this base wrapper.
        Need(channel->GetInstanceTypeId()==QbbChannel::GetTypeId(),
             "WS31 endpoint observation requires an exact local QbbChannel");
        Need(channel->m_nDevices==2 && !channel->m_ws31Owner &&
             !channel->m_ws31Enter && !channel->m_ws31Leave &&
             channel->m_ws31Pending==0 && !channel->m_ws31Failed,
             "WS31 channel is incomplete, already bound, pending, or failed");
        const auto forward=Link(channel->m_link[0].m_src,channel->m_link[0].m_dst);
        const auto reverse=Link(channel->m_link[1].m_src,channel->m_link[1].m_dst);
        Need(forward!=reverse && std::get<0>(forward)==std::get<2>(reverse) &&
             std::get<1>(forward)==std::get<3>(reverse) &&
             std::get<2>(forward)==std::get<0>(reverse) &&
             std::get<3>(forward)==std::get<1>(reverse),"Invalid WS31 duplex link binding");
        const auto shared=state;
        const uint32_t id=channel->GetId();
        channels.push_back(channel);
        channel->m_ws31Enter=[shared,id,forward,reverse](Ptr<const Packet> p,
                             Ptr<QbbNetDevice> src,Ptr<QbbNetDevice> dst) {
            return Enter(shared,id,forward,reverse,p,src,dst);
        };
        channel->m_ws31Leave=[shared](uint64_t serial) { Leave(shared,serial); };
        channel->m_ws31Owner=state.get();
    }
    uint64_t Pending() const {
        uint64_t count=0;
        for (const auto &channel:channels) {
            Need(channel->m_ws31Owner==state.get(),"WS31 channel owner changed");
            Need(!channel->m_ws31Failed,"WS31 channel delivery previously failed");
            Need(count<=std::numeric_limits<uint64_t>::max()-channel->m_ws31Pending,
                 "WS31 channel pending sum overflow");
            count+=channel->m_ws31Pending;
        }
        return count;
    }
    std::size_t Open() const { return state->open.size(); }
    const std::vector<Delivery> &History() const { return state->history; }
    void Finish() {
        Need(!finished && Pending()==0 && state->open.empty(),
             "WS31 channel session finished while deliveries remain");
        for (const auto &channel:channels) {
            channel->m_ws31Enter=QbbChannel::Ws31Enter();
            channel->m_ws31Leave=QbbChannel::Ws31Leave();
            channel->m_ws31Owner=nullptr;
        }
        channels.clear(); finished=true;
    }
};

} // namespace ns3
#endif
