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

int main() {
    const EndpointKey tuple(1,2,1000,100,3);
    EndpointLedger ledger;
    EndpointSnapshot quiet;
    quiet.txAbsent=quiet.rxAbsent=quiet.retainedQpsFinished=true;
    Reject([&]{ ledger.Begin(tuple,0,1,8192,1,10); });
    ledger.Begin(tuple,0,0,8192,1,10);
    Reject([&]{ ledger.Begin(tuple,0,0,8192,1,10); });
    Reject([&]{ ledger.Begin(tuple,1,1,8192,2,11); });
    Require(ledger.Requests()==1 && ledger.Get(0).state==EndpointLedger::CREATED,"Rejected begin mutated request registry");
    Reject([&]{ ledger.Enter(0,7,1,2,EndpointLedger::CHANNEL,11); });
    Reject([&]{ ledger.Launch(0,9); });
    ledger.Launch(0,15);
    Reject([&]{ ledger.Launch(0,16); });
    const uint64_t first=ledger.Enter(0,7,1,2,EndpointLedger::CHANNEL,20);
    // A same-UID downstream transmission and held copy are distinct tokens.
    const uint64_t downstream=ledger.Enter(0,7,2,3,EndpointLedger::CHANNEL,21);
    const uint64_t held=ledger.Enter(0,7,1,2,EndpointLedger::HELD_TEST_COPY,22);
    Require(first!=downstream && downstream!=held && ledger.OutstandingTokens()==3 && ledger.Conserved(),"Packet UID was incorrectly used as unique occupancy identity");
    Reject([&]{ ledger.Close(first,0,7,2,1,23); });
    Reject([&]{ ledger.Close(first,1,7,1,2,23); });
    Require(ledger.OutstandingTokens()==3 && ledger.Get(0).closed==0 && ledger.Conserved(),"Rejected token close mutated evidence");
    Reject([&]{ ledger.AckComplete(0,8191,30); });
    Reject([&]{ ledger.CertifyDrain(0,quiet,30); });
    ledger.AckComplete(0,8192,30);
    EndpointSnapshot live=quiet; live.txAbsent=false;
    Require(!ledger.Retire(0,live,31) && ledger.Get(0).state==EndpointLedger::ACK_COMPLETE,"Live sender map was treated as retired");
    live=quiet; live.rxTimers=1;
    Require(!ledger.Retire(0,live,31),"Live receiver timer was ignored");
    Require(ledger.Retire(0,quiet,32),"Actual retired endpoint evidence rejected");
    Require(!ledger.CertifyDrain(0,quiet,33),"Active channel and held-copy tokens were ignored");
    ledger.Close(first,0,7,1,2,34);
    Reject([&]{ ledger.Close(first,0,7,1,2,35); });
    ledger.Close(downstream,0,7,2,3,35);
    Require(ledger.Get(0).outstandingChannel==0 && ledger.Get(0).outstandingHeld==1 && ledger.Conserved(),"Channel completion silently discarded held test copy");
    Require(!ledger.CertifyDrain(0,quiet,36),"Held old-generation test copy did not prevent drain");
    Reject([&]{ ledger.Begin(tuple,1,1,8192,2,37); });
    // The holder explicitly releases/discards its unsent test copy. This is
    // not a simulated old-packet receive rejection or native epoch protocol.
    ledger.Close(held,0,7,1,2,38);
    live=quiet; live.dataQueueBytes=1;
    Require(!ledger.CertifyDrain(0,live,39),"Data queue bytes ignored");
    live=quiet; live.ackQueueBytes=1;
    Require(!ledger.CertifyDrain(0,live,39),"Feedback queue bytes ignored");
    live=quiet; live.transmitting=1;
    Require(!ledger.CertifyDrain(0,live,39),"Current serialization ignored");
    live=quiet; live.retainedQpsFinished=false;
    Require(!ledger.CertifyDrain(0,live,39),"Retained active QP reference ignored");
    Require(ledger.CertifyDrain(0,quiet,40) && ledger.Conserved(),"Quiet retired generation not certified");
    Reject([&]{ ledger.Enter(0,8,1,2,EndpointLedger::CHANNEL,41); });
    Require(!ledger.SwitchCleared(0,quiet,1,0,0,41),"Live pinned route ignored");
    Require(!ledger.SwitchCleared(0,quiet,0,1,0,41),"Live prediction ignored");
    Require(!ledger.SwitchCleared(0,quiet,0,0,1,41),"Live quota entry ignored");
    Require(ledger.SwitchCleared(0,quiet,0,0,0,42),"Actual empty switch state rejected");
    Reject([&]{ ledger.Begin(tuple,1,2,8192,2,43); });
    Reject([&]{ ledger.Begin(tuple,1,1,8192,2,41); });
    ledger.Begin(tuple,1,1,8192,2,100);
    Require(ledger.Requests()==2 && ledger.Get(0).state==EndpointLedger::SWITCH_CLEARED &&
            ledger.Get(0).entered==3 && ledger.Get(0).closed==3 && ledger.Get(0).originalTag==1 &&
            ledger.Get(1).generation==1 && ledger.Get(1).originalTag==2 &&
            ledger.Get(1).entered==0 && ledger.Get(1).demandNs==100 && ledger.Conserved(),
            "Next generation erased historical identity or inherited old evidence");
    Reject([&]{ ledger.Enter(0,7,1,2,EndpointLedger::CHANNEL,101); });
    std::cout << "WS31_ENDPOINT_LEDGER PASS requests=2 closed_tokens=3 real_endpoint_snapshots=0 network_runs=0" << std::endl;
    return 0;
}
