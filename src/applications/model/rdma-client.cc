/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2007,2008,2009 INRIA, UDCAST
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Amine Ismail <amine.ismail@sophia.inria.fr>
 *                      <amine.ismail@udcast.com>
 */
#include "ns3/log.h"
#include "ns3/ipv4-address.h"
#include "ns3/nstime.h"
#include "ns3/inet-socket-address.h"
#include "ns3/inet6-socket-address.h"
#include "ns3/socket.h"
#include "ns3/simulator.h"
#include "ns3/socket-factory.h"
#include "ns3/packet.h"
#include "ns3/uinteger.h"
#include "ns3/integer.h"
#include "ns3/random-variable.h"
#include "ns3/qbb-net-device.h"
#include "ns3/ipv4-end-point.h"
#include "rdma-client.h"
#include "ns3/seq-ts-header.h"
#include <ns3/rdma-driver.h>
#include "ns3/settings.h"
#include "ns3/ws31-start.h"
#include "ns3/ws31-label-fixture.h"
#include "ns3/ws31-v2-native-session.h"
#include "ns3/ws30-observer.h"
#include "ns3/ws30-v13-fixture.h"
#include <stdlib.h>
#include <stdio.h>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("RdmaClient");
NS_OBJECT_ENSURE_REGISTERED (RdmaClient);

TypeId
RdmaClient::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::RdmaClient")
    .SetParent<Application> ()
    .AddConstructor<RdmaClient> ()
    .AddAttribute ("WriteSize",
                   "The number of bytes to write",
                   UintegerValue (10000),
                   MakeUintegerAccessor (&RdmaClient::m_size),
                   MakeUintegerChecker<uint64_t> ())
    .AddAttribute ("SourceIP",
                   "Source IP",
                   Ipv4AddressValue ("0.0.0.0"),
                   MakeIpv4AddressAccessor (&RdmaClient::m_sip),
                   MakeIpv4AddressChecker ())
    .AddAttribute ("DestIP",
                   "Dest IP",
                   Ipv4AddressValue ("0.0.0.0"),
                   MakeIpv4AddressAccessor (&RdmaClient::m_dip),
                   MakeIpv4AddressChecker ())
    .AddAttribute ("SourcePort",
                   "Source Port",
                   UintegerValue (0),
                   MakeUintegerAccessor (&RdmaClient::m_sport),
                   MakeUintegerChecker<uint16_t> ())
    .AddAttribute ("DestPort",
                   "Dest Port",
                   UintegerValue (0),
                   MakeUintegerAccessor (&RdmaClient::m_dport),
                   MakeUintegerChecker<uint16_t> ())
	.AddAttribute ("PriorityGroup", "The priority group of this flow",
				   UintegerValue (0),
				   MakeUintegerAccessor (&RdmaClient::m_pg),
				   MakeUintegerChecker<uint16_t> ())
    .AddAttribute ("Window",
                   "Bound of on-the-fly packets",
                   UintegerValue (0),
                   MakeUintegerAccessor (&RdmaClient::m_win),
                   MakeUintegerChecker<uint32_t> ())
    .AddAttribute ("BaseRtt",
                   "Base Rtt",
                   UintegerValue (0),
                   MakeUintegerAccessor (&RdmaClient::m_baseRtt),
                   MakeUintegerChecker<uint64_t> ())
    .AddAttribute ("StatFlowID",
                   "Flow ID",
                   IntegerValue (-1),
                   MakeIntegerAccessor (&RdmaClient::m_flow_id),
                   MakeIntegerChecker<int32_t> ())
    .AddAttribute ("WorkloadTag", "Input workload label; no routing semantics",
                   UintegerValue (0),
                   MakeUintegerAccessor (&RdmaClient::m_workload_tag),
                   MakeUintegerChecker<uint32_t> ())
  ;
  return tid;
}

RdmaClient::RdmaClient ()
{
  NS_LOG_FUNCTION_NOARGS ();
}

RdmaClient::~RdmaClient ()
{
  NS_LOG_FUNCTION_NOARGS ();
}

void RdmaClient::SetRemote (Ipv4Address ip, uint16_t port)
{
  m_dip = ip;
  m_dport = port;
}

void RdmaClient::SetLocal (Ipv4Address ip, uint16_t port)
{
  m_sip = ip;
  m_sport = port;
}

void RdmaClient::SetPG (uint16_t pg)
{
	m_pg = pg;
}

void RdmaClient::SetSize(uint64_t size){
	m_size = size;
}

