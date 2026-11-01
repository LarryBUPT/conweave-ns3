#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "../src/point-to-point/model/ws31-endpoint-channel.h"
#include <functional>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

using namespace ns3;
using namespace ns3::ws31;

namespace {
void Require(bool ok,const char *message) {
    if (!ok) throw std::runtime_error(message);
}
template<class F> void Refuse(const char *name,F operation) {
    bool caught=false;
    try { operation(); } catch (const std::logic_error &) { caught=true; }
    Require(caught,"Expected channel refusal was not observed");
    std::cout << "WS31_ENDPOINT_CHANNEL_REFUSE case=" << name << '\n';
}
// This fixture deliberately substitutes Receive. It verifies the original
// channel event/virtual-call boundary, not production NIC/switch/transport paths.
class Receiver : public QbbNetDevice {
public:
    std::function<void(Ptr<Packet>)> action;
    void Receive(Ptr<Packet> packet) override {
        Require(static_cast<bool>(action),"Missing controlled Receive action");
        action(packet);
    }
};
struct Pair {
    Ptr<Node> a=CreateObject<Node>(),b=CreateObject<Node>();
    Ptr<Receiver> x=CreateObject<Receiver>(),y=CreateObject<Receiver>();
    Ptr<QbbChannel> channel=CreateObject<QbbChannel>();
    Pair() {
        channel->SetAttribute("Delay",TimeValue(NanoSeconds(3)));
        a->AddDevice(x); b->AddDevice(y); x->Attach(channel); y->Attach(channel);
    }
};
std::shared_ptr<EndpointLedger> Ledger(int32_t id) {
    auto ledger=std::make_shared<EndpointLedger>();
    EndpointResources resources; resources.sourceNode=0; resources.destinationNode=1;
    resources.txKey=11; resources.rxKey=12;
    ledger->Begin(EndpointKey(1,2,100,200,1),resources,id,0,8,1,0);
    ledger->Launch(id,0); return ledger;
}
Ptr<Packet> Tagged(int32_t id) {
    auto packet=Create<Packet>(8); FlowIDNUMTag tag; tag.SetId(id); packet->AddPacketTag(tag);
    return packet;
}
}

