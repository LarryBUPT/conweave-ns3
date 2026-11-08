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
 *
 */

#ifndef RDMA_CLIENT_H
#define RDMA_CLIENT_H

#include "ns3/application.h"
#include "ns3/event-id.h"
#include "ns3/ptr.h"
#include "ns3/ipv4-address.h"
#include <ns3/rdma.h>
#include <memory>

namespace ns3 {

class Socket;
class Packet;
class Ws31V2NativeSession;
class Ws31V2NativeRequest;

/**
 * \ingroup rdmaclientserver
 * \class rdmaClient
 * \brief A RDMA client.
 *
 */
class RdmaClient : public Application
{
public:
  static TypeId
  GetTypeId (void);

  RdmaClient ();

  virtual ~RdmaClient ();

  /**
   * \brief set the remote address and port
   * \param ip remote IP address
   * \param port remote port
   */
  void SetRemote (Ipv4Address ip, uint16_t port);
  void SetLocal (Ipv4Address ip, uint16_t port);
  void SetPG (uint16_t pg);
  void SetSize(uint64_t size);
  void RequireWs31V2Input(std::shared_ptr<Ws31V2NativeSession> session);
  void BindWs31V2Current(std::shared_ptr<Ws31V2NativeRequest> request);

protected:
  virtual void DoDispose (void);
  // Transport seam for the standalone event-boundary fixture. Production
  // dispatch retains the same driver call after demand/launch accounting.
  virtual void DispatchRequest (uint64_t demandStartNs);

private:
  friend class Ws31StartBoundaryProbe;
  friend class Ws31V2NativeBindingFixture;
  friend class Ws31V2NativeEntry;

  bool m_ws31V2Required=false, m_ws31V2Failed=false, m_ws31V2Started=false;
  std::shared_ptr<Ws31V2NativeSession> m_ws31V2Session;
  std::shared_ptr<Ws31V2NativeRequest> m_ws31V2Request;
  void FailWs31V2();

  virtual void StartApplication (void);
  virtual void StopApplication (void);
  void StartRequest (void);
  void CancelPendingRequest (void);

  EventId m_ws31LaunchEvent;
  uint64_t m_ws31DemandNs = 0;
  bool m_ws31Pending = false;

  uint64_t m_size;
  uint16_t m_pg;

  Ipv4Address m_sip, m_dip;
  uint16_t m_sport, m_dport;
  uint32_t m_win; // bound of on-the-fly packets
  uint64_t m_baseRtt; // base Rtt
  int32_t m_flow_id;
  uint32_t m_workload_tag;
};

} // namespace ns3

#endif /* RDMA_CLIENT_H */