void RdmaClient::DoDispose (void)
{
  NS_LOG_FUNCTION_NOARGS ();
  CancelPendingRequest();
  Application::DoDispose ();
}

void RdmaClient::FailWs31V2() {
  if (m_ws31V2Required) {
    m_ws31V2Failed=true;
    Simulator::Cancel(m_ws31LaunchEvent);
    m_ws31Pending=false;
  }
  if (m_ws31V2Session) m_ws31V2Session->Fail("V2 client boundary failed");
  Ws31V2NativeSession::FailHandle(m_ws31V2Request,"V2 client boundary failed");
}

void RdmaClient::RequireWs31V2Input(std::shared_ptr<Ws31V2NativeSession> session) try {
  if (m_ws31V2Required || m_ws31V2Started || m_ws31Pending)
    throw std::logic_error("V2 client configuration repeated/late");
  m_ws31V2Required=true; m_ws31V2Session=session;
  if (!session) throw std::logic_error("V2 client required session missing");
  session->RequireHealthy();
} catch (...) { FailWs31V2(); throw; }

void RdmaClient::BindWs31V2Current(std::shared_ptr<Ws31V2NativeRequest> request) try {
  if (!m_ws31V2Required || m_ws31V2Failed || !m_ws31V2Session || m_ws31V2Request || m_ws31V2Started)
    throw std::logic_error("V2 client current binding invalid/repeated");
  m_ws31V2Session->CheckIssued(request);
  m_ws31V2Request=request;
} catch (...) { m_ws31V2Required=true; Ws31V2NativeSession::FailHandle(request,"V2 client binding failed"); FailWs31V2(); throw; }

void RdmaClient::StartApplication (void) try
{
  NS_LOG_FUNCTION_NOARGS ();
  ws31::VisibleLabel nativePolicy(0,false);
  if (m_ws31V2Required) {
    if (m_ws31V2Failed || m_ws31V2Started || !m_ws31V2Session || !GetNode())
      throw std::logic_error("V2 client demand is not healthy");
    const auto p=m_ws31V2Session->Demand(m_ws31V2Request,GetNode()->GetId(),m_flow_id,
        m_sip.Get(),m_dip.Get(),m_sport,m_dport,m_pg,m_size,m_workload_tag);
    nativePolicy=ws31::VisibleLabel(p.value,p.present);
    m_ws31V2Started=true; m_ws31DemandNs=Simulator::Now().GetNanoSeconds();
  }
  if (ws31::StartMode(Settings::lb_mode)) {
    if (m_ws31Pending) NS_FATAL_ERROR("C2 request started twice while pending");
    m_ws31DemandNs = Simulator::Now().GetNanoSeconds();
    const unsigned tagTransform = m_ws31V2Required?0:Ws30V13TagTransform();
    const unsigned labelProfile = m_ws31V2Required?0:ws31::LabelProfile();
    const ws31::VisibleLabel visible = m_ws31V2Required?nativePolicy:ws31::LabelAt(labelProfile,m_workload_tag,
        m_ws31DemandNs,m_ws31DemandNs,m_sip.Get(),m_dip.Get(),m_sport,m_dport,tagTransform);
    const uint32_t policyTag = m_ws31V2Required?(visible.present?visible.value:0):visible.value;
    const ws31::StartDecision decision=ws31::DecideStart(Settings::lb_mode,policyTag,m_size,
                                                         m_sip.Get(),m_dip.Get(),m_sport,m_dport);
    const uint64_t delay=decision.delayNs;
    ws31::StartCounters &s = ws31::StartData();
    ++s.demanded; s.demandBytes += m_size;
    s.eligible += decision.eligible;
    s.plannedWaited += delay!=0;
    s.plannedDelaySum += delay;
    if (delay>s.plannedDelayMax) s.plannedDelayMax=delay;
    s.eligibilityHashes += decision.eligibilityHashes;
    s.delayHashes += decision.delayHashes;
    s.sizeComparisons += decision.sizeComparisons;
    m_ws31Pending = true;
    if (Ws30Level())
      std::cout << "WS31_C2_DEMAND flow_id=" << m_flow_id << " demand_ns=" << m_ws31DemandNs
                << " size=" << m_size << " tag=" << m_workload_tag
                << " delay_ns=" << delay << " eligible=" << decision.eligible
                << " eligibility_hashes=" << decision.eligibilityHashes
                << " delay_hashes=" << decision.delayHashes
                << " size_comparisons=" << decision.sizeComparisons
                << " policy_tag=" << policyTag
                << " tag_transform=" << tagTransform << std::endl;
    if (labelProfile && Ws30Level())
      std::cout << "WS31_LABEL_DEMAND flow_id=" << m_flow_id << " generation=0"
                << " demand_ns=" << m_ws31DemandNs << " profile=" << labelProfile
                << " original=" << m_workload_tag << " visible=" << visible.value
                << " present=" << visible.present << std::endl;
    if (delay) {
      m_ws31LaunchEvent = Simulator::Schedule(NanoSeconds(delay), &RdmaClient::StartRequest, this);
      return;
    }
  }
  StartRequest();
} catch (...) { FailWs31V2(); throw; }

