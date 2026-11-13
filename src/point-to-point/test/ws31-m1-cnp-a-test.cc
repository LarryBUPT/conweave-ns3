#include "ns3/boolean.h"
#include "ns3/ipv4-header.h"
#include "ns3/node.h"
#include "ns3/ppp-header.h"
#include "ns3/qbb-header.h"
#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/simulator.h"
#include "ns3/test.h"
#include "ns3/uinteger.h"

namespace ns3 {

class Ws31M1CnpAReceiverCase : public TestCase {
 public:
  Ws31M1CnpAReceiverCase()
      : TestCase("IRN out-of-order CNP switch preserves SACK and cumulative progress") {}

  void DoRun() override {
    for (int setting = 0; setting < 3; ++setting) {
      Ptr<RdmaHw> hw = CreateObject<RdmaHw>();
      hw->SetAttribute("IrnEnable", BooleanValue(true));
      if (setting != 0)
        hw->SetAttribute("OoOCnpEnabled", BooleanValue(setting == 1));

      BooleanValue actual;
      hw->GetAttribute("OoOCnpEnabled", actual);
      const bool expectedCnp = setting != 2;
      NS_TEST_ASSERT_MSG_EQ(actual.Get(), expectedCnp, "default or explicit switch differs");

      Ptr<RdmaRxQueuePair> rx = CreateObject<RdmaRxQueuePair>();
      bool cnp = false;
      int result = hw->ReceiverCheckSeq(1000, rx, 1000, cnp);
      NS_TEST_ASSERT_MSG_EQ(result, 2, "out-of-order segment must request SACK");
      NS_TEST_ASSERT_MSG_EQ(cnp, expectedCnp, "only the out-of-order CNP reason may change");
      NS_TEST_ASSERT_MSG_EQ(rx->ReceiverNextExpectedSeq, 0u, "gap must remain unconfirmed");
      NS_TEST_ASSERT_MSG_EQ(rx->m_irn_sack_.blockExists(1000, 1000), true,
                            "out-of-order segment must be retained in SACK");

      cnp = false;
      result = hw->ReceiverCheckSeq(1000, rx, 1000, cnp);
      NS_TEST_ASSERT_MSG_EQ(result, 4, "repeat SACK inside the NACK interval is suppressed");
      NS_TEST_ASSERT_MSG_EQ(cnp, false, "suppressed feedback must not create CNP");

      cnp = false;
      result = hw->ReceiverCheckSeq(0, rx, 1000, cnp);
      NS_TEST_ASSERT_MSG_EQ(result, 6, "gap filling must generate cumulative ACK");
      NS_TEST_ASSERT_MSG_EQ(cnp, false, "in-order gap fill must not create OOO CNP");
      NS_TEST_ASSERT_MSG_EQ(rx->ReceiverNextExpectedSeq, 2000u,
                            "cumulative progress must cover the SACKed segment");
      NS_TEST_ASSERT_MSG_EQ(rx->m_irn_sack_.IsEmpty(), true, "SACK must drain on progress");
    }
    Simulator::Destroy();
  }
};

// Keep both NICs disconnected so the production receiver queues its serialized
// feedback without a network run. The sender still processes that exact frame.
class Ws31M1CnpAProtocolCase : public TestCase {
 public:
  Ws31M1CnpAProtocolCase()
      : TestCase("actual UDP feedback, DCQCN and IRN recovery retain their paths") {}

  struct Fixture {
    Ptr<Node> txNode = CreateObject<Node>();
    Ptr<Node> rxNode = CreateObject<Node>();
    Ptr<QbbNetDevice> txDev = CreateObject<QbbNetDevice>();
    Ptr<QbbNetDevice> rxDev = CreateObject<QbbNetDevice>();
    Ptr<RdmaHw> tx = CreateObject<RdmaHw>();
    Ptr<RdmaHw> rx = CreateObject<RdmaHw>();
    Ptr<RdmaQueuePair> qp;
    const Ipv4Address source = Ipv4Address("11.0.0.1");
    const Ipv4Address destination = Ipv4Address("11.0.0.2");
    uint32_t completed = 0;
    int32_t completedFlow = -1;

