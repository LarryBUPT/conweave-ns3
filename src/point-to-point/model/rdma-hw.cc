#include "rdma-hw.h"
#include "ws30-v13-fixture.h"
#include "ws30-observer.h"
#include "ws31-c3-observation.h"
#include "ws31-c3r-control.h"
#include "ws31-label-fixture.h"
#include "ws31-endpoint-identity.h"
#include "ws31-v2-native-session.h"

#include <ns3/ipv4-header.h>
#include <ns3/seq-ts-header.h>
#include <ns3/simulator.h>
#include <ns3/udp-header.h>

#include <climits>
#include <cstdlib>
#include <map>
#include <iomanip>
#include <sstream>

#include "cn-header.h"
#include "flow-stat-tag.h"
#include "irn-pfc-timeout.h"
#include "ns3/boolean.h"
#include "ns3/data-rate.h"
#include "ns3/double.h"
#include "ns3/flow-id-num-tag.h"
#include "ns3/pointer.h"
#include "ns3/ppp-header.h"
#include "ns3/settings.h"
#include "ns3/switch-node.h"
#include "ns3/uinteger.h"
#include "ns3/workload-tag.h"
#include "ppp-header.h"
#include "qbb-header.h"

namespace ns3 {

static bool Ws31C3ObserveQp() {
    return Ws30Level()==2 && Settings::lb_mode>=47 && Settings::lb_mode<=49;
}

static uint64_t ws31C3QpGeneration=0;
static std::map<const RdmaQueuePair*,uint64_t> ws31C3QpGenerations;

// Passive snapshots of real protocol state. No GetBytesLeft/IsFinished calls:
// those helpers can consume SACK blocks in this simulator.
static void Ws30V14State(const char *event, Ptr<RdmaQueuePair> q) {
    if (!Ws30V14Enabled() || !Ws30Level() || !q->m_ws30Serial) return;
    std::ostringstream o;
    o << std::setprecision(17) << "WS30V14_STATE event=" << event
      << " time_ns=" << Simulator::Now().GetNanoSeconds()
      << " object=" << reinterpret_cast<uintptr_t>(PeekPointer(q))
      << " serial=" << q->m_ws30Serial << " flow_id=" << q->m_flow_id
      << " rounds_done=" << q->m_ws30RoundDone << " released=" << q->m_ws30Released
      << " snd_nxt=" << q->snd_nxt << " snd_una=" << q->snd_una
      << " highest_ack=" << q->irn.m_highest_ack << " max_seq=" << q->irn.m_max_seq
      << " sack_bytes=" << q->irn.m_sack.getSackBufferOverhead()
      << " recovery=" << q->irn.m_recovery << " recovery_seq=" << q->irn.m_recovery_seq
      << " rate=" << q->m_rate.GetBitRate() << " target=" << q->mlx.m_targetRate.GetBitRate()
      << " alpha=" << q->mlx.m_alpha << " first_cnp=" << q->mlx.m_first_cnp
      << " sack_events=" << q->m_ws30SackEvents << " cnp_events=" << q->m_ws30CnpEvents
      << " recovery_events=" << q->m_ws30RecoveryEvents
      << " alpha_timer=" << q->mlx.m_eventUpdateAlpha.GetUid()
      << " alpha_running=" << q->mlx.m_eventUpdateAlpha.IsRunning()
      << " decrease_timer=" << q->mlx.m_eventDecreaseRate.GetUid()
      << " decrease_running=" << q->mlx.m_eventDecreaseRate.IsRunning()
      << " rp_timer=" << q->mlx.m_rpTimer.GetUid()
      << " rp_running=" << q->mlx.m_rpTimer.IsRunning()
      << " rto_timer=" << q->m_retransmit.GetUid()
      << " rto_running=" << q->m_retransmit.IsRunning();
    static uint64_t bytes=0; bytes+=o.str().size()+1;
    if (bytes>67108864ULL) NS_FATAL_ERROR("WS30V14 observation overflow");
    std::cout << o.str() << std::endl;
}

struct Ws25QpDiagnostic {
    uint64_t rx_ooo_packets = 0, sack_feedback = 0, cnp_feedback = 0;
    uint64_t repeated_sends = 0, timeout_recovery = 0;
    uint64_t rx_duplicate=0, repeated_bytes=0, nack_feedback=0;
    uint64_t rx_ooo_payload_bytes=0, rx_sack_pending_peak_bytes=0;
    uint64_t feedback_wire_bytes=0;
};
static std::map<int32_t, Ws25QpDiagnostic> ws25_qp_diagnostics;
static bool Ws25DiagnosticEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS25_DIAG");
        return Ws30Level() || (value && value[0] == '1' && value[1] == '\0');
    }();
    return enabled;
}

