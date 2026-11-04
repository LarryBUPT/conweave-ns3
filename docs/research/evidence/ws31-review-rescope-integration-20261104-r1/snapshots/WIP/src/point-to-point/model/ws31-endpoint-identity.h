#ifndef WS31_ENDPOINT_IDENTITY_H
#define WS31_ENDPOINT_IDENTITY_H

// Draft endpoint-fixture guard. The future entry must fully parse its actual
// input and supply actual production packed keys before Seal. This class does
// not itself parse a configuration or authorize attaching any observer.
#include "ws31-endpoint-ledger.h"
#include "ns3/flow-id-num-tag.h"
#include "ns3/packet.h"
#include "ns3/custom-header.h"
#include <memory>

namespace ns3 {

class Ws31EndpointIdentity {
    std::shared_ptr<ws31::EndpointLedger> ledger;
    std::map<int32_t,ws31::EndpointLedger::Entry> manifest;
    std::map<std::pair<uint32_t,uint64_t>,ws31::EndpointKey> txOwners,rxOwners;
    std::map<ws31::EndpointRouteKey,ws31::EndpointKey> routeOwners;
    bool sealed=false, failed=false;
    uint64_t senderChecks=0, dataChecks=0, ackChecks=0, feedbackChecks=0;
    void Need(bool ok,const char *message) {
        if (!ok) { failed=true; throw std::logic_error(message); }
    }
    const ws31::EndpointLedger::Entry &Active(int32_t id,bool dataOnly) try {
        Need(sealed && !failed,"WS31 endpoint identity manifest is unsealed or failed");
        auto found=manifest.find(id);
        Need(found!=manifest.end(),"WS31 endpoint identity was not declared before launch");
        const auto &actual=ledger->Get(id), &expected=found->second;
        Need(actual.tuple==expected.tuple && actual.generation==expected.generation &&
             actual.bytes==expected.bytes && actual.originalTag==expected.originalTag &&
             actual.demandNs==expected.demandNs &&
             actual.resources.sourceNode==expected.resources.sourceNode &&
             actual.resources.destinationNode==expected.resources.destinationNode &&
             actual.resources.txKey==expected.resources.txKey && actual.resources.rxKey==expected.resources.rxKey,
             "WS31 live identity differs from the frozen full-input manifest");
        Need(actual.state==ws31::EndpointLedger::ACTIVE || (!dataOnly &&
             (actual.state==ws31::EndpointLedger::ACK_COMPLETE ||
              actual.state==ws31::EndpointLedger::ENDPOINTS_RETIRED)),
             "WS31 packet identity is outside its allowed generation state");
        return actual;
    } catch (...) { failed=true; throw; }
    const ws31::EndpointLedger::Entry &PacketIdentity(Ptr<const Packet> packet,bool dataOnly) {
        Need(packet!=nullptr,"WS31 endpoint identity packet is absent");
        FlowIDNUMTag tag;
        Need(packet->PeekPacketTag(tag),"WS31 endpoint packet lacks FlowIDNUMTag");
        const auto &entry=Active(tag.GetId(),dataOnly);
        Need(tag.GetFlowSize()==entry.bytes,"WS31 encoded flow size differs from original input");
        return entry;
    }
    template<class K> void Own(std::map<K,ws31::EndpointKey> &owners,
                               const K &key,const ws31::EndpointKey &tuple) {
        auto it=owners.find(key);
        Need(it==owners.end() || it->second==tuple,
             "WS31 full input aliases an actual packed key or switch fourtuple");
        owners.insert(std::make_pair(key,tuple));
    }
public:
    explicit Ws31EndpointIdentity(std::shared_ptr<ws31::EndpointLedger> value):ledger(value) {
        Need(static_cast<bool>(ledger),"WS31 endpoint identity ledger is absent");
    }
    Ws31EndpointIdentity(const Ws31EndpointIdentity &)=delete;
    Ws31EndpointIdentity &operator=(const Ws31EndpointIdentity &)=delete;
    void Declare(int32_t id,const ws31::EndpointLedger::Entry &entry) {
        try {
            Need(!sealed && !failed,"WS31 identity declaration after seal or failure");
            Need(id>=0 && id<=65535 && uint64_t(id)==manifest.size(),
                 "WS31 identity input ordinals exceed U16 or are not consecutive");
            Need(entry.bytes>0 && entry.bytes<=std::numeric_limits<uint32_t>::max() &&
                 entry.demandNs<=uint64_t(std::numeric_limits<int64_t>::max()),
                 "WS31 identity input size/time exceeds production encoding");
            Need(entry.resources.sourceNode!=entry.resources.destinationNode,
                 "WS31 identity fixture requires distinct endpoint nodes");
            Own(txOwners,std::make_pair(entry.resources.sourceNode,entry.resources.txKey),entry.tuple);
            Own(rxOwners,std::make_pair(entry.resources.destinationNode,entry.resources.rxKey),entry.tuple);
            const auto &t=entry.tuple;
            Own(routeOwners,ws31::EndpointRouteKey(std::get<0>(t),std::get<1>(t),
                std::get<2>(t),std::get<3>(t)),t);
            Need(manifest.insert(std::make_pair(id,entry)).second,"WS31 duplicate declared identity");
        } catch (...) { failed=true; throw; }
    }
    void Seal(uint64_t fullyParsedRows) {
        Need(!sealed && !failed && fullyParsedRows>0 && fullyParsedRows==manifest.size(),
             "WS31 identity seal lacks the complete parsed input");
        sealed=true;
    }
    void RequireHealthy() const {
        if (!sealed || failed) throw std::logic_error("WS31 endpoint identity guard is not healthy");
    }
    void Reject(const char *message) { Need(false,message); }
    void Protocol(uint8_t protocol) {
        Need(sealed && !failed,"WS31 endpoint protocol check lacks a healthy sealed manifest");
        Need(protocol==0x11 || protocol==0xFC || protocol==0xFD,
             "WS31 endpoint identity guard received unsupported NIC protocol");
    }
    void Sender(uint32_t node,int32_t id,const ws31::EndpointKey &tuple,
                uint64_t actualTxKey,uint64_t bytes,uint32_t originalTag,uint64_t demandNs,uint64_t now,
                bool creation=false) {
        // Check original, unnarrowed fields before tag creation or mutable QP
        // getters. Decoding a truncated tag can never provide this provenance.
        Need(id>=0 && id<=65535 && bytes>0 && bytes<=std::numeric_limits<uint32_t>::max(),
             "WS31 original producer identity/size exceeds tag encoding");
        const auto &entry=Active(id,true);
        Need(node==entry.resources.sourceNode && actualTxKey==entry.resources.txKey &&
             tuple==entry.tuple && bytes==entry.bytes &&
             originalTag==entry.originalTag && demandNs==entry.demandNs &&
             entry.launchNs>=entry.demandNs && now>=entry.launchNs &&
             (!creation || now==entry.launchNs),
             "WS31 original sender fields differ from declared active request");
        ++senderChecks;
    }
    int32_t Data(uint32_t node,uint64_t actualRxKey,Ptr<const Packet> packet,const CustomHeader &ch) {
        const auto &entry=PacketIdentity(packet,true);
        Need(ch.l3Prot==0x11 && node==entry.resources.destinationNode && actualRxKey==entry.resources.rxKey &&
             ws31::EndpointKey(ch.sip,ch.dip,ch.udp.sport,ch.udp.dport,ch.udp.pg)==entry.tuple,
             "WS31 incoming data direction/tuple differs from original identity");
        FlowIDNUMTag tag; packet->PeekPacketTag(tag); ++dataChecks;
        return tag.GetId();
    }
    void FeedbackSource(uint32_t node,uint64_t actualRxKey,Ptr<const Packet> packet,
                        const CustomHeader &ch,int32_t rxId) {
        const int32_t id=Data(node,actualRxKey,packet,ch);
        Need(id==rxId,"WS31 feedback source tag differs from actual RX identity");
        ++feedbackChecks;
    }
    int32_t Ack(uint32_t node,uint64_t actualTxKey,Ptr<const Packet> packet,const CustomHeader &ch) {
        const auto &entry=PacketIdentity(packet,false);
        Need((ch.l3Prot==0xFC || ch.l3Prot==0xFD) && node==entry.resources.sourceNode &&
             actualTxKey==entry.resources.txKey &&
             ws31::EndpointKey(ch.dip,ch.sip,ch.ack.dport,ch.ack.sport,ch.ack.pg)==entry.tuple,
             "WS31 incoming feedback direction/tuple differs from original identity");
        FlowIDNUMTag tag; packet->PeekPacketTag(tag); ++ackChecks;
        return tag.GetId();
    }
    void ReceiverBinding(int32_t incomingId,int32_t storedId) {
        Need(storedId==-1 || storedId==incomingId,"WS31 actual RX has another request identity");
    }
    void SenderBinding(int32_t incomingId,int32_t storedId) {
        Need(storedId==incomingId,"WS31 actual TX has another request identity");
    }
    uint64_t SenderChecks() const { return senderChecks; }
    uint64_t DataChecks() const { return dataChecks; }
    uint64_t AckChecks() const { return ackChecks; }
    uint64_t FeedbackChecks() const { return feedbackChecks; }
};

} // namespace ns3
#endif