int main() {
    try {
        // Default-off keeps the direct event and virtual Receive dispatch.
        {
            Pair pair; unsigned calls=0;
            auto packet=Create<Packet>(8); const auto uid=packet->GetUid();
            pair.y->action=[&](Ptr<Packet> actual) {
                Require(actual==packet && actual->GetUid()==uid,"Default packet identity changed");
                Require(Simulator::Now()==NanoSeconds(13) && Simulator::GetContext()==pair.b->GetId(),
                        "Default delivery time/context changed"); ++calls;
            };
            pair.channel->TransmitStart(packet,pair.x,NanoSeconds(10));
            Simulator::Run(); Require(calls==1,"Default delivery count changed");
            std::cout << "WS31_ENDPOINT_CHANNEL case=default-off calls=1 time_ns=13\n";
            Simulator::Destroy();
        }
        {
            Pair pair; auto ledger=Ledger(0); Ws31EndpointChannel session(ledger);
            session.Register(0,0);
            Refuse("duplicate-registration",[&](){ session.Register(0,0); });
            Refuse("wrong-registration-generation",[&](){ session.Register(0,1); });
            Refuse("incomplete-channel",[&](){ session.Bind(CreateObject<QbbChannel>()); });
            Refuse("remote-channel",[&](){ session.Bind(CreateObject<QbbRemoteChannel>()); });
            session.Bind(pair.channel);
            Ws31EndpointChannel other(ledger);
            Refuse("bound-owner",[&](){ other.Bind(pair.channel); });
            Refuse("missing-tag",[&](){ pair.channel->TransmitStart(Create<Packet>(8),pair.x,NanoSeconds(1)); });
            Refuse("negative-tag",[&](){ pair.channel->TransmitStart(Tagged(-1),pair.x,NanoSeconds(1)); });
            Refuse("unregistered-flow",[&](){ pair.channel->TransmitStart(Tagged(99),pair.x,NanoSeconds(1)); });
            auto packet=Tagged(0); const uint64_t uid=packet->GetUid();
            Refuse("wrong-source",[&](){ pair.channel->TransmitStart(packet,CreateObject<Receiver>(),NanoSeconds(1)); });
            Require(session.Open()==0 && session.Pending()==0 && ledger->Get(0).entered==0,
                    "Rejected input created a token");
            unsigned calls=0;
            pair.y->action=[&](Ptr<Packet> actual) {
                ++calls;
                Require(actual==packet && Simulator::Now()==NanoSeconds(13) &&
                        Simulator::GetContext()==pair.b->GetId(),"Observed packet/time/context changed");
                Require(session.Pending()==2 && session.Open()==2 && ledger->Get(0).outstandingChannel==2,
                        "Receive observed premature closure");
                Refuse(calls==1?"finish-inside-first-receive":"finish-inside-second-receive",[&](){ session.Finish(); });
                if (calls==1) {
                    pair.channel->TransmitStart(actual,pair.y,NanoSeconds(0));
                    Require(session.Pending()==3 && session.Open()==3,"Nested delivery lost its parent token");
                }
            };
            pair.x->action=[&](Ptr<Packet> actual) {
                ++calls;
                Require(actual==packet && Simulator::Now()==NanoSeconds(16) &&
                        Simulator::GetContext()==pair.a->GetId(),"Nested reverse delivery changed");
                Require(session.Pending()==1 && session.Open()==1,"Nested token closed before Receive returned");
            };
            pair.channel->TransmitStart(packet,pair.x,NanoSeconds(10));
            pair.channel->TransmitStart(packet,pair.x,NanoSeconds(10));
            Refuse("finish-inflight",[&](){ session.Finish(); });
            Refuse("rebind-inflight",[&](){ other.Bind(pair.channel); });
            Simulator::Run();
            Require(calls==3 && session.Pending()==0 && session.Open()==0 &&
                    ledger->OutstandingTokens()==0 && ledger->Get(0).entered==3 && ledger->Get(0).closed==3,
                    "Observed delivery accounting mismatch");
            const auto &history=session.History(); Require(history.size()==3,"Wrong channel history size");
            for (std::size_t i=0;i<history.size();++i) {
                const auto &r=history[i];
                Require(r.serial==i+1 && r.uid==uid && r.flowId==0 && r.generation==0 && r.receiveReturned,
                        "Serial/UID/generation/return record mismatch");
                Require(r.enteredNs==(i<2?0:13) && r.returnedNs==(i<2?13:16),"Wrong recorded channel timing");
                Require(r.link==(i<2?EndpointLink(pair.a->GetId(),pair.x->GetIfIndex(),pair.b->GetId(),pair.y->GetIfIndex()):
                                             EndpointLink(pair.b->GetId(),pair.y->GetIfIndex(),pair.a->GetId(),pair.x->GetIfIndex())),
                        "Wrong recorded directed link");
                std::cout << "WS31_ENDPOINT_CHANNEL_TOKEN serial=" << r.serial << " uid=" << r.uid
                    << " enter_ns=" << r.enteredNs << " return_ns=" << r.returnedNs
                    << " destination_context=" << r.destinationContext << '\n';
            }
            session.Finish(); Refuse("finish-twice",[&](){ session.Finish(); });
            other.Bind(pair.channel); other.Finish();
            std::cout << "WS31_ENDPOINT_CHANNEL case=observed calls=3 tokens=3 closed=3\n";
            Simulator::Destroy();
        }
        {
            Pair pair; auto ledger=Ledger(1); Ws31EndpointChannel session(ledger);
            session.Register(1,0); session.Bind(pair.channel);
            pair.y->action=[](Ptr<Packet>){ throw std::logic_error("controlled Receive failure"); };
            pair.channel->TransmitStart(Tagged(1),pair.x,NanoSeconds(1));
            Refuse("receive-throws",[](){ Simulator::Run(); });
            Require(session.Open()==1 && ledger->OutstandingTokens()==1 &&
                    session.History().size()==1 && !session.History()[0].receiveReturned,
                    "Receive exception fabricated closure");
            Refuse("failed-channel-read",[&](){ session.Pending(); });
            Refuse("failed-channel-finish",[&](){ session.Finish(); });
            std::cout << "WS31_ENDPOINT_CHANNEL case=receive-exception open=1 closed=0\n";
            Simulator::Destroy();
            Require(ledger->OutstandingTokens()==1,"Destroy fabricated a drain certificate");
        }
        std::cout << "WS31_ENDPOINT_CHANNEL_SUMMARY PASS production_receive_calls=0 transport_completions=0\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "WS31_ENDPOINT_CHANNEL_FAIL " << error.what() << '\n';
        Simulator::Destroy(); return 1;
    }
}