static bool Ws13DiagnosticEnabled() {
    static const bool enabled = []() {
        const char *value = std::getenv("WS13_DIAG");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

static bool Ws13BackgroundQp(Ptr<RdmaQueuePair> qp) {
    if (!Ws13DiagnosticEnabled() || qp->m_workload_tag != 1) return false;
    auto dst = Settings::hostIp2IdMap.find(qp->dip.Get());
    return dst != Settings::hostIp2IdMap.end() &&
           (Settings::lb_mode == 20 || dst->second == 856 || dst->second == 576);
}

static void Ws13LogQp(const char *event, Ptr<RdmaQueuePair> qp,
                      uint16_t irn_nack_size = 0) {
    auto src = Settings::hostIp2IdMap.find(qp->sip.Get());
    auto dst = Settings::hostIp2IdMap.find(qp->dip.Get());
    NS_ASSERT_MSG(src != Settings::hostIp2IdMap.end() && dst != Settings::hostIp2IdMap.end(),
                  "WS-13 QP host address absent");
    std::cout << "WS13_QP event=" << event
              << " time_ns=" << Simulator::Now().GetNanoSeconds()
              << " src=" << src->second << " dst=" << dst->second
              << " sport=" << qp->sport << " dport=" << qp->dport
              << " flow_id=" << qp->m_flow_id << " snd_una=" << qp->snd_una
              << " snd_nxt=" << qp->snd_nxt
              << " rate_bps=" << qp->m_rate.GetBitRate()
              << " irn_nack_size=" << irn_nack_size << std::endl;
}

NS_LOG_COMPONENT_DEFINE("RdmaHw");

std::unordered_map<unsigned, unsigned> acc_timeout_count;
uint64_t RdmaHw::nAllPkts = 0;

TypeId RdmaHw::GetTypeId(void) {
    static TypeId tid =
        TypeId("ns3::RdmaHw")
            .SetParent<Object>()
            .AddAttribute("MinRate", "Minimum rate of a throttled flow",
                          DataRateValue(DataRate("100Mb/s")),
                          MakeDataRateAccessor(&RdmaHw::m_minRate), MakeDataRateChecker())
            .AddAttribute("Mtu", "Mtu.", UintegerValue(1000), MakeUintegerAccessor(&RdmaHw::m_mtu),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("CcMode", "which mode of DCQCN is running", UintegerValue(0),
                          MakeUintegerAccessor(&RdmaHw::m_cc_mode), MakeUintegerChecker<uint32_t>())
            .AddAttribute("NACKGenerationInterval", "The NACK/CNP Generation interval",
                          DoubleValue(4.0), MakeDoubleAccessor(&RdmaHw::m_nack_interval),
                          MakeDoubleChecker<double>())
            .AddAttribute("L2ChunkSize", "Layer 2 chunk size. Disable chunk mode if equals to 0.",
                          UintegerValue(4000), MakeUintegerAccessor(&RdmaHw::m_chunk),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("L2AckInterval", "Layer 2 Ack intervals. Disable ack if equals to 0.",
                          UintegerValue(1), MakeUintegerAccessor(&RdmaHw::m_ack_interval),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("L2BackToZero", "Layer 2 go back to zero transmission.",
                          BooleanValue(false), MakeBooleanAccessor(&RdmaHw::m_backto0),
                          MakeBooleanChecker())
            .AddAttribute("EwmaGain",
                          "Control gain parameter which determines the level of rate decrease",
                          DoubleValue(1.0 / 16), MakeDoubleAccessor(&RdmaHw::m_g),
                          MakeDoubleChecker<double>())
            .AddAttribute("RateOnFirstCnp", "the fraction of rate on first CNP", DoubleValue(1.0),
                          MakeDoubleAccessor(&RdmaHw::m_rateOnFirstCNP),
                          MakeDoubleChecker<double>())
            .AddAttribute("ClampTargetRate", "Clamp target rate.", BooleanValue(false),
                          MakeBooleanAccessor(&RdmaHw::m_EcnClampTgtRate), MakeBooleanChecker())
            .AddAttribute("RPTimer", "The rate increase timer at RP in microseconds",
                          DoubleValue(300.0), MakeDoubleAccessor(&RdmaHw::m_rpgTimeReset),
                          MakeDoubleChecker<double>())
            .AddAttribute("RateDecreaseInterval", "The interval of rate decrease check",
                          DoubleValue(4.0), MakeDoubleAccessor(&RdmaHw::m_rateDecreaseInterval),
                          MakeDoubleChecker<double>())
            .AddAttribute("FastRecoveryTimes", "The rate increase timer at RP", UintegerValue(1),
                          MakeUintegerAccessor(&RdmaHw::m_rpgThreshold),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("AlphaResumInterval", "The interval of resuming alpha", DoubleValue(1.0),
                          MakeDoubleAccessor(&RdmaHw::m_alpha_resume_interval),
                          MakeDoubleChecker<double>())
            .AddAttribute("RateAI", "Rate increment unit in AI period",
                          DataRateValue(DataRate("5Mb/s")), MakeDataRateAccessor(&RdmaHw::m_rai),
                          MakeDataRateChecker())
            .AddAttribute("RateHAI", "Rate increment unit in hyperactive AI period",
                          DataRateValue(DataRate("50Mb/s")), MakeDataRateAccessor(&RdmaHw::m_rhai),
                          MakeDataRateChecker())
            .AddAttribute("VarWin", "Use variable window size or not", BooleanValue(false),
                          MakeBooleanAccessor(&RdmaHw::m_var_win), MakeBooleanChecker())
            .AddAttribute("FastReact", "Fast React to congestion feedback", BooleanValue(true),
                          MakeBooleanAccessor(&RdmaHw::m_fast_react), MakeBooleanChecker())
            .AddAttribute("MiThresh", "Threshold of number of consecutive AI before MI",
                          UintegerValue(5), MakeUintegerAccessor(&RdmaHw::m_miThresh),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("TargetUtil",
                          "The Target Utilization of the bottleneck bandwidth, by default 95%",
                          DoubleValue(0.95), MakeDoubleAccessor(&RdmaHw::m_targetUtil),
                          MakeDoubleChecker<double>())
            .AddAttribute(
                "UtilHigh",
                "The upper bound of Target Utilization of the bottleneck bandwidth, by default 98%",
                DoubleValue(0.98), MakeDoubleAccessor(&RdmaHw::m_utilHigh),
                MakeDoubleChecker<double>())
            .AddAttribute("RateBound", "Bound packet sending by rate, for test only",
                          BooleanValue(true), MakeBooleanAccessor(&RdmaHw::m_rateBound),
                          MakeBooleanChecker())
            .AddAttribute("MultiRate", "Maintain multiple rates in HPCC", BooleanValue(true),
                          MakeBooleanAccessor(&RdmaHw::m_multipleRate), MakeBooleanChecker())
            .AddAttribute("SampleFeedback", "Whether sample feedback or not", BooleanValue(false),
                          MakeBooleanAccessor(&RdmaHw::m_sampleFeedback), MakeBooleanChecker())
            .AddAttribute("TimelyAlpha", "Alpha of TIMELY", DoubleValue(0.875),
                          MakeDoubleAccessor(&RdmaHw::m_tmly_alpha), MakeDoubleChecker<double>())
            .AddAttribute("TimelyBeta", "Beta of TIMELY", DoubleValue(0.8),
                          MakeDoubleAccessor(&RdmaHw::m_tmly_beta), MakeDoubleChecker<double>())
            .AddAttribute("TimelyTLow", "TLow of TIMELY (ns)", UintegerValue(50000),
                          MakeUintegerAccessor(&RdmaHw::m_tmly_TLow),
                          MakeUintegerChecker<uint64_t>())
            .AddAttribute("TimelyTHigh", "THigh of TIMELY (ns)", UintegerValue(500000),
                          MakeUintegerAccessor(&RdmaHw::m_tmly_THigh),
                          MakeUintegerChecker<uint64_t>())
            .AddAttribute("TimelyMinRtt", "MinRtt of TIMELY (ns)", UintegerValue(20000),
                          MakeUintegerAccessor(&RdmaHw::m_tmly_minRtt),
                          MakeUintegerChecker<uint64_t>())
            .AddAttribute("DctcpRateAI", "DCTCP's Rate increment unit in AI period",
                          DataRateValue(DataRate("1000Mb/s")),
                          MakeDataRateAccessor(&RdmaHw::m_dctcp_rai), MakeDataRateChecker())
            .AddAttribute("IrnEnable", "Enable IRN", BooleanValue(false),
                          MakeBooleanAccessor(&RdmaHw::m_irn), MakeBooleanChecker())
            .AddAttribute("OoOCnpEnabled", "Emit CNP for IRN out-of-order feedback",
                          BooleanValue(true), MakeBooleanAccessor(&RdmaHw::m_oooCnpEnabled),
                          MakeBooleanChecker())
            .AddAttribute("IrnRtoLow", "Low RTO for IRN", TimeValue(MicroSeconds(454)),
                          MakeTimeAccessor(&RdmaHw::m_irn_rtoLow), MakeTimeChecker())
            .AddAttribute("IrnRtoHigh", "High RTO for IRN", TimeValue(MicroSeconds(1350)),
                          MakeTimeAccessor(&RdmaHw::m_irn_rtoHigh), MakeTimeChecker())
            .AddAttribute("IrnBdp", "BDP Limit for IRN in Bytes", UintegerValue(100000),
                          MakeUintegerAccessor(&RdmaHw::m_irn_bdp), MakeUintegerChecker<uint32_t>())
            .AddAttribute("L2Timeout", "Sender's timer of waiting for the ack",
                          TimeValue(MilliSeconds(4)), MakeTimeAccessor(&RdmaHw::m_waitAckTimeout),
                          MakeTimeChecker());
    return tid;
}

RdmaHw::RdmaHw() {
    cnp_total = 0;
    cnp_by_ecn = 0;
    cnp_by_ooo = 0;
}

void RdmaHw::SetNode(Ptr<Node> node) { m_node = node; }
void RdmaHw::Setup(QpCompleteCallback cb) {
    for (uint32_t i = 0; i < m_nic.size(); i++) {
        Ptr<QbbNetDevice> dev = m_nic[i].dev;
        if (dev == NULL) continue;
        // share data with NIC
        dev->m_rdmaEQ->m_qpGrp = m_nic[i].qpGrp;
        // setup callback
        dev->m_rdmaReceiveCb = MakeCallback(&RdmaHw::Receive, this);
        dev->m_rdmaLinkDownCb = MakeCallback(&RdmaHw::SetLinkDown, this);
        dev->m_rdmaPktSent = MakeCallback(&RdmaHw::PktSent, this);
        // config NIC
        dev->m_rdmaEQ->m_mtu = m_mtu;
        dev->m_rdmaEQ->m_rdmaGetNxtPkt = MakeCallback(&RdmaHw::GetNxtPacket, this);
    }
    // setup qp complete callback
    m_qpCompleteCallback = cb;
}

uint32_t RdmaHw::GetNicIdxOfQp(Ptr<RdmaQueuePair> qp) {
    auto &v = m_rtTable[qp->dip.Get()];
    if (v.size() > 0) {
        return v[qp->GetHash() % v.size()];
    }
    NS_ASSERT_MSG(false, "We assume at least one NIC is alive");
    std::cout << "We assume at least one NIC is alive" << std::endl;
    exit(1);
}

uint64_t RdmaHw::GetQpKey(uint32_t dip, uint16_t sport, uint16_t dport,
                          uint16_t pg) {  // Sender perspective
    return ((uint64_t)dip << 32) | ((uint64_t)sport << 16) | (uint64_t)dport | (uint64_t)pg;
}
Ptr<RdmaQueuePair> RdmaHw::GetQp(uint64_t key) {
    auto it = m_qpMap.find(key);

    // lookup main memory
    if (it != m_qpMap.end()) {
        return it->second;
    }

    return NULL;
}
void RdmaHw::AddQueuePair(uint64_t size, uint16_t pg, Ipv4Address sip, Ipv4Address dip,
                          uint16_t sport, uint16_t dport, uint32_t win, uint64_t baseRtt,
                          int32_t flow_id, uint32_t workload_tag, uint64_t demand_start_ns) {
    AddQueuePairWithNative(size,pg,sip,dip,sport,dport,win,baseRtt,flow_id,workload_tag,
                          demand_start_ns,std::shared_ptr<Ws31V2NativeRequest>());
}

void RdmaHw::FailWs31V2() {
    if (m_ws31V2Required) m_ws31V2Failed=true;
    if (m_ws31V2Session) m_ws31V2Session->Fail("V2 hardware boundary failed");
}

void RdmaHw::RequireWs31V2Input(std::shared_ptr<Ws31V2NativeSession> session) try {
    if (m_ws31V2Required) throw std::logic_error("V2 hardware configuration repeated");
    m_ws31V2Required=true; m_ws31V2Session=session;
    if (!session || !m_node || !m_qpMap.empty() || !akashic_Qp.empty() || Ws30V13Life()!=0)
        throw std::logic_error("V2 hardware lacks clean node/session");
    session->RequireHealthy();
} catch (...) { FailWs31V2(); throw; }

void RdmaHw::AddQueuePairV2(uint64_t size,uint16_t pg,Ipv4Address sip,Ipv4Address dip,
        uint16_t sport,uint16_t dport,uint32_t win,uint64_t baseRtt,int32_t flowId,
        uint32_t originalTag,uint64_t demandNs,std::shared_ptr<Ws31V2NativeRequest> request) {
    if (!m_ws31V2Required) {
        m_ws31V2Required=true; m_ws31V2Failed=true;
        Ws31V2NativeSession::FailHandle(request,"V2 hardware was not configured");
        throw std::logic_error("V2 hardware was not configured");
    }
    AddQueuePairWithNative(size,pg,sip,dip,sport,dport,win,baseRtt,flowId,originalTag,demandNs,request);
}

void RdmaHw::AddQueuePairWithNative(uint64_t size,uint16_t pg,Ipv4Address sip,Ipv4Address dip,
        uint16_t sport,uint16_t dport,uint32_t win,uint64_t baseRtt,int32_t flow_id,
        uint32_t workload_tag,uint64_t demand_start_ns,std::shared_ptr<Ws31V2NativeRequest> request) try {
    if (m_ws31V2Required) {
        if (m_ws31V2Failed || !m_ws31V2Session || !m_node)
            throw std::logic_error("V2 QP creation lacks healthy configured hardware");
        m_ws31V2Session->ValidateLaunch(request,m_node->GetId(),flow_id,sip.Get(),dip.Get(),
            sport,dport,pg,size,workload_tag,demand_start_ns);
        const uint64_t key=GetQpKey(dip.Get(),sport,dport,pg);
        if (m_qpMap.count(key) || akashic_Qp.count(key))
            throw std::logic_error("V2 creation replaces live QP/history");
    } else if (request) throw std::logic_error("Legacy hardware received V2 handle");
    if (m_ws31EndpointIdentity) {
        if (!m_node) m_ws31EndpointIdentity->Reject("WS31 sender hardware has no node");
        const uint64_t key=GetQpKey(dip.Get(),sport,dport,pg);
        m_ws31EndpointIdentity->Sender(m_node->GetId(),flow_id,
            ws31::EndpointKey(sip.Get(),dip.Get(),sport,dport,pg),key,size,
            workload_tag,demand_start_ns,Simulator::Now().GetNanoSeconds(),true);
        if (m_qpMap.count(key) || akashic_Qp.count(key))
            m_ws31EndpointIdentity->Reject("WS31 sender creation replaces live QP or unreleased history");
    }
    // create qp
    Ptr<RdmaQueuePair> qp = CreateObject<RdmaQueuePair>(pg, sip, dip, sport, dport);
    if (demand_start_ns != uint64_t(-1)) {
        const uint64_t now=Simulator::Now().GetNanoSeconds();
        if (demand_start_ns>now) NS_FATAL_ERROR("QP demand time is in the future");
        qp->startTime=NanoSeconds(demand_start_ns);
        qp->m_ws31LaunchDelayNs=now-demand_start_ns;
    }
    qp->SetSize(size);
    qp->SetWin(win);
    qp->SetBaseRtt(baseRtt);
    qp->SetVarWin(m_var_win);
    qp->SetFlowId(flow_id);
    qp->m_workload_tag = workload_tag;
    qp->SetTimeout(m_waitAckTimeout);
    if (Ws30V13Life() && workload_tag == 2) {
        static uint64_t serial = 0;
        qp->m_ws30Serial = ++serial;
        qp->m_ws30Released = size;
        if (Ws30V13Life() == 1) {
            if (size != uint64_t(3)*Ws30RoundBytes()) NS_FATAL_ERROR("Persistent fixture requires three fixed-size requests");
            qp->m_ws30Persistent = true;
            qp->m_ws30Released = Ws30RoundBytes();
            for (uint32_t r=1; r<3; ++r)
                Simulator::Schedule(NanoSeconds(uint64_t(r)*Ws30RoundIntervalNs()), &RdmaHw::ReleaseWs30Round, this, qp, r);
        }
        std::cout << "WS30V13_CREATE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " serial=" << qp->m_ws30Serial << " flow_id=" << flow_id
                  << " persistent=" << qp->m_ws30Persistent << " size=" << size
                  << " sport=" << sport << " dport=" << dport << std::endl;

    }

    if (m_irn) {
        qp->irn.m_enabled = m_irn;
        qp->irn.m_bdp = m_irn_bdp;
        qp->irn.m_rtoLow = m_irn_rtoLow;
        qp->irn.m_rtoHigh = m_irn_rtoHigh;
    }

    // add qp
    uint32_t nic_idx = GetNicIdxOfQp(qp);
    m_nic[nic_idx].qpGrp->AddQp(qp);
    uint64_t key = GetQpKey(dip.Get(), sport, dport, pg);
    if (Settings::lb_mode == 57) {
        if (m_qpMap.count(key)) NS_FATAL_ERROR("C3R sender generation overlaps a live QP");
        // The former QP completed before the scheduler may reuse this tuple.
        // Late feedback is checked against the new flow ID below.
        akashic_Qp.erase(key);
    }
    if (Ws30V13Life() >= 3) {
        if (m_qpMap.count(key)) NS_FATAL_ERROR("Tuple fixture attempted to replace a live QP");
        // Explicit test-only recreation after final ACK and receiver deletion.
        akashic_Qp.erase(key);
    }
    m_qpMap[key] = qp;
    if (Settings::lb_mode == 57 && m_ws31C3rReplayStale &&
        m_ws31C3rSavedFeedback && m_ws31C3rSavedFeedbackKey == key) {
        Simulator::Schedule(NanoSeconds(1), &RdmaHw::ReplayWs31C3rStaleFeedback, this);
    }

    // set init variables
    DataRate m_bps = m_nic[nic_idx].dev->GetDataRate();
    qp->m_rate = m_bps;
    qp->m_max_rate = m_bps;
    if (m_cc_mode == 1) {
        qp->mlx.m_targetRate = m_bps;
    } else if (m_cc_mode == 3) {
        qp->hp.m_curRate = m_bps;
        if (m_multipleRate) {
            for (uint32_t i = 0; i < IntHeader::maxHop; i++) qp->hp.hopState[i].Rc = m_bps;
        }
    } else if (m_cc_mode == 7) {
        qp->tmly.m_curRate = m_bps;
    }

    // Notify Nic
    if (qp->m_ws30Serial) {
        Ws30V14State("created",qp);
        std::cout << "WS30V13_RELEASE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " serial=" << qp->m_ws30Serial << " round=0 demand_ns="
                  << qp->startTime.GetNanoSeconds() << " released=" << qp->m_ws30Released
                  << " snd_nxt=0 snd_una=0 rate=" << qp->m_rate.GetBitRate() << " alpha=" << qp->mlx.m_alpha << std::endl;
    }
    if (m_ws31V2Required) m_ws31V2Session->BindActual(request,m_node->GetId(),qp);
    if (Ws31C3ObserveQp()) {
        const uint64_t generation=++ws31C3QpGeneration;
        ws31C3QpGenerations[PeekPointer(qp)]=generation;
        std::cout << "WS31_C3_QP_REGISTER time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " event=" << NextWs31C3ObservationEvent()
                  << " generation=" << generation << " host=" << m_node->GetId()
                  << " flow_id=" << qp->m_flow_id
                  << " sip=" << qp->sip.Get() << " dip=" << qp->dip.Get()
                  << " sport=" << qp->sport << " dport=" << qp->dport
                  << " pg=" << qp->m_pg << " tag=" << qp->m_workload_tag
                  << " size=" << qp->m_size << " demand_ns="
                  << qp->startTime.GetNanoSeconds() << std::endl;
    }
    m_nic[nic_idx].dev->NewQp(qp);
    if (Ws31C3ObserveQp())
        std::cout << "WS31_C3_QP_LAUNCH time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " event=" << NextWs31C3ObservationEvent()
                  << " generation=" << ws31C3QpGenerations.at(PeekPointer(qp))
                  << " host=" << m_node->GetId() << " flow_id=" << qp->m_flow_id
                  << std::endl;
} catch (...) {
    FailWs31V2(); Ws31V2NativeSession::FailHandle(request,"V2 QP creation failed"); throw;
}

void RdmaHw::ReleaseWs30Round(Ptr<RdmaQueuePair> qp, uint32_t round) {
    if (!qp->m_ws30Persistent || qp->m_ws30Released != uint64_t(round)*Ws30RoundBytes() ||
        qp->m_ws30RoundDone != round || qp->snd_una != uint64_t(round)*Ws30RoundBytes())
        NS_FATAL_ERROR("Persistent round released before prior request was acknowledged");
    if (Ws30V14Enabled() && (qp->irn.m_sack.getSackBufferOverhead()!=0 || qp->irn.m_recovery))
        NS_FATAL_ERROR("Completed prior request still has unresolved SACK/recovery state");
    Ws30V14State("release_before",qp);
    qp->m_ws30Released += Ws30RoundBytes();
    Ws30V14State("release_after",qp);
    std::cout << "WS30V13_RELEASE time_ns=" << Simulator::Now().GetNanoSeconds()
              << " serial=" << qp->m_ws30Serial << " round=" << round
              << " demand_ns=" << qp->startTime.GetNanoSeconds()+uint64_t(round)*Ws30RoundIntervalNs()
              << " released=" << qp->m_ws30Released << " snd_nxt=" << qp->snd_nxt
              << " snd_una=" << qp->snd_una << " rate=" << qp->m_rate.GetBitRate()
              << " alpha=" << qp->mlx.m_alpha << std::endl;
    m_nic[GetNicIdxOfQp(qp)].dev->TriggerTransmit();
}

void RdmaHw::DeleteQueuePair(Ptr<RdmaQueuePair> qp) {
    if (qp->m_ws31C3rLease.IsRunning()) qp->m_ws31C3rLease.Cancel();
    if (qp->m_ws31C3rCeilingActive) qp->ClearWs31C3rSendCeiling();
    qp->m_ws31C3rPending = false;
    // remove qp from the m_qpMap
    uint64_t key = GetQpKey(qp->dip.Get(), qp->sport, qp->dport, qp->m_pg);
    if (qp->m_ws30Serial)
        std::cout << "WS30V13_DELETE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " serial=" << qp->m_ws30Serial << " snd_una=" << qp->snd_una << std::endl;

    // record to Akashic record
    NS_ASSERT(akashic_Qp.find(key) == akashic_Qp.end());  // should not be already existing
    akashic_Qp.insert(key);

    // delete
    m_qpMap.erase(key);
}

// DATA UDP's src = this key's dst (receiver's dst)
uint64_t RdmaHw::GetRxQpKey(uint32_t dip, uint16_t dport, uint16_t sport,
                            uint16_t pg) {  // Receiver perspective
    return ((uint64_t)dip << 32) | ((uint64_t)pg << 16) | ((uint64_t)sport << 16) |
           (uint64_t)dport;  // srcIP, srcPort
}

// src/dst are already flipped (this is calleld by UDP Data packet)
Ptr<RdmaRxQueuePair> RdmaHw::GetRxQp(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport,
                                     uint16_t pg, bool create) {
    uint64_t rxKey = GetRxQpKey(dip, dport, sport, pg);
    auto it = m_rxQpMap.find(rxKey);

    // main memory lookup
    if (it != m_rxQpMap.end()) return it->second;

    if (create) {
        if (Settings::lb_mode == 57 &&
            !m_ws31C3rRxGeneration.Accept(rxKey, m_ws31C3rRxGeneration.Current(rxKey)))
            return NULL;
        // Recreated endpoints are activated by the request scheduler, never by
        // a delayed data packet after cumulative completion.
        if (Ws30V13Life() >= 3 && !m_ws30RxGeneration.Accept(rxKey, m_ws30RxGeneration.Current(rxKey)))
            return NULL;
        // create new rx qp
        Ptr<RdmaRxQueuePair> q = CreateObject<RdmaRxQueuePair>();
        // init the qp
        q->sip = sip;
        q->dip = dip;
        q->sport = sport;
        q->dport = dport;
        q->m_ecn_source.qIndex = pg;
        q->m_flow_id = -1;     // unknown
        m_rxQpMap[rxKey] = q;  // store in map
        return q;
    }
    return NULL;
}
uint32_t RdmaHw::GetNicIdxOfRxQp(Ptr<RdmaRxQueuePair> q) {
    auto &v = m_rtTable[q->dip];
    if (v.size() > 0) {
        return v[q->GetHash() % v.size()];
    }
    NS_ASSERT_MSG(false, "We assume at least one NIC is alive");
    std::cout << "We assume at least one NIC is alive" << std::endl;
    exit(1);
}

// Receiver's perspective?
void RdmaHw::BeginWs30RxGeneration(uint32_t sip, uint32_t dip, uint16_t sport,
                                   uint16_t dport, uint16_t pg, int32_t flow_id) {
    if (Ws30V13Life() < 3) NS_FATAL_ERROR("Endpoint generation outside synthetic recreation fixture");
    const uint64_t key = GetRxQpKey(dip, dport, sport, pg);
    if (m_rxQpMap.count(key) || !m_ws30RxGeneration.Begin(key, flow_id))
        NS_FATAL_ERROR("Synthetic receive generation overlaps live or earlier incarnation");
    akashic_RxQp.erase(key);
    Ptr<RdmaRxQueuePair> q = GetRxQp(sip, dip, sport, dport, pg, true);
    if (!q) NS_FATAL_ERROR("Explicit receive generation was not created");
    q->m_flow_id = flow_id;
    if (Ws30Level())
        std::cout << "WS30V15_GENERATION event=begin time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " sip=" << dip << " dip=" << sip << " sport=" << dport << " dport=" << sport
                  << " pg=" << pg << " flow_id=" << flow_id
                  << " expected=" << q->ReceiverNextExpectedSeq
                  << " sack_bytes=" << q->m_irn_sack_.getSackBufferOverhead()
                  << " nack_timer=" << q->m_nackTimer.GetNanoSeconds()
                  << " qcn_running=" << q->QcnTimerEvent.IsRunning()
                  << " object=" << reinterpret_cast<uintptr_t>(PeekPointer(q)) << std::endl;
}

void RdmaHw::BeginWs31C3rRxGeneration(uint32_t sip, uint32_t dip, uint16_t sport,
                                       uint16_t dport, uint16_t pg, int32_t flow_id) {
    if (Settings::lb_mode != 57) NS_FATAL_ERROR("C3R receiver generation outside mode 57");
    const uint64_t key = GetRxQpKey(dip, dport, sport, pg);
    const int32_t previous = m_ws31C3rRxGeneration.Current(key);
    if (m_rxQpMap.count(key) || !m_ws31C3rRxGeneration.Begin(key, flow_id))
        NS_FATAL_ERROR("C3R receiver generation overlaps an active QP");
    akashic_RxQp.erase(key);
    Ptr<RdmaRxQueuePair> q = GetRxQp(sip, dip, sport, dport, pg, true);
    if (!q) NS_FATAL_ERROR("C3R receiver generation was not created");
    q->m_flow_id = flow_id;
    if (previous >= 0)
        std::cout << "WS31_C3R_GENERATION event=reuse time_ns="
                  << Simulator::Now().GetNanoSeconds() << " host=" << m_node->GetId()
                  << " previous=" << previous << " flow_id=" << flow_id
                  << " key=" << key << std::endl;
    if (previous >= 0 && m_ws31C3rReplayStale &&
        m_ws31C3rSavedData && m_ws31C3rSavedDataKey == key)
        Simulator::Schedule(NanoSeconds(1), &RdmaHw::ReplayWs31C3rStaleData, this);
}

void RdmaHw::ReplayWs31C3rStaleData() {
    if (!m_ws31C3rSavedData) NS_FATAL_ERROR("C3R stale data replay has no packet");
    Ptr<Packet> old = m_ws31C3rSavedData;
    CustomHeader header = m_ws31C3rSavedDataHeader;
    m_ws31C3rSavedData = NULL;
    const uint64_t before = m_ws31C3rStaleDataDrops;
    ReceiveUdp(old, header);
    if (m_ws31C3rStaleDataDrops != before + 1)
        NS_FATAL_ERROR("C3R stale data replay reached the new receiver");
}

void RdmaHw::ReplayWs31C3rStaleFeedback() {
    if (!m_ws31C3rSavedFeedback) NS_FATAL_ERROR("C3R stale feedback replay has no packet");
    Ptr<Packet> old = m_ws31C3rSavedFeedback;
    CustomHeader header = m_ws31C3rSavedFeedbackHeader;
    m_ws31C3rSavedFeedback = NULL;
    const uint64_t before = m_ws31C3rStaleFeedbackDrops;
    ReceiveAck(old, header);
    if (m_ws31C3rStaleFeedbackDrops != before + 1)
        NS_FATAL_ERROR("C3R stale feedback replay reached the new sender");
}

bool RdmaHw::AcceptWs30DataGeneration(Ptr<Packet> p, const CustomHeader &ch) {
    if (Ws30V13Life() < 3) return true;
    FlowIDNUMTag fit;
    const int32_t incoming = p->PeekPacketTag(fit) ? fit.GetId() : -1;
    const uint64_t key = GetRxQpKey(ch.sip, ch.udp.sport, ch.udp.dport, ch.udp.pg);
    const bool accepted = m_ws30RxGeneration.Accept(key, incoming);
    if (!accepted && Ws30Level())
        std::cout << "WS30V15_DATA event=drop time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " uid=" << p->GetUid() << " packet_flow=" << incoming
                  << " current_flow=" << m_ws30RxGeneration.Current(key)
                  << " current_active=" << m_ws30RxGeneration.Accept(key, m_ws30RxGeneration.Current(key))
                  << " rx_present=" << m_rxQpMap.count(key)
                  << " sip=" << ch.sip << " dip=" << ch.dip << " sport=" << ch.udp.sport
                  << " dport=" << ch.udp.dport << " pg=" << ch.udp.pg << " seq=" << ch.udp.seq
                  << " payload=" << p->GetSize()-ch.GetSerializedSize() << std::endl;
    return accepted;
}

bool RdmaHw::AcceptWs30AckGeneration(Ptr<Packet> p, Ptr<RdmaQueuePair> qp) {
    if (Ws30V13Life() < 3) return true;
    FlowIDNUMTag fit;
    const int32_t incoming = p->PeekPacketTag(fit) ? fit.GetId() : -1;
    const bool accepted = incoming >= 0 && incoming == qp->m_flow_id;
    if (Ws30Level())
        std::cout << "WS30V15_FEEDBACK event=" << (accepted ? "accept" : "drop")
                  << " time_ns=" << Simulator::Now().GetNanoSeconds() << " uid=" << p->GetUid()
                  << " packet_flow=" << incoming << " current_flow=" << qp->m_flow_id
                  << " snd_una=" << qp->snd_una << " sack_bytes=" << qp->irn.m_sack.getSackBufferOverhead()
                  << std::endl;
    return accepted;
}

void RdmaHw::DeleteRxQp(uint32_t dip, uint16_t dport, uint16_t sport, uint16_t pg, int32_t flow_id) {
    uint64_t key = GetRxQpKey(dip, dport, sport, pg);

    if (Settings::lb_mode >= 58 && Settings::lb_mode <= 61) {
        auto it = m_rxQpMap.find(key);
        if (it == m_rxQpMap.end() || it->second->m_flow_id != flow_id)
            NS_FATAL_ERROR("M1 receiver completion has wrong request identity");
        std::cout << "WS31_M1_RX_COMPLETE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " flow_id=" << flow_id << " sip=" << dip << " sport=" << dport
                  << " dport=" << sport << " pg=" << pg
                  << " receiver_cum_bytes=" << it->second->ReceiverNextExpectedSeq
                  << " receiver_sack_bytes=" << it->second->m_irn_sack_.getSackBufferOverhead()
                  << std::endl;
    }

    if (Settings::lb_mode == 57) {
        auto it = m_rxQpMap.find(key);
        if (it == m_rxQpMap.end() || it->second->m_flow_id != flow_id ||
            !m_ws31C3rRxGeneration.Close(key, flow_id))
            NS_FATAL_ERROR("C3R receiver completion has wrong generation");
        it->second->QcnTimerEvent.Cancel();
    }

    if (Ws30V13Life() >= 3) {
        auto it = m_rxQpMap.find(key);
        if (it == m_rxQpMap.end() || it->second->m_flow_id != flow_id ||
            !m_ws30RxGeneration.Close(key, flow_id))
            NS_FATAL_ERROR("Synthetic receive completion has wrong generation");
        it->second->QcnTimerEvent.Cancel();
        if (Ws30Level())
            std::cout << "WS30V15_GENERATION event=end time_ns=" << Simulator::Now().GetNanoSeconds()
                      << " sip=" << dip << " sport=" << dport << " dport=" << sport << " pg=" << pg
                      << " flow_id=" << flow_id << " expected=" << it->second->ReceiverNextExpectedSeq
                      << " sack_bytes=" << it->second->m_irn_sack_.getSackBufferOverhead()
                      << " object=" << reinterpret_cast<uintptr_t>(PeekPointer(it->second)) << std::endl;
    }

    // record to Akashic record
    NS_ASSERT(akashic_RxQp.find(key) == akashic_RxQp.end());  // should not be already existing
    akashic_RxQp.insert(key);

    // delete
    m_rxQpMap.erase(key);
}

int RdmaHw::ReceiveUdp(Ptr<Packet> p, CustomHeader &ch) {
    if (Settings::lb_mode == 57) {
        FlowIDNUMTag tag;
        const int32_t incoming = p->PeekPacketTag(tag) ? tag.GetId() : -1;
        const uint64_t key = GetRxQpKey(ch.sip, ch.udp.sport, ch.udp.dport, ch.udp.pg);
        if (!m_ws31C3rRxGeneration.Accept(key, incoming)) {
            if (++m_ws31C3rStaleDataDrops <= 8)
                std::cout << "WS31_C3R_STALE_DATA time_ns=" << Simulator::Now().GetNanoSeconds()
                          << " host=" << m_node->GetId() << " incoming=" << incoming
                          << " current=" << m_ws31C3rRxGeneration.Current(key)
                          << " key=" << key << std::endl;
            return 1;
        }
        if (m_ws31C3rReplayStale && !m_ws31C3rSavedData) {
            m_ws31C3rSavedData = p->Copy();
            m_ws31C3rSavedDataHeader = ch;
            m_ws31C3rSavedDataKey = key;
        }
    }
    int32_t ws31IncomingIdentity=-1;
    if (m_ws31EndpointIdentity) {
        if (!m_node) m_ws31EndpointIdentity->Reject("WS31 receiver hardware has no node");
        ws31IncomingIdentity=m_ws31EndpointIdentity->Data(m_node->GetId(),
            GetRxQpKey(ch.sip,ch.udp.sport,ch.udp.dport,ch.udp.pg),p,ch);
    }
    if (!AcceptWs30DataGeneration(p, ch)) return 1;
    uint8_t ecnbits = ch.GetIpv4EcnBits();

    uint32_t payload_size = p->GetSize() - ch.GetSerializedSize();

    // find corresponding rx queue pair
    Ptr<RdmaRxQueuePair> rxQp =
        GetRxQp(ch.dip, ch.sip, ch.udp.dport, ch.udp.sport, ch.udp.pg, true);
    if (rxQp == NULL) {
        uint64_t rxKey = GetRxQpKey(ch.sip, ch.udp.sport, ch.udp.dport, ch.udp.pg);
        if (akashic_RxQp.find(rxKey) != akashic_RxQp.end()) {
            // printf("[GetRxQPUDP] Akashic access: %u(%d) -> %u(%d)\n", this->m_node->GetId(),
            // ch.udp.dport, ch.sip, ch.udp.sport);
            return 1;  // just drop
        } else {
            printf("ERROR: UDP NIC cannot find the flow\n");
            exit(1);
        }
    }

    if (m_ws31EndpointIdentity)
        m_ws31EndpointIdentity->ReceiverBinding(ws31IncomingIdentity,rxQp->m_flow_id);

    if (ecnbits != 0) {
        rxQp->m_ecn_source.ecnbits |= ecnbits;
        rxQp->m_ecn_source.qfb++;
    }

    rxQp->m_ecn_source.total++;
    rxQp->m_milestone_rx = m_ack_interval;

    if (rxQp->m_flow_id < 0) {
        FlowIDNUMTag fit;
        if (p->PeekPacketTag(fit)) {
            rxQp->m_flow_id = fit.GetId();
        }
    }

    bool cnp_check = false;
    uint32_t expected_before = rxQp->ReceiverNextExpectedSeq;
    if (Ws30V13Life() && ch.udp.seq%Ws30RoundBytes() == 0) {
        std::cout << "WS30V13_RX time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " flow_id=" << rxQp->m_flow_id
                  << " object=" << reinterpret_cast<uintptr_t>(PeekPointer(rxQp))
                  << " seq=" << ch.udp.seq << " expected=" << expected_before << std::endl;
    }
    int x = ReceiverCheckSeq(ch.udp.seq, rxQp, payload_size, cnp_check);
    if (Settings::lb_mode>=58 && Settings::lb_mode<=61 && rxQp->m_flow_id>=0) {
        Ws25QpDiagnostic &cost=ws25_qp_diagnostics[rxQp->m_flow_id];
        if (ch.udp.seq>expected_before) cost.rx_ooo_payload_bytes+=payload_size;
        cost.rx_sack_pending_peak_bytes=std::max<uint64_t>(
            cost.rx_sack_pending_peak_bytes,rxQp->m_irn_sack_.getSackBufferOverhead());
    }
    if (Ws30V13Life() >= 3 && Ws30Level()) {
        FlowIDNUMTag fit;
        if (!p->PeekPacketTag(fit) || fit.GetId()!=rxQp->m_flow_id)
            NS_FATAL_ERROR("Accepted receive identity differs from active generation");
        std::cout << "WS30V15_DATA event=accept time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " uid=" << p->GetUid() << " packet_flow=" << fit.GetId()
                  << " current_flow=" << rxQp->m_flow_id
                  << " sip=" << ch.sip << " dip=" << ch.dip << " sport=" << ch.udp.sport
                  << " dport=" << ch.udp.dport << " pg=" << ch.udp.pg << " seq=" << ch.udp.seq
                  << " payload=" << payload_size << " expected_before=" << expected_before
                  << " expected_after=" << rxQp->ReceiverNextExpectedSeq
                  << " sack_bytes=" << rxQp->m_irn_sack_.getSackBufferOverhead()
                  << " object=" << reinterpret_cast<uintptr_t>(PeekPointer(rxQp)) << std::endl;
    }
    if (Ws30V14Enabled() && Ws30Level() && ch.sip==0x0b000001 && ch.dip==0x0b000301 &&
        (ecnbits || cnp_check || ch.udp.seq%Ws30RoundBytes()==0))
        std::cout << "WS30V14_RX_STATE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " object=" << reinterpret_cast<uintptr_t>(PeekPointer(rxQp))
                  << " flow_id=" << rxQp->m_flow_id << " seq=" << ch.udp.seq
                  << " expected_before=" << expected_before
                  << " expected_after=" << rxQp->ReceiverNextExpectedSeq
                  << " ecn_bits=" << unsigned(ecnbits) << " cnp_check=" << cnp_check
                  << " sack_bytes=" << rxQp->m_irn_sack_.getSackBufferOverhead() << std::endl;
    if (Ws25DiagnosticEnabled() && rxQp->m_flow_id >= 0 && ch.udp.seq > expected_before)
        ++ws25_qp_diagnostics[rxQp->m_flow_id].rx_ooo_packets;
    if (Ws30Level() && rxQp->m_flow_id >= 0 && ch.udp.seq < expected_before)
        ++ws25_qp_diagnostics[rxQp->m_flow_id].rx_duplicate;
    if (x == 2 && !m_irn) {
        std::cout << "WS08_RX_NACK time_ns=" << Simulator::Now().GetTimeStep()
                  << " flow_id=" << rxQp->m_flow_id << " seq=" << ch.udp.seq
                  << " expected=" << expected_before << " size=" << payload_size << std::endl;
    }

    if (x == 1 || x == 2 || x == 6) {  // generate ACK or NACK
        qbbHeader seqh;
        seqh.SetSeq(rxQp->ReceiverNextExpectedSeq);
        seqh.SetPG(ch.udp.pg);
        seqh.SetSport(ch.udp.dport);
        seqh.SetDport(ch.udp.sport);
        seqh.SetIntHeader(ch.udp.ih);

        if (m_irn) {
            if (x == 2) {
                seqh.SetIrnNack(ch.udp.seq);
                seqh.SetIrnNackSize(payload_size);
            } else {
                seqh.SetIrnNack(0);  // NACK without ackSyndrome (ACK) in loss recovery mode
                seqh.SetIrnNackSize(0);
            }
        }

        if (ecnbits || cnp_check) {  // NACK accompanies with CNP packet
            // XXX monitor CNP generation at sender
            cnp_total++;
            if (ecnbits) cnp_by_ecn++;
            if (cnp_check) cnp_by_ooo++;
            seqh.SetCnp();
        }

        Ptr<Packet> newp =
            Create<Packet>(std::max(60 - 14 - 20 - (int)seqh.GetSerializedSize(), 0));
        newp->AddHeader(seqh);

        Ipv4Header head;  // Prepare IPv4 header
        head.SetDestination(Ipv4Address(ch.sip));
        head.SetSource(Ipv4Address(ch.dip));
        head.SetProtocol(x == 1 ? 0xFC : 0xFD);  // ack=0xFC nack=0xFD
        head.SetTtl(64);
        head.SetPayloadSize(newp->GetSize());
        head.SetIdentification(rxQp->m_ipid++);

        {
            FlowIDNUMTag fit;
            if (m_ws31EndpointIdentity)
                m_ws31EndpointIdentity->FeedbackSource(m_node->GetId(),
                    GetRxQpKey(ch.sip,ch.udp.sport,ch.udp.dport,ch.udp.pg),p,ch,rxQp->m_flow_id);
            if (p->PeekPacketTag(fit)) {
                newp->AddPacketTag(fit);
            }
        }

        newp->AddHeader(head);
        AddHeader(newp, 0x800);  // Attach PPP header
        if (Settings::lb_mode>=58 && Settings::lb_mode<=61 && rxQp->m_flow_id>=0)
            ws25_qp_diagnostics[rxQp->m_flow_id].feedback_wire_bytes+=newp->GetSize();

        // send
        uint32_t nic_idx = GetNicIdxOfRxQp(rxQp);
        m_nic[nic_idx].dev->RdmaEnqueueHighPrioQ(newp);
        m_nic[nic_idx].dev->TriggerTransmit();
    }
    return 0;
}

int RdmaHw::ReceiveCnp(Ptr<Packet> p, CustomHeader &ch) {
    std::cerr << "ReceiveCnp is called. Exit this program." << std::endl;
    exit(1);
    // QCN on NIC
    // This is a Congestion signal
    // Then, extract data from the congestion packet.
    // We assume, without verify, the packet is destinated to me
    uint32_t qIndex = ch.cnp.qIndex;
    if (qIndex == 1) {  // DCTCP
        std::cout << "TCP--ignore\n";
        return 0;
    }
    NS_ASSERT(ch.cnp.fid == ch.udp.dport);
    uint16_t udpport = ch.cnp.fid;  // corresponds to the sport (CNP's dport)
    uint16_t sport = ch.udp.sport;  // corresponds to the dport (CNP's sport)
    uint8_t ecnbits = ch.cnp.ecnBits;
    uint16_t qfb = ch.cnp.qfb;
    uint16_t total = ch.cnp.total;

    uint32_t i;
    // get qp
    uint64_t key = GetQpKey(ch.sip, udpport, sport, qIndex);
    Ptr<RdmaQueuePair> qp = GetQp(key);
    if (qp == NULL) {
        // lookup akashic memory
        if (akashic_Qp.find(key) != akashic_Qp.end()) {
            // printf("[GetQPCNP] Akashic access: %u(%d) -> %u(%d)\n", this->m_node->GetId(),
            // udpport, ch.sip, sport);
            return 1;  // just drop
        } else {
            printf("ERROR: QCN NIC cannot find the flow\n");
            exit(1);
        }
    }
    // get nic
    uint32_t nic_idx = GetNicIdxOfQp(qp);
    Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;

    if (qp->m_rate == 0)  // lazy initialization
    {
        qp->m_rate = dev->GetDataRate();
        if (m_cc_mode == 1) {
            qp->mlx.m_targetRate = dev->GetDataRate();
        } else if (m_cc_mode == 3) {
            qp->hp.m_curRate = dev->GetDataRate();
            if (m_multipleRate) {
                for (uint32_t i = 0; i < IntHeader::maxHop; i++)
                    qp->hp.hopState[i].Rc = dev->GetDataRate();
            }
        } else if (m_cc_mode == 7) {
            qp->tmly.m_curRate = dev->GetDataRate();
        }
    }
    return 0;
}

int RdmaHw::ReceiveAck(Ptr<Packet> p, CustomHeader &ch) {
    if (Settings::lb_mode == 57) {
        const uint64_t key = GetQpKey(ch.sip,ch.ack.dport,ch.ack.sport,ch.ack.pg);
        Ptr<RdmaQueuePair> live = GetQp(key);
        if (live) {
            FlowIDNUMTag tag;
            const int32_t incoming = p->PeekPacketTag(tag) ? tag.GetId() : -1;
            if (incoming != live->m_flow_id) {
                if (++m_ws31C3rStaleFeedbackDrops <= 8)
                    std::cout << "WS31_C3R_STALE_FEEDBACK time_ns="
                              << Simulator::Now().GetNanoSeconds() << " host=" << m_node->GetId()
                              << " incoming=" << incoming << " current=" << live->m_flow_id
                              << " key=" << key << std::endl;
                return 1;
            }
            if (m_ws31C3rReplayStale && !m_ws31C3rSavedFeedback) {
                m_ws31C3rSavedFeedback = p->Copy();
                m_ws31C3rSavedFeedbackHeader = ch;
                m_ws31C3rSavedFeedbackKey = key;
            }
        }
    }
    int32_t ws31IncomingIdentity=-1;
    if (m_ws31EndpointIdentity) {
        if (!m_node) m_ws31EndpointIdentity->Reject("WS31 feedback hardware has no node");
        ws31IncomingIdentity=m_ws31EndpointIdentity->Ack(m_node->GetId(),
            GetQpKey(ch.sip,ch.ack.dport,ch.ack.sport,ch.ack.pg),p,ch);
    }
    uint16_t qIndex = ch.ack.pg;
    uint16_t port = ch.ack.dport;   // sport for this host
    uint16_t sport = ch.ack.sport;  // dport for this host (sport of ACK packet)
    uint32_t seq = ch.ack.seq;
    uint8_t cnp = (ch.ack.flags >> qbbHeader::FLAG_CNP) & 1;
    int i;
    uint64_t key = GetQpKey(ch.sip, port, sport, qIndex);
    Ptr<RdmaQueuePair> qp = GetQp(key);
    if (qp == NULL) {
        // lookup akashic memory
        if (akashic_Qp.find(key) != akashic_Qp.end()) {
            // printf("[GetQPACK] Akashic access: %u(%d) -> %u(%d)\n", this->m_node->GetId(), port,
            // ch.sip, sport);
            return 1;
        } else {
            printf("ERROR: Node: %u %s - NIC cannot find the flow\n", m_node->GetId(),
                   (ch.l3Prot == 0xFC ? "ACK" : "NACK"));
            exit(1);
        }
    }

    if (m_ws31EndpointIdentity)
        m_ws31EndpointIdentity->SenderBinding(ws31IncomingIdentity,qp->m_flow_id);
    if (!AcceptWs30AckGeneration(p, qp)) return 1;

    if (Ws25DiagnosticEnabled()) {
        Ws25QpDiagnostic &s = ws25_qp_diagnostics[qp->m_flow_id];
        if (ch.l3Prot == 0xFD && ch.ack.irnNackSize) ++s.sack_feedback;
        if (ch.l3Prot == 0xFD) ++s.nack_feedback;
        if (cnp) ++s.cnp_feedback;
    }

    uint32_t nic_idx = GetNicIdxOfQp(qp);
    Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;

    if (m_ack_interval == 0)
        std::cout << "ERROR: shouldn't receive ack\n";
    else {
        if (!m_backto0) {
            qp->Acknowledge(seq);
        } else {
            uint32_t goback_seq = seq / m_chunk * m_chunk;
            qp->Acknowledge(goback_seq);
        }
        if (qp->irn.m_enabled) {
            // handle NACK
            NS_ASSERT(ch.l3Prot == 0xFD);

            // for bdp-fc calculation update m_irn_maxAck
            if (seq > qp->irn.m_highest_ack) qp->irn.m_highest_ack = seq;

            if (ch.ack.irnNackSize != 0) {
                // ch.ack.irnNack contains the seq triggered this NACK
                qp->irn.m_sack.sack(ch.ack.irnNack, ch.ack.irnNackSize);
                if (Ws30V14Enabled() && Ws30Level() && qp->m_ws30Serial) {
                    ++qp->m_ws30SackEvents;
                    Ws30V14State("sack_insert",qp);
                }
            }

            uint32_t sack_seq, sack_len;
            if (qp->irn.m_sack.peekFrontBlock(&sack_seq, &sack_len)) {
                if (qp->snd_una == sack_seq) {
                    qp->snd_una += sack_len;
                }
            }

            qp->irn.m_sack.discardUpTo(qp->snd_una);

            if (qp->snd_nxt < qp->snd_una) {
                qp->snd_nxt = qp->snd_una;
            }
            // if (qp->irn.m_sack.IsEmpty())  { //
            if (qp->irn.m_recovery && qp->snd_una >= qp->irn.m_recovery_seq) {
                qp->irn.m_recovery = false;
            }
        } else {
            if (qp->snd_nxt < qp->snd_una) {
                qp->snd_nxt = qp->snd_una;
            }
        }
        if (Settings::lb_mode == 57) MaybeSendWs31C3rDrain(qp);
        if (qp->m_ws30Serial) {
            const uint32_t rounds = qp->m_ws30Persistent ? 3 : 1;
            while (qp->m_ws30RoundDone < rounds &&
                   qp->snd_una >= uint64_t(qp->m_ws30RoundDone+1)*Ws30RoundBytes()) {
                const uint32_t r = qp->m_ws30RoundDone++;
                std::cout << "WS30V13_ROUND_DONE time_ns=" << Simulator::Now().GetNanoSeconds()
                          << " serial=" << qp->m_ws30Serial << " round=" << r
                          << " demand_ns=" << qp->startTime.GetNanoSeconds()+uint64_t(r)*Ws30RoundIntervalNs()
                          << " released_ns=" << qp->startTime.GetNanoSeconds()+uint64_t(r)*Ws30RoundIntervalNs()
                          << " snd_nxt=" << qp->snd_nxt << " snd_una=" << qp->snd_una
                          << " rate=" << qp->m_rate.GetBitRate() << " alpha=" << qp->mlx.m_alpha
                          << " highest_ack=" << qp->irn.m_highest_ack
                          << " sack_bytes=" << qp->irn.m_sack.getSackBufferOverhead() << std::endl;
                Ws30V14State("round_drained",qp);
            }
        }
        if (qp->IsFinished()) {
            QpComplete(qp);
        }
    }

    /**
     * IB Spec Vol. 1 o9-85
     * The requester need not separately time each request launched into the
     * fabric, but instead simply begins the timer whenever it is expecting a response.
     * Once started, the timer is restarted each time an acknowledge
     * packet is received as long as there are outstanding expected responses.
     * The timer does not detect the loss of a particular expected acknowledge
     * packet, but rather simply detects the persistent absence of response
     * packets.
     * */
    if (!qp->IsFinished() && qp->GetOnTheFly() > 0) {
        if (qp->m_retransmit.IsRunning()) qp->m_retransmit.Cancel();
        qp->m_retransmit = Simulator::Schedule(qp->GetRto(m_mtu), &RdmaHw::HandleTimeout, this, qp,
                                               qp->GetRto(m_mtu));
    }

    if (m_irn) {
        if (ch.ack.irnNackSize != 0) {
            if (!qp->irn.m_recovery) {
                qp->irn.m_recovery_seq = qp->snd_nxt;
                RecoverQueue(qp);
                qp->irn.m_recovery = true;
                if (Ws30V14Enabled() && Ws30Level() && qp->m_ws30Serial) {
                    ++qp->m_ws30RecoveryEvents;
                    Ws30V14State("recovery_enter",qp);
                }
            }
        } else {
            if (qp->irn.m_recovery) {
                qp->irn.m_recovery = false;
            }
        }

    } else if (ch.l3Prot == 0xFD) {  // NACK
        std::cout << "WS08_TX_NACK time_ns=" << Simulator::Now().GetTimeStep()
                  << " flow_id=" << qp->m_flow_id << " ack=" << seq
                  << " snd_una=" << qp->snd_una << " snd_nxt=" << qp->snd_nxt
                  << std::endl;
        RecoverQueue(qp);
    }

    if (Ws13BackgroundQp(qp)) {
        // IRN ACKs and SACK feedback both use 0xFD; only a nonzero size is SACK.
        // Retain one ordinary ACK per QP as a progress marker. Logging every
        // packet ACK scales with payload packet count and overwhelms long-tail runs.
        if (ch.l3Prot == 0xFD && ch.ack.irnNackSize) {
            Ws13LogQp("sack", qp, ch.ack.irnNackSize);
        } else if (ch.l3Prot == 0xFD && !qp->m_ws13FirstIrnAckLogged) {
            qp->m_ws13FirstIrnAckLogged = true;
            Ws13LogQp("irn_ack", qp);
        }
        if (cnp) Ws13LogQp("cnp", qp, ch.ack.irnNackSize);
    }

    // handle cnp
    if (cnp) {
        if (Ws30V14Enabled() && Ws30Level() && qp->m_ws30Serial) ++qp->m_ws30CnpEvents;
        if (m_cc_mode == 1) {  // mlx version
            cnp_received_mlx(qp);
        }
    }

    if (m_cc_mode == 3) {
        HandleAckHp(qp, p, ch);
    } else if (m_cc_mode == 7) {
        HandleAckTimely(qp, p, ch);
    } else if (m_cc_mode == 8) {
        HandleAckDctcp(qp, p, ch);
    }
    // ACK may advance the on-the-fly window, allowing more packets to send
    if (cnp || ch.ack.irnNackSize || (Ws30V14Enabled() && qp->irn.m_recovery))
        Ws30V14State("ack_after",qp);
    dev->TriggerTransmit();
    return 0;
}

size_t RdmaHw::getIrnBufferOverhead() {
    size_t overhead = 0;
    for (auto it = m_rxQpMap.begin(); it != m_rxQpMap.end(); it++) {
        overhead += it->second->m_irn_sack_.getSackBufferOverhead();
    }
    return overhead;
}

void RdmaHw::SendWs31C3rControl(Ptr<RdmaQueuePair> qp, uint8_t type,
                                uint32_t epoch, uint64_t cut, uint32_t torIp) {
    Ws31C3rControl control;
    control.type = type;
    control.pg = qp->m_pg;
    control.sip = qp->sip.Get();
    control.dip = qp->dip.Get();
    control.sport = qp->sport;
    control.dport = qp->dport;
    control.flowId = qp->m_flow_id;
    control.epoch = epoch;
    control.cut = cut;
    control.generatedNs = Simulator::Now().GetNanoSeconds();
    if (!control.IsValid()) NS_FATAL_ERROR("C3R sender generated invalid control");

    Ptr<Packet> packet = Create<Packet>();
    packet->AddHeader(control);
    Ipv4Header ip;
    ip.SetSource(qp->sip);
    ip.SetDestination(Ipv4Address(torIp));
    ip.SetProtocol(Ws31C3rControl::IP_PROTOCOL);
    ip.SetTtl(1);
    ip.SetPayloadSize(packet->GetSize());
    ip.SetIdentification(uint16_t(epoch));
    packet->AddHeader(ip);
    AddHeader(packet, 0x800);
    m_nic[GetNicIdxOfQp(qp)].dev->RdmaEnqueueHighPrioQ(packet);
    m_nic[GetNicIdxOfQp(qp)].dev->TriggerTransmit();
    std::cout << "WS31_C3R_HOST_CONTROL time_ns=" << Simulator::Now().GetNanoSeconds()
              << " type=" << unsigned(type) << " flow_id=" << qp->m_flow_id
              << " epoch=" << epoch << " cut=" << cut
              << " wire_bytes=" << packet->GetSize() << std::endl;
}

void RdmaHw::MaybeSendWs31C3rDrain(Ptr<RdmaQueuePair> qp) {
    if (!qp->m_ws31C3rPending || qp->m_ws31C3rDrainSent ||
        qp->snd_una < qp->m_ws31C3rCeiling) return;
    qp->m_ws31C3rDrainSent = true;
    SendWs31C3rControl(qp, Ws31C3rControl::DRAIN, qp->m_ws31C3rEpoch,
                       qp->m_ws31C3rCeiling, qp->m_ws31C3rTorIp);
}

void RdmaHw::ExpireWs31C3rPause(Ptr<RdmaQueuePair> qp, uint32_t epoch) {
    if (!qp->m_ws31C3rPending || qp->m_ws31C3rEpoch != epoch) return;
    qp->ClearWs31C3rSendCeiling();
    qp->m_ws31C3rPending = false;
    qp->m_ws31C3rDrainSent = false;
    std::cout << "WS31_C3R_HOST_LEASE_EXPIRE time_ns="
              << Simulator::Now().GetNanoSeconds() << " flow_id=" << qp->m_flow_id
              << " epoch=" << epoch << std::endl;
    m_nic[GetNicIdxOfQp(qp)].dev->TriggerTransmit();
}

int RdmaHw::ReceiveWs31C3rControl(Ptr<Packet> p, const CustomHeader &ch) {
    if (m_ws31EndpointIdentity) m_ws31EndpointIdentity->RequireHealthy();
    Ptr<Packet> copy = p->Copy();
    PppHeader ppp;
    Ipv4Header ip;
    Ws31C3rControl control;
    if (copy->GetSize() < ppp.GetSerializedSize() + ip.GetSerializedSize() +
                          control.GetSerializedSize()) return 1;
    copy->RemoveHeader(ppp);
    copy->RemoveHeader(ip);
    copy->RemoveHeader(control);
    if (!control.IsValid() || copy->GetSize() != 0 ||
        ip.GetProtocol() != Ws31C3rControl::IP_PROTOCOL ||
        ip.GetPayloadSize() != control.GetSerializedSize() ||
        ip.GetSource().Get() != ch.sip || ip.GetDestination().Get() != ch.dip ||
        control.sip != ch.dip || control.generatedNs > uint64_t(Simulator::Now().GetNanoSeconds()))
        return 1;
    auto tor = Settings::hostIp2SwitchId.find(control.sip);
    if (tor == Settings::hostIp2SwitchId.end() || ch.sip != tor->second + 1)
        return 1;
    Ptr<RdmaQueuePair> qp;
    for (const auto &entry : m_qpMap) {
        Ptr<RdmaQueuePair> candidate = entry.second;
        if (candidate->m_flow_id == int32_t(control.flowId) &&
            candidate->sip.Get() == control.sip && candidate->dip.Get() == control.dip &&
            candidate->sport == control.sport && candidate->dport == control.dport &&
            candidate->m_pg == control.pg) {
            qp = candidate;
            break;
        }
    }
    if (!qp) return 1;
    if (control.type == Ws31C3rControl::PAUSE) {
        if (control.cut != 0 || control.epoch <= qp->m_ws31C3rEpoch ||
            qp->m_ws31C3rPending) return 1;
        qp->m_ws31C3rEpoch = control.epoch;
        const uint64_t cut = std::max(qp->snd_nxt, qp->m_ws31C3rMaxIssuedEnd);
        if (cut == 0 || cut >= qp->m_size) {
            SendWs31C3rControl(qp, Ws31C3rControl::ABORT, control.epoch, 0, ch.sip);
            return 1;
        }
        qp->SetWs31C3rSendCeiling(cut);
        qp->m_ws31C3rTorIp = ch.sip;
        qp->m_ws31C3rPending = true;
        qp->m_ws31C3rDrainSent = false;
        qp->m_ws31C3rLease = Simulator::Schedule(NanoSeconds(100000),
            &RdmaHw::ExpireWs31C3rPause, this, qp, control.epoch);
        std::cout << "WS31_C3R_HOST_PAUSE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " flow_id=" << qp->m_flow_id << " epoch=" << control.epoch
                  << " cut=" << cut << " snd_una=" << qp->snd_una << std::endl;
        MaybeSendWs31C3rDrain(qp);
    } else if ((control.type == Ws31C3rControl::RESUME ||
                control.type == Ws31C3rControl::ABORT) &&
               qp->m_ws31C3rPending && control.epoch == qp->m_ws31C3rEpoch &&
               (control.type == Ws31C3rControl::ABORT ||
                (qp->m_ws31C3rDrainSent && control.cut == qp->m_ws31C3rCeiling))) {
        if (qp->m_ws31C3rLease.IsRunning()) qp->m_ws31C3rLease.Cancel();
        qp->ClearWs31C3rSendCeiling();
        qp->m_ws31C3rPending = false;
        qp->m_ws31C3rDrainSent = false;
        std::cout << "WS31_C3R_HOST_RESUME time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " type=" << unsigned(control.type) << " flow_id=" << qp->m_flow_id
                  << " epoch=" << control.epoch << std::endl;
        m_nic[GetNicIdxOfQp(qp)].dev->TriggerTransmit();
    }
    return 1;
}

int RdmaHw::Receive(Ptr<Packet> p, CustomHeader &ch) {
    if (Settings::lb_mode == 57 && ch.l3Prot == Ws31C3rControl::IP_PROTOCOL)
        return ReceiveWs31C3rControl(p, ch);
    if (m_ws31EndpointIdentity) m_ws31EndpointIdentity->Protocol(ch.l3Prot);
    // #if (SLB_DEBUG == true)
    //     std::cout << "[RdmaHw::Receive] Node(" << m_node->GetId() << ")," << PARSE_FIVE_TUPLE(ch)
    //     << "l3Prot:" << ch.l3Prot << ",at" << Simulator::Now() << std::endl;
    // #endif
    if (ch.l3Prot == 0x11) {  // UDP
        return ReceiveUdp(p, ch);
    } else if (ch.l3Prot == 0xFF) {  // CNP
        return ReceiveCnp(p, ch);
    } else if (ch.l3Prot == 0xFD) {  // NACK
        return ReceiveAck(p, ch);
    } else if (ch.l3Prot == 0xFC) {  // ACK
        return ReceiveAck(p, ch);
    }
    return 0;
}

/**
 * @brief Check sequence number when UDP DATA is received
 *
 * @return int
 * 0: should not reach here
 * 1: generate ACK
 * 2: still in loss recovery of IRN
 * 4: OoO, but skip to send NACK as it is already NACKed.
 * 6: NACK but functionality is ACK (indicating all packets are received)
 */
int RdmaHw::ReceiverCheckSeq(uint32_t seq, Ptr<RdmaRxQueuePair> q, uint32_t size, bool &cnp) {
    uint32_t expected = q->ReceiverNextExpectedSeq;
    if (seq == expected || (seq < expected && seq + size >= expected)) {
        if (m_irn) {
            if (q->m_milestone_rx < seq + size) q->m_milestone_rx = seq + size;
            q->ReceiverNextExpectedSeq += size - (expected - seq);
            {
                uint32_t sack_seq, sack_len;
                if (q->m_irn_sack_.peekFrontBlock(&sack_seq, &sack_len)) {
                    if (sack_seq <= q->ReceiverNextExpectedSeq)
                        q->ReceiverNextExpectedSeq +=
                            (sack_len - (q->ReceiverNextExpectedSeq - sack_seq));
                }
            }
            size_t progress = q->m_irn_sack_.discardUpTo(q->ReceiverNextExpectedSeq);
            if (q->m_irn_sack_.IsEmpty()) {
                return 6;  // This generates NACK, but actually functions as an ACK (indicates all
                           // packet has been received)
            } else {
                // should we put nack timer here
                return 2;  // Still in loss recovery mode of IRN
            }
            return 0;  // should not reach here
        }

        q->ReceiverNextExpectedSeq += size - (expected - seq);
        if (q->ReceiverNextExpectedSeq >= q->m_milestone_rx) {
            q->m_milestone_rx +=
                m_ack_interval;  // if ack_interval is small (e.g., 1), condition is meaningless
            return 1;            // Generate ACK
        } else if (q->ReceiverNextExpectedSeq % m_chunk == 0) {
            return 1;
        } else {
            return 5;
        }
    } else if (seq > expected) {
        // Generate NACK
        if (m_irn) {
            if (q->m_milestone_rx < seq + size) q->m_milestone_rx = seq + size;

            // if seq is already nacked, check for nacktimer
            if (q->m_irn_sack_.blockExists(seq, size) && Simulator::Now() < q->m_nackTimer) {
                return 4;  // don't need to send nack yet
            }
            q->m_nackTimer = Simulator::Now() + MicroSeconds(m_nack_interval);
            q->m_irn_sack_.sack(seq, size);  // set SACK
            NS_ASSERT(q->m_irn_sack_.discardUpTo(expected) ==
                      0);  // SACK blocks must be larger than expected
            cnp = m_oooCnpEnabled;  // Only the IRN out-of-order CNP reason is optional.
            return 2;      // generate SACK
        }
        if (Simulator::Now() >= q->m_nackTimer || q->m_lastNACK != expected) {  // new NACK
            q->m_nackTimer = Simulator::Now() + MicroSeconds(m_nack_interval);
            q->m_lastNACK = expected;
            if (m_backto0) {
                q->ReceiverNextExpectedSeq = q->ReceiverNextExpectedSeq / m_chunk * m_chunk;
            }
            cnp = true;  // XXX: out-of-order should accompany with CNP (?) TODO: Check on CX6
            return 2;
        } else {
            // skip to send NACK
            return 4;
        }
    } else {
        // Duplicate.
        if (m_irn) {
            // if (q->ReceiverNextExpectedSeq - 1 == q->m_milestone_rx) {
            // 	return 6; // This generates NACK, but actually functions as an ACK (indicates all
            // packet has been received)
            // }
            if (q->m_irn_sack_.IsEmpty()) {
                return 6;  // This generates NACK, but actually functions as an ACK (indicates all
                           // packet has been received)
            } else {
                // should we put nack timer here
                return 2;  // Still in loss recovery mode of IRN
            }
        }
        // Duplicate.
        return 1;  // According to IB Spec C9-110
                   /**
                    * IB Spec C9-110
                    * A responder shall respond to all duplicate requests in PSN order;
                    * i.e. the request with the (logically) earliest PSN shall be executed first. If,
                    * while responding to a new or duplicate request, a duplicate request is received
                    * with a logically earlier PSN, the responder shall cease responding
                    * to the original request and shall begin responding to the duplicate request
                    * with the logically earlier PSN.
                    */
    }
}

void RdmaHw::AddHeader(Ptr<Packet> p, uint16_t protocolNumber) {
    PppHeader ppp;
    ppp.SetProtocol(EtherToPpp(protocolNumber));
    p->AddHeader(ppp);
}

uint16_t RdmaHw::EtherToPpp(uint16_t proto) {
    switch (proto) {
        case 0x0800:
            return 0x0021;  // IPv4
        case 0x86DD:
            return 0x0057;  // IPv6
        default:
            NS_ASSERT_MSG(false, "PPP Protocol number not defined!");
    }
    return 0;
}

void RdmaHw::RecoverQueue(Ptr<RdmaQueuePair> qp) {
    if (Ws13BackgroundQp(qp)) Ws13LogQp("recover_queue", qp);
    qp->snd_nxt = qp->snd_una;
}

void RdmaHw::QpComplete(Ptr<RdmaQueuePair> qp) {
    NS_ASSERT(!m_qpCompleteCallback.IsNull());
    const bool observeC3=Ws31C3ObserveQp();
    const auto c3Generation=observeC3 ? ws31C3QpGenerations.find(PeekPointer(qp)) :
        ws31C3QpGenerations.end();
    if (observeC3)
        std::cout << "WS31_C3_QP_ACK_COMPLETE time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " event=" << NextWs31C3ObservationEvent()
                  << " generation=" << (c3Generation==ws31C3QpGenerations.end() ? 0 : c3Generation->second)
                  << " host=" << m_node->GetId() << " flow_id=" << qp->m_flow_id
                  << " sip=" << qp->sip.Get() << " dip=" << qp->dip.Get()
                  << " sport=" << qp->sport << " dport=" << qp->dport
                  << " pg=" << qp->m_pg << " size=" << qp->m_size
                  << " snd_una=" << qp->snd_una << " snd_nxt=" << qp->snd_nxt
                  << std::endl;
    if (Ws25DiagnosticEnabled()) {
        const Ws25QpDiagnostic &s = ws25_qp_diagnostics[qp->m_flow_id];
        std::cout << "WS25_QP flow_id=" << qp->m_flow_id
                  << " tag=" << uint32_t(qp->m_workload_tag)
                  << " rx_ooo_packets=" << s.rx_ooo_packets
                  << " sack_feedback=" << s.sack_feedback
                  << " cnp_feedback=" << s.cnp_feedback
                  << " repeated_sends=" << s.repeated_sends
                  << " timeout_recovery=" << s.timeout_recovery << std::endl;
        if (Ws30Level()) {
            std::cout << "WS30_QP flow_id=" << qp->m_flow_id
                      << " tag=" << uint32_t(qp->m_workload_tag)
                      << " rx_gap=" << s.rx_ooo_packets << " rx_below_expected=" << s.rx_duplicate
                      << " fd_feedback_frames=" << s.nack_feedback
                      << " fd_without_sack=" << s.nack_feedback-s.sack_feedback
                      << " sack_feedback=" << s.sack_feedback
                      << " cnp_feedback=" << s.cnp_feedback << " retransmit_packets=" << s.repeated_sends
                      << " retransmit_bytes=" << s.repeated_bytes
                      << " timeout=" << s.timeout_recovery;
            if (Settings::lb_mode>=58 && Settings::lb_mode<=61)
                std::cout << " rx_ooo_payload_bytes=" << s.rx_ooo_payload_bytes
                          << " rx_sack_pending_peak_bytes=" << s.rx_sack_pending_peak_bytes
                          << " feedback_wire_bytes=" << s.feedback_wire_bytes;
            std::cout << std::endl;
        }
        ws25_qp_diagnostics.erase(qp->m_flow_id);
    }
    if (qp->irn.m_enabled && m_nic[GetNicIdxOfQp(qp)].dev->IsQbbEnabled()) {
        std::cout << "WS23_IRN_PFC_QP_COMPLETE flow_id=" << qp->m_flow_id
                  << " size=" << qp->m_size << " snd_una=" << qp->snd_una
                  << " snd_nxt=" << qp->snd_nxt
                  << " tx_payload_bytes=" << qp->stat.txTotalBytes
                  << " tx_packets=" << qp->stat.txTotalPkts << std::endl;
    }
    if (m_cc_mode == 1) {
        Simulator::Cancel(qp->mlx.m_eventUpdateAlpha);
        Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
        Simulator::Cancel(qp->mlx.m_rpTimer);
    }
    if (qp->m_retransmit.IsRunning()) qp->m_retransmit.Cancel();

    // This callback will log info. It also calls deletetion the rxQp on the receiver
    m_qpCompleteCallback(qp);
    if (observeC3)
        std::cout << "WS31_C3_QP_CALLBACK_RETURN time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " event=" << NextWs31C3ObservationEvent()
                  << " generation=" << (c3Generation==ws31C3QpGenerations.end() ? 0 : c3Generation->second)
                  << " host=" << m_node->GetId() << " flow_id=" << qp->m_flow_id
                  << std::endl;
    // delete TxQueuePair
    DeleteQueuePair(qp);
    if (c3Generation!=ws31C3QpGenerations.end()) ws31C3QpGenerations.erase(c3Generation);
}

void RdmaHw::SetLinkDown(Ptr<QbbNetDevice> dev) {
    printf("RdmaHw: node:%u a link down\n", m_node->GetId());
}

void RdmaHw::AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx) {
    uint32_t dip = dstAddr.Get();
    m_rtTable[dip].push_back(intf_idx);
}

void RdmaHw::ClearTable() { m_rtTable.clear(); }

void RdmaHw::RedistributeQp() {
    // clear old qpGrp
    for (uint32_t i = 0; i < m_nic.size(); i++) {
        if (m_nic[i].dev == NULL) continue;
        m_nic[i].qpGrp->Clear();
    }

    // redistribute qp
    for (auto &it : m_qpMap) {
        Ptr<RdmaQueuePair> qp = it.second;
        uint32_t nic_idx = GetNicIdxOfQp(qp);
        m_nic[nic_idx].qpGrp->AddQp(qp);
        // Notify Nic
        m_nic[nic_idx].dev->ReassignedQp(qp);
    }
}

Ptr<Packet> RdmaHw::GetNxtPacket(Ptr<RdmaQueuePair> qp) try {
    ws31::VisibleLabel nativePolicy(0,false);
    if (m_ws31V2Required) {
        if (m_ws31V2Failed || !m_ws31V2Session || !m_node || !qp)
            throw std::logic_error("V2 data producer lacks healthy actual hardware/QP");
        const uint64_t key=GetQpKey(qp->dip.Get(),qp->sport,qp->dport,qp->m_pg);
        auto live=m_qpMap.find(key);
        if (live==m_qpMap.end() || live->second!=qp)
            throw std::logic_error("V2 data producer is not live actual QP");
        const auto p=m_ws31V2Session->Packet(m_node->GetId(),qp);
        nativePolicy=ws31::VisibleLabel(p.value,p.present);
    }
    if (m_ws31EndpointIdentity) {
        if (!m_node || !qp) m_ws31EndpointIdentity->Reject("WS31 data producer lacks actual node/QP");
        m_ws31EndpointIdentity->Sender(m_node->GetId(),qp->m_flow_id,
            ws31::EndpointKey(qp->sip.Get(),qp->dip.Get(),qp->sport,qp->dport,qp->m_pg),
            GetQpKey(qp->dip.Get(),qp->sport,qp->dport,qp->m_pg),qp->m_size,
            qp->m_workload_tag,qp->startTime.GetNanoSeconds(),Simulator::Now().GetNanoSeconds());
        auto live=m_qpMap.find(GetQpKey(qp->dip.Get(),qp->sport,qp->dport,qp->m_pg));
        if (live==m_qpMap.end() || live->second!=qp)
            m_ws31EndpointIdentity->Reject("WS31 data producer is not the actual live sender QP");
    }
    uint32_t payload_size = qp->GetBytesLeft();
    if (m_mtu < payload_size) {  // possibly last packet
        payload_size = m_mtu;
    }
    uint32_t seq = (uint32_t)qp->snd_nxt;
    bool proceed_snd_nxt = true;
    qp->stat.txTotalPkts += 1;
    qp->stat.txTotalBytes += payload_size;

    Ptr<Packet> p = Create<Packet>(payload_size);
    WorkloadTag label;
    const unsigned labelProfile=m_ws31V2Required?0:ws31::LabelProfile();
    const ws31::VisibleLabel visible=m_ws31V2Required?nativePolicy:ws31::LabelAt(labelProfile,qp->m_workload_tag,
        qp->startTime.GetNanoSeconds(),Simulator::Now().GetNanoSeconds(),
        qp->sip.Get(),qp->dip.Get(),qp->sport,qp->dport,Ws30V13TagTransform());
    label.SetValue(visible.value);
    if (visible.present) p->AddPacketTag(label);
    if (labelProfile && Ws30Level())
        std::cout << "WS31_LABEL_PACKET time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " demand_ns=" << qp->startTime.GetNanoSeconds()
                  << " uid=" << p->GetUid() << " flow_id=" << qp->m_flow_id
                  << " generation=0 sip=" << qp->sip.Get() << " dip=" << qp->dip.Get()
                  << " sport=" << qp->sport << " dport=" << qp->dport
                  << " seq=" << seq << " payload=" << payload_size
                  << " profile=" << labelProfile << " original=" << qp->m_workload_tag
                  << " visible=" << visible.value << " present=" << visible.present << std::endl;
    // add SeqTsHeader
    SeqTsHeader seqTs;
    seqTs.SetSeq(seq);
    seqTs.SetPG(qp->m_pg);
    p->AddHeader(seqTs);
    // add udp header
    UdpHeader udpHeader;
    udpHeader.SetDestinationPort(qp->dport);
    udpHeader.SetSourcePort(qp->sport);
    p->AddHeader(udpHeader);
    // add ipv4 header
    Ipv4Header ipHeader;
    ipHeader.SetSource(qp->sip);
    ipHeader.SetDestination(qp->dip);
    ipHeader.SetProtocol(0x11);
    ipHeader.SetPayloadSize(p->GetSize());
    ipHeader.SetTtl(64);
    ipHeader.SetTos(0);
    ipHeader.SetIdentification(qp->m_ipid);
    p->AddHeader(ipHeader);
    // add ppp header
    PppHeader ppp;
    ppp.SetProtocol(0x0021);  // EtherToPpp(0x800), see point-to-point-net-device.cc
    p->AddHeader(ppp);

    // attach Stat Tag
    uint8_t packet_pos = UINT8_MAX;
    {
        FlowIDNUMTag fint;
        if (!p->PeekPacketTag(fint)) {
            fint.SetId(qp->m_flow_id);
            fint.SetFlowSize(qp->m_size);
            p->AddPacketTag(fint);
        }
        FlowStatTag fst;
        uint64_t size = qp->m_size;
        if (!p->PeekPacketTag(fst)) {
            if (size < m_mtu && qp->snd_nxt + payload_size >= qp->m_size) {
                fst.SetType(FlowStatTag::FLOW_START_AND_END);
            } else if (qp->snd_nxt + payload_size >= qp->m_size) {
                fst.SetType(FlowStatTag::FLOW_END);
            } else if (qp->snd_nxt == 0) {
                fst.SetType(FlowStatTag::FLOW_START);
            } else {
                fst.SetType(FlowStatTag::FLOW_NOTEND);
            }
            packet_pos = fst.GetType();
            fst.setInitiatedTime(Simulator::Now().GetSeconds());
            p->AddPacketTag(fst);
        }
    }

    if (qp->irn.m_enabled) {
        if (qp->irn.m_max_seq < seq) qp->irn.m_max_seq = seq;
    }

    // // update state
    if (proceed_snd_nxt) qp->snd_nxt += payload_size;

    qp->m_ipid++;

    // return
    return p;
} catch (...) { FailWs31V2(); throw; }

void RdmaHw::PktSent(Ptr<RdmaQueuePair> qp, Ptr<Packet> pkt, Time interframeGap) {
    qp->lastPktSize = pkt->GetSize();
    UpdateNextAvail(qp, interframeGap, pkt->GetSize());

    if (pkt) {
        CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header |
                        CustomHeader::L4_Header);
        pkt->PeekHeader(ch);
#if (SLB_DEBUG == true)
        std::cout << "[RdmaHw::PktSent] Node(" << m_node->GetId() << ")," << PARSE_FIVE_TUPLE(ch)
                  << "l3Prot:" << ch.l3Prot << ",at" << Simulator::Now() << std::endl;
#endif
        RdmaHw::nAllPkts += 1;
        if (ch.l3Prot == 0x11) {  // UDP
            const uint32_t payload_size = pkt->GetSize() - ch.GetSerializedSize();
            if (qp->m_ws30Serial) {
                const uint32_t r = qp->m_ws30Persistent ? ch.udp.seq/Ws30RoundBytes() : 0;
                if (!(qp->m_ws30FirstSentMask & (1U << r))) {
                    qp->m_ws30FirstSentMask |= 1U << r;
                    std::cout << "WS30V13_FIRST_SEND time_ns=" << Simulator::Now().GetNanoSeconds()
                              << " serial=" << qp->m_ws30Serial << " round=" << r
                              << " seq=" << ch.udp.seq << " released=" << qp->m_ws30Released << std::endl;
                }
                if (qp->m_ws30Persistent && ch.udp.seq+payload_size>qp->m_ws30Released)
                    NS_FATAL_ERROR("Persistent fixture transmitted unreleased bytes");
            }
            if (Ws25DiagnosticEnabled() && ch.udp.seq < qp->m_ws13_maxSentSeq)
                ++ws25_qp_diagnostics[qp->m_flow_id].repeated_sends;
            if (Ws30Level() && ch.udp.seq < qp->m_ws13_maxSentSeq)
                ws25_qp_diagnostics[qp->m_flow_id].repeated_bytes += payload_size;
            if (Ws13BackgroundQp(qp) && ch.udp.seq < qp->m_ws13_maxSentSeq)
                Ws13LogQp("retransmit", qp);
            qp->m_ws13_maxSentSeq =
                std::max(qp->m_ws13_maxSentSeq, ch.udp.seq + payload_size);
            if (Settings::lb_mode == 57)
                qp->m_ws31C3rMaxIssuedEnd = std::max(qp->m_ws31C3rMaxIssuedEnd,
                    uint64_t(ch.udp.seq) + payload_size);
            // Update Timer
            if (qp->m_retransmit.IsRunning()) qp->m_retransmit.Cancel();
            qp->m_retransmit = Simulator::Schedule(qp->GetRto(m_mtu), &RdmaHw::HandleTimeout, this,
                                                   qp, qp->GetRto(m_mtu));
        } else if (ch.l3Prot == 0xFC || ch.l3Prot == 0xFD || ch.l3Prot == 0xFF) {  // ACK, NACK, CNP
        } else if (ch.l3Prot == 0xFE) {                                            // PFC
        }
    }
}

void RdmaHw::HandleTimeout(Ptr<RdmaQueuePair> qp, Time rto) {
    // Assume Outstanding Packets are lost
    // std::cerr << "Timeout on qp=" << qp << std::endl;
    if (qp->IsFinished()) {
        return;
    }
    // An ACK may have drained all outstanding data after this timer was set.
    if (qp->GetOnTheFly() == 0) return;

    uint32_t nic_idx = GetNicIdxOfQp(qp);
    Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;

    // A locally paused priority cannot transmit a recovery packet. PFC being
    // enabled is not evidence of a pause, and must not disable recovery forever.
    if (qp->irn.m_enabled && dev->IsQbbEnabled()) {
        Time delay = IrnPfcTimeoutDeferral(Simulator::Now(), rto,
                                           dev->IsPaused(qp->m_pg),
                                           dev->HasResumed(qp->m_pg),
                                           dev->GetLastResumeTime(qp->m_pg));
        if (delay > Time(0)) {
            std::cout << "WS23_IRN_PFC_TIMEOUT_DEFERRED time_ns="
                      << Simulator::Now().GetTimeStep() << " flow_id=" << qp->m_flow_id
                      << " paused=" << dev->IsPaused(qp->m_pg)
                      << " delay_ns=" << delay.GetTimeStep() << std::endl;
            qp->m_retransmit = Simulator::Schedule(delay, &RdmaHw::HandleTimeout, this, qp, rto);
            return;
        }
        std::cout << "WS23_IRN_PFC_TIMEOUT_RECOVERY time_ns="
                  << Simulator::Now().GetTimeStep() << " flow_id=" << qp->m_flow_id
                  << " snd_una=" << qp->snd_una << " snd_nxt=" << qp->snd_nxt
                  << " local_paused=" << dev->IsPaused(qp->m_pg) << std::endl;
    }

    if (Ws13BackgroundQp(qp)) Ws13LogQp("timeout", qp);
    if (Ws25DiagnosticEnabled()) ++ws25_qp_diagnostics[qp->m_flow_id].timeout_recovery;

    std::cout << "WS08_TX_TIMEOUT time_ns=" << Simulator::Now().GetTimeStep()
              << " flow_id=" << qp->m_flow_id << " snd_una=" << qp->snd_una
              << " snd_nxt=" << qp->snd_nxt << " rto_ns=" << rto.GetTimeStep()
              << std::endl;

    if (acc_timeout_count.find(qp->m_flow_id) == acc_timeout_count.end())
        acc_timeout_count[qp->m_flow_id] = 0;
    acc_timeout_count[qp->m_flow_id]++;

    if (qp->irn.m_enabled) {
        qp->irn.m_recovery_seq = qp->snd_nxt;
        qp->irn.m_recovery = true;
    }

    RecoverQueue(qp);
    dev->TriggerTransmit();
}

void RdmaHw::UpdateNextAvail(Ptr<RdmaQueuePair> qp, Time interframeGap, uint32_t pkt_size) {
    Time sendingTime;
    if (m_rateBound)
        sendingTime = interframeGap + Seconds(qp->m_rate.CalculateTxTime(pkt_size));
    else
        sendingTime = interframeGap + Seconds(qp->m_max_rate.CalculateTxTime(pkt_size));
    qp->m_nextAvail = Simulator::Now() + sendingTime;
}

void RdmaHw::ChangeRate(Ptr<RdmaQueuePair> qp, DataRate new_rate) {
#if 1
    Time sendingTime = Seconds(qp->m_rate.CalculateTxTime(qp->lastPktSize));
    Time new_sendintTime = Seconds(new_rate.CalculateTxTime(qp->lastPktSize));
    qp->m_nextAvail = qp->m_nextAvail + new_sendintTime - sendingTime;
    // update nic's next avail event
    uint32_t nic_idx = GetNicIdxOfQp(qp);
    m_nic[nic_idx].dev->UpdateNextAvail(qp->m_nextAvail);
#endif

    // change to new rate
    qp->m_rate = new_rate;
    if (Ws13BackgroundQp(qp)) Ws13LogQp("rate_change", qp);
}

#define PRINT_LOG 0
/******************************
 * Mellanox's version of DCQCN
 *****************************/
void RdmaHw::UpdateAlphaMlx(Ptr<RdmaQueuePair> q) {
#if PRINT_LOG
// std::cout << Simulator::Now() << " alpha update:" << m_node->GetId() << ' ' << q->mlx.m_alpha <<
// ' ' << (int)q->mlx.m_alpha_cnp_arrived << '\n'; printf("%lu alpha update: %08x %08x %u %u
// %.6lf->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport,
// q->mlx.m_alpha);
#endif
    if (q->mlx.m_alpha_cnp_arrived) {                       // cnp -> increase
        q->mlx.m_alpha = (1 - m_g) * q->mlx.m_alpha + m_g;  // binary feedback
    } else {                                                // no cnp -> decrease
        q->mlx.m_alpha = (1 - m_g) * q->mlx.m_alpha;        // binary feedback
    }
#if PRINT_LOG
// printf("%.6lf\n", q->mlx.m_alpha);
#endif
    q->mlx.m_alpha_cnp_arrived = false;  // clear the CNP_arrived bit
    ScheduleUpdateAlphaMlx(q);
    Ws30V14State("alpha_update",q);
}
void RdmaHw::ScheduleUpdateAlphaMlx(Ptr<RdmaQueuePair> q) {
    q->mlx.m_eventUpdateAlpha = Simulator::Schedule(MicroSeconds(m_alpha_resume_interval),
                                                    &RdmaHw::UpdateAlphaMlx, this, q);
}

void RdmaHw::cnp_received_mlx(Ptr<RdmaQueuePair> q) {
    q->mlx.m_alpha_cnp_arrived = true;     // set CNP_arrived bit for alpha update
    q->mlx.m_decrease_cnp_arrived = true;  // set CNP_arrived bit for rate decrease
    if (q->mlx.m_first_cnp) {
        // init alpha
        q->mlx.m_alpha = 1;
        q->mlx.m_alpha_cnp_arrived = false;
        // schedule alpha update
        ScheduleUpdateAlphaMlx(q);
        // schedule rate decrease
        ScheduleDecreaseRateMlx(q, 1);  // add 1 ns to make sure rate decrease is after alpha update
        // set rate on first CNP
        q->mlx.m_targetRate = q->m_rate = m_rateOnFirstCNP * q->m_rate;
        q->mlx.m_first_cnp = false;
        if (Ws13BackgroundQp(q)) Ws13LogQp("rate_first_cnp", q);
        Ws30V14State("first_cnp",q);
    }
}

void RdmaHw::CheckRateDecreaseMlx(Ptr<RdmaQueuePair> q) {
    ScheduleDecreaseRateMlx(q, 0);
    if (q->mlx.m_decrease_cnp_arrived) {
#if PRINT_LOG
        printf("%lu rate dec: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(),
               q->sip.Get(), q->dip.Get(), q->sport, q->dport,
               q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
#endif
        bool clamp = true;
        if (!m_EcnClampTgtRate) {
            if (q->mlx.m_rpTimeStage == 0) clamp = false;
        }
        if (clamp) {
            q->mlx.m_targetRate = q->m_rate;
        }
        q->m_rate = std::max(m_minRate, q->m_rate * (1 - q->mlx.m_alpha / 2));
        if (Ws13BackgroundQp(q)) Ws13LogQp("rate_decrease", q);
        Ws30V14State("rate_decrease",q);
        // reset rate increase related things
        q->mlx.m_rpTimeStage = 0;
        q->mlx.m_decrease_cnp_arrived = false;
        Simulator::Cancel(q->mlx.m_rpTimer);
        q->mlx.m_rpTimer = Simulator::Schedule(MicroSeconds(m_rpgTimeReset),
                                               &RdmaHw::RateIncEventTimerMlx, this, q);
#if PRINT_LOG
        printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9,
               q->m_rate.GetBitRate() * 1e-9);
#endif
    }
}
void RdmaHw::ScheduleDecreaseRateMlx(Ptr<RdmaQueuePair> q, uint32_t delta) {
    q->mlx.m_eventDecreaseRate =
        Simulator::Schedule(MicroSeconds(m_rateDecreaseInterval) + NanoSeconds(delta),
                            &RdmaHw::CheckRateDecreaseMlx, this, q);
}

void RdmaHw::RateIncEventTimerMlx(Ptr<RdmaQueuePair> q) {
    q->mlx.m_rpTimer =
        Simulator::Schedule(MicroSeconds(m_rpgTimeReset), &RdmaHw::RateIncEventTimerMlx, this, q);
    RateIncEventMlx(q);
    q->mlx.m_rpTimeStage++;
}
void RdmaHw::RateIncEventMlx(Ptr<RdmaQueuePair> q) {
    // check which increase phase: fast recovery, active increase, hyper increase
    if (q->mlx.m_rpTimeStage < m_rpgThreshold) {  // fast recovery
        FastRecoveryMlx(q);
    } else if (q->mlx.m_rpTimeStage == m_rpgThreshold) {  // active increase
        ActiveIncreaseMlx(q);
    } else {  // hyper increase
        HyperIncreaseMlx(q);
    }
}

void RdmaHw::FastRecoveryMlx(Ptr<RdmaQueuePair> q) {
#if PRINT_LOG
    printf("%lu fast recovery: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(),
           q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9,
           q->m_rate.GetBitRate() * 1e-9);
#endif
    q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
    if (Ws13BackgroundQp(q)) Ws13LogQp("rate_fast_recovery", q);
#if PRINT_LOG
    printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9,
           q->m_rate.GetBitRate() * 1e-9);
#endif
}
void RdmaHw::ActiveIncreaseMlx(Ptr<RdmaQueuePair> q) {
#if PRINT_LOG
    printf("%lu active inc: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(),
           q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9,
           q->m_rate.GetBitRate() * 1e-9);
#endif
    // get NIC
    uint32_t nic_idx = GetNicIdxOfQp(q);
    Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
    // increate rate
    q->mlx.m_targetRate += m_rai;
    if (q->mlx.m_targetRate > dev->GetDataRate()) q->mlx.m_targetRate = dev->GetDataRate();
    q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
    if (Ws13BackgroundQp(q)) Ws13LogQp("rate_active_increase", q);
#if PRINT_LOG
    printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9,
           q->m_rate.GetBitRate() * 1e-9);
#endif
}
void RdmaHw::HyperIncreaseMlx(Ptr<RdmaQueuePair> q) {
#if PRINT_LOG
    printf("%lu hyper inc: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(),
           q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9,
           q->m_rate.GetBitRate() * 1e-9);
#endif
    // get NIC
    uint32_t nic_idx = GetNicIdxOfQp(q);
    Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
    // increate rate
    q->mlx.m_targetRate += m_rhai;
    if (q->mlx.m_targetRate > dev->GetDataRate()) q->mlx.m_targetRate = dev->GetDataRate();
    q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
    if (Ws13BackgroundQp(q)) Ws13LogQp("rate_hyper_increase", q);
#if PRINT_LOG
    printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9,
           q->m_rate.GetBitRate() * 1e-9);
#endif
}

/***********************
 * High Precision CC
 ***********************/
void RdmaHw::HandleAckHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch) {
    uint32_t ack_seq = ch.ack.seq;
    // update rate
    if (ack_seq > qp->hp.m_lastUpdateSeq) {  // if full RTT feedback is ready, do full update
        UpdateRateHp(qp, p, ch, false);
    } else {  // do fast react
        FastReactHp(qp, p, ch);
    }
}

void RdmaHw::UpdateRateHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react) {
    uint32_t next_seq = qp->snd_nxt;
    bool print = !fast_react || true;
    if (qp->hp.m_lastUpdateSeq == 0) {  // first RTT
        qp->hp.m_lastUpdateSeq = next_seq;
        // store INT
        IntHeader &ih = ch.ack.ih;
        NS_ASSERT(ih.nhop <= IntHeader::maxHop);
        for (uint32_t i = 0; i < ih.nhop; i++) qp->hp.hop[i] = ih.hop[i];
#if PRINT_LOG
        if (print) {
            printf("%lu %s %08x %08x %u %u [%u,%u,%u]", Simulator::Now().GetTimeStep(),
                   fast_react ? "fast" : "update", qp->sip.Get(), qp->dip.Get(), qp->sport,
                   qp->dport, qp->hp.m_lastUpdateSeq, ch.ack.seq, next_seq);
            for (uint32_t i = 0; i < ih.nhop; i++)
                printf(" %u %lu %lu", ih.hop[i].GetQlen(), ih.hop[i].GetBytes(),
                       ih.hop[i].GetTime());
            printf("\n");
        }
#endif
    } else {
        // check packet INT
        IntHeader &ih = ch.ack.ih;
        if (ih.nhop <= IntHeader::maxHop) {
            double max_c = 0;
            bool inStable = false;
#if PRINT_LOG
            if (print)
                printf("%lu %s %08x %08x %u %u [%u,%u,%u]", Simulator::Now().GetTimeStep(),
                       fast_react ? "fast" : "update", qp->sip.Get(), qp->dip.Get(), qp->sport,
                       qp->dport, qp->hp.m_lastUpdateSeq, ch.ack.seq, next_seq);
#endif
            // check each hop
            double U = 0;
            uint64_t dt = 0;
            bool updated[IntHeader::maxHop] = {false}, updated_any = false;
            NS_ASSERT(ih.nhop <= IntHeader::maxHop);
            for (uint32_t i = 0; i < ih.nhop; i++) {
                if (m_sampleFeedback) {
                    if (ih.hop[i].GetQlen() == 0 and fast_react) continue;
                }
                updated[i] = updated_any = true;
#if PRINT_LOG
                if (print)
                    printf(" %u(%u) %lu(%lu) %lu(%lu)", ih.hop[i].GetQlen(),
                           qp->hp.hop[i].GetQlen(), ih.hop[i].GetBytes(), qp->hp.hop[i].GetBytes(),
                           ih.hop[i].GetTime(), qp->hp.hop[i].GetTime());
#endif
                uint64_t tau = ih.hop[i].GetTimeDelta(qp->hp.hop[i]);
                ;
                double duration = tau * 1e-9;
                double txRate = (ih.hop[i].GetBytesDelta(qp->hp.hop[i])) * 8 / duration;
                double u = txRate / ih.hop[i].GetLineRate() +
                           (double)std::min(ih.hop[i].GetQlen(), qp->hp.hop[i].GetQlen()) *
                               qp->m_max_rate.GetBitRate() / ih.hop[i].GetLineRate() / qp->m_win;
#if PRINT_LOG
                if (print) printf(" %.3lf %.3lf", txRate, u);
#endif
                if (!m_multipleRate) {
                    // for aggregate (single R)
                    if (u > U) {
                        U = u;
                        dt = tau;
                    }
                } else {
                    // for per hop (per hop R)
                    if (tau > qp->m_baseRtt) tau = qp->m_baseRtt;
                    qp->hp.hopState[i].u =
                        (qp->hp.hopState[i].u * (qp->m_baseRtt - tau) + u * tau) /
                        double(qp->m_baseRtt);
                }
                qp->hp.hop[i] = ih.hop[i];
            }

            DataRate new_rate;
            int32_t new_incStage;
            DataRate new_rate_per_hop[IntHeader::maxHop];
            int32_t new_incStage_per_hop[IntHeader::maxHop];
            if (!m_multipleRate) {
                // for aggregate (single R)
                if (updated_any) {
                    if (dt > qp->m_baseRtt) dt = qp->m_baseRtt;
                    qp->hp.u = (qp->hp.u * (qp->m_baseRtt - dt) + U * dt) / double(qp->m_baseRtt);
                    max_c = qp->hp.u / m_targetUtil;

                    if (max_c >= 1 || qp->hp.m_incStage >= m_miThresh) {
                        new_rate = qp->hp.m_curRate / max_c + m_rai;
                        new_incStage = 0;
                    } else {
                        new_rate = qp->hp.m_curRate + m_rai;
                        new_incStage = qp->hp.m_incStage + 1;
                    }
                    if (new_rate < m_minRate) new_rate = m_minRate;
                    if (new_rate > qp->m_max_rate) new_rate = qp->m_max_rate;
#if PRINT_LOG
                    if (print) printf(" u=%.6lf U=%.3lf dt=%u max_c=%.3lf", qp->hp.u, U, dt, max_c);
#endif
#if PRINT_LOG
                    if (print)
                        printf(" rate:%.3lf->%.3lf\n", qp->hp.m_curRate.GetBitRate() * 1e-9,
                               new_rate.GetBitRate() * 1e-9);
#endif
                }
            } else {
                // for per hop (per hop R)
                new_rate = qp->m_max_rate;
                for (uint32_t i = 0; i < ih.nhop; i++) {
                    if (updated[i]) {
                        double c = qp->hp.hopState[i].u / m_targetUtil;
                        if (c >= 1 || qp->hp.hopState[i].incStage >= m_miThresh) {
                            new_rate_per_hop[i] = qp->hp.hopState[i].Rc / c + m_rai;
                            new_incStage_per_hop[i] = 0;
                        } else {
                            new_rate_per_hop[i] = qp->hp.hopState[i].Rc + m_rai;
                            new_incStage_per_hop[i] = qp->hp.hopState[i].incStage + 1;
                        }
                        // bound rate
                        if (new_rate_per_hop[i] < m_minRate) new_rate_per_hop[i] = m_minRate;
                        if (new_rate_per_hop[i] > qp->m_max_rate)
                            new_rate_per_hop[i] = qp->m_max_rate;
                        // find min new_rate
                        if (new_rate_per_hop[i] < new_rate) new_rate = new_rate_per_hop[i];
#if PRINT_LOG
                        if (print) printf(" [%u]u=%.6lf c=%.3lf", i, qp->hp.hopState[i].u, c);
#endif
#if PRINT_LOG
                        if (print)
                            printf(" %.3lf->%.3lf", qp->hp.hopState[i].Rc.GetBitRate() * 1e-9,
                                   new_rate.GetBitRate() * 1e-9);
#endif
                    } else {
                        if (qp->hp.hopState[i].Rc < new_rate) new_rate = qp->hp.hopState[i].Rc;
                    }
                }
#if PRINT_LOG
                printf("\n");
#endif
            }
            if (updated_any) ChangeRate(qp, new_rate);
            if (!fast_react) {
                if (updated_any) {
                    qp->hp.m_curRate = new_rate;
                    qp->hp.m_incStage = new_incStage;
                }
                if (m_multipleRate) {
                    // for per hop (per hop R)
                    for (uint32_t i = 0; i < ih.nhop; i++) {
                        if (updated[i]) {
                            qp->hp.hopState[i].Rc = new_rate_per_hop[i];
                            qp->hp.hopState[i].incStage = new_incStage_per_hop[i];
                        }
                    }
                }
            }
        }
        if (!fast_react) {
            if (next_seq > qp->hp.m_lastUpdateSeq)
                qp->hp.m_lastUpdateSeq = next_seq;  //+ rand() % 2 * m_mtu;
        }
    }
}

