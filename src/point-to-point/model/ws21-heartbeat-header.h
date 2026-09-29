#ifndef WS21_HEARTBEAT_HEADER_H
#define WS21_HEARTBEAT_HEADER_H

#include "ns3/header.h"

namespace ns3 {

// Direct-neighbor liveness probe. The receiving device identifies the link;
// epoch and sequence identify the current outstanding probe on that link.
class Ws21HeartbeatHeader : public Header {
 public:
  Ws21HeartbeatHeader();

  static TypeId GetTypeId(void);
  virtual TypeId GetInstanceTypeId(void) const;
  virtual void Print(std::ostream &os) const;
  virtual uint32_t GetSerializedSize(void) const;
  virtual void Serialize(Buffer::Iterator start) const;
  virtual uint32_t Deserialize(Buffer::Iterator start);

  bool IsValid(void) const;

  uint8_t version;
  uint8_t type;
  uint32_t epoch;
  uint32_t sequence;

  static const uint8_t HELLO = 2;
  static const uint8_t ACK = 3;
  static const uint32_t SERIALIZED_SIZE = 10;
};

}  // namespace ns3

#endif  // WS21_HEARTBEAT_HEADER_H
