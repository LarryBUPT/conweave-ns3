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
template<class F> void Fail(const char *name,F operation) {
    bool caught=false;
    try { operation(); } catch (const std::runtime_error &) { caught=true; }
    Require(caught,"Expected controlled failure was not observed");
    std::cout << "WS31_ENDPOINT_CHANNEL_FAILURE case=" << name << '\n';
}
template<class F> void FailureMessage(const char *name,const char *expected,F operation) {
    bool caught=false;
    try { operation(); } catch (const std::exception &error) {
        caught=true; Require(std::string(error.what())==expected,"Original failure message was replaced");
    }
    Require(caught,"Expected original saved failure was not observed");
    std::cout << "WS31_ENDPOINT_CHANNEL_FAILURE case=" << name << " original_message=\"" << expected << "\"\n";
}
void FailAnimation(Ptr<const Packet>,Ptr<NetDevice>,Ptr<NetDevice>,Time,Time) {
    throw std::runtime_error("Controlled WS31 animation trace failure");
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
class UnregisteredOverride : public QbbChannel {
public:
    bool TransmitStart(Ptr<Packet>,Ptr<QbbNetDevice>,Time) override { return true; }
};
struct Pair {
    Ptr<Node> a=CreateObject<Node>(),b=CreateObject<Node>();
    Ptr<Receiver> x=CreateObject<Receiver>(),y=CreateObject<Receiver>();
    Ptr<QbbChannel> channel;
    explicit Pair(Ptr<QbbChannel> c=CreateObject<QbbChannel>()):channel(c) {
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
    auto packet=Create<Packet>(8); Ws31EndpointChannel::EncodeIdentity(packet,id,8);
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
            Refuse("negative-registration",[&](){ session.Register(-1,0); });
            Refuse("high-registration",[&](){ session.Register(65536,0); });
            Refuse("incomplete-channel",[&](){ session.Bind(CreateObject<QbbChannel>()); });
            Refuse("remote-channel",[&](){ session.Bind(CreateObject<QbbRemoteChannel>()); });
            Pair overriding(CreateObject<UnregisteredOverride>());
            Require(overriding.channel->GetInstanceTypeId()==QbbChannel::GetTypeId(),
                    "Overriding test channel should inherit the old TypeId");
            Refuse("unregistered-overriding-channel",[&](){ session.Bind(overriding.channel); });
            session.Bind(pair.channel);
            Ws31EndpointChannel other(ledger);
            Refuse("bound-owner",[&](){ other.Bind(pair.channel); });
            Refuse("missing-tag",[&](){ pair.channel->TransmitStart(Create<Packet>(8),pair.x,NanoSeconds(1)); });
            Refuse("negative-id-before-encoding",[&](){ Tagged(-1); });
            Refuse("high-id-before-encoding",[&](){ Tagged(65536); });
            for (int32_t id : {0,65535}) {
                auto boundary=Tagged(id); FlowIDNUMTag tag;
                Require(boundary->PeekPacketTag(tag) && tag.GetId()==id && tag.GetFlowSize()==8,
                        "Legal identity/initialized size did not round trip");
            }
            // Show why an input/producer domain gate is mandatory. These raw
            // alias demonstration packets are never transmitted or registered.
            for (int32_t id : {-1,65536}) {
                auto alias=Create<Packet>(8); FlowIDNUMTag tag; tag.SetId(id); tag.SetFlowSize(8);
                alias->AddPacketTag(tag); FlowIDNUMTag decoded;
                Require(alias->PeekPacketTag(decoded) && decoded.GetId()==(id==-1?65535:0),
                        "Baseline U16 alias demonstration changed");
            }
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
            Refuse("used-channel-rebind",[&](){ other.Bind(pair.channel); });
            std::cout << "WS31_ENDPOINT_CHANNEL case=observed calls=3 tokens=3 closed=3\n";
            Simulator::Destroy();
        }
        {
            Pair pair; auto ledger=Ledger(1); Ws31EndpointChannel session(ledger);
            session.Register(1,0); session.Bind(pair.channel);
            pair.y->action=[](Ptr<Packet>){ throw std::logic_error("controlled Receive failure"); };
            pair.channel->TransmitStart(Tagged(1),pair.x,NanoSeconds(1));
            Simulator::Run();
            Require(session.Failed(),"Receive exception was not retained outside the event");
            FailureMessage("receive-failure-after-run","controlled Receive failure",[&](){ session.RethrowFailure(); });
            Require(session.Open()==1 && ledger->OutstandingTokens()==1 &&
                    session.History().size()==1 && !session.History()[0].receiveReturned,
                    "Receive exception fabricated closure");
            Refuse("failed-channel-read",[&](){ session.Pending(); });
            Refuse("failed-channel-finish",[&](){ session.Finish(); });
            std::cout << "WS31_ENDPOINT_CHANNEL case=receive-exception open=1 closed=0\n";
            Simulator::Destroy();
            Require(ledger->OutstandingTokens()==1,"Destroy fabricated a drain certificate");
        }
        {
            Pair pair; auto ledger=Ledger(2); Ws31EndpointChannel session(ledger);
            auto packet=Create<Packet>(8);
            unsigned calls=0; pair.y->action=[&](Ptr<Packet>){ ++calls; };
            pair.channel->TransmitStart(packet,pair.x,NanoSeconds(1));
            Refuse("bind-after-default-scheduled",[&](){ session.Bind(pair.channel); });
            Simulator::Run(); Require(calls==1,"Rejected late binding changed default delivery");
            Refuse("bind-after-default-returned",[&](){ session.Bind(pair.channel); });
            std::cout << "WS31_ENDPOINT_CHANNEL case=late-bind calls=1\n";
            Simulator::Destroy();
        }
        // Controlled throws at allocation transaction boundaries. They are not
        // claims of actual allocator exhaustion or scheduler insertion failure.
        for (auto fault : {Ws31EndpointChannel::AFTER_LEDGER_ENTER,Ws31EndpointChannel::AFTER_HISTORY_APPEND}) {
            Pair pair; auto ledger=Ledger(3); Ws31EndpointChannel session(ledger);
            session.Register(3,0); session.Bind(pair.channel); session.ArmFaultForTesting(fault);
            Fail(fault==Ws31EndpointChannel::AFTER_LEDGER_ENTER?"after-ledger-enter":"after-history-append",
                 [&](){ pair.channel->TransmitStart(Tagged(3),pair.x,NanoSeconds(1)); });
            Require(session.Failed() && session.Open()==0 && ledger->OutstandingTokens()==1,
                    "Partial observer transaction lost failure/token evidence");
            Refuse("partial-enter-finish",[&](){ session.Finish(); });
            Simulator::Destroy();
        }
        {
            Pair pair; auto ledger=Ledger(4); Ws31EndpointChannel session(ledger);
            session.ArmFaultForTesting(Ws31EndpointChannel::BEFORE_BIND_COMMIT);
            Fail("bind-staged-before-commit",[&](){ session.Bind(pair.channel); });
            Require(!session.Failed() && session.Pending()==0 && session.Open()==0,
                    "Staged binding failure mutated a live observer");
            session.Bind(pair.channel); session.Finish();
            Ws31EndpointChannel next(ledger); next.Bind(pair.channel); next.Finish();
            std::cout << "WS31_ENDPOINT_CHANNEL case=atomic-bind retry=1\n";
            Simulator::Destroy();
        }
        {
            Pair pair; auto ledger=Ledger(5); Ws31EndpointChannel session(ledger);
            session.Register(5,0); session.Bind(pair.channel); session.FailNextScheduleForTesting(pair.channel);
            Fail("after-pending-before-schedule",[&](){ pair.channel->TransmitStart(Tagged(5),pair.x,NanoSeconds(1)); });
            Require(session.Failed() && session.Open()==1 && ledger->OutstandingTokens()==1,
                    "Scheduling boundary failure fabricated closure");
            Refuse("failed-schedule-finish",[&](){ session.Finish(); });
            Simulator::Destroy();
        }
        {
            Pair pair; auto ledger=Ledger(6); Ws31EndpointChannel session(ledger);
            session.Register(6,0); session.Bind(pair.channel);
            unsigned calls=0; pair.y->action=[&](Ptr<Packet>){ ++calls; };
            Require(pair.channel->TraceConnectWithoutContext("TxRxQbb",MakeCallback(&FailAnimation)),
                    "Animation failure trace was not connected");
            Fail("animation-after-schedule",[&](){ pair.channel->TransmitStart(Tagged(6),pair.x,NanoSeconds(1)); });
            Simulator::Run();
            Require(session.Failed() && calls==0 && session.Open()==1 && ledger->OutstandingTokens()==1,
                    "Animation failure was forgotten by a later delivery");
            FailureMessage("animation-original-failure-retained","Controlled WS31 animation trace failure",
                           [&](){ session.RethrowFailure(); });
            Refuse("failed-animation-finish",[&](){ session.Finish(); });
            Simulator::Destroy();
        }
        {
            Pair pair; auto ledger=Ledger(7); Ws31EndpointChannel session(ledger);
            session.Register(7,0); session.Bind(pair.channel);
            pair.y->action=[](Ptr<Packet>){};
            session.ArmFaultForTesting(Ws31EndpointChannel::LEAVE_BEFORE_CLOSE);
            pair.channel->TransmitStart(Tagged(7),pair.x,NanoSeconds(1)); Simulator::Run();
            Require(session.Failed() && session.Open()==1 && ledger->OutstandingTokens()==1 &&
                    !session.History()[0].receiveReturned,"Leave failure fabricated a returned token");
            FailureMessage("leave-failure-after-run","Controlled WS31 observer boundary failure",
                           [&](){ session.RethrowFailure(); });
            Refuse("failed-leave-finish",[&](){ session.Finish(); });
            Simulator::Destroy();
        }
        for (bool inflight : {false,true}) {
            Pair pair; auto ledger=Ledger(8);
            std::unique_ptr<Ws31EndpointChannel> owner(new Ws31EndpointChannel(ledger));
            owner->Register(8,0); owner->Bind(pair.channel);
            unsigned calls=0; pair.y->action=[&](Ptr<Packet>){ ++calls; };
            if (inflight) pair.channel->TransmitStart(Tagged(8),pair.x,NanoSeconds(1));
            owner.reset();
            Ws31EndpointChannel next(ledger);
            Refuse(inflight?"owner-lost-inflight":"owner-lost-idle",[&](){ next.Bind(pair.channel); });
            Simulator::Run();
            Require(calls==unsigned(inflight) && ledger->Get(8).closed==unsigned(inflight) &&
                    ledger->OutstandingTokens()==0,"Event callback used a destroyed session owner");
            std::cout << "WS31_ENDPOINT_CHANNEL case=owner-loss inflight=" << inflight
                      << " returned=" << calls << " normal_finish=0\n";
            Simulator::Destroy();
        }
        std::cout << "WS31_ENDPOINT_CHANNEL_SUMMARY PASS production_receive_calls=0 transport_completions=0\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "WS31_ENDPOINT_CHANNEL_FAIL " << error.what() << '\n';
        Simulator::Destroy(); return 1;
    }
}
