/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2007, 2008 University of Washington
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
 */

#include "qbb-channel.h"
#include "qbb-net-device.h"
#include "ws30-observer.h"
#include "ws31-c3-observation.h"
#include "ns3/custom-header.h"
#include "ns3/settings.h"
#include "ns3/trace-source-accessor.h"
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include "ns3/log.h"
#include <iostream>
#include <fstream>
#include <limits>
#include <stdexcept>

NS_LOG_COMPONENT_DEFINE ("QbbChannel");

namespace ns3 {

static bool Ws31C3ObserveChannelPacket(Ptr<Packet> packet, Ptr<QbbNetDevice> source)
{
  if (Ws30Level()!=2 || Settings::lb_mode<47 || Settings::lb_mode>49 ||
      !source || source->GetNode()->GetNodeType()!=1) return false;
  return IsWs31C3SourcePacket(packet,source->GetNode()->GetId(),source->GetIfIndex());
}

static void Ws31C3DeliverObserved(Ptr<QbbNetDevice> destination, Ptr<Packet> packet,
                                  uint64_t token, uint32_t sourceNode, uint32_t sourcePort)
{
  std::cout << "WS31_C3_CHANNEL_DELIVER time_ns=" << Simulator::Now().GetNanoSeconds()
            << " event=" << NextWs31C3ObservationEvent()
            << " token=" << token << " token_kind=observation"
            << " source_switch=" << sourceNode
            << " source_port=" << sourcePort << " destination_node="
            << destination->GetNode()->GetId() << " destination_port="
            << destination->GetIfIndex() << " uid=" << packet->GetUid() << std::endl;
  destination->Receive(packet);
  std::cout << "WS31_C3_CHANNEL_RETURN time_ns=" << Simulator::Now().GetNanoSeconds()
            << " event=" << NextWs31C3ObservationEvent()
            << " token=" << token << " token_kind=observation"
            << " uid=" << packet->GetUid() << std::endl;
}

NS_OBJECT_ENSURE_REGISTERED (QbbChannel);

TypeId 
QbbChannel::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::QbbChannel")
    .SetParent<Channel> ()
    .AddConstructor<QbbChannel> ()
    .AddAttribute ("Delay", "Transmission delay through the channel",
                   TimeValue (Seconds (0)),
                   MakeTimeAccessor (&QbbChannel::m_delay),
                   MakeTimeChecker ())
    .AddTraceSource ("TxRxQbb",
                     "Trace source indicating transmission of packet from the QbbChannel, used by the Animation interface.",
                     MakeTraceSourceAccessor (&QbbChannel::m_txrxQbb))
  ;
  return tid;
}

//
// By default, you get a channel that 
// has an "infitely" fast transmission speed and zero delay.
QbbChannel::QbbChannel()
  :
    PointToPointChannel ()
{
  NS_LOG_FUNCTION_NOARGS ();
  m_nDevices = 0;
}

void
QbbChannel::Attach (Ptr<QbbNetDevice> device)
{
  
  //std::cout << m_nDevices << " " << N_DEVICES << "\n";
  //fflush(stdout);
  NS_LOG_FUNCTION (this << device);
  NS_ASSERT_MSG (m_nDevices < N_DEVICES, "Only two devices permitted");
  NS_ASSERT (device != 0);

  m_link[m_nDevices++].m_src = device;
//
// If we have both devices connected to the channel, then finish introducing
// the two halves and set the links to IDLE.
//
  if (m_nDevices == N_DEVICES)
    {
      m_link[0].m_dst = m_link[1].m_src;
      m_link[1].m_dst = m_link[0].m_src;
      m_link[0].m_state = IDLE;
      m_link[1].m_state = IDLE;
    }


}

