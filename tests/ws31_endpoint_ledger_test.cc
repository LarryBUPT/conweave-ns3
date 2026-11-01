#include "../src/point-to-point/model/ws31-endpoint-ledger.h"
#include <iostream>
#include <stdexcept>
using namespace ns3::ws31;

static void Require(bool ok,const char *message) { if (!ok) throw std::runtime_error(message); }
template<class F> static void Reject(F action) {
    bool rejected=false;
    try { action(); } catch (const std::logic_error &) { rejected=true; }
    Require(rejected,"Invalid lifecycle action was accepted");
}

// Portable mirror of fixed 1f keys, NOT a call into the actual transport.
// The later NS-3 adapter must compare against RdmaHw's real key functions.
static EndpointResources Resources(const EndpointKey &t) {
    EndpointResources r;
    r.sourceNode=std::get<0>(t); r.destinationNode=std::get<1>(t);
    r.txKey=(uint64_t(std::get<1>(t))<<32) | (uint64_t(std::get<2>(t))<<16) |
            uint64_t(std::get<3>(t)) | uint64_t(std::get<4>(t));
    r.rxKey=(uint64_t(std::get<0>(t))<<32) | (uint64_t(std::get<3>(t))<<16) |
            (uint64_t(std::get<4>(t))<<16) | uint64_t(std::get<2>(t));
    return r;
}

// Manually supplied evidence checks the core contract only. No NS-3 state is
// measured here, despite all categories being marked present in these mocks.
static EndpointSnapshot Quiet(const EndpointLedger &ledger,int32_t id,uint64_t now,bool released=false) {
    EndpointSnapshot s;
    s.observedFields=EndpointSnapshot::ALL; s.flowId=id;
    s.tuple=ledger.Get(id).tuple; s.generation=ledger.Get(id).generation; s.observedNs=now;
    s.txAbsent=s.rxAbsent=s.retainedQpsFinished=true;
    s.completionHistoryReleased=released;
    return s;
}