void RdmaHw::FastReactHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch) {
    if (m_fast_react) UpdateRateHp(qp, p, ch, true);
}

/**********************
 * TIMELY
 *********************/
void RdmaHw::HandleAckTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch) {
    uint32_t ack_seq = ch.ack.seq;
    // update rate
    if (ack_seq > qp->tmly.m_lastUpdateSeq) {  // if full RTT feedback is ready, do full update
        UpdateRateTimely(qp, p, ch, false);
    } else {  // do fast react
        FastReactTimely(qp, p, ch);
    }
}
void RdmaHw::UpdateRateTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool us) {
    uint32_t next_seq = qp->snd_nxt;
    uint64_t rtt = Simulator::Now().GetTimeStep() - ch.ack.ih.ts;
    bool print = !us;
    if (qp->tmly.m_lastUpdateSeq != 0) {  // not first RTT
        int64_t new_rtt_diff = (int64_t)rtt - (int64_t)qp->tmly.lastRtt;
        double rtt_diff = (1 - m_tmly_alpha) * qp->tmly.rttDiff + m_tmly_alpha * new_rtt_diff;
        double gradient = rtt_diff / m_tmly_minRtt;
        bool inc = false;
        double c = 0;
#if PRINT_LOG
        if (print)
            printf("%lu node:%u rtt:%lu rttDiff:%.0lf gradient:%.3lf rate:%.3lf",
                   Simulator::Now().GetTimeStep(), m_node->GetId(), rtt, rtt_diff, gradient,
                   qp->tmly.m_curRate.GetBitRate() * 1e-9);
#endif
        if (rtt < m_tmly_TLow) {
            inc = true;
        } else if (rtt > m_tmly_THigh) {
            c = 1 - m_tmly_beta * (1 - (double)m_tmly_THigh / rtt);
            inc = false;
        } else if (gradient <= 0) {
            inc = true;
        } else {
            c = 1 - m_tmly_beta * gradient;
            if (c < 0) c = 0;
            inc = false;
        }
        if (inc) {
            if (qp->tmly.m_incStage < 5) {
                qp->m_rate = qp->tmly.m_curRate + m_rai;
            } else {
                qp->m_rate = qp->tmly.m_curRate + m_rhai;
            }
            if (qp->m_rate > qp->m_max_rate) qp->m_rate = qp->m_max_rate;
            if (!us) {
                qp->tmly.m_curRate = qp->m_rate;
                qp->tmly.m_incStage++;
                qp->tmly.rttDiff = rtt_diff;
            }
        } else {
            qp->m_rate = std::max(m_minRate, qp->tmly.m_curRate * c);
            if (!us) {
                qp->tmly.m_curRate = qp->m_rate;
                qp->tmly.m_incStage = 0;
                qp->tmly.rttDiff = rtt_diff;
            }
        }
#if PRINT_LOG
        if (print) {
            printf(" %c %.3lf\n", inc ? '^' : 'v', qp->m_rate.GetBitRate() * 1e-9);
        }
#endif
    }
    if (!us && next_seq > qp->tmly.m_lastUpdateSeq) {
        qp->tmly.m_lastUpdateSeq = next_seq;
        // update
        qp->tmly.lastRtt = rtt;
    }
}
void RdmaHw::FastReactTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch) {}

