#ifndef WS31_V2_NATIVE_ENTRY_H
#define WS31_V2_NATIVE_ENTRY_H

// Simulation entry only. The complete declaration never enters online state.
// This header installs no network topology or completion/retirement wrapper.
#include "ns3/rdma-client.h"
#include "ns3/rdma-driver.h"
#include "ns3/ipv4.h"
#include "ns3/integer.h"
#include "ns3/uinteger.h"
#include "ns3/simulator.h"
#include "ns3/settings.h"
#include "ns3/ws31-v2-native-declarations.h"
#include "ns3/ws31-v2-native-session.h"
#include "ns3/ws31-label-fixture.h"
#include "ns3/ws30-v13-fixture.h"
#include <exception>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace ns3 {
class Ws31V2NativeEntry {
public:
    struct PairTiming {
        uint64_t bdp, rtt;
        PairTiming(uint64_t b, uint64_t r):bdp(b),rtt(r) {}
    };
    typedef std::map<std::pair<uint32_t,uint32_t>,PairTiming> PairTimings;
    typedef std::map<uint32_t,Ptr<Node>> Hosts;
    struct RunConfig {
        uint32_t mode, hasWindow, globalTiming, mtu, ccMode;
        uint64_t maxBdp, maxRtt;
        bool irn;
        PairTimings pairs;
        RunConfig(uint32_t m,uint32_t w,uint32_t g,uint64_t b,uint64_t r,
                  const PairTimings &p,uint32_t packetMtu,uint32_t cc,bool enableIrn)
            :mode(m),hasWindow(w),globalTiming(g),mtu(packetMtu),ccMode(cc),
             maxBdp(b),maxRtt(r),irn(enableIrn),pairs(p) {}
    };
    struct Arrival {
        uint32_t ordinal;
        int32_t id;
        uint64_t actualNs;
        bool clientCreated=false, clientStarted=false;
        Arrival(uint32_t i,int32_t request,uint64_t t):ordinal(i),id(request),actualNs(t) {}
    };
    struct Diagnostics {
        bool entryFinished=false, failed=false;
        std::string firstError;
        uint64_t declared=0, entered=0, issued=0, demandReads=0, bindings=0;
        uint64_t packetReads=0, cancellations=0, clients=0, pending=0;
        // unentered includes callbacks rejected before admission, not only unrun events.
        uint64_t unentered=0, liveQPs=0;
        size_t declarationCapacity=0, eventCapacity=0, clientCapacity=0;
        size_t declarationElementBytes=sizeof(ws31v2::Declaration);
        std::vector<Arrival> arrivals;
    };
private:
    friend class Ws31V2NativeEntryFixture;
    enum Phase { NEW, INSTALLED, RUNNING, FINISHED, FAILED };
    Phase phase=NEW;
    std::shared_ptr<Ws31V2NativeSession> session;
    std::unique_ptr<ws31v2::DeclaredInput> input;
    std::unique_ptr<RunConfig> config;
    Hosts hosts;
    std::map<uint32_t,Ptr<RdmaHw>> hardware;
    std::vector<EventId> events;
    std::vector<Ptr<RdmaClient>> clients;
    std::vector<Arrival> arrivals;
    uint32_t nextOrdinal=0;
    std::string firstError;

