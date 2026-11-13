#include "ns3/boolean.h"
#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/simulator.h"
#include "ns3/test.h"

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

class Ws31M1CnpASuite : public TestSuite {
 public:
  Ws31M1CnpASuite() : TestSuite("ws31-m1-cnp-a", UNIT) {
    AddTestCase(new Ws31M1CnpAReceiverCase());
  }
};

static Ws31M1CnpASuite g_ws31M1CnpASuite;

}  // namespace ns3
