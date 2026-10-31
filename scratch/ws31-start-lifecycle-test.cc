#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/rdma-client.h"
#include "ns3/settings.h"
#include "ns3/ws31-start.h"
#include <iostream>
using namespace ns3;

static void DisposePending(Ptr<RdmaClient> app) { app->Dispose(); }
int main() {
    Settings::lb_mode=43;
    const Ipv4Address sip("11.0.0.1"), dip("11.0.1.1");
    uint16_t sport=1;
    while (sport<65535 && ws31::StartDelay(43,2,8192,sip.Get(),dip.Get(),sport,100)<=10) ++sport;
    if (ws31::StartDelay(43,2,8192,sip.Get(),dip.Get(),sport,100)<=10)
        NS_FATAL_ERROR("C2 lifecycle fixture lacks a pending interval");
    for (unsigned kind=0; kind<2; ++kind) {
        ws31::StartData()=ws31::StartCounters();
        Ptr<Node> node=CreateObject<Node>();
        Ptr<RdmaClient> app=CreateObject<RdmaClient>();
        app->SetLocal(sip,sport); app->SetRemote(dip,100); app->SetSize(8192); app->SetPG(3);
        app->SetAttribute("WorkloadTag",UintegerValue(2));
        app->SetAttribute("StatFlowID",IntegerValue(kind));
        node->AddApplication(app); app->SetStartTime(NanoSeconds(0));
        if (!kind) app->SetStopTime(NanoSeconds(1));
        else Simulator::Schedule(NanoSeconds(1),&DisposePending,app);
        Simulator::Stop(NanoSeconds(1000)); Simulator::Run();
        const ws31::StartCounters &s=ws31::StartData();
        // There is intentionally no RDMA driver: any uncancelled launch is an error.
        if (s.demanded!=1 || s.launched!=0 || s.cancelled!=1 || s.finished!=0 ||
            s.demandBytes!=8192 || s.cancelBytes!=8192 || s.launchBytes || s.finishBytes)
            NS_FATAL_ERROR("C2 pending cancellation violated request/byte conservation");
        Simulator::Destroy();
        if (ws31::StartData().cancelled!=1) NS_FATAL_ERROR("C2 disposal counted cancellation twice");
        std::cout << "WS31_C2_LIFECYCLE PASS kind=" << (kind?"dispose":"stop") << std::endl;
    }
    return 0;
}
