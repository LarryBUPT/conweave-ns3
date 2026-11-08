// Finite entry checks with actual IPv4/Qbb/Client/Hw/QP/Packet objects.
// All Qbb devices remain unattached and link-down. No scientific network run.
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/rdma-driver.h"
#include "ns3/workload-tag.h"
#include "ns3/ws31-start.h"
#include "ns3/ws31-v2-native-entry.h"
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <tuple>

namespace ns3 {
class Ws31V2NativeEntryFixture {
    typedef Ws31V2NativeEntry Entry;
    std::string name, text, installText;
    ws31v2::DeclaredInput expected;
    NodeContainer nodes;
    Entry::Hosts hosts;
    std::map<uint32_t,Ptr<RdmaHw>> hw;
    std::map<uint32_t,uint32_t> ipInterface;
    Entry::PairTimings pairs;
    std::unique_ptr<Entry> entry;
    std::shared_ptr<Ws31V2NativeSession> savedSession;
    Entry::Diagnostics observed;
    bool diagObserved=false;
    unsigned rejections=0, entryRunCalls=0;
    uint32_t mode=12;
    uint64_t pendingAtFault=0;

    static void Need(bool ok,const char *message) {
        if (!ok) throw std::runtime_error(message);
    }
    void Reject(const std::function<void()> &action,const std::string &reason) {
        bool caught=false;
        try { action(); }
        catch (const std::logic_error &error) {
            Need(std::string(error.what()).find(reason)!=std::string::npos,
                 "unexpected rejection reason");
            std::cout<<"EXPECTED_REJECT "<<error.what()<<'\n';
            caught=true;
        }
        Need(caught,"registered rejection did not happen");
        ++rejections;
    }
    void Advance(uint64_t ns) {
        Need(Simulator::Now().GetNanoSeconds()>=0 &&
             uint64_t(Simulator::Now().GetNanoSeconds())<ns,"invalid fixture advance");
        Simulator::Stop(NanoSeconds(ns-Simulator::Now().GetNanoSeconds()));
        Simulator::Run();
        Need(uint64_t(Simulator::Now().GetNanoSeconds())==ns,"fixture advance shifted time");
    }
    Entry::RunConfig Config() const {
        const bool perPair=name=="entry-d2" || name=="missing-pair-timing";
        return Entry::RunConfig(mode,1,perPair?0:1,12500,1000,pairs,1000,1,false);
    }
    void Install() {
        std::istringstream stream(installText);
        entry->Install(stream,hosts,Config());
    }
    void RunEntry() { ++entryRunCalls; entry->Run(); }
    Entry::Diagnostics Observe() {
        diagObserved=true;
        observed=entry->GetDiagnostics();
        return observed;
    }
    Ptr<RdmaQueuePair> Actual(uint32_t ordinal) {
        const auto &r=expected.requests.at(ordinal);
        const auto found=hw.at(r.source)->m_qpMap.find(RdmaHw::GetQpKey(r.destinationIp,r.sport,r.dport,r.pg));
        Need(found!=hw.at(r.source)->m_qpMap.end() && found->second,"actual bound QP missing");
        return found->second;
    }
    void Packet(uint32_t ordinal) {
        const auto &r=expected.requests.at(ordinal);
        auto q=Actual(ordinal);
        const uint64_t delay=ws31::StartDelay(mode,r.policyPresent?r.policyTag:0,r.bytes,
                                            r.sourceIp,r.destinationIp,r.sport,r.dport);
        Need(q->m_flow_id==r.flowId && q->sip.Get()==r.sourceIp && q->dip.Get()==r.destinationIp &&
             q->sport==r.sport && q->dport==r.dport && q->m_pg==r.pg && q->m_size==r.bytes &&
             q->m_workload_tag==r.originalTag && q->startTime.GetNanoSeconds()==int64_t(r.demandNs) &&
             q->m_ws31LaunchDelayNs==delay && q->m_win==12500 && q->m_baseRtt==1000,
             "actual QP identity/time/transport differs from declaration");
        auto packet=hw.at(r.source)->GetNxtPacket(q);
        WorkloadTag tag;
        const bool present=packet->PeekPacketTag(tag);
        Need(present==r.policyPresent && (!present || tag.GetValue()==r.policyTag),
             "actual Packet policy differs from current capability");
        std::cout<<"ENTRY_PACKET ordinal="<<ordinal<<" id="<<r.id<<" src="<<r.source
                 <<" dst="<<r.destination<<" sport="<<q->sport<<" dport="<<q->dport
                 <<" pg="<<q->m_pg<<" bytes="<<q->m_size<<" original="<<q->m_workload_tag
                 <<" present="<<present<<" policy="<<(present?tag.GetValue():0)
                 <<" demand_ns="<<q->startTime.GetNanoSeconds()
                 <<" delay_ns="<<q->m_ws31LaunchDelayNs<<" uid="<<packet->GetUid()<<'\n';
    }
    void Healthy(bool allPackets) {
        auto d=Observe();
        Need(d.entryFinished && !d.failed && d.firstError.empty() && d.declared==1120 &&
             d.entered==1120 && d.issued==1120 && d.demandReads==1120 && d.bindings==1120 &&
             d.clients==1120 && d.liveQPs==1120 && d.pending==0 && d.unentered==0 &&
             d.cancellations==0 && d.arrivals.size()==1120,"healthy entry ledger mismatch");
        for (uint32_t i=0;i<expected.requests.size();++i) {
            const auto &r=expected.requests[i]; const auto &a=d.arrivals[i];
            Need(a.ordinal==i && a.id==r.id && a.actualNs==r.demandNs && a.clientCreated && a.clientStarted,
                 "actual arrival/ordinal/client start mismatch");
            Need(hosts.at(r.source)->GetNApplications()==0,"entry mixed automatic Application startup");
            if (allPackets) Packet(i);
        }
        if (allPackets) {
            d=Observe();
            Need(d.entryFinished && !d.failed && d.packetReads==1120,"actual Packet read ledger mismatch");
        }
    }
    void Failed(bool zeroIssued) {
        const auto d=Observe();
        Need(!d.entryFinished && d.failed && !d.firstError.empty() && d.pending==0 &&
             d.cancellations==0 && ws31::StartData().cancelled==0 && ws31::StartData().cancelBytes==0,
             "failed entry invented success/cancellation or retained pending");
        if (zeroIssued) Need(d.issued==0 && d.demandReads==0 && d.bindings==0,
                            "pre-admission failure issued a partial request");
        for (const auto &event:entry->events) Need(!event.IsRunning(),"failure retained demand event");
    }
    void ChangeTerminal() {
        const auto &r=expected.requests.front();
        if (name=="terminal-mtu") hw.at(r.source)->m_mtu=999;
        else Need(hw.at(r.source)->m_rtTable.erase(r.destinationIp)==1,"terminal route erase missed");
    }
    void FailProducer() {
        Need(Simulator::Now().GetNanoSeconds()==2005000093LL,"fault injection time shifted");
        const auto &s=ws31::StartData();
        Need(s.demanded>s.launched+s.cancelled,"no actual C2 pending request at producer fault");
        pendingAtFault=s.demanded-s.launched-s.cancelled;
        const auto &r=expected.requests.at(13);
        auto actual=Actual(13);
        Need(actual->m_ws31LaunchDelayNs==92,"fast actual QP delay differs from frozen tuple");
        const uint64_t sequence=actual->snd_nxt, bytes=actual->stat.txTotalBytes;
        const uint64_t reads=savedSession->PacketReads();
        Need(hw.at(r.source)->m_qpMap.erase(RdmaHw::GetQpKey(r.destinationIp,r.sport,r.dport,r.pg))==1,
             "fault erase missed genuine live QP");
        try { hw.at(r.source)->GetNxtPacket(actual); }
        catch (...) {
            Need(actual->snd_nxt==sequence && actual->stat.txTotalBytes==bytes &&
                 savedSession->PacketReads()==reads,"rejected asynchronous producer changed payload state");
            std::cout<<"ASYNC_PRODUCER_FAULT id=13 pending="<<pendingAtFault
                     <<" before_seq="<<sequence<<" after_seq="<<actual->snd_nxt
                     <<" before_tx="<<bytes<<" after_tx="<<actual->stat.txTotalBytes<<'\n';
            throw;
        }
        Need(false,"genuine non-live QP produced a Packet");
    }
    void BuildObjects() {
        nodes.Create(128);
        std::set<uint32_t> used;
        for (const auto &r:expected.requests) { used.insert(r.source); used.insert(r.destination); }
        NodeContainer endpoints;
        std::map<uint32_t,Ptr<QbbNetDevice>> devices;
        for (uint32_t id:used) {
            auto node=nodes.Get(id); Need(node->GetId()==id,"fixture requires fresh process Node IDs");
            auto dev=CreateObject<QbbNetDevice>(); dev->SetDataRate(DataRate("100Gbps"));
            node->AddDevice(dev); devices.emplace(id,dev); hosts.emplace(id,node); endpoints.Add(node);
            Need(!dev->IsLinkUp() && !dev->GetChannel(),"fixture Qbb unexpectedly networked");
        }
        InternetStackHelper stack; stack.SetIpv6StackInstall(false); stack.Install(endpoints);
        for (uint32_t id:used) {
            auto node=nodes.Get(id); auto ipv4=node->GetObject<Ipv4>();
            int32_t iface=ipv4->GetInterfaceForDevice(devices.at(id));
            if (iface<0) iface=ipv4->AddInterface(devices.at(id));
            Need(ipv4->AddAddress(iface,Ipv4InterfaceAddress(Ipv4Address(ws31v2::NodeIp(id)),
                                                         Ipv4Mask("255.255.255.0"))),"fixture address install failed");
            ipv4->SetUp(iface); ipInterface.emplace(id,uint32_t(iface));
            auto actualHw=CreateObject<RdmaHw>(); actualHw->m_mtu=1000; actualHw->m_cc_mode=1; actualHw->m_irn=false;
            auto driver=CreateObject<RdmaDriver>(); driver->SetNode(node); driver->SetRdmaHw(actualHw);
            node->AggregateObject(driver); driver->Init(); hw.emplace(id,actualHw);
        }
        for (const auto &r:expected.requests) {
            auto srcDevice=devices.at(r.source), dstDevice=devices.at(r.destination);
            Ipv4Address dip(r.destinationIp), sip(r.sourceIp);
            // Each route is a single actual Node device index, not an IPv4 interface index.
            if (!hw.at(r.source)->m_rtTable.count(r.destinationIp))
                hw.at(r.source)->AddTableEntry(dip,srcDevice->GetIfIndex());
            if (!hw.at(r.destination)->m_rtTable.count(r.sourceIp))
                hw.at(r.destination)->AddTableEntry(sip,dstDevice->GetIfIndex());
            pairs.emplace(std::make_pair(r.source,r.destination),Entry::PairTiming(12500,1000));
        }
    }
    std::string PolicyVariant() {
        std::istringstream source(text); std::ostringstream target; std::string line;
        for (unsigned h=0;h<3;++h) { Need(bool(std::getline(source,line)),"variant header missing"); target<<line<<'\n'; }
        for (uint32_t i=0;i<expected.requests.size();++i) {
            Need(bool(std::getline(source,line)),"variant row missing");
            auto words=ws31v2::Words(line); Need(words.size()==15,"variant expected 15 columns");
            if (i==0) words[10]="1",words[11]="1";
            if (i==1) words[10]="0",words[11]="0";
            if (i==2) words[10]="1",words[11]="99";
            if (i==16) { Need(expected.requests[i].originalTag==1,"variant original class changed"); words[10]="1";words[11]="2"; }
            for (size_t k=0;k<words.size();++k) target<<(k?" ":"")<<words[k];
            target<<'\n';
        }
        std::istringstream modified(target.str()); auto changed=ws31v2::ReadDeclarations(modified);
        Need(changed.requests.size()==expected.requests.size(),"variant changed original population");
        for (size_t i=0;i<expected.requests.size();++i) {
            const auto &a=expected.requests[i], &b=changed.requests[i];
            Need(std::tie(a.id,a.generation,a.source,a.destination,a.sourceIp,a.destinationIp,a.pg,a.bytes,
                          a.demandNs,a.originalTag,a.sport,a.dport,a.flowId)==
                 std::tie(b.id,b.generation,b.source,b.destination,b.sourceIp,b.destinationIp,b.pg,b.bytes,
                          b.demandNs,b.originalTag,b.sport,b.dport,b.flowId),
                 "technical policy variant changed an original identity or demand field");
        }
        expected=changed;
        return target.str();
    }
public:
    Ws31V2NativeEntryFixture(const std::string &caseName,const std::string &inputPath):name(caseName) {
        std::ifstream file(inputPath.c_str(),std::ios::binary);
        Need(file.good(),"registered declaration file unavailable");
        text.assign(std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>());
        std::istringstream original(text); expected=ws31v2::ReadDeclarations(original); installText=text;
        Need(expected.seed==5310001 && expected.family==(name=="entry-d2"?"D2":"D1"),
             "fixture requires its registered existing family/seed");
        if (name=="nonzero-install" || name=="pending-producer-failure" || name=="policy-variants") mode=43;
        Settings::lb_mode=mode;
        BuildObjects();
        entry.reset(new Entry()); savedSession=entry->session;
        if (name=="policy-variants") installText=PolicyVariant();
    }
    void Run() {
        const auto first=expected.requests.front();
        if (name=="bad-final-declaration") {
            while (!installText.empty() && (installText.back()=='\n' || installText.back()=='\r')) installText.pop_back();
            installText+=" EXTRA\n";
            Reject([this](){Install();},"declaration"); Failed(true);
        } else if (name=="late-install") {
            Advance(first.demandNs+1); Reject([this](){Install();},"late/out-of-range"); Failed(true);
        } else if (name=="wrong-address" || name=="wrong-hw-owner" ||
                   name=="bad-reverse-route" || name=="missing-pair-timing") {
            if (name=="wrong-address") {
                auto ipv4=hosts.at(first.source)->GetObject<Ipv4>();
                Need(ipv4->RemoveAddress(ipInterface.at(first.source),uint32_t(0)),"address removal missed");
            } else if (name=="wrong-hw-owner") {
                hosts.at(first.source)->GetObject<RdmaDriver>()->SetNode(hosts.at(first.destination));
            } else if (name=="bad-reverse-route") {
                Need(hw.at(first.destination)->m_rtTable.erase(first.sourceIp)==1,"reverse route erase missed");
            } else pairs.erase(std::make_pair(first.source,first.destination));
            const std::string reason=name=="wrong-address"?"address missing":name=="wrong-hw-owner"?"owner mismatch":
                                     name=="bad-reverse-route"?"route missing":"pair BDP/RTT missing";
            Reject([this](){Install();},reason); Failed(true);
        } else {
            if (name=="nonzero-install") Advance(100);
            Install();
            if (name=="duplicate-install") {
                Reject([this](){Install();},"installation repeated"); Failed(true);
            } else if (name=="dispose-before-run" || name=="diagnostic-before-terminal") {
                if (name=="diagnostic-before-terminal")
                    Reject([this](){entry->GetDiagnostics();},"diagnostics before terminal");
                entry.reset(); Advance(expected.stop);
                Need(savedSession->Issued()==0 && savedSession->DemandReads()==0 && savedSession->Bindings()==0,
                     "disposed Entry left active demand callback");
                Reject([this](){savedSession->RequireHealthy();},"disposed before terminal");
            } else if (name=="early-stop") {
                Simulator::Stop(NanoSeconds(first.demandNs-1-Simulator::Now().GetNanoSeconds()));
                Reject([this](){RunEntry();},"early stop/unentered"); Failed(true);
            } else if (name=="pending-producer-failure") {
                Need(expected.requests[13].demandNs==2005000000ULL &&
                     ws31::StartDelay(43,2,expected.requests[13].bytes,expected.requests[13].sourceIp,
                        expected.requests[13].destinationIp,expected.requests[13].sport,expected.requests[13].dport)==92 &&
                     ws31::StartDelay(43,2,first.bytes,first.sourceIp,first.destinationIp,first.sport,first.dport)==455,
                     "frozen pending injection tuples changed");
                Simulator::Schedule(NanoSeconds(2005000093ULL-Simulator::Now().GetNanoSeconds()),
                                    &Ws31V2NativeEntryFixture::FailProducer,this);
                Reject([this](){RunEntry();},"not live actual QP"); Failed(false);
                Need(pendingAtFault>0 && observed.bindings>0 && observed.packetReads==0 && observed.unentered>0,
                     "asynchronous producer failure did not preserve bounded residue");
                const auto failedBefore=observed;
                const auto startBefore=ws31::StartData();
                const uint64_t drainFrom=Simulator::Now().GetNanoSeconds();
                // Keep Entry/Client alive: an uncancelled failed-client launch must be observable.
                // Do not catch a residual callback exception here or Dispose before advancing.
                Advance(expected.stop);
                const auto failedAfter=Observe();
                const auto &startAfter=ws31::StartData();
                Need(failedAfter.failed && !failedAfter.entryFinished &&
                     failedAfter.firstError==failedBefore.firstError &&
                     std::tie(failedAfter.declared,failedAfter.entered,failedAfter.issued,
                              failedAfter.demandReads,failedAfter.bindings,failedAfter.packetReads,
                              failedAfter.cancellations,failedAfter.clients,failedAfter.pending,
                              failedAfter.unentered,failedAfter.liveQPs)==
                     std::tie(failedBefore.declared,failedBefore.entered,failedBefore.issued,
                              failedBefore.demandReads,failedBefore.bindings,failedBefore.packetReads,
                              failedBefore.cancellations,failedBefore.clients,failedBefore.pending,
                              failedBefore.unentered,failedBefore.liveQPs),
                     "failure drain changed shared request/packet/cancel/residue ledger");
                Need(std::tie(startAfter.demanded,startAfter.launched,startAfter.cancelled,startAfter.finished,
                              startAfter.demandBytes,startAfter.launchBytes,startAfter.cancelBytes,startAfter.finishBytes,
                              startAfter.waited,startAfter.delaySum,startAfter.delayMax)==
                     std::tie(startBefore.demanded,startBefore.launched,startBefore.cancelled,startBefore.finished,
                              startBefore.demandBytes,startBefore.launchBytes,startBefore.cancelBytes,startBefore.finishBytes,
                              startBefore.waited,startBefore.delaySum,startBefore.delayMax),
                     "failure drain executed a residual request/launch/completion callback");
                std::cout<<"ENTRY_FAILURE_DRAIN from_ns="<<drainFrom
                         <<" to_ns="<<Simulator::Now().GetNanoSeconds()
                         <<" pending="<<failedAfter.pending<<" bindings="<<failedAfter.bindings
                         <<" ledger_unchanged=1 original_error_preserved=1\n";
            } else if (name=="terminal-mtu" || name=="terminal-route") {
                Simulator::Schedule(NanoSeconds(expected.requests.back().demandNs+1-Simulator::Now().GetNanoSeconds()),
                                    &Ws31V2NativeEntryFixture::ChangeTerminal,this);
                Reject([this](){RunEntry();},name=="terminal-mtu"?"configuration mismatch":"route missing");
                Failed(false); Need(observed.bindings==1120,"terminal fault occurred before full admission");
            } else {
                RunEntry();
                if (name=="repeated-run") {
                    Healthy(false); Reject([this](){RunEntry();},"Run missing install/repeated/failed"); Failed(false);
                } else if (name=="postrun-live-map" || name=="postrun-context") {
                    Healthy(false); Packet(0); auto before=Observe();
                    std::string sessionFailure;
                    if (name=="postrun-live-map") {
                        auto actual=Actual(0); const uint64_t seq=actual->snd_nxt, bytes=actual->stat.txTotalBytes;
                        Need(hw.at(first.source)->m_qpMap.erase(RdmaHw::GetQpKey(first.destinationIp,first.sport,first.dport,first.pg))==1,
                             "postrun actual QP erase missed");
                        Reject([&](){hw.at(first.source)->GetNxtPacket(actual);},"not live actual QP");
                        Need(actual->snd_nxt==seq && actual->stat.txTotalBytes==bytes,
                             "postrun rejected producer changed actual sequence/bytes");
                        std::cout<<"POSTRUN_PRODUCER before_seq="<<seq<<" after_seq="<<actual->snd_nxt
                                 <<" before_tx="<<bytes<<" after_tx="<<actual->stat.txTotalBytes<<'\n';
                        try { savedSession->RequireHealthy(); }
                        catch (const std::logic_error &error) { sessionFailure=error.what(); }
                        Need(!sessionFailure.empty(),"actual producer refusal did not fail shared Session");
                        std::cout<<"POSTRUN_SESSION_FAILURE "<<sessionFailure<<'\n';
                    } else hw.at(first.source)->m_mtu=999;
                    Failed(false); const auto failed=observed; const auto again=Observe();
                    Need(again.failed && !again.entryFinished && again.firstError==failed.firstError &&
                         again.packetReads==before.packetReads && again.bindings==before.bindings &&
                         again.cancellations==0,"live repeated diagnostic lost first failure or original ledger");
                    if (name=="postrun-context") Need(failed.firstError.find("configuration mismatch")!=std::string::npos,
                                                      "live context diagnosis lost original mismatch");
                    else Need(failed.firstError.find(sessionFailure)!=std::string::npos,
                              "live diagnosis lost the original shared Session reason");
                    if (name=="postrun-context") {
                        std::cout<<"EXPECTED_FAILED_EXPORT "<<failed.firstError<<'\n';
                        ++rejections; // Checked failed live export; no thrown API promised.
                    }
                } else {
                    Healthy(true);
                    if (name=="policy-variants")
                        Need(Actual(0)->m_ws31LaunchDelayNs==0 && Actual(1)->m_ws31LaunchDelayNs==0 &&
                             Actual(2)->m_ws31LaunchDelayNs==0 && Actual(16)->m_ws31LaunchDelayNs==485,
                             "policy eligibility did not remain separate from original class");
                }
            }
        }
        bool sessionFailed=false;
        try { savedSession->RequireHealthy(); } catch (const std::logic_error &) { sessionFailed=true; }
        const bool positive=name=="entry-d1" || name=="entry-d2" || name=="nonzero-install" || name=="policy-variants";
        Need(positive?(!rejections && !sessionFailed):(rejections && sessionFailed),
             "case success/rejection/session classification mismatch");
        for (const auto &item:hw) for (const auto &nic:item.second->m_nic) if (nic.dev)
            Need(!nic.dev->IsLinkUp() && !nic.dev->GetChannel(),"fixture acquired a network channel");
        std::cout<<"WS31_V2_NATIVE_ENTRY_PASS case="<<name<<" expected_reject="<<(!positive)
                 <<" failure_observations="<<rejections<<" session_failed="<<sessionFailed
                 <<" diag_observed="<<diagObserved<<" issued="<<savedSession->Issued()
                 <<" demand_reads="<<savedSession->DemandReads()<<" bindings="<<savedSession->Bindings()
                 <<" packet_reads="<<savedSession->PacketReads()<<" cancellations="<<savedSession->Cancellations()
                 <<" entry_run_calls="<<entryRunCalls<<" cancel_bytes="<<ws31::StartData().cancelBytes;
        if (diagObserved)
            std::cout<<" entry_finished="<<observed.entryFinished<<" failed="<<observed.failed
                     <<" pending="<<observed.pending<<" not_admitted="<<observed.unentered
                     <<" live_qps="<<observed.liveQPs;
        else std::cout<<" diagnostic=not_sampled";
        std::cout<<" network=0 completion=0 generation=0\n";
        if (diagObserved) std::cout<<"ENTRY_DIAGNOSTIC first_error="<<observed.firstError<<'\n';
        entry.reset();
        Simulator::Destroy();
    }
};
} // namespace ns3