    static void Need(bool ok,const char *message) {
        if (!ok) throw std::logic_error(message);
    }
    static std::string ActiveError() {
        try { throw; }
        catch (const std::exception &e) { return e.what(); }
        catch (...) { return "V2 entry non-standard exception"; }
    }
    static uint64_t NowNs() {
        const int64_t now=Simulator::Now().GetNanoSeconds();
        Need(now>=0,"V2 entry negative simulation time");
        return uint64_t(now);
    }
    void FailAll(const std::string &message) {
        if (firstError.empty()) firstError=message;
        session->Fail(firstError.c_str());
        phase=FAILED;
        for (const auto &event:events) Simulator::Cancel(event);
        // Failure withdrawal is not a successful pending-request cancellation.
        for (const auto &client:clients) if (client) client->FailWs31V2();
    }
    void CheckEnvironment() const {
        Need(bool(config),"V2 entry configuration missing");
        Need(Settings::lb_mode==config->mode && Ws30V13Life()==0 &&
             Ws30V13TagTransform()==0 && ws31::LabelProfile()==0,
             "V2 entry mode/lifecycle/tag/profile changed");
        session->RequireHealthy();
    }
    Ptr<RdmaHw> CheckHost(uint32_t id,uint32_t ip,bool requireFrozen) const {
        const auto found=hosts.find(id);
        Need(found!=hosts.end() && found->second,"V2 entry host missing");
        Ptr<Node> node=found->second;
        Need(node->GetId()==id && node->GetNodeType()==0,"V2 entry actual Node identity mismatch");
        auto driver=node->GetObject<RdmaDriver>();
        Need(driver && driver->m_node==node && driver->m_rdma &&
             driver->m_rdma->m_node==node,"V2 entry Driver/Hw owner mismatch");
        Ptr<RdmaHw> hw=driver->m_rdma;
        if (requireFrozen) {
            const auto saved=hardware.find(id);
            Need(saved!=hardware.end() && saved->second==hw,"V2 entry hardware replaced");
        }
        Need(hw->m_mtu==config->mtu && hw->m_cc_mode==config->ccMode && hw->m_irn==config->irn,
             "V2 entry actual transport configuration mismatch");
        Need(!hw->m_qpCompleteCallback.IsNull(),"V2 entry original completion callback missing");
        auto ipv4=node->GetObject<Ipv4>();
        Need(ipv4!=nullptr,"V2 entry actual Ipv4 missing");
        uint32_t matches=0;
        for (uint32_t iface=0;iface<ipv4->GetNInterfaces();++iface) {
            for (uint32_t addr=0;addr<ipv4->GetNAddresses(iface);++addr) {
                if (ipv4->GetAddress(iface,addr).GetLocal().Get()!=ip) continue;
                ++matches;
                auto device=DynamicCast<QbbNetDevice>(ipv4->GetNetDevice(iface));
                Need(device && device->GetNode()==node && ipv4->IsUp(iface),
                     "V2 entry business address is not on an owned/up Qbb interface");
                uint32_t deviceMatches=0;
                for (uint32_t index=0;index<node->GetNDevices();++index) {
                    if (node->GetDevice(index)!=device) continue;
                    ++deviceMatches;
                    Need(index<hw->m_nic.size() && hw->m_nic[index].dev==device &&
                         hw->m_nic[index].qpGrp && device->m_rdmaEQ &&
                         device->m_rdmaEQ->m_qpGrp==hw->m_nic[index].qpGrp,
                         "V2 entry interface/device/NIC group mismatch");
                }
                Need(deviceMatches==1,"V2 entry ambiguous Node device index");
            }
        }
        Need(matches==1,"V2 entry business address missing or ambiguous");
        return hw;
    }
    static void CheckRoute(Ptr<RdmaHw> hw,uint32_t destination) {
        const auto route=hw->m_rtTable.find(destination);
        Need(route!=hw->m_rtTable.end() && !route->second.empty(),"V2 entry route missing");
        for (int index:route->second) {
            Need(index>=0 && size_t(index)<hw->m_nic.size() &&
                 uint32_t(index)<hw->m_node->GetNDevices(),"V2 entry route NIC index invalid");
            const auto &nic=hw->m_nic[index];
            Need(nic.dev && nic.qpGrp && nic.dev->GetNode()==hw->m_node &&
                 hw->m_node->GetDevice(index)==nic.dev && nic.dev->m_rdmaEQ &&
                 nic.dev->m_rdmaEQ->m_qpGrp==nic.qpGrp,"V2 entry route device/group mismatch");
        }
    }
    PairTiming Timing(const ws31v2::Declaration &r) const {
        if (config->globalTiming) return PairTiming(config->maxBdp,config->maxRtt);
        const auto value=config->pairs.find(std::make_pair(r.source,r.destination));
        Need(value!=config->pairs.end(),"V2 entry explicit pair BDP/RTT missing");
        return value->second;
    }
    void CheckRequest(const ws31v2::Declaration &r,bool requireFrozen) const {
        auto source=CheckHost(r.source,r.sourceIp,requireFrozen);
        auto destination=CheckHost(r.destination,r.destinationIp,requireFrozen);
        CheckRoute(source,r.destinationIp);
        CheckRoute(destination,r.sourceIp);
        const auto timing=Timing(r);
        Need(timing.rtt>0 && timing.rtt<=uint64_t(std::numeric_limits<int64_t>::max()) &&
             (!config->hasWindow || (timing.bdp>0 && timing.bdp<=std::numeric_limits<uint32_t>::max())),
             "V2 entry selected window/RTT out of range");
    }
    void CheckTerminalContext() const {
        session->RequireHealthy();
        CheckEnvironment();
        Need(bool(input),"V2 entry terminal input missing");
        // Point check of the observed terminal context, not transient-mutation detection.
        for (const auto &r:input->requests) CheckRequest(r,true);
    }
    void OnDemand(uint32_t ordinal) try {
        Need(phase==RUNNING && input && ordinal<input->requests.size(),"V2 entry demand phase/index");
        CheckEnvironment();
        const auto &r=input->requests[ordinal];
        Need(ordinal==nextOrdinal && NowNs()==r.demandNs,"V2 entry demand order/time changed");
        CheckRequest(r,true);
        ++nextOrdinal;
        arrivals.emplace_back(ordinal,r.id,NowNs());
        auto client=CreateObject<RdmaClient>();
        clients[ordinal]=client;
        arrivals.back().clientCreated=true;
        client->SetNode(hosts.find(r.source)->second);
        client->SetLocal(Ipv4Address(r.sourceIp),r.sport);
        client->SetRemote(Ipv4Address(r.destinationIp),r.dport);
        client->SetPG(r.pg); client->SetSize(r.bytes);
        client->SetAttribute("StatFlowID",IntegerValue(r.flowId));
        client->SetAttribute("WorkloadTag",UintegerValue(r.originalTag));
        const auto timing=Timing(r);
        client->SetAttribute("Window",UintegerValue(config->hasWindow?timing.bdp:0));
        client->SetAttribute("BaseRtt",UintegerValue(timing.rtt));
        client->RequireWs31V2Input(session);
        auto handle=session->IssueCurrent(r.source,r.id,r.sourceIp,r.destinationIp,r.sport,r.dport,
            r.pg,r.bytes,r.originalTag,r.demandNs,r.policyPresent,r.policyTag,r.generation);
        client->BindWs31V2Current(handle);
        // No AddApplication/helper/Application::Start: one manual demand only.
        client->StartApplication();
        arrivals.back().clientStarted=true;
    } catch (...) { FailAll(ActiveError()); throw; }
public:
    Ws31V2NativeEntry():session(std::make_shared<Ws31V2NativeSession>()) {}
    Ws31V2NativeEntry(const Ws31V2NativeEntry &)=delete;
    Ws31V2NativeEntry &operator=(const Ws31V2NativeEntry &)=delete;
    ~Ws31V2NativeEntry() {
        if (phase==INSTALLED || phase==RUNNING) FailAll("V2 entry disposed before terminal run");
        for (const auto &event:events) Simulator::Cancel(event);
        for (const auto &client:clients) if (client) {
            // FailAll has cleared failure-pending timers; normal terminal has none.
            try { client->Dispose(); }
            catch (...) { session->Fail("V2 entry Client disposal failed"); }
        }
    }
    void Install(std::istream &declarations,const Hosts &actualHosts,const RunConfig &runConfig) try {
        Need(phase==NEW,"V2 entry installation repeated or failed");
        session->RequireHealthy();
        config.reset(new RunConfig(runConfig));
        const bool c1Mode=config->mode==36 || config->mode==37 || config->mode==38 ||
            config->mode==42 || config->mode==53 || config->mode==54;
        Need((config->mode==12 || config->mode==33 || config->mode==43 || c1Mode) && config->hasWindow<=1 &&
             config->globalTiming<=1 && config->mtu==1000 && config->ccMode==1 && !config->irn,
             "V2 entry unsupported finite configuration");
        input.reset(new ws31v2::DeclaredInput(ws31v2::ReadDeclarations(declarations)));
        Need(input->requests.size()==1120 && !input->requests.empty(),"V2 entry declaration count");
        const uint64_t now=NowNs();
        Need(input->requests.front().demandNs>=now && input->stop>now &&
             input->stop<=uint64_t(std::numeric_limits<int64_t>::max()),"V2 entry late/out-of-range installation");
        hosts=actualHosts;
        CheckEnvironment();
        std::set<RdmaHw*> distinct;
        for (const auto &r:input->requests) {
            CheckRequest(r,false);
            const uint32_t ids[]={r.source,r.destination};
            const uint32_t ips[]={r.sourceIp,r.destinationIp};
            for (unsigned n=0;n<2;++n) if (!hardware.count(ids[n])) {
                auto hw=CheckHost(ids[n],ips[n],false);
                Need(distinct.insert(PeekPointer(hw)).second,"V2 entry hosts share one Hw");
                Need(hw->m_qpMap.empty() && hw->m_rxQpMap.empty() &&
                     hw->akashic_Qp.empty() && hw->akashic_RxQp.empty(),"V2 entry hardware not initially empty");
                hardware.emplace(ids[n],hw);
            }
        }
        // Validate everything before touching Hw or queuing a single demand.
        for (const auto &item:hardware) item.second->RequireWs31V2Input(session);
        events.resize(input->requests.size()); clients.resize(input->requests.size());
        arrivals.reserve(input->requests.size());
        for (uint32_t i=0;i<input->requests.size();++i) {
            const uint64_t demand=input->requests[i].demandNs;
            Need(demand>=now && demand<=uint64_t(std::numeric_limits<int64_t>::max()),
                 "V2 entry event delay out of range");
            events[i]=Simulator::Schedule(NanoSeconds(demand-now),&Ws31V2NativeEntry::OnDemand,this,i);
        }
        phase=INSTALLED;
    } catch (...) { FailAll(ActiveError()); throw; }

