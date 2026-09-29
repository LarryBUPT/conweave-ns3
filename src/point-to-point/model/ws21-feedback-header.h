/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */

#ifndef WS21_FEEDBACK_HEADER_H
#define WS21_FEEDBACK_HEADER_H

#include "ns3/header.h"

namespace ns3 {

/** Fixed-width payload carried by the WS-21 feedback IPv4 protocol. */
class Ws21FeedbackHeader : public Header {
 public:
  Ws21FeedbackHeader();

  static TypeId GetTypeId(void);
  virtual TypeId GetInstanceTypeId(void) const;
  virtual void Print(std::ostream &os) const;
  virtual uint32_t GetSerializedSize(void) const;
  virtual void Serialize(Buffer::Iterator start) const;
  virtual uint32_t Deserialize(Buffer::Iterator start);

  bool IsValid(void) const;

  uint8_t version;
  uint32_t sourceTor;
  uint32_t destinationTor;
  uint16_t candidatePort;
  uint64_t windowStartNs;
  uint64_t windowEndNs;
  uint32_t cePackets;
  uint32_t samplePackets;
  uint64_t sequence;
  uint64_t generatedNs;

  static const uint8_t IP_PROTOCOL = 0xFA;
  static const uint32_t SERIALIZED_SIZE = 51;
};

}  // namespace ns3

#endif  // WS21_FEEDBACK_HEADER_H
