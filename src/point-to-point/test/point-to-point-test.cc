#include "ns3/test.h"
#include "ns3/drop-tail-queue.h"
#include "ns3/simulator.h"
#include "ns3/point-to-point-net-device.h"
#include "ns3/point-to-point-channel.h"
#include "ns3/packet.h"
#include "ns3/ws21-feedback-header.h"
#include "ns3/ws21-heartbeat-header.h"
#include "ns3/irn-pfc-timeout.h"

#include <limits>

namespace ns3 {

class PointToPointTest : public TestCase
{
public:
  PointToPointTest ();

  virtual void DoRun (void);

private:
  void SendOnePacket (Ptr<PointToPointNetDevice> device);
};

class IrnPfcTimeoutTestCase : public TestCase
{
public:
  IrnPfcTimeoutTestCase () : TestCase ("IRN timeout is deferred only for an actual PFC pause and its resume grace") {}
  virtual void DoRun (void)
  {
    const Time rto = MicroSeconds (454);
    const Time resume = MicroSeconds (200);
    NS_TEST_ASSERT_MSG_EQ (IrnPfcTimeoutDeferral (MicroSeconds (500), rto, false,
                                                  false, Time (0)), Time (0),
                           "PFC enabled without a pause must not suppress recovery");
    NS_TEST_ASSERT_MSG_EQ (IrnPfcTimeoutDeferral (MicroSeconds (500), rto, true,
                                                  false, Time (0)), rto,
                           "timeout during a pause must be rescheduled");
    NS_TEST_ASSERT_MSG_EQ (IrnPfcTimeoutDeferral (MicroSeconds (500), rto, false,
                                                  true, resume), MicroSeconds (154),
                           "resume must leave one full RTO before recovery");
    NS_TEST_ASSERT_MSG_EQ (IrnPfcTimeoutDeferral (MicroSeconds (654), rto, false,
                                                  true, resume), Time (0),
                           "persistent silence after resume must allow recovery");
  }
};

class Ws21FeedbackHeaderTestCase : public TestCase
{
public:
  Ws21FeedbackHeaderTestCase () : TestCase ("WS-21 feedback header serialization and validation") {}
  virtual void DoRun (void)
  {
    Ws21FeedbackHeader sent;
    sent.candidatePort = 4;
    sent.windowEndNs = 129000;
    sent.cePackets = 7;
    sent.samplePackets = 19;
    sent.sequence = 0x10203040;
    sent.generationDelayNs = 1000;
    NS_TEST_ASSERT_MSG_EQ (sent.GetSerializedSize (), Ws21FeedbackHeader::SERIALIZED_SIZE,
                           "unexpected fixed feedback header size");
    NS_TEST_ASSERT_MSG_EQ (sent.IsValid (), true, "valid report rejected");

    Ptr<Packet> packet = Create<Packet> ();
    packet->AddHeader (sent);
    Ws21FeedbackHeader received;
    NS_TEST_ASSERT_MSG_EQ (packet->RemoveHeader (received), Ws21FeedbackHeader::SERIALIZED_SIZE,
                           "wrong number of feedback header bytes");
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), true, "round-tripped report rejected");
    NS_TEST_ASSERT_MSG_EQ (received.version, sent.version, "version changed");
    NS_TEST_ASSERT_MSG_EQ (received.type, sent.type, "message type changed");
    NS_TEST_ASSERT_MSG_EQ (received.candidatePort, sent.candidatePort,
                           "candidate port changed");
    NS_TEST_ASSERT_MSG_EQ (received.windowEndNs, sent.windowEndNs, "window end changed");
    NS_TEST_ASSERT_MSG_EQ (received.cePackets, sent.cePackets, "CE count changed");
    NS_TEST_ASSERT_MSG_EQ (received.samplePackets, sent.samplePackets,
                           "sample count changed");
    NS_TEST_ASSERT_MSG_EQ (received.sequence, sent.sequence, "sequence changed");
    NS_TEST_ASSERT_MSG_EQ (received.GetGeneratedNs (), 130000ULL,
                           "generation time changed");

