#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/rdma-client.h"
#include "ns3/settings.h"
#include "ns3/ws31-start.h"
#include "ns3/ws31-label-fixture.h"
#include "ns3/ws30-v13-fixture.h"
#include <iostream>

namespace ns3 {
// This probe invokes production application methods, never a duplicate of the
// timer or cancellation logic. It does not install a simulation configuration.
class Ws31StartBoundaryProbe {
public:
    static void Start(Ptr<RdmaClient> app) { app->StartApplication(); }
    static void Stop(Ptr<RdmaClient> app) { app->StopApplication(); }
    static bool Pending(Ptr<RdmaClient> app) { return app->m_ws31Pending; }
    static EventId Launch(Ptr<RdmaClient> app) { return app->m_ws31LaunchEvent; }
};

class Ws31BoundaryClient : public RdmaClient {
public:
    static TypeId GetTypeId() {
        static TypeId tid=TypeId("ns3::Ws31BoundaryClient")
            .SetParent<RdmaClient>().AddConstructor<Ws31BoundaryClient>();
        return tid;
    }
    uint64_t calls=0, launchNs=0, demandNs=0;
protected:
    void DispatchRequest(uint64_t demand) override {
        ++calls; launchNs=Simulator::Now().GetNanoSeconds(); demandNs=demand;
        if (calls!=1 || Ws31StartBoundaryProbe::Pending(this) || ws31::StartData().launched!=1)
            NS_FATAL_ERROR("C2 transport dispatch is duplicated or precedes launch accounting");
        // No QP or completion is synthesized by this transport substitute.
    }
};
} // namespace ns3

using namespace ns3;

struct BoundaryCase {
    Ptr<Ws31BoundaryClient> app;
    uint64_t wait=0, controlNs=0;
    uint32_t phase=0;
    bool dispose=false;
    EventId control, launch;
};

static void Control(BoundaryCase *c) {
    c->controlNs=Simulator::Now().GetNanoSeconds();
    if (c->dispose) c->app->Dispose();
    else Ws31StartBoundaryProbe::Stop(c->app);
}

static void Begin(BoundaryCase *c) {
    // Both same-time orders are created explicitly. Application::SetStopTime
    // alone would normally enqueue only the control-before-launch order.
    const uint64_t offset=c->phase==0 ? c->wait-1 : c->phase==3 ? c->wait+1 : c->wait;
    if (c->phase==1)
        c->control=Simulator::Schedule(NanoSeconds(offset),&Control,c);
    Ws31StartBoundaryProbe::Start(c->app);
    c->launch=Ws31StartBoundaryProbe::Launch(c->app);
    if (c->phase!=1)
        c->control=Simulator::Schedule(NanoSeconds(offset),&Control,c);
    if (c->phase==4 && (c->app->calls!=1 || c->app->launchNs!=10))
        NS_FATAL_ERROR("C2 zero wait was not a synchronous launch");
    if (c->phase==1 && !(c->control.GetUid()<c->launch.GetUid()))
        NS_FATAL_ERROR("C2 control-before-launch event uid order missing");
    if (c->phase==2 && !(c->launch.GetUid()<c->control.GetUid()))
        NS_FATAL_ERROR("C2 launch-before-control event uid order missing");
}

