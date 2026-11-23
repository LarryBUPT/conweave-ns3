#ifndef WS31_RX_REORDER_FIXTURE_H
#define WS31_RX_REORDER_FIXTURE_H

#include <ns3/flow-id-num-tag.h>
#include <ns3/qbb-net-device.h>
#include <ns3/simulator.h>

#include <iostream>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace ns3 {

// The fixture holds only the listed first transmissions at the receiver ingress.
// Sender timeout and recovery packets continue through the ordinary receive path.
class Ws31RxReorderFixture {
  public:
    void Install(Ptr<QbbNetDevice> device, const std::string &scenario) {
        if (scenario == "gap_closure") {
            m_steps = {{1, {0, 1000}, true}, {2, {0, 1000}, false},
                       {3, {0, 2000}, false}, {5, {0, 0}, false}};
        } else if (scenario == "two_caps") {
            m_steps = {{1, {0, 1000}, false}, {2, {0, 2000}, false}, {3, {1, 1000}, false},
                       {4, {2, 1000}, false}, {5, {0, 0}, false}, {6, {1, 0}, false},
                       {7, {2, 0}, false}};
        } else if (scenario == "receiver_deadline") {
            m_steps = {{1, {0, 1000}, false}, {22, {0, 2000}, false}};
            m_dropOriginalGap = true;
            m_expected.insert({0, 0});
        } else {
            NS_FATAL_ERROR("Unknown WS-31 receiver fixture " << scenario);
        }
        for (const auto &step : m_steps) m_expected.insert(step.packet);
        m_receive = device->m_rdmaReceiveCb;
        device->m_rdmaReceiveCb = MakeCallback(&Ws31RxReorderFixture::Receive, this);
    }

    bool Finished() const { return m_expected.empty() && m_held.empty(); }

  private:
    using Key = std::pair<int32_t, uint32_t>;  // frozen demand row and payload offset
    struct Step {
        uint32_t delayUs;
        Key packet;
        bool keepOriginal;
    };
    struct Arrival {
        Ptr<Packet> packet;
        CustomHeader header;
    };

    QbbNetDevice::RdmaReceiveCb m_receive;
    std::vector<Step> m_steps;
    std::set<Key> m_expected;
    std::map<Key, Arrival> m_held;
    bool m_dropOriginalGap = false;

    void Trace(const char *event, Key key) const {
        std::cout << "WS31_RX_FIXTURE event=" << event
                  << " time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " flow_id=" << key.first << " seq=" << key.second << std::endl;
    }

    int Receive(Ptr<Packet> packet, CustomHeader &header) {
        FlowIDNUMTag flow;
        if (header.l3Prot != 0x11 || !packet->PeekPacketTag(flow)) {
            return m_receive(packet, header);
        }
        const Key key(flow.GetId(), header.udp.seq);
        if (m_expected.erase(key) == 0) return m_receive(packet, header);

        Trace("hold_first", key);
        m_held.emplace(key, Arrival{packet, header});
        if (m_expected.empty()) {
            if (m_dropOriginalGap) {
                m_held.erase({0, 0});
                Trace("drop_first", {0, 0});
            }
            for (const auto &step : m_steps) {
                Simulator::Schedule(MicroSeconds(step.delayUs),
                                    &Ws31RxReorderFixture::Release, this, step.packet,
                                    step.keepOriginal);
            }
        }
        return 1;
    }

    void Release(Key key, bool keepOriginal) {
        const auto found = m_held.find(key);
        NS_ABORT_MSG_IF(found == m_held.end(), "Receiver fixture did not hold scheduled payload");
        Ptr<Packet> packet = keepOriginal ? found->second.packet->Copy() : found->second.packet;
        CustomHeader header = found->second.header;
        if (!keepOriginal) m_held.erase(found);
        Trace("release", key);
        m_receive(packet, header);
    }
};

}  // namespace ns3

#endif
