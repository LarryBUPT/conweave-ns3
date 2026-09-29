#include "ns3/test.h"
#include "ns3/drop-tail-queue.h"
#include "ns3/simulator.h"
#include "ns3/point-to-point-net-device.h"
#include "ns3/point-to-point-channel.h"
#include "ns3/packet.h"
#include "ns3/ws21-feedback-header.h"

namespace ns3 {

class PointToPointTest : public TestCase
{
public:
  PointToPointTest ();

  virtual void DoRun (void);

private:
  void SendOnePacket (Ptr<PointToPointNetDevice> device);
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
  AddTestCase (new Ws21FeedbackHeaderTestCase);
}

static PointToPointTestSuite g_pointToPointTestSuite;

} // namespace ns3