/**********************
 * DCTCP
 *********************/
void RdmaHw::HandleAckDctcp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch) {
    uint32_t ack_seq = ch.ack.seq;
    uint8_t cnp = (ch.ack.flags >> qbbHeader::FLAG_CNP) & 1;
    bool new_batch = false;

    // update alpha
    qp->dctcp.m_ecnCnt += (cnp > 0);
    if (ack_seq > qp->dctcp.m_lastUpdateSeq) {  // if full RTT feedback is ready, do alpha update
#if PRINT_LOG
        printf("%lu %s %08x %08x %u %u [%u,%u,%u] %.3lf->", Simulator::Now().GetTimeStep(), "alpha",
               qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->dctcp.m_lastUpdateSeq,
               ch.ack.seq, qp->snd_nxt, qp->dctcp.m_alpha);
#endif
        new_batch = true;
        if (qp->dctcp.m_lastUpdateSeq == 0) {  // first RTT
            qp->dctcp.m_lastUpdateSeq = qp->snd_nxt;
            qp->dctcp.m_batchSizeOfAlpha = qp->snd_nxt / m_mtu + 1;
        } else {
            double frac = std::min(1.0, double(qp->dctcp.m_ecnCnt) / qp->dctcp.m_batchSizeOfAlpha);
            qp->dctcp.m_alpha = (1 - m_g) * qp->dctcp.m_alpha + m_g * frac;
            qp->dctcp.m_lastUpdateSeq = qp->snd_nxt;
            qp->dctcp.m_ecnCnt = 0;
            qp->dctcp.m_batchSizeOfAlpha = (qp->snd_nxt - ack_seq) / m_mtu + 1;
#if PRINT_LOG
            printf("%.3lf F:%.3lf", qp->dctcp.m_alpha, frac);
#endif
        }
#if PRINT_LOG
        printf("\n");
#endif
    }

    // check cwr exit
    if (qp->dctcp.m_caState == 1) {
        if (ack_seq > qp->dctcp.m_highSeq) qp->dctcp.m_caState = 0;
    }

    // check if need to reduce rate: ECN and not in CWR
    if (cnp && qp->dctcp.m_caState == 0) {
#if PRINT_LOG
        printf("%lu %s %08x %08x %u %u %.3lf->", Simulator::Now().GetTimeStep(), "rate",
               qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->m_rate.GetBitRate() * 1e-9);
#endif
        qp->m_rate = std::max(m_minRate, qp->m_rate * (1 - qp->dctcp.m_alpha / 2));
#if PRINT_LOG
        printf("%.3lf\n", qp->m_rate.GetBitRate() * 1e-9);
#endif
        qp->dctcp.m_caState = 1;
        qp->dctcp.m_highSeq = qp->snd_nxt;
    }

    // additive inc
    if (qp->dctcp.m_caState == 0 && new_batch)
        qp->m_rate = std::min(qp->m_max_rate, qp->m_rate + m_dctcp_rai);
}

}  // namespace ns3
