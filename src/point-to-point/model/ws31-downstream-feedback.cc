#include "ws31-downstream-feedback.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED(Ws31DownstreamFeedback);

bool Ws31DownstreamPath::operator==(const Ws31DownstreamPath &other) const {
    return sourceLeaf == other.sourceLeaf && destinationLeaf == other.destinationLeaf &&
           sourcePort == other.sourcePort && measuredSwitch == other.measuredSwitch &&
           measuredPort == other.measuredPort && measuredPeer == other.measuredPeer;
}

TypeId Ws31DownstreamFeedback::GetTypeId() {
    static TypeId id = TypeId("ns3::Ws31DownstreamFeedback")
                           .SetParent<Header>()
                           .AddConstructor<Ws31DownstreamFeedback>();
    return id;
}

TypeId Ws31DownstreamFeedback::GetInstanceTypeId() const { return GetTypeId(); }

uint32_t Ws31DownstreamFeedback::GetSerializedSize() const {
    return SerializedBytes + (flowBound ? 4 : 0);
}

void Ws31DownstreamFeedback::Serialize(Buffer::Iterator out) const {
    out.WriteHtonU32(path.sourceLeaf);
    out.WriteHtonU32(path.destinationLeaf);
    out.WriteHtonU32(path.sourcePort);
    out.WriteHtonU32(path.measuredSwitch);
    out.WriteHtonU32(path.measuredPort);
    out.WriteHtonU32(path.measuredPeer);
    out.WriteHtonU32(queueBytes);
    out.WriteHtonU64(sampleNs);
    if (flowBound) {
        out.WriteHtonU16(sourceUdpPort);
        out.WriteHtonU16(destinationUdpPort);
    }
}

uint32_t Ws31DownstreamFeedback::Deserialize(Buffer::Iterator in) {
    path.sourceLeaf = in.ReadNtohU32();
    path.destinationLeaf = in.ReadNtohU32();
    path.sourcePort = in.ReadNtohU32();
    path.measuredSwitch = in.ReadNtohU32();
    path.measuredPort = in.ReadNtohU32();
    path.measuredPeer = in.ReadNtohU32();
    queueBytes = in.ReadNtohU32();
    sampleNs = in.ReadNtohU64();
    if (flowBound) {
        sourceUdpPort = in.ReadNtohU16();
        destinationUdpPort = in.ReadNtohU16();
    }
    return GetSerializedSize();
}

void Ws31DownstreamFeedback::Print(std::ostream &out) const {
    out << "source_leaf=" << path.sourceLeaf << " destination_leaf=" << path.destinationLeaf
        << " candidate_port=" << path.sourcePort << " measured_switch=" << path.measuredSwitch
        << " measured_port=" << path.measuredPort << " measured_peer=" << path.measuredPeer
        << " queue_bytes=" << queueBytes << " sample_ns=" << sampleNs;
    if (flowBound) out << " sport=" << sourceUdpPort << " dport=" << destinationUdpPort;
}

}  // namespace ns3
