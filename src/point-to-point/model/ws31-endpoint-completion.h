#ifndef WS31_ENDPOINT_COMPLETION_H
#define WS31_ENDPOINT_COMPLETION_H

// WIP fixture adapter: no production caller or Waf registration.
// The new fixture must call CaptureBeforeReceiverDeletion before its existing
// completion handler deletes RX, then allow that handler and QpComplete to
// return normally. Capture does not delete a QP, retire an endpoint, schedule
// reuse, or certify that the current Receive invocation has returned.
#include "ws31-endpoint-switch-probe.h"
#include <map>

namespace ns3 {

class Ws31EndpointCompletion {
public:
    struct Saved {
        Ptr<RdmaHw> tx, rx;
        Ptr<RdmaQueuePair> sender;
        Ptr<RdmaRxQueuePair> receiver;
        uint64_t capturedNs=0;
    };
private:
    ws31::EndpointLedger &ledger;
    std::map<int32_t,Saved> saved;
    static void Need(bool ok,const char *message) {
        if (!ok) throw std::logic_error(message);
    }
    static void Identity(int32_t id,const ws31::EndpointLedger::Entry &entry,
                         Ptr<RdmaHw> tx,Ptr<RdmaHw> rx,
                         Ptr<RdmaQueuePair> sender,Ptr<RdmaRxQueuePair> receiver) {
        Need(tx && rx && tx!=rx && tx->m_node && rx->m_node && sender && receiver,
             "WS31 completion requires actual distinct endpoint hardware and saved QPs");
        const auto &t=entry.tuple;
        const uint32_t sip=std::get<0>(t), dip=std::get<1>(t);
        const uint16_t sport=std::get<2>(t), dport=std::get<3>(t), pg=std::get<4>(t);
        Need(tx->m_node->GetId()==entry.resources.sourceNode &&
             rx->m_node->GetId()==entry.resources.destinationNode &&
             RdmaHw::GetQpKey(dip,sport,dport,pg)==entry.resources.txKey &&
             RdmaHw::GetRxQpKey(sip,sport,dport,pg)==entry.resources.rxKey,
             "WS31 completion actual endpoint resources differ from ledger");
        Need(sender->m_flow_id==id && sender->sip.Get()==sip && sender->dip.Get()==dip &&
             sender->sport==sport && sender->dport==dport && sender->m_pg==pg &&
             sender->m_size==entry.bytes && sender->m_workload_tag==entry.originalTag &&
             uint64_t(sender->startTime.GetNanoSeconds())==entry.demandNs &&
             entry.launchNs>=entry.demandNs &&
             sender->m_ws31LaunchDelayNs==entry.launchNs-entry.demandNs,
             "WS31 completion sender identity differs from ledger generation");
        Need(receiver->m_flow_id==id && receiver->sip==dip && receiver->dip==sip &&
             receiver->sport==dport && receiver->dport==sport && receiver->m_ecn_source.qIndex==pg,
             "WS31 completion receiver identity differs from ledger generation");
    }
public:
    explicit Ws31EndpointCompletion(ws31::EndpointLedger &value):ledger(value) {}
    Ws31EndpointCompletion(const Ws31EndpointCompletion &)=delete;
    Ws31EndpointCompletion &operator=(const Ws31EndpointCompletion &)=delete;

    const Saved &Get(int32_t id) const {
        auto it=saved.find(id);
        Need(it!=saved.end(),"WS31 completion has no saved actual RX object");
        return it->second;
    }
    std::size_t Captured() const { return saved.size(); }

    void CaptureBeforeReceiverDeletion(Ptr<RdmaQueuePair> sender,
                                       Ptr<RdmaHw> tx,Ptr<RdmaHw> rx) {
        Need(sender!=nullptr,"WS31 completion callback has no sender");
        const int32_t id=sender->m_flow_id;
        const auto &entry=ledger.Get(id);
        Need(entry.state==ws31::EndpointLedger::ACTIVE && !saved.count(id),
             "WS31 completion capture repeated or outside active generation");
        Need(tx && rx,"WS31 completion callback has no endpoint hardware");
        auto actualTx=tx->m_qpMap.find(entry.resources.txKey);
        auto actualRx=rx->m_rxQpMap.find(entry.resources.rxKey);
        Need(actualTx!=tx->m_qpMap.end() && actualTx->second==sender &&
             actualRx!=rx->m_rxQpMap.end() && actualRx->second,
             "WS31 completion capture must precede actual TX and RX map deletion");
        Identity(id,entry,tx,rx,sender,actualRx->second);
        Need(sender->snd_una==entry.bytes && sender->IsFinishedConst(),
             "WS31 completion callback lacks exact cumulative ACK");
        const uint64_t now=Simulator::Now().GetNanoSeconds();
        Need(now>=entry.lastNs,"WS31 completion capture moves evidence backwards");
        Saved record;
        record.tx=tx; record.rx=rx; record.sender=sender;
        record.receiver=actualRx->second; record.capturedNs=now;
        // Allocate retained references before changing the evidence ledger.
        // A failed capture must not leave a phantom completion record.
        auto inserted=saved.insert(std::make_pair(id,record));
        Need(inserted.second,"WS31 completion record insertion repeated");
        try { ledger.AckComplete(id,sender->snd_una,now); }
        catch (...) { saved.erase(inserted.first); throw; }
    }

    // The caller must use a successor event after the original Receive/token
    // wrapper returns. Reading early merely exposes the still-present maps;
    // it must never be interpreted as a retirement certificate.
    Ws31EndpointSwitchProbe::Observation Read(int32_t id,
            const Ws31EndpointSwitchProbe::Scope &scope,uint32_t txNic,uint32_t rxNic) const {
        const auto &record=Get(id);
        const auto &entry=ledger.Get(id);
        Identity(id,entry,record.tx,record.rx,record.sender,record.receiver);
        return Ws31EndpointSwitchProbe::Read(id,entry,record.tx,record.rx,
            record.sender,record.receiver,scope,txNic,rxNic);
    }

    // Explicit fixture action, separate from Read and from completion. The
    // channel adapter must already be healthy with all delivery/held tokens
    // accounted for in this same ledger. No normal timeout invokes this path.
    // The next certificate must use another fresh composite Read after erasure.
    void ReleaseHistoryAfterCertifiedDrain(int32_t id,
            const Ws31EndpointSwitchProbe::Scope &scope,uint32_t txNic,uint32_t rxNic) {
        const auto &entry=ledger.Get(id);
        Need(entry.state==ws31::EndpointLedger::DRAINED && ledger.OutstandingTokens()==0 &&
             ledger.Conserved(),"WS31 completion history release precedes certified drain");
        const auto observation=Read(id,scope,txNic,rxNic);
        Need(observation.snapshot.Quiet() && observation.endpoint.txHistory && observation.endpoint.rxHistory,
             "WS31 completion history release requires fresh quiet endpoints and both histories");
        const auto &record=Get(id);
        // These integer-key erases cannot recreate/delete transport objects,
        // change old finished slots, clear shared switch histories, or retire
        // the ledger entry. Saved RX/TX references remain available for reuse.
        record.tx->akashic_Qp.erase(entry.resources.txKey);
        record.rx->akashic_RxQp.erase(entry.resources.rxKey);
    }
};

} // namespace ns3
#endif