    Fixture(int setting, uint64_t bytes) {
      txNode->AddDevice(txDev);
      rxNode->AddDevice(rxDev);
      txDev->SetDataRate(DataRate("100Gbps"));
      rxDev->SetDataRate(DataRate("100Gbps"));
      tx->SetNode(txNode);
      rx->SetNode(rxNode);
      tx->SetAttribute("IrnEnable", BooleanValue(true));
      rx->SetAttribute("IrnEnable", BooleanValue(true));
      tx->SetAttribute("CcMode", UintegerValue(1));
      tx->SetAttribute("IrnBdp", UintegerValue(30000));
      tx->SetAttribute("IrnRtoLow", TimeValue(MicroSeconds(100)));
      tx->SetAttribute("IrnRtoHigh", TimeValue(MicroSeconds(320)));
      if (setting != 0)
        rx->SetAttribute("OoOCnpEnabled", BooleanValue(setting == 1));

      RdmaInterfaceMgr txNic(txDev), rxNic(rxDev);
      txNic.qpGrp = CreateObject<RdmaQueuePairGroup>();
      rxNic.qpGrp = CreateObject<RdmaQueuePairGroup>();
      tx->m_nic.push_back(txNic);
      rx->m_nic.push_back(rxNic);
      tx->m_rtTable[destination.Get()].push_back(0);
      rx->m_rtTable[source.Get()].push_back(0);
      tx->Setup(MakeCallback(&Fixture::OnComplete, this));
      rx->Setup(RdmaHw::QpCompleteCallback());

      qp = CreateObject<RdmaQueuePair>(3, source, destination, 1234, 5678);
      qp->SetSize(bytes);
      qp->SetFlowId(47);
      qp->m_rate = qp->m_max_rate = DataRate("100Gbps");
      qp->irn.m_enabled = true;
      qp->irn.m_bdp = 30000;
      qp->irn.m_rtoLow = MicroSeconds(100);
      qp->irn.m_rtoHigh = MicroSeconds(320);
      tx->m_qpMap[RdmaHw::GetQpKey(destination.Get(), 1234, 5678, 3)] = qp;
    }

    void OnComplete(Ptr<RdmaQueuePair> actual) {
      ++completed;
      completedFlow = actual->m_flow_id;
    }

    Ptr<Packet> SendNext() {
      Ptr<Packet> packet = tx->GetNxtPacket(qp);
      tx->PktSent(qp, packet, NanoSeconds(0));
      return packet;
    }

    Ptr<Packet> ReceiveData(Ptr<Packet> packet, bool ce) {
      Ptr<Packet> incoming = packet->Copy();
      if (ce) {
        PppHeader ppp;
        Ipv4Header ip;
        incoming->RemoveHeader(ppp);
        incoming->RemoveHeader(ip);
        ip.SetTos(3);
        incoming->AddHeader(ip);
        incoming->AddHeader(ppp);
      }
      CustomHeader data(CustomHeader::L2_Header | CustomHeader::L3_Header |
                        CustomHeader::L4_Header);
      incoming->PeekHeader(data);
      rx->ReceiveUdp(incoming, data);
      return rxDev->m_rdmaEQ->DequeueQindex(-1);
    }

    void ReceiveFeedback(Ptr<Packet> feedback) {
      CustomHeader ack(CustomHeader::L2_Header | CustomHeader::L3_Header |
                       CustomHeader::L4_Header);
      feedback->PeekHeader(ack);
      tx->ReceiveAck(feedback, ack);
    }
  };