int main() {
    const EndpointKey tuple(1,2,1000,100,3);
    const EndpointResources resources=Resources(tuple);
    const EndpointLink firstLink(1,1,2,1), downstreamLink(2,2,3,1), parallelLink(1,2,2,2);
    EndpointLedger ledger;
    Reject([&]{ ledger.Begin(tuple,resources,0,1,8192,1,10); });
    ledger.Begin(tuple,resources,0,0,8192,1,10);
    Reject([&]{ ledger.Begin(tuple,resources,0,0,8192,1,10); });
    Reject([&]{ ledger.Begin(tuple,resources,1,1,8192,2,11); });
    Require(ledger.Requests()==1 && ledger.Get(0).state==EndpointLedger::CREATED,"Rejected begin mutated registry");
    const EndpointKey alias(1,2,1000,103,3);
    Require(Resources(alias).txKey==resources.txKey && Resources(alias).rxKey==resources.rxKey,"Actual packed-key alias missing");
    Reject([&]{ ledger.Begin(alias,Resources(alias),2,0,8192,2,11); });
    const EndpointKey pgAlias(1,2,1000,100,8);
    Require(Resources(pgAlias).txKey!=resources.txKey && Resources(pgAlias).rxKey!=resources.rxKey,"Route-only alias setup failed");
    Reject([&]{ ledger.Begin(pgAlias,Resources(pgAlias),3,0,8192,2,11); });
    Require(ledger.Requests()==1,"Aliased key registered before resource guard");
    Reject([&]{ ledger.Enter(0,7,firstLink,EndpointLedger::CHANNEL,11); });
    Reject([&]{ ledger.Launch(0,9); });
    ledger.Launch(0,15);
    Reject([&]{ ledger.Launch(0,16); });
    const uint64_t first=ledger.Enter(0,7,firstLink,EndpointLedger::CHANNEL,20);
    const uint64_t sameLink=ledger.Enter(0,7,firstLink,EndpointLedger::CHANNEL,20);
    const uint64_t downstream=ledger.Enter(0,7,downstreamLink,EndpointLedger::CHANNEL,21);
    const uint64_t held=ledger.Enter(0,7,firstLink,EndpointLedger::HELD_TEST_COPY,22);
    Require(first!=sameLink && sameLink!=downstream && downstream!=held && ledger.OutstandingTokens()==4 && ledger.Conserved(),"UID used as unique occupancy identity");
    Reject([&]{ ledger.Close(first,0,7,parallelLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,23); });
    Reject([&]{ ledger.Close(first,1,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,23); });
    Reject([&]{ ledger.Close(first,0,8,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,23); });
    Reject([&]{ ledger.Close(999,0,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,23); });
    Reject([&]{ ledger.Close(first,0,7,firstLink,EndpointLedger::HELD_TEST_COPY,EndpointLedger::HELD_DISCARDED,23); });
    Reject([&]{ ledger.Close(held,0,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,23); });
    Reject([&]{ ledger.Close(first,0,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::HELD_DISCARDED,23); });
    Require(ledger.OutstandingTokens()==4 && ledger.Get(0).closed==0 && ledger.Conserved(),"Rejected close mutated evidence");
    Reject([&]{ ledger.AckComplete(0,8191,30); });
    Reject([&]{ ledger.CertifyDrain(0,Quiet(ledger,0,30),30); });
    ledger.AckComplete(0,8192,30);
    EndpointSnapshot live=Quiet(ledger,0,31); live.txAbsent=false;
    Require(!ledger.Retire(0,live,31) && ledger.Get(0).state==EndpointLedger::ACK_COMPLETE,"Live sender map treated as retired");
    Reject([&]{ ledger.Retire(0,Quiet(ledger,0,30),30); });
    live=Quiet(ledger,0,31); live.rxTimers=1;
    Require(!ledger.Retire(0,live,31),"Live receiver timer ignored");
    live=Quiet(ledger,0,32); live.observedFields=EndpointSnapshot::MAPS;
    Reject([&]{ ledger.Retire(0,live,32); });
    live=Quiet(ledger,0,32); live.generation=1;
    Reject([&]{ ledger.Retire(0,live,32); });
    live=Quiet(ledger,0,32); live.flowId=99;
    Reject([&]{ ledger.Retire(0,live,32); });
    live=Quiet(ledger,0,32); live.tuple=alias;
    Reject([&]{ ledger.Retire(0,live,32); });
    live=Quiet(ledger,0,31);
    Reject([&]{ ledger.Retire(0,live,32); });
    Require(ledger.Retire(0,Quiet(ledger,0,32),32),"Retired endpoint evidence rejected");
    Require(!ledger.CertifyDrain(0,Quiet(ledger,0,33),33),"Outstanding tokens ignored");
    const uint64_t late=ledger.Enter(0,8,downstreamLink,EndpointLedger::CHANNEL,33);
    ledger.Close(first,0,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,34);
    Reject([&]{ ledger.Close(first,0,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,35); });
    ledger.Close(sameLink,0,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,34);
    ledger.Close(downstream,0,7,downstreamLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,35);
    ledger.Close(late,0,8,downstreamLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,35);
    Require(ledger.Get(0).outstandingChannel==0 && ledger.Get(0).outstandingHeld==1 && ledger.Conserved(),"Channel close discarded held copy");
    Require(!ledger.CertifyDrain(0,Quiet(ledger,0,36),36),"Held copy did not prevent drain");
    // Explicit discard of an UNSENT copy is not native stale-packet rejection.
    ledger.Close(held,0,7,firstLink,EndpointLedger::HELD_TEST_COPY,EndpointLedger::HELD_DISCARDED,38);
    uint64_t EndpointSnapshot::* fields[]={&EndpointSnapshot::dataQueueBytes,&EndpointSnapshot::ackQueueBytes,
        &EndpointSnapshot::transmitting,&EndpointSnapshot::deviceTimers,&EndpointSnapshot::pendingPayloadBytes};
    for (auto field:fields) {
        live=Quiet(ledger,0,39); live.*field=1;
        Require(!ledger.CertifyDrain(0,live,39),"Nonzero device/queue/payload observation ignored");
    }
    live=Quiet(ledger,0,39); live.retainedQpsFinished=false;
    Require(!ledger.CertifyDrain(0,live,39),"Retained active QP ignored");
    live=Quiet(ledger,0,39); live.rxAbsent=false;
    Require(!ledger.CertifyDrain(0,live,39),"Revived RX endpoint ignored");
    Require(ledger.CertifyDrain(0,Quiet(ledger,0,40),40) && ledger.Conserved(),"Quiet generation not certified");
    Reject([&]{ ledger.Enter(0,8,firstLink,EndpointLedger::CHANNEL,41); });
    Require(!ledger.SwitchCleared(0,Quiet(ledger,0,41),41),"Unreleased transport history ignored");
    uint64_t EndpointSnapshot::* stateFields[]={&EndpointSnapshot::pinnedEntries,&EndpointSnapshot::budgetEntries,&EndpointSnapshot::quotaEntries};
    for (auto field:stateFields) {
        live=Quiet(ledger,0,41,true); live.*field=1;
        Require(!ledger.SwitchCleared(0,live,41),"Live switch state ignored");
    }
    Require(ledger.SwitchCleared(0,Quiet(ledger,0,42,true),42),"Empty switch state rejected");
    Reject([&]{ ledger.Begin(tuple,resources,1,1,8192,2,100); });
    live=Quiet(ledger,0,100,true); live.rxAbsent=false;
    Reject([&]{ ledger.Begin(tuple,resources,1,1,8192,2,100,&live); });
    live=Quiet(ledger,0,99,true);
    Reject([&]{ ledger.Begin(tuple,resources,1,1,8192,2,100,&live); });
    live=Quiet(ledger,0,100,true);
    Reject([&]{ ledger.Begin(tuple,resources,1,2,8192,2,100,&live); });
    Reject([&]{ ledger.Begin(alias,Resources(alias),2,0,8192,2,100); });
    ledger.Begin(tuple,resources,1,1,8192,2,100,&live);
    Require(ledger.Requests()==2 && ledger.Get(0).entered==5 && ledger.Get(0).closed==5 &&
        ledger.Get(0).state==EndpointLedger::SWITCH_CLEARED && ledger.Get(1).generation==1 && ledger.Get(1).originalTag==2,
        "Reuse erased old generation or inherited evidence");
    Reject([&]{ ledger.Enter(0,7,firstLink,EndpointLedger::CHANNEL,101); });
    ledger.Launch(1,105);
    const uint64_t second=ledger.Enter(1,7,firstLink,EndpointLedger::CHANNEL,106);
    ledger.AckComplete(1,8192,110);
    ledger.Close(second,1,7,firstLink,EndpointLedger::CHANNEL,EndpointLedger::RECEIVE_RETURNED,110);
    Require(ledger.Retire(1,Quiet(ledger,1,111),111),"Second generation retirement failed");
    Require(ledger.CertifyDrain(1,Quiet(ledger,1,112),112),"Second generation drain failed");
    Require(ledger.SwitchCleared(1,Quiet(ledger,1,113,true),113),"Second generation clear failed");
    Require(ledger.Get(0).demandNs==10 && ledger.Get(0).launchNs==15 && ledger.Get(0).finishNs==30 &&
        ledger.Get(1).demandNs==100 && ledger.Get(1).launchNs==105 && ledger.Get(1).finishNs==110 &&
        ledger.Get(1).entered==1 && ledger.Get(1).closed==1 && ledger.Conserved() && ledger.OutstandingTokens()==0,
        "Two-generation evidence failed conservation or original timing");
    std::cout << "WS31_ENDPOINT_LEDGER PASS requests=2 completed_generations=2 closed_tokens=6 real_endpoint_snapshots=0 network_runs=0" << std::endl;
    return 0;
}