bool
QbbChannel::TransmitStart (
  Ptr<Packet> p,
  Ptr<QbbNetDevice> src,
  Time txTime)
{
  NS_LOG_FUNCTION (this << p << src);
  NS_LOG_LOGIC ("UID is " << p->GetUid () << ")");

  NS_ASSERT (m_link[0].m_state != INITIALIZING);
  NS_ASSERT (m_link[1].m_state != INITIALIZING);

  uint32_t wire = src == m_link[0].m_src ? 0 : 1;

  if (!m_ws31Enter)
    {
      m_ws31EverTransmitted = true;
      if (Ws31C3ObserveChannelPacket(p,src))
        {
          const uint64_t token=NextWs31C3DeliveryToken();
          Simulator::ScheduleWithContext (m_link[wire].m_dst->GetNode ()->GetId (),
                                      txTime + m_delay, &Ws31C3DeliverObserved,
                                      m_link[wire].m_dst, p, token,
                                      src->GetNode()->GetId(), src->GetIfIndex());
          std::cout << "WS31_C3_CHANNEL_SCHEDULE time_ns=" << Simulator::Now().GetNanoSeconds()
                    << " event=" << NextWs31C3ObservationEvent()
                    << " token=" << token << " token_kind=observation"
                    << " source_switch=" << src->GetNode()->GetId()
                    << " source_port=" << src->GetIfIndex() << " uid=" << p->GetUid()
                    << " delivery_due_ns=" <<
                       (Simulator::Now()+txTime+m_delay).GetNanoSeconds() << std::endl;
        }
      else
        Simulator::ScheduleWithContext (m_link[wire].m_dst->GetNode ()->GetId (),
                                    txTime + m_delay, &QbbNetDevice::Receive,
                                    m_link[wire].m_dst, p);
    }
  else
    {
      if (!m_ws31Leave || !m_ws31Owner || m_ws31Failed ||
          m_nDevices != N_DEVICES ||
          (src != m_link[0].m_src && src != m_link[1].m_src) ||
          m_ws31Pending == std::numeric_limits<uint64_t>::max ())
        throw std::logic_error ("Invalid WS31 channel observer or source");
      const uint64_t serial = m_ws31Enter (p, src, m_link[wire].m_dst);
      if (serial == 0)
        throw std::logic_error ("WS31 channel observer returned an empty token");
      m_ws31EverTransmitted = true;
      ++m_ws31Pending;
      // Exactly one delivery event, with the original delay, context and packet.
      try
        {
          if (m_ws31FailScheduleForTest)
            {
              m_ws31FailScheduleForTest = false;
              throw std::runtime_error ("Controlled WS31 pre-schedule failure");
            }
          Simulator::ScheduleWithContext (m_link[wire].m_dst->GetNode ()->GetId (),
                                      txTime + m_delay, &QbbChannel::DeliverWs31,
                                      Ptr<QbbChannel> (this), m_link[wire].m_dst,
                                      p, serial, m_ws31Leave);
          m_txrxQbb (p, src, m_link[wire].m_dst, txTime, txTime + m_delay);
          if (Ws31C3ObserveChannelPacket(p,src))
            std::cout << "WS31_C3_CHANNEL_SCHEDULE time_ns=" << Simulator::Now().GetNanoSeconds()
                      << " event=" << NextWs31C3ObservationEvent()
                      << " token=" << serial << " token_kind=endpoint_observer"
                      << " source_switch=" << src->GetNode()->GetId()
                      << " source_port=" << src->GetIfIndex() << " uid=" << p->GetUid()
                      << " delivery_due_ns=" <<
                         (Simulator::Now()+txTime+m_delay).GetNanoSeconds() << std::endl;
        }
      catch (...)
        {
          m_ws31Failed = true;
          if (!m_ws31Failure) m_ws31Failure = std::current_exception ();
          throw;
        }
      return true;
    }

  // Call the tx anim callback on the net device
  m_txrxQbb (p, src, m_link[wire].m_dst, txTime, txTime + m_delay);
  return true;
}

void
QbbChannel::DeliverWs31 (Ptr<QbbChannel> channel, Ptr<QbbNetDevice> destination,
                        Ptr<Packet> packet, uint64_t serial, const Ws31Leave &leave)
{
  try
    {
      if (!channel->m_ws31Owner || channel->m_ws31Failed ||
          channel->m_ws31Pending == 0 || !leave)
        throw std::logic_error ("WS31 delivery lost its channel observer");
      Ptr<QbbNetDevice> source=channel->m_link[0].m_dst==destination ?
          channel->m_link[0].m_src : channel->m_link[1].m_src;
      const bool observe=Ws31C3ObserveChannelPacket(packet,source);
      if (observe)
        std::cout << "WS31_C3_CHANNEL_DELIVER time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " event=" << NextWs31C3ObservationEvent()
                  << " token=" << serial << " token_kind=endpoint_observer"
                  << " source_switch=" << source->GetNode()->GetId()
                  << " source_port=" << source->GetIfIndex() << " destination_node="
                  << destination->GetNode()->GetId() << " destination_port="
                  << destination->GetIfIndex() << " uid=" << packet->GetUid() << std::endl;
      destination->Receive (packet);
      if (observe)
        std::cout << "WS31_C3_CHANNEL_RETURN time_ns=" << Simulator::Now().GetNanoSeconds()
                  << " event=" << NextWs31C3ObservationEvent()
                  << " token=" << serial << " token_kind=endpoint_observer"
                  << " uid=" << packet->GetUid() << std::endl;
      // A completion callback inside Receive is still part of the open token.
      leave (serial);
      --channel->m_ws31Pending;
      if (observe)
        std::cout << "WS31_C3_CHANNEL_OBSERVER_CLOSED time_ns="
                  << Simulator::Now().GetNanoSeconds()
                  << " event=" << NextWs31C3ObservationEvent()
                  << " token=" << serial << " token_kind=endpoint_observer"
                  << " uid=" << packet->GetUid() << std::endl;
    }
  catch (...)
    {
      // Do not manufacture closure if Receive or the evidence callback failed.
      channel->m_ws31Failed = true;
      if (!channel->m_ws31Failure) channel->m_ws31Failure = std::current_exception ();
      // Old ProcessOneEvent must return from Invoke to reach its Unref.
      // Report the saved failure outside Run, not through the event stack.
      Simulator::Stop ();
    }
}

uint32_t 
QbbChannel::GetNDevices (void) const
{
  NS_LOG_FUNCTION_NOARGS ();

  //std::cout<<m_nDevices<<"\n";
  //std::cout.flush();


  return m_nDevices;
}

Ptr<QbbNetDevice>
QbbChannel::GetQbbDevice (uint32_t i) const
{
  NS_LOG_FUNCTION_NOARGS ();
  NS_ASSERT (i < 2);
  return m_link[i].m_src;
}

Ptr<NetDevice>
QbbChannel::GetDevice (uint32_t i) const
{
  NS_LOG_FUNCTION_NOARGS ();
  return GetQbbDevice (i);
}

Time
QbbChannel::GetDelay (void) const
{
  return m_delay;
}

Ptr<QbbNetDevice>
QbbChannel::GetSource (uint32_t i) const
{
  return m_link[i].m_src;
}

Ptr<QbbNetDevice>
QbbChannel::GetDestination (uint32_t i) const
{
  return m_link[i].m_dst;
}

bool
QbbChannel::IsInitialized (void) const
{
  NS_ASSERT (m_link[0].m_state != INITIALIZING);
  NS_ASSERT (m_link[1].m_state != INITIALIZING);
  return true;
}

} // namespace ns3
