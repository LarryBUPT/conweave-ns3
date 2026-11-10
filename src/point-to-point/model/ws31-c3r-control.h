#ifndef WS31_C3R_CONTROL_H
#define WS31_C3R_CONTROL_H

#include "ns3/header.h"

namespace ns3 {

// Serialized switch/host control for the C3R mode. Flow ID represents the
// live QP generation; data packets already carry its FlowIDNUMTag equivalent.
class Ws31C3rControl : public Header {
 public:
  enum Type { PAUSE = 1, DRAIN = 2, RESUME = 3, ABORT = 4 };
  static const uint8_t IP_PROTOCOL = 0xFB;
  static const uint32_t SERIALIZED_SIZE = 40;

  Ws31C3rControl();
  static TypeId GetTypeId(void);
  virtual TypeId GetInstanceTypeId(void) const;
  virtual void Print(std::ostream &os) const;
  virtual uint32_t GetSerializedSize(void) const;
  virtual void Serialize(Buffer::Iterator start) const;
  virtual uint32_t Deserialize(Buffer::Iterator start);
  bool IsValid(void) const;

  uint8_t version;
  uint8_t type;
  uint16_t pg;
  uint32_t sip, dip;
  uint16_t sport, dport;
  uint32_t flowId, epoch;
  uint64_t cut, generatedNs;
};

}  // namespace ns3

#endif  // WS31_C3R_CONTROL_H