    received.cePackets = received.samplePackets + 1;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "invalid CE/sample ratio accepted");
    received.cePackets = sent.cePackets;
    received.version = 1;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "legacy version accepted");
    received.version = 2;
    received.type = 2;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "unknown message type accepted");
    received.type = 1;
    received.samplePackets = 0;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "empty sample accepted as zero congestion");
    received.samplePackets = sent.samplePackets;
    received.sequence = 0;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "zero sequence accepted");
    received.sequence = sent.sequence;
    received.candidatePort = 0;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "zero candidate port accepted");
    received.candidatePort = sent.candidatePort;
    received.windowEndNs = std::numeric_limits<uint64_t>::max ();
    received.generationDelayNs = 1;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "generation-time overflow accepted");
  }
};

class Ws21HeartbeatHeaderTestCase : public TestCase
{
public:
  Ws21HeartbeatHeaderTestCase () : TestCase ("WS-21 heartbeat header serialization and validation") {}
  virtual void DoRun (void)
  {
    Ws21HeartbeatHeader sent;
    sent.type = Ws21HeartbeatHeader::HELLO;
    sent.epoch = 0x10203040;
    sent.sequence = 0x50607080;
    NS_TEST_ASSERT_MSG_EQ (sent.GetSerializedSize (), Ws21HeartbeatHeader::SERIALIZED_SIZE,
                           "unexpected heartbeat header size");
    NS_TEST_ASSERT_MSG_EQ (sent.IsValid (), true, "valid HELLO rejected");
    Ptr<Packet> packet = Create<Packet> ();
    packet->AddHeader (sent);
    Ws21HeartbeatHeader received;
    NS_TEST_ASSERT_MSG_EQ (packet->RemoveHeader (received), Ws21HeartbeatHeader::SERIALIZED_SIZE,
                           "wrong number of heartbeat header bytes");
    NS_TEST_ASSERT_MSG_EQ (received.version, sent.version, "version changed");
    NS_TEST_ASSERT_MSG_EQ (received.type, sent.type, "type changed");
    NS_TEST_ASSERT_MSG_EQ (received.epoch, sent.epoch, "epoch changed");
    NS_TEST_ASSERT_MSG_EQ (received.sequence, sent.sequence, "sequence changed");
    received.type = Ws21HeartbeatHeader::ACK;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), true, "valid ACK rejected");
    received.type = 1;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "STATE decoded as heartbeat");
    received.type = Ws21HeartbeatHeader::HELLO;
    received.version = 1;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "old version accepted");
    received.version = 2;
    received.epoch = 0;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "zero epoch accepted");
    received.epoch = sent.epoch;
    received.sequence = 0;
    NS_TEST_ASSERT_MSG_EQ (received.IsValid (), false, "zero sequence accepted");
  }
};

PointToPointTest::PointToPointTest ()
  : TestCase ("PointToPoint")
{
}

void
PointToPointTest::SendOnePacket (Ptr<PointToPointNetDevice> device)
{
  Ptr<Packet> p = Create<Packet> ();
  device->Send (p, device->GetBroadcast (), 0x800);
}


void
PointToPointTest::DoRun (void)
{
  Ptr<Node> a = CreateObject<Node> ();
  Ptr<Node> b = CreateObject<Node> ();
  Ptr<PointToPointNetDevice> devA = CreateObject<PointToPointNetDevice> ();
  Ptr<PointToPointNetDevice> devB = CreateObject<PointToPointNetDevice> ();
  Ptr<PointToPointChannel> channel = CreateObject<PointToPointChannel> ();

  devA->Attach (channel);
  devA->SetAddress (Mac48Address::Allocate ());
  devA->SetQueue (CreateObject<DropTailQueue> ());
  devB->Attach (channel);
  devB->SetAddress (Mac48Address::Allocate ());
  devB->SetQueue (CreateObject<DropTailQueue> ());

  a->AddDevice (devA);
  b->AddDevice (devB);

  Simulator::Schedule (Seconds (1.0), &PointToPointTest::SendOnePacket, this, devA);

  Simulator::Run ();

  Simulator::Destroy ();
}
//-----------------------------------------------------------------------------
class PointToPointTestSuite : public TestSuite
{
public:
  PointToPointTestSuite ();
};

PointToPointTestSuite::PointToPointTestSuite ()
  : TestSuite ("devices-point-to-point", UNIT)
{
  AddTestCase (new PointToPointTest);
  AddTestCase (new IrnPfcTimeoutTestCase);
  AddTestCase (new Ws21FeedbackHeaderTestCase);
  AddTestCase (new Ws21HeartbeatHeaderTestCase);
}

static PointToPointTestSuite g_pointToPointTestSuite;

} // namespace ns3
