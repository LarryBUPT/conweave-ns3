// Actual Client/Hw/QP/Packet checks on an unattached, link-down device.
// No channel, received packet, completion, OS2 topology or network experiment.
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/rdma-client.h"
#include "ns3/rdma-driver.h"
#include "ns3/rdma-hw.h"
#include "ns3/qbb-net-device.h"
#include "ns3/workload-tag.h"
#include "ns3/ws31-v2-native-session.h"
#include "ns3/ws31-start.h"
#include "ns3/ws31-label-fixture.h"
#include "ns3/ws30-v13-fixture.h"
#include "ns3/settings.h"
#include <functional>
#include <iostream>
#include <string>

namespace ns3 {
class Ws31V2NativeBindingFixture {
    typedef Ws31V2NativeSession Session;
    typedef Session::Handle Handle;
    std::string name;
    Ptr<Node> node;
    Ptr<QbbNetDevice> device;
    Ptr<RdmaHw> hw;
    Ptr<RdmaDriver> driver;
    Ptr<RdmaClient> clients[2];
    std::shared_ptr<Session> session;
    Handle handles[2];
    uint32_t sip=0x0b000001U, dip=0x0b004001U;
    uint64_t wait=0, packets=0;
    unsigned rejected=0;
    static void Need(bool ok,const char *message) {
        if (!ok) throw std::runtime_error(message);
    }
    static void Reject(const std::function<void()> &fn) {
        bool caught=false;
        try { fn(); } catch (const std::logic_error &error) {
            caught=true; std::cout<<"EXPECTED_REJECT "<<error.what()<<'\n';
        }
        Need(caught,"expected V2 rejection did not occur");
    }
    void SessionFailed(const std::shared_ptr<Session> &s) {
        Reject([s](){s->RequireHealthy();});
    }
    Ptr<RdmaQueuePair> Qp(unsigned id) {
        auto qp=hw->GetQp(RdmaHw::GetQpKey(dip,uint16_t(10000+id),100,3));
        Need(qp!=nullptr,"actual sender QP missing"); return qp;
    }
    void CheckPacket(unsigned id,uint32_t original,bool present,uint32_t policy) {
        auto qp=Qp(id);
        Need(qp->m_workload_tag==original && qp->startTime.GetNanoSeconds()==10,
             "original QP label/demand changed");
        auto p=hw->GetNxtPacket(qp); ++packets;
        WorkloadTag tag; const bool found=p->PeekPacketTag(tag);
        Need(found==present && (!found || tag.GetValue()==policy),"actual packet policy mismatch");
        std::cout<<"PACKET id="<<id<<" original="<<original<<" present="<<found
                 <<" policy="<<(found?tag.GetValue():0)<<" uid="<<p->GetUid()
                 <<" demand_ns="<<qp->startTime.GetNanoSeconds()
                 <<" launch_delay_ns="<<qp->m_ws31LaunchDelayNs<<'\n';
    }
    Handle Issue(unsigned id,uint32_t original,bool present,uint32_t policy,
                 std::shared_ptr<Session> owner=std::shared_ptr<Session>(),uint64_t demand=10) {
        if (!owner) owner=session;
        return owner->IssueCurrent(node->GetId(),id,sip,dip,uint16_t(10000+id),100,3,
                                   16384,original,demand,present,policy);
    }
    void BindStart(unsigned id,uint32_t original,bool present,uint32_t policy) {
        clients[id]->SetAttribute("WorkloadTag",UintegerValue(original));
        handles[id]=Issue(id,original,present,policy);
        clients[id]->BindWs31V2Current(handles[id]);
        clients[id]->StartApplication();
    }
    static void Begin(Ws31V2NativeBindingFixture *f,unsigned id) { f->BeginAtDemand(id); }
    static void End(Ws31V2NativeBindingFixture *f) { f->Observe(); }
    void BeginAtDemand(unsigned id) {
        Need(Simulator::Now().GetNanoSeconds()==10,"wrong demand event");
        if (name=="legacy") { clients[0]->StartApplication(); return; }
        if (name=="missing-session") {
            Reject([this](){clients[0]->RequireWs31V2Input(std::shared_ptr<Session>());});
            Reject([this](){clients[0]->StartApplication();}); ++rejected; return;
        }
        if (name=="missing-handle") {
            Reject([this](){clients[0]->StartApplication();}); SessionFailed(session); ++rejected; return;
        }
        if (name=="future-issue") {
            Reject([this](){Issue(0,2,true,1,session,11);}); SessionFailed(session); ++rejected; return;
        }
        if (name=="foreign-session") {
            auto other=std::make_shared<Session>(); auto h=Issue(0,2,true,1,other);
            Reject([this,h](){clients[0]->BindWs31V2Current(h);});
            SessionFailed(session); SessionFailed(other); ++rejected; return;
        }
        if (name=="failed-reuse") {
            auto h=Issue(0,2,true,1); session->Fail("explicit fixture failure");
            Reject([this,h](){clients[0]->BindWs31V2Current(h);}); SessionFailed(session); ++rejected; return;
        }
        if (name=="repeat-binding" || name=="changed-origin") {
            auto h=Issue(0,2,true,1); clients[0]->BindWs31V2Current(h);
            if (name=="repeat-binding") Reject([this,h](){clients[0]->BindWs31V2Current(h);});
            else { clients[0]->SetSize(16385); Reject([this](){clients[0]->StartApplication();}); }
            SessionFailed(session); ++rejected; return;
        }
        if (name=="hardware-no-session" || name=="history-collision") {
            if (name=="history-collision") hw->akashic_Qp.insert(RdmaHw::GetQpKey(dip,10000,100,3));
            Reject([this](){BindStart(0,2,true,1);}); SessionFailed(session); ++rejected; return;
        }
        if (name=="same-time") { BindStart(id,id==0?2:1,true,id==0?1:2); return; }
        if (name=="c2-absent" || name=="c2-unknown") {
            BindStart(0,2,name=="c2-unknown",name=="c2-unknown"?99:0);
            const auto &s=ws31::StartData();
            Need(hw->m_qpMap.size()==1 && !clients[0]->m_ws31Pending &&
                 Qp(0)->m_ws31LaunchDelayNs==0 && Qp(0)->startTime.GetNanoSeconds()==10 &&
                 s.demanded==1 && s.launched==1 && s.waited==0 && s.delaySum==0 &&
                 s.demandBytes==16384 && s.launchBytes==16384,
                 "C2 missing/unknown policy did not launch immediately at demand");
            CheckPacket(0,2,name=="c2-unknown",name=="c2-unknown"?99:0);
            return;
        }
        if (name=="c2-policy" || name=="c2-cancel" || name=="c2-cancel-mutated-size") {
            BindStart(0,1,true,2);
            Need(clients[0]->m_ws31Pending && hw->m_qpMap.empty(),"C2 did not delay eligible policy");
            if (name=="c2-cancel") clients[0]->StopApplication();
            if (name=="c2-cancel-mutated-size") {
                clients[0]->SetSize(16385);
                Reject([this](){clients[0]->StopApplication();}); SessionFailed(session);
                Need(!clients[0]->m_ws31Pending && !clients[0]->m_ws31LaunchEvent.IsRunning(),
                     "failed cancellation retained launch event");
                ++rejected;
            }
            return;
        }
        BindStart(0,2,name!="absent",name=="absent"?0:name=="unknown"?99:1);
        if (name=="wrong-qp") {
            auto fake=CreateObject<RdmaQueuePair>(3,Ipv4Address(sip),Ipv4Address(dip),10000,100);
            fake->SetSize(16384); fake->SetFlowId(0); fake->m_workload_tag=2; fake->startTime=NanoSeconds(10);
            Reject([this,fake](){hw->GetNxtPacket(fake);}); SessionFailed(session); ++rejected;
        } else if (name=="not-live-qp") {
            auto actual=Qp(0);
            const uint64_t sequence=actual->snd_nxt, txBytes=actual->stat.txTotalBytes;
            hw->m_qpMap.erase(RdmaHw::GetQpKey(dip,10000,100,3));
            Reject([this,actual](){hw->GetNxtPacket(actual);}); SessionFailed(session);
            Need(session->PacketReads()==0 && actual->snd_nxt==sequence &&
                 actual->stat.txTotalBytes==txBytes,"non-live QP read policy or produced payload");
            ++rejected;
        } else if (name=="repeat-actual-binding") {
            auto qp=Qp(0);
            Reject([this,qp](){session->BindActual(handles[0],node->GetId(),qp);});
            SessionFailed(session); ++rejected;
        }
    }
    void Observe() {
        Need(!device->IsLinkUp() && !device->GetChannel(),"nonnetwork device unexpectedly attached");
        if (rejected) {
            Need(packets==0 && session->PacketReads()==0,"rejected request produced a packet");
            if (name=="c2-cancel-mutated-size") {
                const auto &s=ws31::StartData();
                Need(hw->m_qpMap.empty() && session->Cancellations()==0 && session->Bindings()==0 &&
                     !clients[0]->m_ws31Pending && !clients[0]->m_ws31LaunchEvent.IsRunning() &&
                     s.demandBytes==16384 && s.cancelBytes==0 && s.launchBytes==0 &&
                     s.cancelled==0 && s.launched==0,"failed cancellation changed original byte ledger");
            }
            return;
        }
        if (name=="legacy") { CheckPacket(0,2,true,2); return; }
        session->RequireHealthy();
        if (name=="c2-cancel") {
            const auto &s=ws31::StartData();
            Need(hw->m_qpMap.empty() && session->Cancellations()==1 && session->Bindings()==0 &&
                 !clients[0]->m_ws31Pending && s.cancelled==1 && s.launched==0 &&
                 s.demanded==1 && s.demandBytes==16384 && s.cancelBytes==16384 && s.launchBytes==0,
                 "pending cancellation did not conserve original bytes/zero QPs"); return;
        }
        if (name=="c2-absent" || name=="c2-unknown") {
            Need(packets==1 && session->PacketReads()==1 && session->Bindings()==1 &&
                 !clients[0]->m_ws31Pending && ws31::StartData().delaySum==0,
                 "C2 immediate-boundary evidence changed after demand"); return;
        }
        if (name=="same-time") {
            CheckPacket(0,2,true,1); CheckPacket(1,1,true,2);
            Need(session->Bindings()==2 && session->DemandReads()==2,"same-time requests conflated"); return;
        }
        if (name=="c2-policy") {
            Need(Qp(0)->m_ws31LaunchDelayNs==wait && session->DemandReads()==1 &&
                 ws31::StartData().delaySum==wait,"C2 policy/origin delay mismatch");
            CheckPacket(0,1,true,2); return;
        }
        CheckPacket(0,2,name!="absent",name=="absent"?0:name=="unknown"?99:1);
        if (name=="repeat-seq") {
            Qp(0)->snd_nxt=0; // Repeated production only, not a timeout/feedback test.
            CheckPacket(0,2,true,1);
        }
    }
public:
    explicit Ws31V2NativeBindingFixture(const std::string &value):name(value) {
        node=CreateObject<Node>(); device=CreateObject<QbbNetDevice>(); node->AddDevice(device);
        device->SetDataRate(DataRate("100Gbps"));
        Need(!device->IsLinkUp() && !device->GetChannel(),"fixture requires unattached device");
        hw=CreateObject<RdmaHw>(); hw->m_mtu=1000; hw->m_cc_mode=1;
        driver=CreateObject<RdmaDriver>(); driver->SetNode(node); driver->SetRdmaHw(hw);
        node->AggregateObject(driver); driver->Init();
        Ipv4Address dst(dip); hw->AddTableEntry(dst,0);
        session=std::make_shared<Session>();
        for (unsigned i=0;i<2;++i) {
            clients[i]=CreateObject<RdmaClient>(); clients[i]->SetNode(node);
            clients[i]->SetLocal(Ipv4Address(sip),uint16_t(10000+i));
            clients[i]->SetRemote(Ipv4Address(dip),100); clients[i]->SetPG(3); clients[i]->SetSize(16384);
            clients[i]->SetAttribute("StatFlowID",IntegerValue(i));
            clients[i]->SetAttribute("WorkloadTag",UintegerValue(2));
            if (name!="legacy" && name!="missing-session") clients[i]->RequireWs31V2Input(session);
        }
        if (name!="legacy" && name!="hardware-no-session") hw->RequireWs31V2Input(session);
        Settings::lb_mode=name.compare(0,3,"c2-")==0?43:12;
        wait=ws31::StartDelay(43,2,16384,sip,dip,10000,100);
        Need(wait>0,"fixed C2 fixture tuple requires positive delay");
    }
    void Run() {
        Simulator::Schedule(NanoSeconds(10),&Begin,this,0U);
        if (name=="same-time") Simulator::Schedule(NanoSeconds(10),&Begin,this,1U);
        Simulator::Schedule(NanoSeconds(11+wait),&End,this);
        Simulator::Run();
        std::cout<<"WS31_V2_NATIVE_POLICY_PASS case="<<name<<" issued="<<session->Issued()
                 <<" demand_reads="<<session->DemandReads()<<" bindings="<<session->Bindings()
                 <<" packet_reads="<<session->PacketReads()<<" cancellations="<<session->Cancellations()
                 <<" expected_reject="<<rejected<<" network=0 completion=0 generation=0\n";
        Simulator::Destroy();
    }
};
} // namespace ns3

int main(int argc,char **argv) {
    std::string name;
    ns3::CommandLine cmd; cmd.AddValue("case","One fixed nonnetwork object case",name); cmd.Parse(argc,argv);
    const char *cases[]={"legacy","policy-different","absent","unknown","same-time","c2-policy","c2-cancel",
        "repeat-seq","missing-session","missing-handle","foreign-session","repeat-binding","wrong-qp",
        "changed-origin","future-issue","failed-reuse","hardware-no-session","history-collision","repeat-actual-binding",
        "c2-absent","c2-unknown","c2-cancel-mutated-size","not-live-qp"};
    try {
        if (ns3::Ws30V13Life()!=0 || ns3::Ws30V13TagTransform()!=0 || ns3::ws31::LabelProfile()!=0)
            throw std::runtime_error("fixture requires legacy lifecycle/transform/profile disabled");
        bool known=false; for (const char *item:cases) if (name==item) known=true;
        if (!known) throw std::runtime_error("unregistered case");
        ns3::Ws31V2NativeBindingFixture fixture(name); fixture.Run(); return 0;
    } catch (const std::exception &error) {
        std::cerr<<"WS31_V2_NATIVE_POLICY_FAILURE "<<error.what()<<'\n'; return 2;
    }
}