void RdmaClient::StartRequest (void) try
{
  uint64_t demand = m_ws31V2Required?m_ws31DemandNs:uint64_t(-1);
  if (m_ws31V2Required) {
    if (m_ws31V2Failed || !m_ws31V2Started || !m_ws31V2Session)
      throw std::logic_error("V2 client launch lacks healthy demand");
    m_ws31V2Session->RequireHealthy();
  }
  if (ws31::StartMode(Settings::lb_mode)) {
    if (!m_ws31Pending) NS_FATAL_ERROR("C2 request launched without pending demand");
    m_ws31Pending = false;
    demand = m_ws31DemandNs;
    const uint64_t now = Simulator::Now().GetNanoSeconds();
    if (now < demand) NS_FATAL_ERROR("C2 launch precedes demand");
    const uint64_t delay = now-demand;
    if (delay>500) NS_FATAL_ERROR("C2 launch exceeds frozen delay bound");
    ws31::StartCounters &s = ws31::StartData();
    ++s.launched; s.launchBytes += m_size; s.waited += delay!=0;
    s.delaySum += delay; if (delay>s.delayMax) s.delayMax=delay;
    if (Ws30Level())
      std::cout << "WS31_C2_LAUNCH flow_id=" << m_flow_id << " demand_ns=" << demand
                << " launch_ns=" << now << " wait_ns=" << delay
                << " size=" << m_size << std::endl;
  }
  DispatchRequest(demand);
} catch (...) { FailWs31V2(); throw; }

void RdmaClient::DispatchRequest (uint64_t demand) try
{
  // get RDMA driver and add up queue pair
  Ptr<Node> node = GetNode();
  Ptr<RdmaDriver> rdma = node->GetObject<RdmaDriver>();
  if (m_ws31V2Required) {
    if (!rdma || !rdma->m_rdma || m_ws31V2Failed || !m_ws31V2Session)
      throw std::logic_error("V2 dispatch lacks actual driver/hardware");
    rdma->m_rdma->AddQueuePairV2(m_size,m_pg,m_sip,m_dip,m_sport,m_dport,m_win,m_baseRtt,
        m_flow_id,m_workload_tag,demand,m_ws31V2Request);
    return;
  }
  rdma->AddQueuePair(m_size, m_pg, m_sip, m_dip, m_sport, m_dport, m_win, m_baseRtt, m_flow_id, m_workload_tag, demand);
} catch (...) { FailWs31V2(); throw; }

void RdmaClient::CancelPendingRequest (void) try
{
  if (!m_ws31Pending) return;
  if (m_ws31V2Required) {
    if (m_ws31V2Failed || !m_ws31V2Session || !GetNode())
      throw std::logic_error("V2 cancel lacks healthy session/node");
    m_ws31V2Session->CancelPending(m_ws31V2Request,GetNode()->GetId(),m_flow_id,
        m_sip.Get(),m_dip.Get(),m_sport,m_dport,m_pg,m_size,m_workload_tag,m_ws31DemandNs);
  }
  Simulator::Cancel(m_ws31LaunchEvent);
  m_ws31Pending = false;
  ws31::StartCounters &s = ws31::StartData();
  ++s.cancelled; s.cancelBytes += m_size;
  if (Ws30Level())
    std::cout << "WS31_C2_CANCEL flow_id=" << m_flow_id << " demand_ns=" << m_ws31DemandNs
              << " time_ns=" << Simulator::Now().GetNanoSeconds() << " size=" << m_size << std::endl;
} catch (...) { FailWs31V2(); throw; }

void RdmaClient::StopApplication ()
{
  NS_LOG_FUNCTION_NOARGS ();
  CancelPendingRequest();
  // TODO stop the queue pair
}

} // Namespace ns3