int main() {
    if (ws31::LabelProfile()!=0 || Ws30V13TagTransform()!=0 || Ws30V13Life()!=0)
        NS_FATAL_ERROR("C2 boundary fixture requires label, transform and legacy lifecycle zero");
    Settings::lb_mode=43;
    const Ipv4Address sip("11.0.0.1"), dip("11.0.1.1");
    uint16_t sport=1;
    while (sport<65535 && ws31::StartDelay(43,2,8192,sip.Get(),dip.Get(),sport,100)<=1) ++sport;
    const uint64_t delayed=ws31::StartDelay(43,2,8192,sip.Get(),dip.Get(),sport,100);
    if (delayed<=1) NS_FATAL_ERROR("C2 fixture has no positive interior wait");
    const char *phases[]={"before","same-control-first","same-launch-first","after","zero"};
    for (unsigned kind=0; kind<2; ++kind) for (unsigned phase=0; phase<5; ++phase) {
        ws31::StartData()=ws31::StartCounters();
        BoundaryCase c; c.dispose=kind!=0; c.phase=phase; c.wait=phase==4?0:delayed;
        Ptr<Node> node=CreateObject<Node>();
        c.app=CreateObject<Ws31BoundaryClient>();
        // Deliberately bypass automatic Application scheduling, so the probe
        // starts exactly once and controls the equal-time uid order.
        c.app->SetNode(node);
        c.app->SetLocal(sip,sport); c.app->SetRemote(dip,100);
        c.app->SetPG(3); c.app->SetSize(8192);
        c.app->SetAttribute("WorkloadTag",UintegerValue(phase==4?1:2));
        c.app->SetAttribute("StatFlowID",IntegerValue(kind*5+phase));
        Simulator::Schedule(NanoSeconds(10),&Begin,&c);
        Simulator::Stop(NanoSeconds(1010)); Simulator::Run();
        const bool cancelled=phase<=1;
        const ws31::StartCounters s=ws31::StartData();
        if (s.demanded!=1 || s.demandBytes!=8192 || s.cancelled!=uint64_t(cancelled) ||
            s.launched!=uint64_t(!cancelled) || s.cancelBytes!=(cancelled?8192:0) ||
            s.launchBytes!=(cancelled?0:8192) || s.finished || s.finishBytes ||
            s.demanded!=s.launched+s.cancelled || s.demandBytes!=s.launchBytes+s.cancelBytes ||
            s.waited!=uint64_t(!cancelled && c.wait!=0) ||
            s.delaySum!=(cancelled?0:c.wait) || s.delayMax!=(cancelled?0:c.wait) ||
            c.app->calls!=s.launched || Ws31StartBoundaryProbe::Pending(c.app) ||
            c.controlNs!=10+(phase==0?c.wait-1:phase==3?c.wait+1:c.wait))
            NS_FATAL_ERROR("C2 boundary request/byte/time conservation failed");
        if (!cancelled && (c.app->demandNs!=10 || c.app->launchNs!=10+c.wait))
            NS_FATAL_ERROR("C2 dispatch lost the original demand clock");
        // Repeated controls, disposal and simulator destruction must not
        // reclassify an already launched request or double-count cancellation.
        Ws31StartBoundaryProbe::Stop(c.app);
        Ws31StartBoundaryProbe::Stop(c.app);
        c.app->Dispose(); c.app->Dispose(); Simulator::Destroy();
        const ws31::StartCounters &after=ws31::StartData();
        if (after.demanded!=s.demanded || after.demandBytes!=s.demandBytes ||
            after.launched!=s.launched || after.launchBytes!=s.launchBytes ||
            after.cancelled!=s.cancelled || after.cancelBytes!=s.cancelBytes ||
            after.finished || after.finishBytes || after.waited!=s.waited ||
            after.delaySum!=s.delaySum || after.delayMax!=s.delayMax || c.app->calls!=s.launched)
            NS_FATAL_ERROR("C2 repeated control/disposal changed terminal accounting");
        std::cout << "WS31_C2_BOUNDARY PASS kind=" << (kind?"dispose":"stop")
                  << " phase=" << phases[phase] << " demand_ns=10 wait_ns=" << c.wait
                  << " sip=" << sip.Get() << " dip=" << dip.Get() << " sport=" << sport
                  << " dport=100 tag=" << (phase==4?1:2) << " size=8192"
                  << " launch_uid=" << c.launch.GetUid() << " control_uid=" << c.control.GetUid()
                  << " control_ns=" << c.controlNs << " launched=" << s.launched
                  << " launch_ns=" << c.app->launchNs << " dispatch_demand_ns=" << c.app->demandNs
                  << " calls=" << c.app->calls << " demanded=" << s.demanded
                  << " demand_bytes=" << s.demandBytes << " launch_bytes=" << s.launchBytes
                  << " cancel_bytes=" << s.cancelBytes << " waited=" << s.waited
                  << " delay_sum_ns=" << s.delaySum << " delay_max_ns=" << s.delayMax
                  << " cancelled=" << s.cancelled << " finished=0 pending=0 transport=fixture" << std::endl;
    }
    std::cout << "WS31_C2_BOUNDARY_SUMMARY PASS cases=10 network_runs=0 completions=0" << std::endl;
    return 0;
}