  void DoRun() override {
    for (int setting = 0; setting < 3; ++setting) {
      for (int ce = 0; ce < 2; ++ce) {
        for (int ooo = 0; ooo < 2; ++ooo) {
          Fixture fixture(setting, 3000);
          Ptr<Packet> first = fixture.SendNext();
          Ptr<Packet> second = fixture.SendNext();
          Ptr<Packet> feedback = fixture.ReceiveData(ooo ? second : first, ce != 0);
          NS_TEST_ASSERT_MSG_NE(feedback, Ptr<Packet>(), "feedback frame missing");
          CustomHeader ack(CustomHeader::L2_Header | CustomHeader::L3_Header |
                           CustomHeader::L4_Header);
          feedback->PeekHeader(ack);
          const bool expectedCnp = ce || (ooo && setting != 2);
          NS_TEST_ASSERT_MSG_EQ(ack.l3Prot, 0xFDu, "IRN feedback protocol changed");
          NS_TEST_ASSERT_MSG_EQ(bool((ack.ack.flags >> qbbHeader::FLAG_CNP) & 1),
                                expectedCnp, "serialized CNP does not match CE/OOO table");
          NS_TEST_ASSERT_MSG_EQ(ack.ack.seq, ooo ? 0u : 1000u,
                                "cumulative ACK changed");
          NS_TEST_ASSERT_MSG_EQ(ack.ack.irnNack, ooo ? 1000u : 0u,
                                "SACK start changed");
          NS_TEST_ASSERT_MSG_EQ(ack.ack.irnNackSize, ooo ? 1000u : 0u,
                                "SACK length changed");
          NS_TEST_ASSERT_MSG_EQ(fixture.rx->cnp_total, expectedCnp ? 1u : 0u,
                                "CNP total must count the OR once");
          NS_TEST_ASSERT_MSG_EQ(fixture.rx->cnp_by_ecn, ce ? 1u : 0u,
                                "CE reason count changed");
          NS_TEST_ASSERT_MSG_EQ(fixture.rx->cnp_by_ooo,
                                ooo && setting != 2 ? 1u : 0u,
                                "OOO reason count changed");

          Ptr<Packet> parsed = feedback->Copy();
          PppHeader ppp;
          Ipv4Header ip;
          qbbHeader wire;
          parsed->RemoveHeader(ppp);
          parsed->RemoveHeader(ip);
          parsed->RemoveHeader(wire);
          NS_TEST_ASSERT_MSG_EQ(wire.GetSeq(), ack.ack.seq,
                                "serialized qbb cumulative ACK differs");
          NS_TEST_ASSERT_MSG_EQ(wire.GetIrnNackSize(), ack.ack.irnNackSize,
                                "serialized qbb SACK differs");

          fixture.ReceiveFeedback(feedback);
          NS_TEST_ASSERT_MSG_EQ(fixture.qp->snd_una, ooo ? 0u : 1000u,
                                "sender cumulative progress changed");
          NS_TEST_ASSERT_MSG_EQ(fixture.qp->irn.m_recovery, bool(ooo),
                                "sender recovery entry changed");
          NS_TEST_ASSERT_MSG_EQ(fixture.qp->mlx.m_first_cnp, !expectedCnp,
                                "sender DCQCN did not receive the serialized flag");
          Simulator::Stop(MicroSeconds(5));
          Simulator::Run();
          const bool rateReduced = fixture.qp->m_rate.GetBitRate() < 100000000000ULL;
          NS_TEST_ASSERT_MSG_EQ(rateReduced, expectedCnp,
                                "CE/OOO CNP did not control sender rate");
          Simulator::Destroy();
        }
      }
    }

    // A true missing first segment is selectively retransmitted after SACK.
    {
      Fixture fixture(2, 2000);
      Ptr<Packet> missing = fixture.SendNext();
      Ptr<Packet> later = fixture.SendNext();
      Ptr<Packet> sack = fixture.ReceiveData(later, false);
      fixture.ReceiveFeedback(sack);
      NS_TEST_ASSERT_MSG_EQ(fixture.qp->irn.m_recovery, true,
                            "true loss did not enter IRN recovery");
      Ptr<Packet> retry = fixture.SendNext();
      CustomHeader retried(CustomHeader::L2_Header | CustomHeader::L3_Header |
                           CustomHeader::L4_Header);
      retry->PeekHeader(retried);
      NS_TEST_ASSERT_MSG_EQ(retried.udp.seq, 0u, "recovery did not resend the gap");
      Ptr<Packet> finalAck = fixture.ReceiveData(retry, false);
      fixture.ReceiveFeedback(finalAck);
      NS_TEST_ASSERT_MSG_EQ(fixture.completed, 1u, "true-loss completion missing");
      NS_TEST_ASSERT_MSG_EQ(fixture.completedFlow, 47, "completion identity changed");
      NS_TEST_ASSERT_MSG_EQ(fixture.qp->snd_una, 2000u, "true-loss final ACK incomplete");
      Simulator::Destroy();
      (void)missing;
    }

    // A delivered tail whose ACK is lost must still complete after the RTO.
    {
      Fixture fixture(2, 1000);
      Ptr<Packet> tail = fixture.SendNext();
      Ptr<Packet> lostAck = fixture.ReceiveData(tail, false);
      NS_TEST_ASSERT_MSG_NE(lostAck, Ptr<Packet>(), "tail ACK missing at receiver");
      Simulator::Stop(MicroSeconds(101));
      Simulator::Run();
      NS_TEST_ASSERT_MSG_EQ(fixture.qp->snd_nxt, 0u,
                            "tail ACK loss did not rewind at actual RTO");
      Ptr<Packet> retry = fixture.SendNext();
      Ptr<Packet> recoveredAck = fixture.ReceiveData(retry, false);
      fixture.ReceiveFeedback(recoveredAck);
      NS_TEST_ASSERT_MSG_EQ(fixture.completed, 1u, "tail ACK recovery did not complete");
      NS_TEST_ASSERT_MSG_EQ(fixture.completedFlow, 47, "tail completion identity changed");
      Simulator::Destroy();
    }
  }
};

class Ws31M1CnpASuite : public TestSuite {
 public:
  Ws31M1CnpASuite() : TestSuite("ws31-m1-cnp-a", UNIT) {
    AddTestCase(new Ws31M1CnpAReceiverCase());
    AddTestCase(new Ws31M1CnpAProtocolCase());
  }
};

static Ws31M1CnpASuite g_ws31M1CnpASuite;

}  // namespace ns3
