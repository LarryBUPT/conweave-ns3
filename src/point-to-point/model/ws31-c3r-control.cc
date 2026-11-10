#include "ws31-c3r-control.h"

#include <iostream>

#include "ns3/log.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("Ws31C3rControl");
NS_OBJECT_ENSURE_REGISTERED(Ws31C3rControl);
const uint8_t Ws31C3rControl::IP_PROTOCOL;
const uint32_t Ws31C3rControl::SERIALIZED_SIZE;

Ws31C3rControl::Ws31C3rControl()
    : version(1), type(0), pg(0), sip(0), dip(0), sport(0), dport(0),
      flowId(0), epoch(0), cut(0), generatedNs(0) {}

TypeId Ws31C3rControl::GetTypeId(void) {
  static TypeId tid = TypeId("ns3::Ws31C3rControl")
                          .SetParent<Header>()
                          .SetGroupName("PointToPoint")
                          .AddConstructor<Ws31C3rControl>();
  return tid;
}

TypeId Ws31C3rControl::GetInstanceTypeId(void) const { return GetTypeId(); }

void Ws31C3rControl::Print(std::ostream &os) const {
  os << "C3R type=" << unsigned(type) << " epoch=" << epoch
     << " flow=" << flowId << " cut=" << cut;
}

uint32_t Ws31C3rControl::GetSerializedSize(void) const { return SERIALIZED_SIZE; }

void Ws31C3rControl::Serialize(Buffer::Iterator i) const {
  i.WriteU8(version);
  i.WriteU8(type);
  i.WriteHtonU16(pg);
  i.WriteHtonU32(sip);
  i.WriteHtonU32(dip);
  i.WriteHtonU16(sport);
  i.WriteHtonU16(dport);
  i.WriteHtonU32(flowId);
  i.WriteHtonU32(epoch);
  i.WriteHtonU64(cut);
  i.WriteHtonU64(generatedNs);
}

uint32_t Ws31C3rControl::Deserialize(Buffer::Iterator i) {
  version = i.ReadU8();
  type = i.ReadU8();
  pg = i.ReadNtohU16();
  sip = i.ReadNtohU32();
  dip = i.ReadNtohU32();
  sport = i.ReadNtohU16();
  dport = i.ReadNtohU16();
  flowId = i.ReadNtohU32();
  epoch = i.ReadNtohU32();
  cut = i.ReadNtohU64();
  generatedNs = i.ReadNtohU64();
  return SERIALIZED_SIZE;
}

bool Ws31C3rControl::IsValid(void) const {
  return version == 1 && type >= PAUSE && type <= ABORT &&
         sip != 0 && dip != 0 && epoch != 0 && generatedNs != 0 &&
         (type != DRAIN && type != RESUME || cut != 0);
}

}  // namespace ns3