int main(int argc,char **argv) {
    std::string name,input;
    ns3::CommandLine command; command.AddValue("case","One registered finite object case",name);
    command.AddValue("input","Fixed existing declaration file",input); command.Parse(argc,argv);
    const char *cases[]={"entry-d1","entry-d2","nonzero-install","bad-final-declaration","duplicate-install",
        "late-install","wrong-address","wrong-hw-owner","bad-reverse-route","missing-pair-timing",
        "repeated-run","early-stop","pending-producer-failure","terminal-mtu","terminal-route",
        "postrun-live-map","dispose-before-run","diagnostic-before-terminal","policy-variants","postrun-context"};
    try {
        bool known=false; for (const char *value:cases) if (name==value) known=true;
        if (!known || input.empty()) throw std::runtime_error("unregistered case or missing input");
        if (ns3::Ws30V13Life()!=0 || ns3::Ws30V13TagTransform()!=0 || ns3::ws31::LabelProfile()!=0)
            throw std::runtime_error("entry fixture requires old lifecycle/transform/profile disabled");
        ns3::Ws31V2NativeEntryFixture fixture(name,input); fixture.Run(); return 0;
    } catch (const std::exception &error) {
        std::cerr<<"WS31_V2_NATIVE_ENTRY_FAILURE "<<error.what()<<'\n';
        ns3::Simulator::Destroy(); return 2;
    }
}
