/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */

#include "ws21-feedback-header.h"

#include <iostream>
#include <limits>

#include "ns3/log.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("Ws21FeedbackHeader");
NS_OBJECT_ENSURE_REGISTERED(Ws21FeedbackHeader);
const uint8_t Ws21FeedbackHeader::IP_PROTOCOL;
const uint32_t Ws21FeedbackHeader::SERIALIZED_SIZE;

Ws21FeedbackHeader::Ws21FeedbackHeader()
    : version(2),
      type(1),
      candidatePort(0),
      windowEndNs(0),
      cePackets(0),
      samplePackets(0),
      sequence(0),
      generationDelayNs(0), session(0), windowStartNs(0) {}

TypeId Ws21FeedbackHeader::GetTypeId(void) {
  static TypeId tid = TypeId("ns3::Ws21FeedbackHeader")
                          .SetParent<Header>()
                          .SetGroupName("PointToPoint")
                          .AddConstructor<Ws21FeedbackHeader>();
  return tid;
}

TypeId Ws21FeedbackHeader::GetInstanceTypeId(void) const { return GetTypeId(); }

void Ws21FeedbackHeader::Print(std::ostream &os) const {
  os << "WS21Feedback version=" << unsigned(version) << " type=" << unsigned(type)
     << " candidate_port=" << candidatePort
     << " sequence=" << sequence << " ce=" << cePackets << "/" << samplePackets
     << " window_end_ns=" << windowEndNs
     << " generated_ns=" << GetGeneratedNs();
}

uint32_t Ws21FeedbackHeader::GetSerializedSize(void) const {
  return version == 3 ? SERIALIZED_SIZE + 12 : SERIALIZED_SIZE;
}

void Ws21FeedbackHeader::Serialize(Buffer::Iterator start) const {
  start.WriteU8(version);
  start.WriteU8(type);
  start.WriteHtonU16(candidatePort);
  start.WriteHtonU64(windowEndNs);
  start.WriteHtonU32(cePackets);
  start.WriteHtonU32(samplePackets);
  start.WriteHtonU32(sequence);
  start.WriteHtonU16(generationDelayNs);
  if (version == 3) {
    start.WriteHtonU32(session);
    start.WriteHtonU64(windowStartNs);
  }
}

uint32_t Ws21FeedbackHeader::Deserialize(Buffer::Iterator start) {
  const uint32_t available = start.GetSize();
  if (available < SERIALIZED_SIZE) { version = 0; return 0; }
  version = start.ReadU8();
  if (version == 3 && available < SERIALIZED_SIZE + 12) { version = 0; return 0; }
  type = start.ReadU8();
  candidatePort = start.ReadNtohU16();
  windowEndNs = start.ReadNtohU64();
  cePackets = start.ReadNtohU32();
  samplePackets = start.ReadNtohU32();
  sequence = start.ReadNtohU32();
  generationDelayNs = start.ReadNtohU16();
  session = version == 3 ? start.ReadNtohU32() : 0;
  windowStartNs = version == 3 ? start.ReadNtohU64() : 0;
  return GetSerializedSize();
}

uint64_t Ws21FeedbackHeader::GetGeneratedNs(void) const {
  return windowEndNs + generationDelayNs;
}

bool Ws21FeedbackHeader::IsValid(void) const {
  return (version == 2 || (version == 3 && session > 0 && windowStartNs > 0 &&
                         windowStartNs <= windowEndNs)) &&
         type == 1 && candidatePort != 0 && windowEndNs > 0 &&
         samplePackets > 0 &&
         cePackets <= samplePackets && sequence > 0 &&
         windowEndNs <= std::numeric_limits<uint64_t>::max() - generationDelayNs;
}

}  // namespace ns3
