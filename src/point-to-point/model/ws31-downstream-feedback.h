#ifndef WS31_DOWNSTREAM_FEEDBACK_H
#define WS31_DOWNSTREAM_FEEDBACK_H

#include <ns3/header.h>

namespace ns3 {

struct Ws31DownstreamPath {
    uint32_t sourceLeaf = 0;
    uint32_t destinationLeaf = 0;
    uint32_t sourcePort = 0;
    uint32_t measuredSwitch = 0;
    uint32_t measuredPort = 0;
    uint32_t measuredPeer = 0;

    bool operator==(const Ws31DownstreamPath &other) const;
};

class Ws31DownstreamFeedback : public Header {
  public:
    enum : uint8_t { Protocol = 0xF9 };
    enum : uint32_t { SerializedBytes = 36 };
    explicit Ws31DownstreamFeedback(bool bound = false) : flowBound(bound) {}

    static TypeId GetTypeId();
    TypeId GetInstanceTypeId() const override;
    uint32_t GetSerializedSize() const override;
    void Serialize(Buffer::Iterator start) const override;
    uint32_t Deserialize(Buffer::Iterator start) override;
    void Print(std::ostream &out) const override;

    Ws31DownstreamPath path;
    uint32_t queueBytes = 0;
    uint64_t sampleNs = 0;
    bool flowBound;
    uint16_t sourceUdpPort = 0, destinationUdpPort = 0;
};

}  // namespace ns3

#endif
