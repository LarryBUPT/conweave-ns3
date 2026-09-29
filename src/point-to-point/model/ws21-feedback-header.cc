/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */

#include "ws21-feedback-header.h"

#include <iostream>

#include "ns3/log.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("Ws21FeedbackHeader");
NS_OBJECT_ENSURE_REGISTERED(Ws21FeedbackHeader);
const uint8_t Ws21FeedbackHeader::IP_PROTOCOL;
const uint32_t Ws21FeedbackHeader::SERIALIZED_SIZE;

Ws21FeedbackHeader::Ws21FeedbackHeader()
    : version(1),
      sourceTor(0),
      destinationTor(0),
      candidatePort(0),
      windowStartNs(0),
      windowEndNs(0),
      cePackets(0),
      samplePackets(0),
      sequence(0),
      generatedNs(0) {}

TypeId Ws21FeedbackHeader::GetTypeId(void) {
  static TypeId tid = TypeId("ns3::Ws21FeedbackHeader")
                          .SetParent<Header>()
                          .SetGroupName("PointToPoint")
                          .AddConstructor<Ws21FeedbackHeader>();
  return tid;
}

TypeId Ws21FeedbackHeader::GetInstanceTypeId(void) const { return GetTypeId(); }

void Ws21FeedbackHeader::Print(std::ostream &os) const {
  os << "WS21Feedback version=" << unsigned(version) << " source_tor=" << sourceTor
     << " destination_tor=" << destinationTor << " candidate_port=" << candidatePort
     << " sequence=" << sequence << " ce=" << cePackets << "/" << samplePackets
     << " window_ns=" << windowStartNs << "-" << windowEndNs
     << " generated_ns=" << generatedNs;
}

uint32_t Ws21FeedbackHeader::GetSerializedSize(void) const { return SERIALIZED_SIZE; }

void Ws21FeedbackHeader::Serialize(Buffer::Iterator start) const {
  start.WriteU8(version);
  start.WriteHtonU32(sourceTor);
  start.WriteHtonU32(destinationTor);
  start.WriteHtonU16(candidatePort);
  start.WriteHtonU64(windowStartNs);
  start.WriteHtonU64(windowEndNs);
  start.WriteHtonU32(cePackets);
  start.WriteHtonU32(samplePackets);
  start.WriteHtonU64(sequence);
  start.WriteHtonU64(generatedNs);
}

uint32_t Ws21FeedbackHeader::Deserialize(Buffer::Iterator start) {
  version = start.ReadU8();
  sourceTor = start.ReadNtohU32();
  destinationTor = start.ReadNtohU32();
  candidatePort = start.ReadNtohU16();
  windowStartNs = start.ReadNtohU64();
  windowEndNs = start.ReadNtohU64();
  cePackets = start.ReadNtohU32();
  samplePackets = start.ReadNtohU32();
  sequence = start.ReadNtohU64();
  generatedNs = start.ReadNtohU64();
  return SERIALIZED_SIZE;
}

bool Ws21FeedbackHeader::IsValid(void) const {
  return version == 1 && candidatePort != 0 && samplePackets > 0 &&
         cePackets <= samplePackets && windowStartNs <= windowEndNs &&
         windowEndNs <= generatedNs && sequence > 0;
}

}  // namespace ns3
