#include "ws21-heartbeat-header.h"

#include "ns3/log.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("Ws21HeartbeatHeader");
NS_OBJECT_ENSURE_REGISTERED(Ws21HeartbeatHeader);
const uint8_t Ws21HeartbeatHeader::HELLO;
const uint8_t Ws21HeartbeatHeader::ACK;
const uint32_t Ws21HeartbeatHeader::SERIALIZED_SIZE;

Ws21HeartbeatHeader::Ws21HeartbeatHeader()
    : version(2), type(HELLO), epoch(0), sequence(0) {}

TypeId Ws21HeartbeatHeader::GetTypeId(void) {
  static TypeId tid = TypeId("ns3::Ws21HeartbeatHeader")
                          .SetParent<Header>()
                          .SetGroupName("PointToPoint")
                          .AddConstructor<Ws21HeartbeatHeader>();
  return tid;
}

TypeId Ws21HeartbeatHeader::GetInstanceTypeId(void) const { return GetTypeId(); }

void Ws21HeartbeatHeader::Print(std::ostream &os) const {
  os << "WS21Heartbeat version=" << unsigned(version) << " type=" << unsigned(type)
     << " epoch=" << epoch << " sequence=" << sequence;
}

uint32_t Ws21HeartbeatHeader::GetSerializedSize(void) const { return SERIALIZED_SIZE; }

void Ws21HeartbeatHeader::Serialize(Buffer::Iterator start) const {
  start.WriteU8(version);
  start.WriteU8(type);
  start.WriteHtonU32(epoch);
  start.WriteHtonU32(sequence);
}

uint32_t Ws21HeartbeatHeader::Deserialize(Buffer::Iterator start) {
  version = start.ReadU8();
  type = start.ReadU8();
  epoch = start.ReadNtohU32();
  sequence = start.ReadNtohU32();
  return SERIALIZED_SIZE;
}

bool Ws21HeartbeatHeader::IsValid(void) const {
  return version == 2 && (type == HELLO || type == ACK) && epoch != 0 && sequence != 0;
}

}  // namespace ns3