    void Run() try {
        Need(phase==INSTALLED,"V2 entry Run missing install/repeated/failed");
        CheckEnvironment();
        const uint64_t now=NowNs();
        Need(now<=input->stop,"V2 entry Run after stop");
        phase=RUNNING;
        Simulator::Stop(NanoSeconds(input->stop-now));
        Simulator::Run();
        CheckEnvironment();
        Need(NowNs()==input->stop && nextOrdinal==input->requests.size(),"V2 entry early stop/unentered demands");
        Need(session->Issued()==input->requests.size() && session->DemandReads()==input->requests.size() &&
             session->Bindings()==input->requests.size() && session->Cancellations()==0,
             "V2 entry issue/demand/binding ledger mismatch");
        for (const auto &client:clients)
            Need(client && !client->m_ws31Pending && !client->m_ws31LaunchEvent.IsRunning(),
                 "V2 entry terminal pending client");
        CheckTerminalContext();
        phase=FINISHED;
    } catch (...) { FailAll(ActiveError()); throw; }

    Diagnostics GetDiagnostics() {
        Need(phase==FINISHED || phase==FAILED,"V2 entry diagnostics before terminal state");
        if (phase==FINISHED) {
            // Live counters must not borrow an old success flag after Session failure.
            try { CheckTerminalContext(); }
            catch (...) { FailAll(ActiveError()); }
        }
        Diagnostics d;
        d.entryFinished=phase==FINISHED; d.failed=phase==FAILED; d.firstError=firstError;
        d.declared=input?input->requests.size():0; d.entered=nextOrdinal;
        d.issued=session->Issued(); d.demandReads=session->DemandReads(); d.bindings=session->Bindings();
        d.packetReads=session->PacketReads(); d.cancellations=session->Cancellations();
        d.unentered=d.declared-nextOrdinal;
        for (const auto &client:clients) if (client) { ++d.clients; d.pending+=client->m_ws31Pending; }
        for (const auto &item:hardware) d.liveQPs+=item.second->m_qpMap.size();
        d.declarationCapacity=input?input->requests.capacity():0;
        d.eventCapacity=events.capacity(); d.clientCapacity=clients.capacity(); d.arrivals=arrivals;
        return d;
    }
};
} // namespace ns3
#endif
