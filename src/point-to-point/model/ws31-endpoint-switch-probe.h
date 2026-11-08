#ifndef WS31_ENDPOINT_SWITCH_PROBE_H
#define WS31_ENDPOINT_SWITCH_PROBE_H

// Fixture-only, pure target-fourtuple switch state observation. This adds the
// switch field to a fresh actual-endpoint observation, not a network certificate.
#include "ws31-endpoint-probe.h"
#include "switch-node.h"
#include "settings.h"
#include <typeinfo>
#include <limits>
#include <set>
#include <vector>
#include <stdexcept>

namespace ns3 {

class Ws31EndpointSwitchProbe {
public:
    struct Switch {
        uint32_t node=0;
        uintptr_t object=0;
        uint64_t q12Pins=0, ws31Pins=0, budget=0, quota=0;
        uint64_t allQ12Pins=0, allWs31Pins=0, allBudget=0, allQuota=0, observedPorts=0;
        ws31::QuotaAdmission::ActivitySnapshot sharedActivity;
        uint64_t liveBorrowed[3]={0,0,0};
    };
    class Scope {
        friend class Ws31EndpointSwitchProbe;
        struct NodeBinding {
            Ptr<Node> node;
            Ptr<SwitchNode> sw;
            uint32_t id=0, type=0;
            std::vector<Ptr<NetDevice>> devices;
        };
        std::vector<NodeBinding> nodes;
        Ws31EndpointProbe::Scope endpoint;
        uint32_t mode=0;
        bool captured=false;
    };
    struct Observation {
        Ws31EndpointProbe::Observation endpoint;
        ws31::EndpointSnapshot snapshot;
        std::vector<Switch> switches;
    };
private:
    static void Need(bool ok,const char *message) {
        if (!ok) throw std::logic_error(message);
    }
    static void Add(uint64_t &total,uint64_t count) {
        Need(count<=std::numeric_limits<uint64_t>::max()-total,"WS31 switch count overflow");
        total+=count;
    }
    static void DeviceBinding(Ptr<Node> node,uint32_t slot,Ptr<NetDevice> device,
                              std::set<uintptr_t> &seen) {
        Need(device && device->GetNode()==node && device->GetIfIndex()==slot &&
             seen.insert(reinterpret_cast<uintptr_t>(PeekPointer(device))).second,
             "WS31 switch scope device owner/index/uniqueness changed");
        Need(DynamicCast<QbbNetDevice>(device)!=nullptr ||
             DynamicCast<LoopbackNetDevice>(device)!=nullptr,
             "Unsupported interface in WS31 switch scope");
    }
    static void Validate(const Scope &scope) {
        Need(scope.captured && scope.mode==Settings::lb_mode &&
             scope.nodes.size()==NodeList::GetNNodes(),
             "WS31 switch scope is absent or its node count changed");
        std::size_t index=0;
        std::set<uintptr_t> devices;
        for (auto it=NodeList::Begin();it!=NodeList::End();++it,++index) {
            Ptr<Node> node=*it; const auto &binding=scope.nodes.at(index);
            Need(node==binding.node && node->GetId()==binding.id && node->GetNodeType()==binding.type &&
                 node->GetNDevices()==binding.devices.size(),"WS31 switch scope node identity changed");
            for (uint32_t i=0;i<node->GetNDevices();++i) {
                Need(node->GetDevice(i)==binding.devices[i],"WS31 switch scope interface identity changed");
                DeviceBinding(node,i,node->GetDevice(i),devices);
            }
            if (binding.sw)
                Need(DynamicCast<SwitchNode>(node)==binding.sw &&
                     typeid(*PeekPointer(binding.sw))==typeid(SwitchNode),
                     "WS31 switch scope dynamic type changed");
        }
    }
public:
    static Scope Capture(const std::vector<Ptr<RdmaDriver> > &drivers) {
        Scope scope; uint32_t switches=0;
        Need(Settings::lb_mode>=33 && Settings::lb_mode<=50,
             "WS31 switch probe supports only Q12 and C1/C2/C3 table modes");
        scope.mode=Settings::lb_mode;
        std::set<uintptr_t> devices;
        for (auto it=NodeList::Begin();it!=NodeList::End();++it) {
            Ptr<Node> node=*it; Scope::NodeBinding binding;
            binding.node=node; binding.id=node->GetId(); binding.type=node->GetNodeType();
            Need(binding.type==0 || binding.type==1,"Unsupported node type in WS31 switch scope");
            binding.sw=DynamicCast<SwitchNode>(node);
            Need((binding.type==1)==(binding.sw!=nullptr),"WS31 node role and switch object disagree");
            if (binding.sw) {
                Need(typeid(*PeekPointer(binding.sw))==typeid(SwitchNode),
                     "WS31 switch observation requires an exact SwitchNode");
                ++switches;
            }
            for (uint32_t i=0;i<node->GetNDevices();++i) {
                Ptr<NetDevice> device=node->GetDevice(i);
                DeviceBinding(node,i,device,devices);
                binding.devices.push_back(device);
            }
            scope.nodes.push_back(binding);
        }
        Need(switches>0,"WS31 switch scope has no actual switch");
        scope.endpoint=Ws31EndpointProbe::Capture(drivers);
        scope.captured=true; Validate(scope); return scope;
    }
    static Observation Read(int32_t id,const ws31::EndpointLedger::Entry &entry,
                            Ptr<RdmaHw> tx,Ptr<RdmaHw> rx,
                            Ptr<RdmaQueuePair> savedTx,Ptr<RdmaRxQueuePair> savedRx,
                            const Scope &scope,uint32_t txNic,uint32_t rxNic) {
        Validate(scope);
        // The endpoint scope is captured with this switch scope. Read actual
        // endpoint state inside the same synchronous operation; callers cannot
        // supply an old Observation or interleave an event between the reads.
        Observation result;
        result.endpoint=Ws31EndpointProbe::Read(id,entry,tx,rx,savedTx,savedRx,
                                               scope.endpoint,txNic,rxNic);
        const auto &endpoint=result.endpoint;
        const int64_t now=Simulator::Now().GetNanoSeconds();
        const auto &base=endpoint.snapshot;
        Need(id>=0 && now>=0 && base.observedNs==uint64_t(now) && base.flowId==id &&
             base.tuple==entry.tuple && base.generation==entry.generation &&
             base.observedFields==(ws31::EndpointSnapshot::ALL ^ ws31::EndpointSnapshot::SWITCH_STATE) &&
             base.pinnedEntries==0 && base.budgetEntries==0 && base.quotaEntries==0 &&
             endpoint.nodes==scope.nodes.size(),
             "WS31 switch read needs a fresh matching incomplete endpoint observation");
        const ws31::Key key(std::get<0>(entry.tuple),std::get<1>(entry.tuple),
                            std::get<2>(entry.tuple),std::get<3>(entry.tuple));
        result.snapshot=base;
        for (const auto &binding:scope.nodes) {
            if (!binding.sw) continue;
            Ptr<SwitchNode> sw=binding.sw;
            Switch row; row.node=binding.id;
            row.object=reinterpret_cast<uintptr_t>(PeekPointer(sw));
            row.q12Pins=sw->m_ws30V13Pairs.count(key);
            row.ws31Pins=sw->m_ws31Pairs.count(key);
            row.budget=sw->m_ws31Budget.Contains(key);
            row.quota=sw->m_ws31Quota.Contains(key);
            // Global/shared history is reported separately and never cleared.
            row.allQ12Pins=sw->m_ws30V13Pairs.size(); row.allWs31Pins=sw->m_ws31Pairs.size();
            row.allBudget=sw->m_ws31Budget.Size(); row.allQuota=sw->m_ws31Quota.Size();
            row.observedPorts=sw->m_ws31Observed.PortCount();
            row.sharedActivity=sw->m_ws31Quota.SharedActivity();
            for (unsigned i=0;i<3;++i) row.liveBorrowed[i]=sw->m_ws31Quota.liveBorrowed[i];
            Add(result.snapshot.pinnedEntries,row.q12Pins); Add(result.snapshot.pinnedEntries,row.ws31Pins);
            Add(result.snapshot.budgetEntries,row.budget); Add(result.snapshot.quotaEntries,row.quota);
            result.switches.push_back(row);
        }
        Need(!result.switches.empty(),"WS31 switch observation omitted all switches");
        result.snapshot.observedFields|=ws31::EndpointSnapshot::SWITCH_STATE;
        return result;
    }
};

} // namespace ns3
#endif
