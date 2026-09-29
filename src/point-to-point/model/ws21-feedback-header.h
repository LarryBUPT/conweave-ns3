/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */

#ifndef WS21_FEEDBACK_HEADER_H
#define WS21_FEEDBACK_HEADER_H

#include "ns3/header.h"

namespace ns3 {

/** Compact, versioned payload carried by the WS-21 feedback IPv4 protocol.
 *  The source/destination ToRs are derived from the IPv4 host addresses.
 */
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
  uint64_t GetGeneratedNs(void) const;

  uint8_t version;
  uint8_t type;
  uint16_t candidatePort;
  uint64_t windowEndNs;
  uint32_t cePackets;
  uint32_t samplePackets;
  uint32_t sequence;
  uint16_t generationDelayNs;

  static const uint8_t IP_PROTOCOL = 0xFA;
  static const uint32_t SERIALIZED_SIZE = 26;
};

}  // namespace ns3

#endif  // WS21_FEEDBACK_HEADER_H
