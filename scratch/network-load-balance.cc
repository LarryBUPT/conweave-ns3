/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2023 NUS
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
 * Authors: Chahwan Song <skychahwan@gmail.com>
 */

#include <ns3/assert.h>
#include <ns3/rdma-client-helper.h>
#include <ns3/rdma-client.h>
#include <ns3/rdma-driver.h>
#include <ns3/rdma.h>
#include <ns3/sim-setting.h>
#include <ns3/switch-node.h>
#include <ns3/ws30-cw-observer.h>
#include <time.h>

#include <fstream>
#include <iostream>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <unordered_map>

#include "ns3/applications-module.h"
#include "ns3/broadcom-node.h"
#include "ns3/conga-routing.h"
#include "ns3/conweave-voq.h"
#include "ns3/core-module.h"
#include "ns3/error-model.h"
#include "ns3/global-route-manager.h"
#include "ns3/internet-module.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/letflow-routing.h"
#include "ns3/packet.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/qbb-helper.h"
#include "ns3/qbb-net-device.h"
#include "ns3/rdma-hw.h"
#include "ns3/settings.h"
#include "ns3/workload-tag.h"
#include "ns3/ws30-v13-fixture.h"
#include "ns3/ws31-start.h"
#include "ns3/ws31-label-fixture.h"
#include "ns3/ws31-ofan.h"
#include "ws30-composition-fixture.h"
#include "ns3/ws31-v2-native-entry.h"
#include "ns3/qbb-channel.h"
#include "ns3/ppp-header.h"
#include "ns3/seq-ts-header.h"
#include "ns3/qbb-header.h"
#include "ns3/pause-header.h"
#include "ns3/flow-id-num-tag.h"
#include <algorithm>
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <vector>

using namespace ns3;
using namespace std;

NS_LOG_COMPONENT_DEFINE("GENERIC_SIMULATION");

/*------Load balancing parameters-----*/
// mode for load balancer, 0: flow ECMP, 2: DRILL, 3: Conga, 6: Letflow, 9: ConWeave
uint32_t lb_mode = 0;
uint64_t ws31_c2_size_target_bytes = 0;
uint32_t ws31_c2_size_cutoff = 0;
uint32_t guardhash_lambda = 1;
uint32_t guardhash_tau_bytes = 0;
uint32_t harm_gate_on_bytes = 8192;
uint32_t harm_gate_off_bytes = 4096;
bool ws18_admission = false, ws18_path = false;
uint32_t ws18_admission_rate_gbps = 400;
std::string ws18_output_file;
FILE *ws18_output = NULL;
bool ws21_identity = false;
bool ws21_feedback = false;
uint32_t ws21_feedback_interval_ns = 10000;
bool ws21_heartbeat = false;
uint32_t ws21_heartbeat_interval_ns = 200000;
uint32_t ws21_heartbeat_fault_mode = 0, ws21_heartbeat_fault_tor = 0;
uint32_t ws21_heartbeat_fault_port = 0;
uint64_t ws21_heartbeat_fault_start_ns = 0, ws21_heartbeat_fault_end_ns = 0;
std::string ws21_identity_output_file;
bool ws21_port_events = false;
std::string ws21_port_output_file;
uint64_t ws21_port_max_bytes = 268435456;
FILE *ws21_port_output = NULL;

// Conga params (based on paper recommendation)
Time conga_flowletTimeout = MicroSeconds(100);  // 100us
Time conga_dreTime = MicroSeconds(50);
Time conga_agingTime = MicroSeconds(500);
uint32_t conga_quantizeBit = 3;
double conga_alpha = 0.2;

// Letflow params
Time letflow_flowletTimeout = MicroSeconds(100);  // 100us
Time letflow_agingTime = MilliSeconds(2);  // just to clear the unused map entries for simul speed

// Conweave params
Time conweave_extraReplyDeadline = MicroSeconds(4);       // additional term to reply deadline
Time conweave_pathPauseTime = MicroSeconds(8);            // time to send packets to congested path
Time conweave_txExpiryTime = MicroSeconds(1000);          // waiting time for CLEAR
Time conweave_extraVOQFlushTime = MicroSeconds(32);       // extra for uncertainty
Time conweave_defaultVOQWaitingTime = MicroSeconds(500);  // default flush timer if no history
bool conweave_pathAwareRerouting = true;

/*------------------------ simulation variables -----------------------------*/
uint64_t one_hop_delay = 1000;  // nanoseconds
uint32_t cc_mode = 1;           // mode for congestion control, 1: DCQCN
bool enable_qcn = true, enable_pfc = true, use_dynamic_pfc_threshold = true;
uint32_t packet_payload_size = 1000, l2_chunk_size = 0, l2_ack_interval = 0;
double pause_time = 5;  // PFC pause, microseconds
int32_t ws23_pfc_probe_host = -1;
uint32_t ws23_pfc_probe_pg = 3;
uint64_t ws23_pfc_probe_start_ns = 0, ws23_pfc_probe_end_ns = 0;
double flowgen_start_time = 2.0, flowgen_stop_time = 2.5, simulator_extra_time = 0.1;
// queue length monitoring time is not used in this simulator
// uint32_t qlen_dump_interval = 100000000, qlen_mon_interval = 1000;  // ns
uint64_t qlen_mon_start;               // ns
uint64_t qlen_mon_end;                 // ns
uint32_t switch_mon_interval = 10000;  // ns
uint64_t cnp_mon_start;                // ns
uint64_t cnp_monitor_bucket = 100000;  // ns
uint64_t irn_mon_start;                // ns
uint64_t irn_monitor_bucket = 100000;  // ns

bool ws31_native_declarations_seen=false, ws31_native_output_seen=false;
bool ws31_c3r_reuse_tuple=false;
bool ws31_c3r_replay_stale=false;
std::string ws31_native_declarations, ws31_native_output_prefix;

FILE *pfc_file = NULL;
FILE *fct_output = NULL;
FILE *flow_input_stream = NULL;
FILE *cnp_output = NULL;
FILE *est_error_output = NULL;
FILE *voq_output = NULL;
FILE *voq_detail_output = NULL;
FILE *uplink_output = NULL;
FILE *conn_output = NULL;

std::string data_rate, link_delay, topology_file, flow_file;
std::string flow_input_file = "flow.txt";
std::string fct_output_file = "fct.txt";
std::string pfc_output_file = "pfc.txt";
std::string cnp_output_file = "cnp.txt";
std::string qlen_mon_file = "qlen.txt";
std::string voq_mon_file = "voq.txt";
std::string voq_mon_detail_file = "voq_detail.txt";
std::string uplink_mon_file = "uplink.txt";
std::string conn_mon_file = "conn.txt";
std::string est_error_output_file = "est_error.txt";

// CC params
double alpha_resume_interval = 55, rp_timer = 300, ewma_gain = 1 / 16;
double rate_decrease_interval = 4;
uint32_t fast_recovery_times = 1;
std::string rate_ai, rate_hai, min_rate = "100Mb/s";
std::string dctcp_rate_ai = "1000Mb/s";

bool clamp_target_rate = false, l2_back_to_zero = false;
double error_rate_per_link = 0.0;
uint32_t has_win = 1;
uint32_t global_t = 1;
uint32_t mi_thresh = 5;
bool var_win = false, fast_react = true;
bool multi_rate = true;
bool sample_feedback = false;
double u_target = 0.95;
uint32_t int_multi = 1;
bool rate_bound = true;
unordered_map<uint64_t, uint32_t> rate2kmax, rate2kmin;
unordered_map<uint64_t, double> rate2pmax;
unordered_map<uint32_t, Ptr<SwitchNode>> idxNodeToR;  // Id -> Ptr

// config of link-down scenario, ACK priority, and buffer
uint64_t link_down_time = 0;
uint32_t link_down_A = 0, link_down_B = 0;
uint32_t buffer_size = 0;  // 0 to set buffer size automatically

// Added from Here
double load = 10.0;
int enable_irn = 0;
int random_seed = 1;  // change this randomly if you want random expt

uint64_t maxRtt, maxBdp;

// app parameters
struct Interface {
    uint32_t idx;
    bool up;
    uint64_t delay;
    uint64_t bw;

    Interface() : idx(0), up(false) {}
};
map<Ptr<Node>, map<Ptr<Node>, Interface>> nbr2if;
// Mapping destination to next hop for each node: <node, <dest, <nexthop0, ...> > >
map<Ptr<Node>, map<Ptr<Node>, vector<Ptr<Node>>>> nextHop;
map<Ptr<Node>, map<Ptr<Node>, uint64_t>> pairDelay;
map<Ptr<Node>, map<Ptr<Node>, uint64_t>> pairTxDelay;
map<Ptr<Node>, map<Ptr<Node>, uint64_t>> pairBw;
map<Ptr<Node>, map<Ptr<Node>, uint64_t>> pairBdp;
map<Ptr<Node>, map<Ptr<Node>, uint64_t>> pairRtt;

// for uplink/Downlink monitoring at TOR switches (load balance performance)
std::map<uint32_t, std::vector<uint32_t>> torId2UplinkIf;
std::map<uint32_t, std::vector<uint32_t>> torId2DownlinkIf;

// input files
std::ifstream topof, flowf;
NodeContainer n;                         // node container
std::vector<Ipv4Address> serverAddress;  // server address

// flow generator
std::unordered_map<uint32_t, uint32_t> flows_per_host;
uint32_t flow_id = 0;
std::unordered_map<uint32_t, uint16_t> portNumber;
std::unordered_map<uint32_t, uint16_t> dportNumber;
uint16_t *port_per_host;

// Scheduling input flows from flow.txt
struct FlowInput {
    uint32_t src, dst, pg, maxPacketCount, port;
    double start_time;
    int64_t start_time_ns;
    uint32_t idx;
    uint32_t workload_tag;
};
FlowInput flow_input = {0};  // global variable

Time FlowInputStartTime() {
    // Preserve the legacy double-to-Time conversion outside WS-18. In WS-18,
    // the trace's demand is an integer nanosecond, not a truncated double.
    return lb_mode == 20 ? NanoSeconds(flow_input.start_time_ns)
                         : Seconds(flow_input.start_time);
}
uint32_t flow_num;
uint32_t flow_line_number = 1;
double previous_flow_start = -1.0;
std::map<uint32_t, uint64_t> input_tag_counts;
struct Ws18Flow {
    uint32_t src, dst, pg, sport, dport, bytes, tag;
    uint64_t demand_ns, release_ns;
    bool released, finished;
};
std::vector<Ws18Flow> ws18_flows;
std::map<uint32_t, uint64_t> ws18_next_release_ns;

void ReleaseWs18Flow(uint32_t id) {
    Ws18Flow &flow = ws18_flows.at(id);
    NS_ASSERT_MSG(!flow.released && Simulator::Now().GetNanoSeconds() == flow.release_ns,
                  "WS-18 release must happen once at its recorded time");
    flow.released = true;
    Ptr<Node> source = n.Get(flow.src), destination = n.Get(flow.dst);
    NS_ASSERT_MSG(pairRtt.count(source) && pairRtt[source].count(destination),
                  "WS-18 source/destination RTT must exist");
    RdmaClientHelper clientHelper(
        flow.pg, serverAddress[flow.src], serverAddress[flow.dst], flow.sport, flow.dport,
        flow.bytes, has_win ? (global_t == 1 ? maxBdp : pairBdp[source][destination]) : 0,
        global_t == 1 ? maxRtt : pairRtt[source][destination]);
    clientHelper.SetAttribute("StatFlowID", IntegerValue(id));
    clientHelper.SetAttribute("WorkloadTag", UintegerValue(flow.tag));
    ApplicationContainer app = clientHelper.Install(source);
    // ApplicationContainer::Start takes a delay from its installation event.
    // Installing at release and starting with zero delay starts the QP now.
    app.Start(Seconds(Time(0)));
    app.Stop(Seconds(100.0));
}

/**
 * Read flow input from file "flowf"
 */
void ReadFlowInput() {
    if (flow_input.idx < flow_num) {
        std::string line;
        if (!std::getline(flowf, line)) {
            std::cerr << "FLOW_INPUT_ERROR line " << flow_line_number + 1
                      << ": fewer records than declared " << flow_num << std::endl;
            std::exit(1);
        }
        ++flow_line_number;
        std::istringstream fields(line);
        int64_t src, dst, pg, bytes, tag = 0;
        double start;
        std::string extra;
        if (!(fields >> src >> dst >> pg >> bytes >> start) ||
            (fields >> tag && (fields >> extra)) ||
            (!fields.eof() && fields.fail() && !fields.eof())) {
            std::cerr << "FLOW_INPUT_ERROR line " << flow_line_number
                      << ": expected src dst pg bytes start_s [tag]" << std::endl;
            std::exit(1);
        }
        if (src < 0 || dst < 0 || src >= static_cast<int64_t>(Settings::host_num) ||
            dst >= static_cast<int64_t>(Settings::host_num) || src == dst || pg < 0 || pg > 7 ||
            bytes <= 0 || bytes > std::numeric_limits<uint32_t>::max() || tag < 0 ||
            tag > std::numeric_limits<uint32_t>::max() || !std::isfinite(start) || start < 0 ||
            start < previous_flow_start ||
            n.Get(src)->GetNodeType() != 0 || n.Get(dst)->GetNodeType() != 0) {
            std::cerr << "FLOW_INPUT_ERROR line " << flow_line_number
                      << ": invalid host, priority, size, time order, or tag" << std::endl;
            std::exit(1);
        }
        const long double start_ns = static_cast<long double>(start) * 1000000000.0L;
        if (lb_mode == 20 && start_ns >
                                static_cast<long double>(std::numeric_limits<int64_t>::max()) -
                                    0.5L) {
            std::cerr << "FLOW_INPUT_ERROR line " << flow_line_number
                      << ": demand time exceeds integer nanosecond range" << std::endl;
            std::exit(1);
        }
        flow_input.src = src;
        flow_input.dst = dst;
        flow_input.pg = pg;
        flow_input.maxPacketCount = bytes;
        flow_input.start_time = start;
        if (lb_mode == 20) flow_input.start_time_ns = std::llround(start_ns);
        flow_input.workload_tag = tag;
        previous_flow_start = start;
        ++input_tag_counts[flow_input.workload_tag];
    } else {
        std::string extra;
        while (std::getline(flowf, extra)) {
            ++flow_line_number;
            if (extra.find_first_not_of(" \t\r") != std::string::npos) {
                std::cerr << "FLOW_INPUT_ERROR line " << flow_line_number
                          << ": more records than declared " << flow_num << std::endl;
                std::exit(1);
            }
        }
        for (const auto &entry : input_tag_counts)
            std::cout << "WS06_INPUT_TAG tag=" << entry.first << " flows=" << entry.second << std::endl;
    }
}

/**
 * Scheduling flows given in /config/L_XX....txt file
 */
void ScheduleFlowInputs(FILE *infile) {
    NS_LOG_DEBUG("ScheduleFlowInputs at " << Simulator::Now());
    while (flow_input.idx < flow_num && FlowInputStartTime() == Simulator::Now()) {
        uint32_t pg, src, dst, sport, dport, maxPacketCount, target_len;
        pg = flow_input.pg;
        src = flow_input.src;
        dst = flow_input.dst;

        // src port
        sport = portNumber[src];  // get a new port number
        portNumber[src] = portNumber[src] + 1;

        // dst port
        dport = dportNumber[dst];
        dportNumber[dst] = dportNumber[dst] + 1;
        if (Ws30V14Enabled() && flow_input.workload_tag == 2) {
            if (src!=0 || dst!=3) NS_FATAL_ERROR("v14 probe requires host 0 to host 3");
            // Lowest three source ports with distinct native hashed candidates at switch 4.
            static uint32_t probeIndex=0;
            const uint16_t ports[3]={10003,10006,10008};
            sport=ports[Ws30V13Life()==2?probeIndex%3:0]; dport=100; ++probeIndex;
        } else if (Ws30V13Life() >= 3 && flow_input.workload_tag == 2) {
            sport = 10000;
            dport = 100;
        } else if (lb_mode == 57 && ws31_c3r_reuse_tuple) {
            sport = 10000;
            dport = 100;
        }

        target_len = flow_input.maxPacketCount;  // this is actually not packet-count, but bytes
        if (target_len == 0) {
            target_len = 1;
        }
        assert(n.Get(src)->GetNodeType() == 0 && n.Get(dst)->GetNodeType() == 0);

        if (lb_mode == 20) {
            const uint64_t demand = flow_input.start_time_ns;
            NS_ASSERT_MSG(demand == uint64_t(Simulator::Now().GetNanoSeconds()),
                          "WS-18 demand event must match the trace nanosecond");
            uint64_t release = demand;
            if (ws18_admission && flow_input.workload_tag == 2) {
                release = std::max(demand, ws18_next_release_ns[dst]);
                const uint64_t service = std::max<uint64_t>(
                    1, (uint64_t(target_len) * 8 + ws18_admission_rate_gbps - 1) /
                           ws18_admission_rate_gbps);
                ws18_next_release_ns[dst] = release + service;
            }
            NS_ASSERT_MSG(ws18_flows.size() == flow_input.idx, "Stable input ID mismatch");
            ws18_flows.push_back({src, dst, pg, sport, dport, target_len,
                                  flow_input.workload_tag, demand, release, false, false});
            if (release == demand)
                ReleaseWs18Flow(flow_input.idx);
            else
                Simulator::Schedule(NanoSeconds(release - demand), &ReleaseWs18Flow,
                                    flow_input.idx);
            flow_input.idx++;
            ReadFlowInput();
            continue;
        }

        /**
         * Turn on if you want to record all input streams into output file for logging.
         * But, the input stream can be found in config. We do not recommend to do this
         * as it consumes storage resource, redundantly.
         */
        if (0) {  // logging input streams to "XXXX_out_in.txt"
            /************************
             * record flow's 4-tuple
             ************************/
            fprintf(infile, "%u %u %u %u %u %lu\n", src, dst, sport, dport, target_len,
                    (uint64_t)(flow_input.start_time * (uint64_t)1000000000));
            fflush(infile);

            /***********    FCT Tracking    **************/
            UdpServerHelper server0(dport);
            server0.SetAttribute("FlowSize", UintegerValue(target_len));
            server0.SetAttribute("irn", BooleanValue(enable_irn));
            server0.SetAttribute("StatHostSrc", UintegerValue(src));
            server0.SetAttribute("StatHostDst", UintegerValue(dst));
            server0.SetAttribute("StatRxLen", UintegerValue(target_len));
            server0.SetAttribute("StatFlowID", UintegerValue(flow_input.idx));
            server0.SetAttribute("Port", UintegerValue(dport));

            ApplicationContainer apps0s = server0.Install(n.Get(dst));  // DST
            apps0s.Start(Seconds(Time(0)));
            apps0s.Stop(Seconds(100.0));
        }  // end of logging input streams

        if (pairRtt.find(n.Get(src)) == pairRtt.end() ||
            pairRtt[n.Get(src)].find(n.Get(dst)) == pairRtt[n.Get(src)].end()) {
            std::cerr << "pairRtt src: " << src << " -> dst: " << dst
                      << " ==> cannot be found from database" << std::endl;
            assert(false);
        }

        if (Ws30V13Life() >= 3) {
            // Explicit test-only endpoint creation for every request, independent
            // of workload class or route label. Reverse tuple for receiver view.
            Ptr<RdmaDriver> receiver = n.Get(dst)->GetObject<RdmaDriver>();
            receiver->m_rdma->BeginWs30RxGeneration(serverAddress[dst].Get(), serverAddress[src].Get(),
                                                   dport, sport, pg, flow_input.idx);
        } else if (lb_mode == 57) {
            Ptr<RdmaDriver> receiver = n.Get(dst)->GetObject<RdmaDriver>();
            receiver->m_rdma->BeginWs31C3rRxGeneration(
                serverAddress[dst].Get(), serverAddress[src].Get(),
                dport, sport, pg, flow_input.idx);
        }
        RdmaClientHelper clientHelper(
            pg, serverAddress[src], serverAddress[dst], sport, dport, target_len,
            has_win ? (global_t == 1 ? maxBdp : pairBdp[n.Get(src)][n.Get(dst)]) : 0,
            global_t == 1 ? maxRtt : pairRtt[n.Get(src)][n.Get(dst)]);
        clientHelper.SetAttribute("StatFlowID", IntegerValue(flow_input.idx));
        clientHelper.SetAttribute("WorkloadTag", UintegerValue(flow_input.workload_tag));

        ApplicationContainer appCon = clientHelper.Install(n.Get(src));  // SRC
        appCon.Start(Seconds(Time(0)));
        appCon.Stop(Seconds(100.0));

        flow_input.idx++;
        ReadFlowInput();
    }

    // schedule the next time to run this function
    if (flow_input.idx < flow_num) {
        Simulator::Schedule(FlowInputStartTime() - Simulator::Now(), &ScheduleFlowInputs, infile);
    } else {  // no more flows, close the file
        flowf.close();
    }
}

/**
 * @brief CNP frequency monitoring (timestamp nodeId ECN OoO Total)
 */
void cnp_freq_monitoring(FILE *fout, Ptr<RdmaHw> rdmahw) {
    if (rdmahw->cnp_total > 0) {
        // flush
        fprintf(fout, "%lu %u %u %u %u\n", Simulator::Now().GetNanoSeconds(),
                rdmahw->m_node->GetId(), rdmahw->cnp_by_ecn, rdmahw->cnp_by_ooo, rdmahw->cnp_total);
        fflush(fout);

        // initialize
        rdmahw->cnp_by_ecn = 0;
        rdmahw->cnp_by_ooo = 0;
        rdmahw->cnp_total = 0;
    }

    // recursive callback
    Simulator::Schedule(NanoSeconds(cnp_monitor_bucket), &cnp_freq_monitoring, fout, rdmahw);
}

/**
 * @brief TOR Switch monitoring
 * - VOQ number and uplink throughput at switches
 * - the number of active connections at RNICS
 */
void periodic_monitoring(FILE *fout_voq, FILE *fout_voq_detail, FILE *fout_uplink, FILE *fout_conn,
                         uint32_t *lb_mode) {
    uint32_t lb_mode_val = *lb_mode;
    uint64_t now = Simulator::Now().GetNanoSeconds();
    for (const auto &tor2If : torId2UplinkIf) {  // for each TOR switches
        Ptr<Node> node = n.Get(tor2If.first);    // tor id
        auto swNode = DynamicCast<SwitchNode>(node);
        assert(swNode->m_isToR == true);  // sanity check

        if (lb_mode_val == 9) {  // Conweave
            // monitor VOQ number per switch <time, ToRId, #VOQ, #Pkts>
            uint32_t nVOQ = swNode->m_mmu->m_conweaveRouting.GetNumVOQ();
            uint32_t nVolumeVOQ = swNode->m_mmu->m_conweaveRouting.GetVolumeVOQ();
            fprintf(fout_voq, "%lu,%u,%u,%u\n", now, tor2If.first, nVOQ, nVolumeVOQ);

            // monitor VOQ per destination IP <time, dstip, #VOQ, #Pkts>
            std::unordered_map<uint32_t, std::pair<uint32_t, uint32_t>> dip_to_nvoq_npkt;
            for (auto voq : swNode->m_mmu->m_conweaveRouting.GetVOQMap()) {
                auto &nvoq_npkt = dip_to_nvoq_npkt[voq.second.getDIP()];
                nvoq_npkt.first += 1;
                nvoq_npkt.second += voq.second.getQueueSize();
            }
            for (auto x : dip_to_nvoq_npkt) {
                fprintf(fout_voq_detail, "%lu,%u,%u,%u\n", now, x.first, x.second.first,
                        x.second.second);
            }
        }

        // common: monitor TOR's uplink to measure load balancing performance
        for (const auto &iface : tor2If.second) {
            // monitor uplink txBytes <time, ToRId, OutDev, Bytes>
            uint64_t uplink_txbyte = swNode->GetTxBytesOutDev(iface);
            fprintf(fout_uplink, "%lu,%u,%u,%lu\n", now, tor2If.first, iface, uplink_txbyte);
        }
    }

    // common: get number of concurrent connections at each server
    for (uint32_t i = 0; i < Settings::node_num; i++) {
        if (n.Get(i)->GetNodeType() == 0) {  // is server
            Ptr<Node> server = n.Get(i);
            Ptr<RdmaDriver> rdmaDriver = server->GetObject<RdmaDriver>();
            Ptr<RdmaHw> rdmaHw = rdmaDriver->m_rdma;
            // monitor total/active QP number <time, serverId, #ExistingQP, #ActiveQP>
            uint64_t nQP = rdmaHw->m_qpMap.size();
            uint64_t nActiveQP = 0;
            for (auto qp : rdmaHw->m_qpMap) {
                if (qp.second->GetBytesLeft() > 0) {  // conns with bytes left
                    nActiveQP++;
                }
            }
            fprintf(fout_conn, "%lu,%u,%lu,%lu\n", now, i, nQP, nActiveQP);
        }
    }

    if (Simulator::Now() < Seconds(flowgen_stop_time + 0.05)) {
        // recursive callback
        Simulator::Schedule(NanoSeconds(switch_mon_interval), &periodic_monitoring, fout_voq,
                            fout_voq_detail, fout_uplink, fout_conn, lb_mode);  // every 10us
    }
    return;
}

/**
 * @brief Conga timeout number recording
 */
void conga_history_print() {
    std::cout << "\n------------CONGA History---------------" << std::endl;
    std::cout << "Number of flowlet's timeout:" << CongaRouting::nFlowletTimeout
              << "Conga's timeout: " << conga_flowletTimeout << std::endl;
}

/**
 * @brief Letflow timeout number recording
 */
void letflow_history_print() {
    std::cout << "\n------------Letflow History---------------" << std::endl;
    std::cout << "Number of flowlet's timeout:" << LetflowRouting::nFlowletTimeout
              << "\nLetflow's timeout: " << letflow_flowletTimeout << std::endl;
}

/**
 * @brief Conweave rerouting/VOQ number recording
 */
void conweave_history_print() {
    // Conweave params
    std::cout << "\n------ConWeave parameters-----" << std::endl;
    std::cout << "Param - extraReplyDeadline:" << conweave_extraReplyDeadline << std::endl;
    std::cout << "Param - extraVOQFlushTime:" << conweave_extraVOQFlushTime << std::endl;
    std::cout << "Param - txExpiryTime:" << conweave_txExpiryTime << std::endl;
    std::cout << "Param - defaultVOQWaitingTime:" << conweave_defaultVOQWaitingTime << std::endl;
    std::cout << "Param - pathPauseTime:" << conweave_pathPauseTime << std::endl;
    std::cout << "Param - pathAwareRerouting:" << conweave_pathAwareRerouting << std::endl;

    std::cout << "\n------------ConWeave History---------------" << std::endl;
    std::cout << "Number of INIT's Reply sent (RTT_REPLY):" << ConWeaveRouting::m_nReplyInitSent
              << "\nNumber of Timely RTT_REPLY (INIT's Reply):" << ConWeaveRouting::m_nTimelyInitReplied
              << "\nNumber of TAIL's Reply Sent (CLEAR):" << ConWeaveRouting::m_nReplyTailSent
              << "\nNumber of Timely CLEAR (TAIL's Reply):" << ConWeaveRouting::m_nTimelyTailReplied
              << "\nNumber of NOTIFY Sent:" << ConWeaveRouting::m_nNotifySent
              << "\nNumber of Rerouting:" << ConWeaveRouting::m_nReRoute
              << "\nNumber of OoO enqueued pkts:" << ConWeaveRouting::m_nOutOfOrderPkts
              << "\nNumber of VOQ Flush Total:" << ConWeaveRouting::m_nFlushVOQTotal
              << "\nNumber of VOQ Flush From History:" << ConWeaveRouting::m_historyVOQSize.size()
              << "\nNumber of VOQ Flush by TAIL:" << ConWeaveRouting::m_nFlushVOQByTail
              << std::endl;

    std::cout << "--------------------------" << std::endl;

    /** VOQ: Sanity check*/
    for (size_t ToRId = 0; ToRId < Settings::node_num; ToRId++) {
        Ptr<Node> node = n.Get(ToRId);
        if (node->GetNodeType() == 1) {  // switches
            auto swNode = DynamicCast<SwitchNode>(n.Get(ToRId));
            if (swNode->m_isToR) {  // TOR switch
                uint32_t num_remained_voq = swNode->m_mmu->m_conweaveRouting.GetNumVOQ();
                if (num_remained_voq > 0) {
                    printf("*******************************\n");
                    printf("*** WARNING - Tor Sw (%lu) - VOQ (num=%u) is not flushed yet!! ***\n",
                           ToRId, num_remained_voq);
                    printf(
                        " -- Probably the history print is too early so simulation might not be "
                        "finished?");
                    printf("********************************\n");
                }
            }
        }
    }

    /** Get ConWeave Flush Time Estimation Error */
    if (0) {
        // sanity check - extraVOQFlushTime must be large enough to get accuracy
        assert(conweave_extraVOQFlushTime >= MicroSeconds(128) && "PARAMETER ERROR!!");

        std::cout << "\n--------------------------" << std::endl;
        std::cout << "Extracting ConWeave Estimation Error Data..." << std::endl;
        est_error_output = fopen(est_error_output_file.c_str(), "w");
        for (auto x : ConWeaveVOQ::m_flushEstErrorhistory) {
            fprintf(est_error_output, "%d\n", x);
        }
        ConWeaveVOQ::m_flushEstErrorhistory.clear();
        std::cout << "---------D O N E---------" << std::endl;
    }
}

/**
 * @brief When one RDMA is finished, so does (1) QP, (2) RxQP, (3) write it on file fct.txt.
 */
void qp_finish(FILE *fout, Ptr<RdmaQueuePair> q) {
    if (ws31::StartMode(lb_mode)) {
        const uint64_t demand=q->startTime.GetNanoSeconds();
        const uint64_t finish=Simulator::Now().GetNanoSeconds();
        if (finish<demand || finish-demand<q->m_ws31LaunchDelayNs)
            NS_FATAL_ERROR("C2 completion precedes demand or launch");
        ws31::StartCounters &s=ws31::StartData();
        ++s.finished; s.finishBytes+=q->m_size;
        if (Ws30Level() || ws31_native_declarations_seen)
            std::cout << "WS31_C2_FINISH flow_id=" << q->m_flow_id
                      << " demand_ns=" << demand << " launch_ns=" << demand+q->m_ws31LaunchDelayNs
                      << " finish_ns=" << finish << " wait_ns=" << q->m_ws31LaunchDelayNs
                      << " fct_ns=" << finish-demand << " size=" << q->m_size << std::endl;
    }
    uint32_t sid = Settings::ip_to_node_id(q->sip), did = Settings::ip_to_node_id(q->dip);
    uint64_t base_rtt = pairRtt[n.Get(sid)][n.Get(did)];
    uint64_t b = pairBw[n.Get(sid)][n.Get(did)];
    uint32_t total_bytes =
        q->m_size + ((q->m_size - 1) / packet_payload_size + 1) *
                        (CustomHeader::GetStaticWholeHeaderSize() -
                         IntHeader::GetStaticSize());  // translate to the minimum bytes required
                                                       // (with header but no INT)
    uint64_t standalone_fct = base_rtt + total_bytes * 8000000000lu / b;

    // XXX: remove rxQP from the receiver
    Ptr<Node> dstNode = n.Get(did);
    Ptr<RdmaDriver> rdma = dstNode->GetObject<RdmaDriver>();
    rdma->m_rdma->DeleteRxQp(q->sip.Get(), q->sport, q->dport, q->m_pg,
                            Ws30V13Life() >= 3 || lb_mode == 57 ? q->m_flow_id : -1);
    if (Ws30V13Life() == 4 && q->m_ws30Serial) {
        // Only after this request's cumulative ACK, with 100 us before reuse.
        // This is an explicit test intervention, not a timeout eviction policy.
        for (uint32_t i=0; i<n.GetN(); ++i) {
            Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
            if (sw) sw->ResetWs30V13Tuple(q->sip.Get(),q->dip.Get(),q->sport,q->dport);
        }
    }

    // fprintf(fout, "%lu QP complete\n", Simulator::Now().GetTimeStep());
    fprintf(fout, "%u %u %u %u %lu %lu %lu %lu\n", Settings::ip_to_node_id(q->sip),
            Settings::ip_to_node_id(q->dip), q->sport, q->dport, q->m_size,
            q->startTime.GetTimeStep(), (Simulator::Now() - q->startTime).GetTimeStep(),
            standalone_fct);
    if (lb_mode == 20) {
        NS_ASSERT_MSG(q->m_flow_id >= 0 && uint32_t(q->m_flow_id) < ws18_flows.size(),
                      "WS-18 completion has no input ID");
        Ws18Flow &flow = ws18_flows.at(q->m_flow_id);
        const uint64_t finish = Simulator::Now().GetNanoSeconds();
        NS_ASSERT_MSG(flow.released && !flow.finished && flow.src == sid && flow.dst == did &&
                          flow.sport == q->sport && flow.dport == q->dport &&
                          flow.bytes == q->m_size &&
                          flow.demand_ns <= flow.release_ns && flow.release_ns <= finish &&
                          q->startTime.GetNanoSeconds() == flow.release_ns,
                      "WS-18 completion violates identity, bytes, or time ordering");
        flow.finished = true;
        fprintf(ws18_output, "%u %u %u %u %u %u %u %lu %lu %lu %lu %lu\n",
                uint32_t(q->m_flow_id), flow.src, flow.dst, flow.sport, flow.dport,
                flow.tag, flow.bytes, flow.demand_ns, flow.release_ns, finish,
                flow.release_ns - flow.demand_ns, finish - flow.demand_ns);
        fflush(ws18_output);
    }

    // for debugging
    NS_LOG_DEBUG("%u %u %u %u %lu %lu %lu %lu\n" %
                 (Settings::ip_to_node_id(q->sip), Settings::ip_to_node_id(q->dip), q->sport,
                  q->dport, q->m_size, q->startTime.GetTimeStep(),
                  (Simulator::Now() - q->startTime).GetTimeStep(), standalone_fct));
    Settings::cnt_finished_flows++;
    fflush(fout);
}

/**
 * @brief PFC event logging
 */
void get_pfc(FILE *fout, Ptr<QbbNetDevice> dev, uint32_t type) {
    // time, nodeID, nodeType, Interface's Idx, 0:resume, 1:pause
    fprintf(fout, "%lu %u %u %u %u\n", Simulator::Now().GetTimeStep(), dev->GetNode()->GetId(),
            dev->GetNode()->GetNodeType(), dev->GetIfIndex(), type);
}

/*******************************************************************/
#if (false)

/**
 * @brief Qlen monitoring at switches (output: qlen.txt), I think "periodically"...
 *
 */
struct QlenDistribution {
    vector<uint32_t> cnt;  // cnt[i] is the number of times that the queue len is i KB
    void add(uint32_t qlen) {
        uint32_t kb = qlen / 1000;
        if (cnt.size() < kb + 1) cnt.resize(kb + 1);
        cnt[kb]++;
    }
};

map<uint32_t, map<uint32_t, QlenDistribution>> queue_result;
void monitor_buffer(FILE *qlen_output, NodeContainer *n) {
    /*******************************************************************/
    /************************** UNUSED NOW *****************************/
    /*******************************************************************/
    for (uint32_t i = 0; i < n->GetN(); i++) {
        if (n->Get(i)->GetNodeType() == 1) {  // is switch
            Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n->Get(i));
            if (queue_result.find(i) == queue_result.end()) queue_result[i];
            for (uint32_t j = 1; j < sw->GetNDevices(); j++) {
                uint32_t size = 0;
                for (uint32_t k = 0; k < SwitchMmu::qCnt; k++)
                    size += sw->m_mmu->egress_bytes[j][k];
                queue_result[i][j].add(size);
            }
        }
    }
    if (Simulator::Now().GetTimeStep() % qlen_dump_interval == 0) {
        fprintf(qlen_output, "time: %lu\n", Simulator::Now().GetTimeStep());
        for (auto &it0 : queue_result) {
            for (auto &it1 : it0.second) {
                fprintf(qlen_output, "%u %u", it0.first, it1.first);
                auto &dist = it1.second.cnt;
                for (uint32_t i = 0; i < dist.size(); i++) fprintf(qlen_output, " %u", dist[i]);
                fprintf(qlen_output, "\n");
            }
        }
        fflush(qlen_output);
    }
    if (Simulator::Now().GetTimeStep() < qlen_mon_end)
        Simulator::Schedule(NanoSeconds(qlen_mon_interval), &monitor_buffer, qlen_output, n);
}
#endif
/*******************************************************************/

/**
 * @brief Stop simulation in the middle (when almost all flows are done).
 * This function allows to finish simulation quickly when all messages are sent.
 */
void stop_simulation_middle() {
    uint32_t target_flow_num = flow_num - 0;  // can be lower than flownum
    if (Settings::cnt_finished_flows >= target_flow_num) {
        std::cout << "\n*** Simulator is enforced to be finished, finished so far: "
                  << Settings::cnt_finished_flows << "/ total: " << target_flow_num
                  << ", Time:" << Simulator::Now() << std::endl;

        // schedule conga timeout monitor
        if (lb_mode == 3) {  // CONGA
            conga_history_print();
        }
        if (lb_mode == 6) {  // LETFLOW
            letflow_history_print();
        }
        if (lb_mode == 9) {  // CONWEAVE
            conweave_history_print();
        }
        Simulator::Stop(NanoSeconds(1));  // finish soon, stop this schedule (NECESSARY!)
        return;
    }

    Simulator::Schedule(MicroSeconds(100), &stop_simulation_middle);  // check every 100us
}

/**
 * @brief Calculate edge-to-edge delays, TX delays, and bandwidths
 */
void CalculateRoute(Ptr<Node> host) {
    // queue for the BFS.
    vector<Ptr<Node>> q;
    // Distance from the host to each node.
    map<Ptr<Node>, int> dis;
    map<Ptr<Node>, uint64_t> delay;
    map<Ptr<Node>, uint64_t> txDelay;
    map<Ptr<Node>, uint64_t> bw;
    // init BFS.
    q.push_back(host);
    dis[host] = 0;
    delay[host] = 0;
    txDelay[host] = 0;
    bw[host] = 0xfffffffffffffffflu;

    // BFS.
    for (int i = 0; i < (int)q.size(); i++) {
        Ptr<Node> now = q[i];
        int d = dis[now];
        for (auto it = nbr2if[now].begin(); it != nbr2if[now].end(); it++) {
            // skip down link
            if (!it->second.up) continue;
            Ptr<Node> next = it->first;
            // If 'next' have not been visited.
            if (dis.find(next) == dis.end()) {
                dis[next] = d + 1;
                delay[next] = delay[now] + it->second.delay;  // maybe nanoseconds?
                txDelay[next] = txDelay[now] + packet_payload_size * 1000000000lu * 8 /
                                                   it->second.bw;  // maybe nanoseconds?
                bw[next] = std::min(bw[now], it->second.bw);
                // we only enqueue switch, because we do not want packets to go through host as
                // middle point
                if (next->GetNodeType() == 1) {
                    q.push_back(next);
                }
            }
            // if 'now' is on the shortest path from 'next' to 'host'.
            if (d + 1 == dis[next]) {
                // The state fixture has unequal delays on equal-hop routes.
                // Bound every such route, rather than keeping the first BFS
                // discovery's timing. All other topologies retain legacy metrics.
                if (Ws30V14Enabled() && topology_file == "config/ws30v14_state8.txt") {
                    delay[next] = std::max(delay[next], delay[now] + it->second.delay);
                    txDelay[next] = std::max(txDelay[next], txDelay[now] +
                        packet_payload_size * 1000000000lu * 8 / it->second.bw);
                    bw[next] = std::min(bw[next], std::min(bw[now], it->second.bw));
                }
                nextHop[next][host].push_back(now);
            }
        }
    }
    for (auto it : delay) {
        pairDelay[it.first][host] = it.second;
    }
    for (auto it : txDelay) {
        pairTxDelay[it.first][host] = it.second;
    }
    for (auto it : bw) {
        pairBw[it.first][host] = it.second;
    }
}
void CalculateRoutes(NodeContainer &n) {
    for (int i = 0; i < (int)n.GetN(); i++) {
        Ptr<Node> node = n.Get(i);
        if (node->GetNodeType() == 0) {
            CalculateRoute(node);
        }
    }
}

/**
 * @brief Set the Routing Entries object
 */
void SetRoutingEntries() {
    // For each node.
    for (auto i = nextHop.begin(); i != nextHop.end(); i++) {
        Ptr<Node> node = i->first;
        auto &table = i->second;
        for (auto j = table.begin(); j != table.end(); j++) {
            // The destination node.
            Ptr<Node> dst = j->first;
            // The IP address of the dst.
            Ipv4Address dstAddr = dst->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
            // The next hops towards the dst.
            vector<Ptr<Node>> nexts = j->second;
            for (int k = 0; k < (int)nexts.size(); k++) {
                Ptr<Node> next = nexts[k];
                uint32_t interface = nbr2if[node][next].idx;
                if (node->GetNodeType() == 1)
                    DynamicCast<SwitchNode>(node)->AddTableEntry(dstAddr, interface);
                else {
                    node->GetObject<RdmaDriver>()->m_rdma->AddTableEntry(dstAddr, interface);
                }
            }
        }
    }
}
// Enumerate the existing shortest-path DAG only for offline path identity.
// No switch uses this table when deciding an output port.
void BuildWs21IngressMapping() {
    uint64_t pathEnds = 0;
    uint64_t unreachablePairs = 0;
    for (uint32_t hostId = 0; hostId < n.GetN(); ++hostId) {
        Ptr<Node> host = n.Get(hostId);
        if (host->GetNodeType() != 0) continue;
        const uint32_t hostIp = serverAddress.at(hostId).Get();
        auto dstEntry = Settings::hostIp2SwitchId.find(hostIp);
        if (dstEntry == Settings::hostIp2SwitchId.end())
            NS_FATAL_ERROR("WS-21 host has no ToR mapping: host=" << hostId);
        const uint32_t destinationId = dstEntry->second;
        auto destinationEntry = idxNodeToR.find(destinationId);
        if (destinationEntry == idxNodeToR.end())
            NS_FATAL_ERROR("WS-21 destination is not a ToR: host=" << hostId
                           << " tor=" << destinationId);
        Ptr<SwitchNode> destination = destinationEntry->second;
        for (const auto &source : idxNodeToR) {
            if (source.first == destinationId) continue;
            Ptr<SwitchNode> sourceTor = source.second;
            Ptr<Node> sourceNode = sourceTor;
            auto sourceRoutes = nextHop.find(sourceNode);
            if (sourceRoutes == nextHop.end())
                NS_FATAL_ERROR("WS-21 source ToR has no route table: host=" << hostId
                               << " source=" << source.first);
            auto destinationRoute = sourceRoutes->second.find(host);
            if (destinationRoute == sourceRoutes->second.end()) {
                ++unreachablePairs;
                continue;
            }
            const auto &firstHops = destinationRoute->second;
            if (firstHops.empty())
                NS_FATAL_ERROR("WS-21 source has an empty route to host=" << hostId
                               << " source=" << source.first << " destination="
                               << destinationId);
            for (Ptr<Node> first : firstHops) {
                const uint64_t before = pathEnds;
                auto sourcePorts = nbr2if.find(sourceNode);
                if (sourcePorts == nbr2if.end() || !sourcePorts->second.count(first))
                    NS_FATAL_ERROR("WS-21 source first-hop port missing: host=" << hostId
                                   << " source=" << source.first);
                const uint32_t firstPort = sourcePorts->second.find(first)->second.idx;
                std::vector<Ptr<Node>> pending(1, first);
                std::set<Ptr<Node>> visited;
                if (first == destination) {
                    auto destinationPorts = nbr2if.find(destination);
                    if (destinationPorts == nbr2if.end() ||
                        !destinationPorts->second.count(sourceNode))
                        NS_FATAL_ERROR("WS-21 direct destination ingress missing: host="
                                       << hostId);
                    const uint32_t ingress =
                        destinationPorts->second.find(sourceNode)->second.idx;
                    if (!destination->AddWs21IngressMapping(source.first, ingress, firstPort))
                        NS_FATAL_ERROR("WS-21 ambiguous ingress to first-port mapping");
                    ++pathEnds;
                }
                while (!pending.empty()) {
                    Ptr<Node> current = pending.back();
                    pending.pop_back();
                    if (!visited.insert(current).second) continue;
                    if (current == destination) continue;
                    auto currentRoutes = nextHop.find(current);
                    if (currentRoutes == nextHop.end())
                        NS_FATAL_ERROR("WS-21 path switch has no route table: host=" << hostId
                                       << " switch=" << current->GetId());
                    auto currentRoute = currentRoutes->second.find(host);
                    if (currentRoute == currentRoutes->second.end())
                        NS_FATAL_ERROR("WS-21 path switch has no route to host=" << hostId
                                       << " switch=" << current->GetId());
                    for (Ptr<Node> next : currentRoute->second) {
                        if (next == destination) {
                            auto destinationPorts = nbr2if.find(destination);
                            if (destinationPorts == nbr2if.end() ||
                                !destinationPorts->second.count(current))
                                NS_FATAL_ERROR("WS-21 destination ingress port missing: host="
                                               << hostId << " destination=" << destinationId);
                            const uint32_t ingress =
                                destinationPorts->second.find(current)->second.idx;
                            if (!destination->AddWs21IngressMapping(source.first, ingress,
                                                                    firstPort))
                                NS_FATAL_ERROR("WS-21 ambiguous ingress to first-port mapping");
                            ++pathEnds;
                        } else if (next->GetNodeType() == 1) {
                            pending.push_back(next);
                        }
                    }
                }
                if (pathEnds <= before)
                    NS_FATAL_ERROR("WS-21 first hop never reached destination ToR: host="
                                   << hostId << " source=" << source.first);
            }
        }
    }
    if (pathEnds == 0)
        NS_FATAL_ERROR("WS-21 mapping has no cross-ToR paths");
    std::cout << "WS21_MAPPING path_ends=" << pathEnds
              << " unreachable_pairs=" << unreachablePairs << std::endl;
}

void BuildWs31OfanGroups() {
    std::set<uint32_t> switches;
    for (uint32_t i=0; i<n.GetN(); ++i)
        if (n.Get(i)->GetNodeType()==1) switches.insert(i);
    uint64_t mappings=0, edgeMappings=0, aggregationMappings=0;
    for (uint32_t h=0; h<n.GetN(); ++h) {
        Ptr<Node> host=n.Get(h);
        if (host->GetNodeType()!=0) continue;
        const uint32_t ip=serverAddress.at(h).Get();
        auto tor=Settings::hostIp2SwitchId.find(ip);
        if (tor==Settings::hostIp2SwitchId.end()) NS_FATAL_ERROR("Ofan host lacks ToR mapping");
        std::map<uint32_t,std::vector<uint32_t> > dag;
        for (const auto &row : nextHop) {
            if (row.first->GetNodeType()!=1) continue;
            auto route=row.second.find(host);
            if (route==row.second.end()) continue;
            for (Ptr<Node> v : route->second) dag[row.first->GetId()].push_back(v->GetId());
        }
        std::map<uint32_t,uint32_t> groups;
        try { groups=ws31::OfanMandatoryGroups(dag,h,switches); }
        catch (const std::exception &e) { NS_FATAL_ERROR("Ofan grouping host=" << h << ": " << e.what()); }
        for (const auto &g : groups) {
            Ptr<SwitchNode> sw=DynamicCast<SwitchNode>(n.Get(g.first));
            if (sw->m_isToR) {
                if (g.second!=tor->second) NS_FATAL_ERROR("Ofan source edge mandatory group is not destination edge");
                ++edgeMappings;
            } else {
                auto neighbors=nbr2if.find(n.Get(g.second));
                if (neighbors==nbr2if.end() || !neighbors->second.count(n.Get(tor->second)))
                    NS_FATAL_ERROR("Ofan aggregation mandatory group is not adjacent to destination edge");
                ++aggregationMappings;
            }
            std::vector<uint32_t> ports; uint64_t rate=0;
            for (uint32_t v : dag.at(g.first)) {
                const uint32_t port=nbr2if.at(n.Get(g.first)).at(n.Get(v)).idx;
                const uint64_t r=DynamicCast<QbbNetDevice>(sw->GetDevice(port))->GetDataRate().GetBitRate();
                if (rate && rate!=r) NS_FATAL_ERROR("Ofan v2 static port requires equal-rate next hops");
                rate=r; ports.push_back(port);
            }
            sw->AddWs31OfanDestination(ip,g.second,ports); ++mappings;
        }
    }
    if (!mappings) NS_FATAL_ERROR("Ofan topology has no multipath destination groups");
    std::cout << "WS31_OFAN_MAPPING mappings=" << mappings << " edge=" << edgeMappings
              << " aggregation=" << aggregationMappings << " verified_mandatory=1" << std::endl;
}

void Ws23InjectPfc(Ptr<QbbNetDevice> switchPort, uint32_t hostId,
                   uint32_t pg, uint32_t type) {
    uint32_t pauseUs = switchPort->SendPfc(pg, type);
    std::cout << "WS23_PFC_INJECT time_ns=" << Simulator::Now().GetNanoSeconds()
              << " host=" << hostId << " pg=" << pg << " type=" << type
              << " pause_us=" << pauseUs << std::endl;
}

/**
 * @brief take down the link between a and b, and redo the routing
 */
void TakeDownLink(NodeContainer n, Ptr<Node> a, Ptr<Node> b) {
    if (Settings::lb_mode==51 || Settings::lb_mode==52)
        NS_FATAL_ERROR("Ofan static equal-path port does not implement failures/IWRR");
    if (!nbr2if[a][b].up) return;
    // take down link between a and b
    nbr2if[a][b].up = nbr2if[b][a].up = false;
    nextHop.clear();
    CalculateRoutes(n);
    // clear routing tables
    for (uint32_t i = 0; i < n.GetN(); i++) {
        if (n.Get(i)->GetNodeType() == 1)
            DynamicCast<SwitchNode>(n.Get(i))->ClearTable();
        else
            n.Get(i)->GetObject<RdmaDriver>()->m_rdma->ClearTable();
    }
    DynamicCast<QbbNetDevice>(a->GetDevice(nbr2if[a][b].idx))->TakeDown();
    DynamicCast<QbbNetDevice>(b->GetDevice(nbr2if[b][a].idx))->TakeDown();
    // reset routing table
    SetRoutingEntries();

    // redistribute qp on each host
    for (uint32_t i = 0; i < n.GetN(); i++) {
        if (n.Get(i)->GetNodeType() == 0)
            n.Get(i)->GetObject<RdmaDriver>()->m_rdma->RedistributeQp();
    }
}

uint64_t get_nic_rate(NodeContainer &n) {
    uint64_t avg_nic_rate;
    uint64_t n_servers = 0;
    for (uint32_t i = 0; i < n.GetN(); i++) {
        if (n.Get(i)->GetNodeType() == 0) {
            avg_nic_rate +=
                DynamicCast<QbbNetDevice>(n.Get(i)->GetDevice(1))->GetDataRate().GetBitRate();
            n_servers += 1;
        }
    }
    return avg_nic_rate / n_servers;
}

/************************************************************************/
//                                                                      //
//                                M A I N                               //
//                                                                      //
/************************************************************************/

// WS31_NATIVE_OS2_BEGIN: default-off entry and read-only device observations.
namespace {
bool Ws31NativeRequested() {
    return ws31_native_declarations_seen || ws31_native_output_seen;
}
void Ws31NativeNeed(bool ok, const std::string &message) {
    if (!ok) throw std::logic_error("WS31_NATIVE_OS2 " + message);
}
void Ws31NativeValidate() {
    Ws31NativeNeed(ws31_native_declarations_seen && ws31_native_output_seen &&
        !ws31_native_declarations.empty() && !ws31_native_output_prefix.empty(),
        "both native keys are required");
    const bool c1Mode=lb_mode==36 || lb_mode==37 || lb_mode==38 ||
        lb_mode==42 || lb_mode==53 || lb_mode==54;
    const bool c2Mode=lb_mode==43 || lb_mode==44 || lb_mode==46 ||
        lb_mode==55 || lb_mode==56;
    Ws31NativeNeed((lb_mode==33 || c1Mode || c2Mode) && cc_mode==1 && !enable_irn &&
        packet_payload_size==1000 && has_win==0 && global_t==1,
        "unsupported native mode/transport/window");
    Ws31NativeNeed(!ws18_admission && !ws18_path && !ws21_identity &&
        !ws21_feedback && !ws21_heartbeat && !ws21_port_events &&
        !ws21_heartbeat_fault_mode && !ws21_heartbeat_fault_tor &&
        !ws21_heartbeat_fault_port && !ws21_heartbeat_fault_start_ns &&
        !ws21_heartbeat_fault_end_ns && ws23_pfc_probe_host<0 &&
        !ws23_pfc_probe_start_ns && !ws23_pfc_probe_end_ns && !link_down_time &&
        error_rate_per_link==0.0, "legacy diagnostic or fault enabled");
    const char *keys[]={"WS30_OBSERVE","WS30_COMPOSITION","WS30_LIFECYCLE",
        "WS30_LIFE_PROFILE","WS30_TAG_TRANSFORM","WS31_LABEL_PROFILE",
        "WS13_DIAG","WS25_DIAG","WS28_TAIL_DIAG","IRN_PFC_DROP_DIAG",
        "WS23_RECOVERY_DIAG","WS26_MOE_HOP_DIAG","WS26_QUEUE_FRONT_DIAG",
        "WS26_TIME_PROBE","WS26_SEED97_TIME_DIAG"};
    for (const char *key:keys) {
        const char *value=std::getenv(key);
        Ws31NativeNeed(!value || !*value || std::string(value)=="0",
            std::string("conflicting environment ")+key);
    }
}

class Ws31NativeObserver {
public:
    enum Output { MAP, PACKETS, ARRIVALS, TERMINAL, CLEANUP, ERRORS, SOURCE, OUTPUTS };
    struct Device {
        Ws31NativeObserver *owner=nullptr;
        Ptr<QbbNetDevice> dev;
        uint32_t node=0, index=0, peer=0, peerIndex=0;
        int32_t ipv4Interface=-1;
        bool host=false, dequeueConnected=false, dropConnected=false, dataConnected=false;
        uint64_t dequeues=0, dequeueBytes=0, drops=0, dropBytes=0, data=0, dataBytes=0;
        Callback<void,Ptr<const Packet>,uint32_t> dequeue, drop;
        Callback<void,Ptr<const Packet>,Ptr<RdmaQueuePair>> qp;
    };
    struct Parsed {
        bool ok=false;
        std::string error, kind="MALFORMED", raw;
        int64_t protocol=-1, sip=-1, dip=-1, sport=-1, dport=-1, pg=-1;
        int64_t seq=-1, cnp=-1, header=-1, payload=-1, ipPayload=-1, udpLength=-1;
        int64_t padding=-1, pause=-1, qlen=-1;
    };
    struct SourceSwitch {
        Ws31NativeObserver *owner=nullptr;
        Ptr<SwitchNode> node;
        bool connected=false;
        Callback<void,Ptr<const Packet>,const SwitchNode::Ws31SourceDecision &> callback;
    };
private:
    FILE *files[OUTPUTS]={};
    uint64_t bytes=0, sequence=0, copiedBytes=0, sealedSequence=0;
    bool sealed=false;
    uint64_t sourceSequence=0;
    std::string firstError;
    std::vector<std::unique_ptr<Device>> devices;
    std::vector<std::unique_ptr<SourceSwitch>> sourceSwitches;
    static uint16_t U16(const uint8_t *p) { return uint16_t((uint16_t(p[0])<<8)|p[1]); }
    void Write(Output file,const std::string &text) {
        const uint64_t cap=512ULL*1024*1024;
        Ws31NativeNeed(files[file]!=nullptr,"output not open");
        Ws31NativeNeed(text.size()<=cap && bytes<=cap-text.size(),"output byte cap reached");
        Ws31NativeNeed(std::fwrite(text.data(),1,text.size(),files[file])==text.size(),"output write failed");
        bytes+=text.size();
    }
    static Parsed Bad(Parsed r,const std::string &why,const std::vector<uint8_t> &raw) {
        r.error=why;
        static const char hex[]="0123456789abcdef";
        r.raw.reserve(raw.size()*2);
        for (uint8_t b:raw) { r.raw.push_back(hex[b>>4]); r.raw.push_back(hex[b&15]); }
        return r;
    }
    Parsed Parse(Ptr<const Packet> packet) {
        Parsed r;
        if (!packet) { r.error="null packet"; return r; }
        const uint32_t size=packet->GetSize();
        // The bounded prefix is still retained when even IPv4's maximum is exceeded.
        std::vector<uint8_t> raw(std::min(size,uint32_t(65549)));
        if (!raw.empty()) {
            Ws31NativeNeed(packet->CopyData(raw.data(),raw.size())==raw.size(),"CopyData length mismatch");
            copiedBytes+=raw.size();
        }
        if (size>65549 || size<34) return Bad(r,"PPP/IPv4 length outside bounds",raw);
        if (U16(raw.data())!=0x0021) return Bad(r,"unsupported PPP protocol",raw);
        const uint8_t *ip=raw.data()+14;
        if ((ip[0]>>4)!=4 || (ip[0]&15)!=5)
            return Bad(r,"unsupported IPv4 version/IHL",raw);
        const uint16_t total=U16(ip+2);
        if (total<20 || uint32_t(total)!=size-14 || (U16(ip+6)&0x3fff))
            return Bad(r,"IPv4 total length/fragment mismatch",raw);
        Ptr<Packet> copy=packet->Copy();
        PppHeader ppp;
        if (copy->RemoveHeader(ppp)!=14 || ppp.GetProtocol()!=0x0021)
            return Bad(r,"actual PPP consumption mismatch",raw);
        Ipv4Header ipv4;
        if (copy->GetSize()<20 || copy->RemoveHeader(ipv4)!=20 ||
            ipv4.GetPayloadSize()!=copy->GetSize())
            return Bad(r,"actual IPv4 consumption mismatch",raw);
        r.protocol=ipv4.GetProtocol(); r.sip=ipv4.GetSource().Get(); r.dip=ipv4.GetDestination().Get();
        r.ipPayload=copy->GetSize();
        if (r.protocol==0x11) {
            if (copy->GetSize()<14) return Bad(r,"short UDP/SeqTs",raw);
            uint8_t udpWire[8];
            if (copy->CopyData(udpWire,8)!=8) return Bad(r,"short UDP copy",raw);
            r.udpLength=U16(udpWire+4);
            if (r.udpLength<14 || r.udpLength!=r.ipPayload)
                return Bad(r,"UDP/IP length mismatch",raw);
            UdpHeader udp;
            if (copy->RemoveHeader(udp)!=8) return Bad(r,"UDP consumption mismatch",raw);
            if (IntHeader::mode!=5 || SeqTsHeader::GetHeaderSize()!=6 || copy->GetSize()<6)
                return Bad(r,"unsupported actual SeqTs mode/size",raw);
            SeqTsHeader seq;
            if (copy->RemoveHeader(seq)!=6) return Bad(r,"SeqTs consumption mismatch",raw);
            r.sport=udp.GetSourcePort(); r.dport=udp.GetDestinationPort();
            r.pg=seq.GetPG(); r.seq=seq.GetSeq(); r.payload=copy->GetSize();
            r.header=size-r.payload; r.padding=0; r.kind="DATA";
            if (r.header!=48 || r.payload<=0 || r.payload>1000 || r.pg!=3)
                return Bad(r,"native data framing/PG mismatch",raw);
        } else if (r.protocol==0xfc || r.protocol==0xfd) {
            qbbHeader ack;
            const uint32_t length=ack.GetSerializedSize();
            if (IntHeader::mode!=5 || length!=18 || copy->GetSize()<length)
                return Bad(r,"short/unsupported actual qbb header",raw);
            if (copy->RemoveHeader(ack)!=length) return Bad(r,"qbb consumption mismatch",raw);
            r.sport=ack.GetSport(); r.dport=ack.GetDport(); r.pg=ack.GetPG();
            r.seq=ack.GetSeq(); r.cnp=ack.GetCnp(); r.padding=copy->GetSize();
            r.header=14+20+length; r.payload=0;
            r.kind=r.protocol==0xfc?"ACK":"NACK";
            // IRN-only serialized fields are opaque; no zero-value/IRN assertion.
            if (r.padding!=std::max(60-14-20-int(length),0))
                return Bad(r,"control padding mismatch",raw);
        } else if (r.protocol==0xfe) {
            PauseHeader pause;
            if (copy->GetSize()<pause.GetSerializedSize()) return Bad(r,"short PFC",raw);
            const uint32_t length=pause.GetSerializedSize();
            if (copy->RemoveHeader(pause)!=length) return Bad(r,"PFC consumption mismatch",raw);
            r.pg=pause.GetQIndex(); r.pause=pause.GetTime(); r.qlen=pause.GetQLen();
            r.padding=copy->GetSize(); r.header=14+20+length; r.payload=0; r.kind="PFC";
        } else return Bad(r,"unexpected protocol retained",raw);
        r.ok=true;
        return r;
    }
    static void Data(Device *d,Ptr<const Packet> p,Ptr<RdmaQueuePair> qp) {
        d->owner->Observe(*d,"H-DATA",p,-1,qp);
    }
    static void Dequeue(Device *d,Ptr<const Packet> p,uint32_t queue) {
        d->owner->Observe(*d,d->host?"H-CONTROL":"S-EGRESS",p,queue,nullptr);
    }
    static void Drop(Device *d,Ptr<const Packet> p,uint32_t queue) {
        d->owner->Observe(*d,"DROP",p,queue,nullptr);
    }
    static void Source(SourceSwitch *context,Ptr<const Packet> packet,
                       const SwitchNode::Ws31SourceDecision &decision) {
        context->owner->ObserveSource(*context,packet,decision);
    }
    void ObserveSource(SourceSwitch &context,Ptr<const Packet> packet,
                       const SwitchNode::Ws31SourceDecision &decision) {
        Ws31NativeNeed(!sealed && sourceSequence<2000000,"source observation phase/row cap");
        const Parsed parsed=Parse(packet);
        Ws31NativeNeed(parsed.ok && parsed.protocol==0x11 &&
            context.node->m_isToR_hostIP.count(uint32_t(parsed.sip)),
            "source observation framing/owner mismatch");
        WorkloadTag label; FlowIDNUMTag flow;
        const bool hasLabel=packet->PeekPacketTag(label);
        const bool hasFlow=packet->PeekPacketTag(flow);
        std::ostringstream out;
        out<<++sourceSequence<<'\t'<<Simulator::Now().GetNanoSeconds()<<'\t'
           <<context.node->GetId()<<'\t'<<packet->GetUid()<<'\t'<<parsed.sip<<'\t'
           <<parsed.dip<<'\t'<<parsed.sport<<'\t'<<parsed.dport<<'\t'<<parsed.pg<<'\t'
           <<parsed.seq<<'\t'<<parsed.payload<<'\t'<<packet->GetSize()<<'\t'
           <<hasLabel<<'\t'<<(hasLabel?int64_t(label.GetValue()):-1)<<'\t'
           <<hasFlow<<'\t'<<(hasFlow?int64_t(flow.GetId()):-1)<<'\t'
           <<(hasFlow?int64_t(flow.GetFlowSize()):-1)<<'\t'
           <<decision.fresh<<'\t'<<decision.first<<'\t'<<decision.second<<'\t'
           <<decision.chosen<<'\t'<<(decision.fresh?int64_t(decision.q1):-1)<<'\t'
           <<(decision.fresh?int64_t(decision.q2):-1)<<'\t'
           <<(decision.fresh?int64_t(decision.r1):-1)<<'\t'
           <<(decision.fresh?int64_t(decision.r2):-1)<<'\t'
           <<(decision.fresh?int64_t(decision.predicted):-1)<<'\n';
        Write(SOURCE,out.str());
    }
    void Observe(Device &d,const char *point,Ptr<const Packet> packet,int64_t queue,Ptr<RdmaQueuePair> qp) {
        Ws31NativeNeed(sequence<2000000,"packet row cap reached");
        ++sequence;
        Parsed r=Parse(packet);
        const uint64_t size=packet?packet->GetSize():0;
        if (std::string(point)=="DROP") { ++d.drops; d.dropBytes+=size; }
        else if (std::string(point)=="H-DATA") { ++d.data; d.dataBytes+=size; }
        else { ++d.dequeues; d.dequeueBytes+=size; }
        bool qpOK=true;
        if (std::string(point)=="H-DATA") {
            qpOK=qp && r.ok && r.protocol==0x11 && qp->sip.Get()==uint32_t(r.sip) &&
                qp->dip.Get()==uint32_t(r.dip) && qp->sport==r.sport && qp->dport==r.dport &&
                qp->m_pg==r.pg && r.seq>=0 && uint64_t(r.seq)+uint64_t(r.payload)<=qp->m_size &&
                qp->startTime.GetNanoSeconds()<=Simulator::Now().GetNanoSeconds();
        }
        WorkloadTag label; FlowIDNUMTag flow;
        const bool hasLabel=packet && packet->PeekPacketTag(label);
        const bool hasFlow=packet && packet->PeekPacketTag(flow);
        std::ostringstream out;
        out<<sequence<<'\t'<<Simulator::Now().GetNanoSeconds()<<'\t'<<point<<'\t'
           <<(sealed?"POST_SEAL":"RUN")<<'\t'<<d.node<<'\t'<<d.index<<'\t'
           <<d.ipv4Interface<<'\t'<<d.peer<<'\t'<<d.peerIndex<<'\t'<<queue<<'\t'
           <<(packet?int64_t(packet->GetUid()):-1)<<'\t'<<size<<'\t'<<r.protocol<<'\t'
           <<r.kind<<'\t'<<r.sip<<'\t'<<r.dip<<'\t'<<r.sport<<'\t'<<r.dport<<'\t'
           <<r.pg<<'\t'<<r.seq<<'\t'<<r.cnp<<'\t'<<r.header<<'\t'<<r.payload<<'\t'
           <<r.ipPayload<<'\t'<<r.udpLength<<'\t'<<r.padding<<'\t'<<r.pause<<'\t'<<r.qlen<<'\t'
           <<hasLabel<<'\t'<<(hasLabel?int64_t(label.GetValue()):-1)<<'\t'
           <<hasFlow<<'\t'<<(hasFlow?int64_t(flow.GetId()):-1)<<'\t'
           <<(hasFlow?int64_t(flow.GetFlowSize()):-1)<<'\t'
           <<(qp?int64_t(qp->m_flow_id):-1)<<'\t'<<(qp?int64_t(qp->m_size):-1)<<'\t'
           <<(qp?qp->startTime.GetNanoSeconds():-1)<<'\t'<<(qp?int64_t(qp->m_workload_tag):-1)<<'\t'
           <<(r.ok && qpOK?"PARSED":"MALFORMED")<<'\t'<<r.error<<'\t'<<r.raw<<'\n';
        Write(PACKETS,out.str());
        Ws31NativeNeed(r.ok && qpOK,r.ok?"current QP/header mismatch":r.error);
    }
public:
    void Open(const std::string &prefix) {
        const char *suffix[]={".map.tsv",".packets.tsv",".arrivals.tsv",".terminal.tsv",".cleanup.tsv",".errors.tsv",".source.tsv"};
        for (unsigned i=0;i<OUTPUTS;++i) {
            files[i]=std::fopen((prefix+suffix[i]).c_str(),"wx");
            Ws31NativeNeed(files[i]!=nullptr,std::string("cannot exclusively create ")+suffix[i]);
        }
        Write(MAP,"node\tdevice\tif_index\tipv4_interface\tpeer_node\tpeer_device\trate_bps\tdelay_ns\thost\n");
        Write(PACKETS,"event\ttime_ns\tpoint\twindow\tnode\tdevice\tipv4_interface\tpeer\tpeer_device\tqueue\tuid\tpacket_bytes\tprotocol\tkind\tsip\tdip\tsport\tdport\tpg\tseq_ack\tcnp_flag\theader_bytes\tapplication_payload\tip_payload\tudp_wire_length\tpadding\tpause_us\tpfc_qlen\tlabel_present\tlabel\tflow_tag_present\tflow_tag_id\tflow_tag_size\tqp_flow_id\tqp_size\tdemand_ns\tqp_original_tag\tparse_status\terror\traw_hex\n");
        Write(ARRIVALS,"ordinal\trequest_id\tactual_ns\tclient_created\tclient_started\n");
        Write(SOURCE,"event\ttime_ns\tswitch\tuid\tsip\tdip\tsport\tdport\tpg\tseq\tpayload\tpacket_bytes\tlabel_present\tpolicy_tag\tflow_tag_present\tflow_id\ttotal_size\tfresh\tfirst\tsecond\tchosen\tq1\tq2\tr1\tr2\tpredicted\n");
    }
    void Connect() {
        Ws31NativeNeed(n.GetN()==144 && Settings::host_num==128 && Settings::switch_num==16,
            "wrong actual OS2 node counts");
        for (uint32_t i=0;i<n.GetN();++i) {
            Ptr<Node> node=n.Get(i); uint32_t businessLinks=0;
            auto sw=DynamicCast<SwitchNode>(node);
            if (sw) {
                std::unique_ptr<SourceSwitch> source(new SourceSwitch());
                source->owner=this; source->node=sw;
                SourceSwitch *context=source.get();
                sourceSwitches.push_back(std::move(source));
                context->callback=MakeBoundCallback(&Ws31NativeObserver::Source,context);
                context->connected=sw->TraceConnectWithoutContext("Ws31SourceDecision",context->callback);
                Ws31NativeNeed(context->connected,"source observation connection failed");
            }
            for (uint32_t index=0;index<node->GetNDevices();++index) {
                auto dev=DynamicCast<QbbNetDevice>(node->GetDevice(index));
                if (!dev) continue;
                auto channel=DynamicCast<QbbChannel>(dev->GetChannel());
                Ws31NativeNeed(channel && channel->GetNDevices()==2 && dev->GetNode()==node &&
                    dev->GetIfIndex()==index,"invalid actual channel/device owner");
                Ptr<NetDevice> peer;
                for (uint32_t j=0;j<channel->GetNDevices();++j) {
                    auto candidate=channel->GetDevice(j);
                    if (candidate!=dev) { Ws31NativeNeed(!peer,"ambiguous peer"); peer=candidate; }
                }
                Ws31NativeNeed(peer && peer->GetNode(),"missing actual peer");
                Ptr<Node> other=peer->GetNode(); uint32_t peerIndex=other->GetNDevices();
                for (uint32_t j=0;j<other->GetNDevices();++j)
                    if (other->GetDevice(j)==peer) { Ws31NativeNeed(peerIndex==other->GetNDevices(),"duplicate peer device"); peerIndex=j; }
                auto outward=nbr2if.find(node), inward=nbr2if.find(other);
                Ws31NativeNeed(outward!=nbr2if.end() && inward!=nbr2if.end(),"missing adjacency owner");
                auto forward=outward->second.find(other), reverse=inward->second.find(node);
                auto peerQbb=DynamicCast<QbbNetDevice>(peer);
                Ws31NativeNeed(forward!=outward->second.end() && reverse!=inward->second.end() &&
                    forward->second.idx==index && reverse->second.idx==peerIndex &&
                    forward->second.up && reverse->second.up && peerQbb &&
                    forward->second.bw==dev->GetDataRate().GetBitRate() &&
                    reverse->second.bw==peerQbb->GetDataRate().GetBitRate() &&
                    forward->second.delay==uint64_t(channel->GetDelay().GetNanoSeconds()) &&
                    reverse->second.delay==forward->second.delay,"actual adjacency inconsistency");
                auto ipv4=node->GetObject<Ipv4>();
                Ws31NativeNeed(ipv4!=nullptr,"missing actual IPv4");
                int32_t iface=ipv4->GetInterfaceForDevice(dev);
                Ws31NativeNeed(iface>=0 && ipv4->GetNetDevice(iface)==dev && ipv4->IsUp(iface),
                    "actual IPv4/device association mismatch");
                const bool host=node->GetNodeType()==0;
                if (host) {
                    ++businessLinks;
                    Ws31NativeNeed(i<serverAddress.size() && other->GetNodeType()==1,"host peer/address missing");
                    uint32_t matches=0;
                    for (uint32_t a=0;a<ipv4->GetNAddresses(iface);++a)
                        matches+=ipv4->GetAddress(iface,a).GetLocal()==serverAddress[i];
                    auto tor=Settings::hostIp2SwitchId.find(serverAddress[i].Get());
                    Ws31NativeNeed(matches==1 && tor!=Settings::hostIp2SwitchId.end() &&
                        tor->second==other->GetId(),"business address/ToR mismatch");
                }
                std::unique_ptr<Device> context(new Device());
                context->owner=this; context->dev=dev; context->node=node->GetId(); context->index=index;
                context->peer=other->GetId(); context->peerIndex=peerIndex; context->ipv4Interface=iface; context->host=host;
                Device *d=context.get(); devices.push_back(std::move(context));
                std::ostringstream out;
                out<<d->node<<'\t'<<index<<'\t'<<dev->GetIfIndex()<<'\t'<<iface<<'\t'
                   <<d->peer<<'\t'<<peerIndex<<'\t'<<dev->GetDataRate().GetBitRate()<<'\t'
                   <<channel->GetDelay().GetNanoSeconds()<<'\t'<<host<<'\n';
                Write(MAP,out.str());
                d->dequeue=MakeBoundCallback(&Ws31NativeObserver::Dequeue,d);
                d->drop=MakeBoundCallback(&Ws31NativeObserver::Drop,d);
                d->dequeueConnected=dev->TraceConnectWithoutContext("QbbDequeue",d->dequeue);
                Ws31NativeNeed(d->dequeueConnected,"QbbDequeue connection failed");
                d->dropConnected=dev->TraceConnectWithoutContext("QbbDrop",d->drop);
                Ws31NativeNeed(d->dropConnected,"QbbDrop connection failed");
                if (host) {
                    d->qp=MakeBoundCallback(&Ws31NativeObserver::Data,d);
                    d->dataConnected=dev->TraceConnectWithoutContext("RdmaQpDequeue",d->qp);
                    Ws31NativeNeed(d->dataConnected,"RdmaQpDequeue connection failed");
                }
            }
            if (node->GetNodeType()==0) Ws31NativeNeed(businessLinks==1,"ambiguous business host link");
        }
        Ws31NativeNeed(devices.size()==384,"actual directed device count mismatch");
    }
    void Remember(const std::string &error) {
        if (firstError.empty()) firstError=error;
        std::cerr<<"WS31_NATIVE_OS2_ERROR "<<error<<std::endl;
        try { if (files[ERRORS]) Write(ERRORS,error+"\n"); } catch (...) {}
    }
    bool Failed() const { return !firstError.empty(); }
    long OriginalBoundary(const char *phase,FILE *file) {
        if (!file) return -1;
        Ws31NativeNeed(std::fflush(file)==0 && !std::ferror(file),"original output boundary flush failed");
        const long position=std::ftell(file);
        Ws31NativeNeed(position>=0,"original output boundary position failed");
        std::ostringstream row;
        row<<phase<<'\t'<<position<<'\n'; Write(CLEANUP,row.str());
        return position;
    }
    void Terminal(const Ws31V2NativeEntry::Diagnostics &d) {
        for (const auto &arrival:d.arrivals) {
            std::ostringstream out;
            out<<arrival.ordinal<<'\t'<<arrival.id<<'\t'<<arrival.actualNs<<'\t'
               <<arrival.clientCreated<<'\t'<<arrival.clientStarted<<'\n'; Write(ARRIVALS,out.str());
        }
        std::ostringstream out;
        out<<"entry_finished\t"<<d.entryFinished<<"\nentry_failed\t"<<d.failed
           <<"\ndeclared\t"<<d.declared<<"\nentered\t"<<d.entered<<"\nissued\t"<<d.issued
           <<"\ndemand_reads\t"<<d.demandReads<<"\nbindings\t"<<d.bindings
           <<"\npacket_reads\t"<<d.packetReads<<"\npending\t"<<d.pending<<"\nunentered\t"<<d.unentered
           <<"\ncancellations\t"<<d.cancellations<<"\nlive_qps\t"<<d.liveQPs
           <<"\nclients\t"<<d.clients<<"\ndeclaration_capacity\t"<<d.declarationCapacity
           <<"\nevent_capacity\t"<<d.eventCapacity<<"\nclient_capacity\t"<<d.clientCapacity
           <<"\nderived_session_retained_bound_qp_refs\t"<<d.bindings
           <<"\nretained_ref_evidence\tsource-derived bindings; not measured release or heap bytes"
           <<"\nobserved_packet_rows\t"<<sequence<<"\ncopied_bytes\t"<<copiedBytes
           <<"\noutput_bytes_at_terminal\t"<<bytes<<"\ndevice_contexts\t"<<devices.size()
            <<"\ndevice_vector_capacity\t"<<devices.capacity()<<"\ndevice_element_bytes\t"<<sizeof(Device)
            <<"\nsource_rows\t"<<sourceSequence<<"\nsource_switch_contexts\t"<<sourceSwitches.size()
            <<"\nsource_context_element_bytes\t"<<sizeof(SourceSwitch)<<'\n';
        Write(TERMINAL,out.str());
        for (const auto &device:devices) {
            const auto &v=*device; std::ostringstream row;
            row<<"device\t"<<v.node<<'\t'<<v.index<<'\t'<<(v.host?"HOST_CONTROL":"SWITCH_BYTE_HOP")
               <<'\t'<<v.dequeues<<'\t'<<v.dequeueBytes<<'\t'<<v.data<<'\t'<<v.dataBytes
               <<'\t'<<v.drops<<'\t'<<v.dropBytes<<'\n'; Write(TERMINAL,row.str());
        }
        for (const auto &source:sourceSwitches) source->node->WriteWs30V13State();
        for (uint32_t i=0;i<n.GetN();++i) if (n.Get(i)->GetNodeType()==0) {
            auto hw=n.Get(i)->GetObject<RdmaDriver>()->m_rdma; std::ostringstream row;
            row<<"host_maps\t"<<i<<'\t'<<hw->m_qpMap.size()<<'\t'<<hw->m_rxQpMap.size()
               <<'\t'<<hw->akashic_Qp.size()<<'\t'<<hw->akashic_RxQp.size()<<'\n'; Write(TERMINAL,row.str());
        }
    }
    void SealAndDisconnect() {
        sealed=true; sealedSequence=sequence;
        for (const auto &source:sourceSwitches) if (source->connected) {
            const bool ok=source->node->TraceDisconnectWithoutContext("Ws31SourceDecision",source->callback);
            if (!ok) Remember("source observation disconnect failed");
            source->connected=!ok;
        }
        for (const auto &context:devices) {
            auto &d=*context;
            if (d.dataConnected) {
                const bool ok=d.dev->TraceDisconnectWithoutContext("RdmaQpDequeue",d.qp);
                if (!ok) Remember("RdmaQpDequeue disconnect failed");
                d.dataConnected=!ok;
            }
            if (d.dequeueConnected) {
                const bool ok=d.dev->TraceDisconnectWithoutContext("QbbDequeue",d.dequeue);
                if (!ok) Remember("QbbDequeue disconnect failed");
                d.dequeueConnected=!ok;
            }
            if (d.dropConnected) {
                const bool ok=d.dev->TraceDisconnectWithoutContext("QbbDrop",d.drop);
                if (!ok) Remember("QbbDrop disconnect failed");
                d.dropConnected=!ok;
            }
            std::ostringstream row;
            row<<"disconnect\t"<<d.node<<'\t'<<d.index<<'\t'<<!d.dataConnected<<'\t'
               <<!d.dequeueConnected<<'\t'<<!d.dropConnected<<'\n';
            try { Write(CLEANUP,row.str()); } catch (const std::exception &e) { Remember(e.what()); }
        }
    }
    void Finish() {
        try {
            std::ostringstream out;
            out<<"sealed_sequence\t"<<sealedSequence<<"\nlast_sequence\t"<<sequence
               <<"\npost_seal_observations\t"<<(sequence-sealedSequence)
               <<"\noutput_bytes_before_close\t"<<bytes<<"\nfirst_error\t"<<firstError<<'\n';
            Write(CLEANUP,out.str());
            if (sequence!=sealedSequence) Remember("observations occurred after seal");
        } catch (const std::exception &e) { Remember(e.what()); }
        for (unsigned i=0;i<OUTPUTS;++i) if (files[i]) {
            FILE *file=files[i]; files[i]=nullptr;
            const bool flushFailed=std::fflush(file)!=0 || std::ferror(file);
            const bool closeFailed=std::fclose(file)!=0;
            if (flushFailed || closeFailed) Remember("native output flush/close failed");
        }
    }
};

int RunWs31NativeOs2() {
    Ws31NativeObserver observer;
    std::unique_ptr<Ws31V2NativeEntry> entry;
    bool terminalWritten=false;
    try {
        Ws31NativeValidate();
        Ws31NativeNeed(IntHeader::mode==5 && fct_output && pfc_file,"actual INT/FCT/PFC setup missing");
        observer.Open(ws31_native_output_prefix);
        observer.Connect();
        Ws31V2NativeEntry::Hosts hosts;
        Ws31V2NativeEntry::PairTimings pairs;
        for (uint32_t i=0;i<n.GetN();++i)
            if (n.Get(i)->GetNodeType()==0) hosts.emplace(n.Get(i)->GetId(),n.Get(i));
        for (const auto &source:pairRtt) for (const auto &destination:source.second) {
            auto bdpSource=pairBdp.find(source.first);
            Ws31NativeNeed(bdpSource!=pairBdp.end(),"pair BDP owner missing");
            auto bdp=bdpSource->second.find(destination.first);
            Ws31NativeNeed(bdp!=bdpSource->second.end(),"pair BDP missing");
            pairs.emplace(std::make_pair(source.first->GetId(),destination.first->GetId()),
                Ws31V2NativeEntry::PairTiming(bdp->second,destination.second));
        }
        Ws31V2NativeEntry::RunConfig config(lb_mode,has_win,global_t,maxBdp,maxRtt,pairs,
            packet_payload_size,cc_mode,enable_irn);
        std::ifstream declarations(ws31_native_declarations.c_str());
        Ws31NativeNeed(bool(declarations),"cannot open native declarations");
        entry.reset(new Ws31V2NativeEntry());
        entry->Install(declarations,hosts,config);
        entry->Run();
        if (ws31::StartMode(lb_mode)) {
            const ws31::StartCounters &s=ws31::StartData();
            Ws31NativeNeed(s.launched+s.cancelled==s.demanded && s.finished==s.launched &&
                s.launchBytes+s.cancelBytes==s.demandBytes && s.finishBytes==s.launchBytes,
                "C2 request or byte accounting is inconsistent");
            std::cout << "WS31_C2_STATE demanded=" << s.demanded << " launched=" << s.launched
                      << " cancelled=" << s.cancelled << " finished=" << s.finished
                      << " demand_bytes=" << s.demandBytes << " launch_bytes=" << s.launchBytes
                      << " cancel_bytes=" << s.cancelBytes << " finish_bytes=" << s.finishBytes
                      << " eligible=" << s.eligible << " planned_waited=" << s.plannedWaited
                      << " planned_delay_sum_ns=" << s.plannedDelaySum
                      << " planned_delay_max_ns=" << s.plannedDelayMax
                      << " waited=" << s.waited << " delay_sum_ns=" << s.delaySum
                      << " delay_max_ns=" << s.delayMax
                      << " eligibility_hashes=" << s.eligibilityHashes
                      << " delay_hashes=" << s.delayHashes
                      << " size_comparisons=" << s.sizeComparisons << std::endl;
        }
        const auto diagnostics=entry->GetDiagnostics();
        observer.Terminal(diagnostics); terminalWritten=true;
        Ws31NativeNeed(diagnostics.entryFinished && !diagnostics.failed &&
            diagnostics.entered==1120 && diagnostics.issued==1120 &&
            diagnostics.bindings==1120 && diagnostics.pending==0 && diagnostics.cancellations==0,
            "entry demand ledger did not complete");
    } catch (const std::exception &e) { observer.Remember(e.what()); }
      catch (...) { observer.Remember("non-standard native run exception"); }
    if (entry && !terminalWritten) {
        try { observer.Terminal(entry->GetDiagnostics()); }
        catch (const std::exception &e) { observer.Remember(e.what()); }
        catch (...) { observer.Remember("terminal diagnostics failed"); }
    }
    long beforeFct=-1,beforePfc=-1;
    try {
        beforeFct=observer.OriginalBoundary("pre_cleanup_fct_bytes",fct_output);
        beforePfc=observer.OriginalBoundary("pre_cleanup_pfc_bytes",pfc_file);
    } catch (const std::exception &e) { observer.Remember(e.what()); }
    // Observer and original FCT contexts survive disconnect failure and all cleanup.
    try { observer.SealAndDisconnect(); }
    catch (const std::exception &e) { observer.Remember(e.what()); }
    entry.reset();
    try { Simulator::Destroy(); }
    catch (const std::exception &e) { observer.Remember(e.what()); }
    catch (...) { observer.Remember("Destroy non-standard exception"); }
    try {
        const long afterFct=observer.OriginalBoundary("post_destroy_fct_bytes",fct_output);
        const long afterPfc=observer.OriginalBoundary("post_destroy_pfc_bytes",pfc_file);
        if ((beforeFct>=0 && beforeFct!=afterFct) || (beforePfc>=0 && beforePfc!=afterPfc))
            observer.Remember("original FCT/PFC writes occurred during cleanup/Destroy");
    } catch (const std::exception &e) { observer.Remember(e.what()); }
    for (FILE **slot:{&fct_output,&pfc_file}) if (*slot) {
        FILE *file=*slot; *slot=nullptr;
        const bool flushFailed=std::fflush(file)!=0 || std::ferror(file);
        const bool closeFailed=std::fclose(file)!=0;
        if (flushFailed || closeFailed) observer.Remember("original FCT/PFC output flush/close failed");
    }
    observer.Finish();
    return observer.Failed()?2:0;
}
} // namespace
// WS31_NATIVE_OS2_END


int main(int argc, char *argv[]) {
    uint32_t *workload_cdf = nullptr;
    clock_t begint, endt;
    begint = clock();
#ifndef PGO_TRAINING
    if (argc > 1)
#else
    if (true)
#endif
    {
        // Read the configuration file
        std::ifstream conf;
#ifndef PGO_TRAINING
        conf.open(argv[1]);
#else
        conf.open(PATH_TO_PGO_CONFIG);
#endif
        while (!conf.eof()) {
            std::string key;
            conf >> key;
            if (key.compare("WS31_NATIVE_DECLARATIONS") == 0) {
                Ws31NativeNeed(!ws31_native_declarations_seen,"repeated native declarations key");
                ws31_native_declarations_seen=true;
                Ws31NativeNeed(bool(conf >> ws31_native_declarations),"missing native declarations value");
            } else if (key.compare("WS31_NATIVE_OUTPUT_PREFIX") == 0) {
                Ws31NativeNeed(!ws31_native_output_seen,"repeated native output key");
                ws31_native_output_seen=true;
                Ws31NativeNeed(bool(conf >> ws31_native_output_prefix),"missing native output value");
            } else if (key.compare("WS31_C3R_REUSE_TUPLE") == 0) {
                uint32_t enabled=0;
                conf >> enabled;
                if (!conf || enabled != 1 || ws31_c3r_reuse_tuple) {
                    std::cerr << "WS31_C3R_REUSE_TUPLE requires one value of 1" << std::endl;
                    return 2;
                }
                ws31_c3r_reuse_tuple=true;
            } else if (key.compare("WS31_C3R_REPLAY_STALE") == 0) {
                uint32_t enabled=0;
                conf >> enabled;
                if (!conf || enabled != 1 || ws31_c3r_replay_stale) {
                    std::cerr << "WS31_C3R_REPLAY_STALE requires one value of 1" << std::endl;
                    return 2;
                }
                ws31_c3r_replay_stale=true;
            } else if (key.compare("FLOW_INPUT_FILE") == 0) {
                std::string v;
                conf >> v;
                flow_input_file = v;
                std::cerr << "FLOW_INPUT_FILE\t\t\t" << flow_input_file << "\n";
            } else if (key.compare("CNP_OUTPUT_FILE") == 0) {
                std::string v;
                conf >> v;
                cnp_output_file = v;
                std::cerr << "CNP_OUTPUT_FILE\t\t\t" << cnp_output_file << "\n";
            } else if (key.compare("EST_ERROR_MON_FILE") == 0) {
                std::string v;
                conf >> v;
                est_error_output_file = v;
                std::cerr << "EST_ERROR_MON_FILE\t\t\t" << est_error_output_file << "\n";
            } else if (key.compare("LB_MODE") == 0) {
                uint32_t v;
                conf >> v;
                lb_mode = v;
                std::cerr << "LB_MODE\t\t\t" << lb_mode << "\n";
            } else if (key.compare("WS31_C2_SIZE_TARGET_BYTES") == 0) {
                conf >> ws31_c2_size_target_bytes;
            } else if (key.compare("WS31_C2_SIZE_CUTOFF") == 0) {
                conf >> ws31_c2_size_cutoff;
            } else if (key.compare("WS18_ADMISSION") == 0) {
                uint32_t value; conf >> value; ws18_admission = value != 0;
            } else if (key.compare("WS18_PATH") == 0) {
                uint32_t value; conf >> value; ws18_path = value != 0;
            } else if (key.compare("WS18_ADMISSION_RATE_GBPS") == 0) {
                conf >> ws18_admission_rate_gbps;
            } else if (key.compare("WS18_OUTPUT_FILE") == 0) {
                conf >> ws18_output_file;
            } else if (key.compare("WS21_IDENTITY") == 0) {
                uint32_t value; conf >> value; ws21_identity = value != 0;
            } else if (key.compare("WS21_FEEDBACK") == 0) {
                uint32_t value; conf >> value; ws21_feedback = value != 0;
            } else if (key.compare("WS21_FEEDBACK_INTERVAL_NS") == 0) {
                conf >> ws21_feedback_interval_ns;
            } else if (key.compare("WS21_HEARTBEAT") == 0) {
                uint32_t value; conf >> value; ws21_heartbeat = value != 0;
            } else if (key.compare("WS21_HEARTBEAT_INTERVAL_NS") == 0) {
                conf >> ws21_heartbeat_interval_ns;
            } else if (key.compare("WS21_HEARTBEAT_FAULT_MODE") == 0) {
                conf >> ws21_heartbeat_fault_mode;
            } else if (key.compare("WS21_HEARTBEAT_FAULT_TOR") == 0) {
                conf >> ws21_heartbeat_fault_tor;
            } else if (key.compare("WS21_HEARTBEAT_FAULT_PORT") == 0) {
                conf >> ws21_heartbeat_fault_port;
            } else if (key.compare("WS21_HEARTBEAT_FAULT_START_NS") == 0) {
                conf >> ws21_heartbeat_fault_start_ns;
            } else if (key.compare("WS21_HEARTBEAT_FAULT_END_NS") == 0) {
                conf >> ws21_heartbeat_fault_end_ns;
            } else if (key.compare("WS21_IDENTITY_OUTPUT_FILE") == 0) {
                conf >> ws21_identity_output_file;
            } else if (key.compare("WS21_PORT_EVENTS") == 0) {
                uint32_t value; conf >> value; ws21_port_events = value != 0;
            } else if (key.compare("WS21_PORT_OUTPUT_FILE") == 0) {
                conf >> ws21_port_output_file;
            } else if (key.compare("WS21_PORT_MAX_BYTES") == 0) {
                conf >> ws21_port_max_bytes;
            } else if (key.compare("WS23_PFC_PROBE") == 0) {
                conf >> ws23_pfc_probe_host >> ws23_pfc_probe_pg
                     >> ws23_pfc_probe_start_ns >> ws23_pfc_probe_end_ns;
            } else if (key.compare("GUARDHASH_LAMBDA") == 0) {
                conf >> guardhash_lambda;
            } else if (key.compare("GUARDHASH_TAU_BYTES") == 0) {
                conf >> guardhash_tau_bytes;
            } else if (key.compare("HARM_GATE_ON_BYTES") == 0) {
                conf >> harm_gate_on_bytes;
            } else if (key.compare("HARM_GATE_OFF_BYTES") == 0) {
                conf >> harm_gate_off_bytes;
            } else if (key.compare("SW_MONITORING_INTERVAL") == 0) {
                uint32_t v;
                conf >> v;
                switch_mon_interval = v;
                std::cerr << "SW_MONITORING_INTERVAL\t\t\t" << switch_mon_interval << "\n";
            } else if (key.compare("CONWEAVE_TX_EXPIRY_TIME") == 0) {
                uint32_t v;
                conf >> v;
                conweave_txExpiryTime = Time(MicroSeconds(v));
                std::cerr << "CONWEAVE_TX_EXPIRY_TIME\t\t\t" << conweave_txExpiryTime << "\n";
            } else if (key.compare("CONWEAVE_REPLY_TIMEOUT_EXTRA") == 0) {
                uint32_t v;
                conf >> v;
                conweave_extraReplyDeadline = Time(MicroSeconds(v));
                std::cerr << "CONWEAVE_REPLY_TIMEOUT_EXTRA\t\t\t" << conweave_extraReplyDeadline
                          << "\n";
            } else if (key.compare("CONWEAVE_EXTRA_VOQ_FLUSH_TIME") == 0) {
                uint32_t v;
                conf >> v;
                conweave_extraVOQFlushTime = Time(MicroSeconds(v));
                std::cerr << "CONWEAVE_EXTRA_VOQ_FLUSH_TIME\t\t\t" << conweave_extraVOQFlushTime
                          << "\n";
            } else if (key.compare("CONWEAVE_PATH_PAUSE_TIME") == 0) {
                uint32_t v;
                conf >> v;
                conweave_pathPauseTime = Time(MicroSeconds(v));
                std::cerr << "CONWEAVE_PATH_PAUSE_TIME\t\t\t" << conweave_pathPauseTime << "\n";
            } else if (key.compare("CONWEAVE_DEFAULT_VOQ_WAITING_TIME") == 0) {
                uint32_t v;
                conf >> v;
                conweave_defaultVOQWaitingTime = Time(MicroSeconds(v));
                std::cerr << "CONWEAVE_DEFAULT_VOQ_WAITING_TIME\t\t\t"
                          << conweave_defaultVOQWaitingTime << "\n";
            } else if (key.compare("ENABLE_PFC") == 0) {
                uint32_t v;
                conf >> v;
                enable_pfc = v;
                if (enable_pfc)
                    std::cerr << "ENABLE_PFC\t\t\t"
                              << "Yes"
                              << "\n";
                else
                    std::cerr << "ENABLE_PFC\t\t\t"
                              << "No"
                              << "\n";
            } else if (key.compare("ENABLE_QCN") == 0) {
                uint32_t v;
                conf >> v;
                enable_qcn = v;
                if (enable_qcn)
                    std::cerr << "ENABLE_QCN\t\t\t"
                              << "Yes"
                              << "\n";
                else
                    std::cerr << "ENABLE_QCN\t\t\t"
                              << "No"
                              << "\n";
            } else if (key.compare("USE_DYNAMIC_PFC_THRESHOLD") == 0) {
                uint32_t v;
                conf >> v;
                use_dynamic_pfc_threshold = v;
                if (use_dynamic_pfc_threshold)
                    std::cerr << "USE_DYNAMIC_PFC_THRESHOLD\t"
                              << "Yes"
                              << "\n";
                else
                    std::cerr << "USE_DYNAMIC_PFC_THRESHOLD\t"
                              << "No"
                              << "\n";
            } else if (key.compare("CLAMP_TARGET_RATE") == 0) {
                uint32_t v;
                conf >> v;
                clamp_target_rate = v;
                if (clamp_target_rate)
                    std::cerr << "CLAMP_TARGET_RATE\t\t"
                              << "Yes"
                              << "\n";
                else
                    std::cerr << "CLAMP_TARGET_RATE\t\t"
                              << "No"
                              << "\n";
            } else if (key.compare("PAUSE_TIME") == 0) {
                double v;
                conf >> v;
                pause_time = v;
                std::cerr << "PAUSE_TIME\t\t\t" << pause_time << "\n";
            } else if (key.compare("DATA_RATE") == 0) {
                std::string v;
                conf >> v;
                data_rate = v;
                std::cerr << "DATA_RATE\t\t\t" << data_rate << "\n";
            } else if (key.compare("LINK_DELAY") == 0) {
                std::string v;
                conf >> v;
                link_delay = v;
                std::cerr << "LINK_DELAY\t\t\t" << link_delay << "\n";
            } else if (key.compare("PACKET_PAYLOAD_SIZE") == 0) {
                uint32_t v;
                conf >> v;
                packet_payload_size = v;
                std::cerr << "PACKET_PAYLOAD_SIZE\t\t" << packet_payload_size << "\n";
            } else if (key.compare("L2_CHUNK_SIZE") == 0) {
                uint32_t v;
                conf >> v;
                l2_chunk_size = v;
                std::cerr << "L2_CHUNK_SIZE\t\t\t" << l2_chunk_size << "\n";
            } else if (key.compare("L2_ACK_INTERVAL") == 0) {
                uint32_t v;
                conf >> v;
                l2_ack_interval = v;
                std::cerr << "L2_ACK_INTERVAL\t\t\t" << l2_ack_interval << "\n";
            } else if (key.compare("L2_BACK_TO_ZERO") == 0) {
                uint32_t v;
                conf >> v;
                l2_back_to_zero = v;
                if (l2_back_to_zero)
                    std::cerr << "L2_BACK_TO_ZERO\t\t\t"
                              << "Yes"
                              << "\n";
                else
                    std::cerr << "L2_BACK_TO_ZERO\t\t\t"
                              << "No"
                              << "\n";
            } else if (key.compare("TOPOLOGY_FILE") == 0) {
                std::string v;
                conf >> v;
                topology_file = v;
                std::cerr << "TOPOLOGY_FILE\t\t\t" << topology_file << "\n";
            } else if (key.compare("FLOW_FILE") == 0) {
                std::string v;
                conf >> v;
                flow_file = v;
                std::cerr << "FLOW_FILE\t\t\t" << flow_file << "\n";
            } else if (key.compare("FLOWGEN_START_TIME") == 0) {
                double v;
                conf >> v;
                flowgen_start_time = v;
                qlen_mon_start = v;
                qlen_mon_end = v;
                cnp_mon_start = v;
                irn_mon_start = v;
                std::cerr << "FLOWGEN_START_TIME\t\t" << flowgen_start_time << "\n";
            } else if (key.compare("FLOWGEN_STOP_TIME") == 0) {
                double v;
                conf >> v;
                flowgen_stop_time = v;
                std::cerr << "FLOWGEN_STOP_TIME\t\t" << flowgen_stop_time << "\n";
            } else if (key.compare("ALPHA_RESUME_INTERVAL") == 0) {
                double v;
                conf >> v;
                alpha_resume_interval = v;
                std::cerr << "ALPHA_RESUME_INTERVAL\t\t" << alpha_resume_interval << "\n";
            } else if (key.compare("RP_TIMER") == 0) {
                double v;
                conf >> v;
                rp_timer = v;
                std::cerr << "RP_TIMER\t\t\t" << rp_timer << "\n";
            } else if (key.compare("EWMA_GAIN") == 0) {
                double v;
                conf >> v;
                ewma_gain = v;
                std::cerr << "EWMA_GAIN\t\t\t" << ewma_gain << "\n";
            } else if (key.compare("FAST_RECOVERY_TIMES") == 0) {
                uint32_t v;
                conf >> v;
                fast_recovery_times = v;
                std::cerr << "FAST_RECOVERY_TIMES\t\t" << fast_recovery_times << "\n";
            } else if (key.compare("RATE_AI") == 0) {
                std::string v;
                conf >> v;
                rate_ai = v;
                std::cerr << "RATE_AI\t\t\t\t" << rate_ai << "\n";
            } else if (key.compare("RATE_HAI") == 0) {
                std::string v;
                conf >> v;
                rate_hai = v;
                std::cerr << "RATE_HAI\t\t\t" << rate_hai << "\n";
            } else if (key.compare("ERROR_RATE_PER_LINK") == 0) {
                double v;
                conf >> v;
                error_rate_per_link = v;
                std::cerr << "ERROR_RATE_PER_LINK\t\t" << error_rate_per_link << "\n";
            } else if (key.compare("CC_MODE") == 0) {
                conf >> cc_mode;
                std::cerr << "CC_MODE\t\t" << cc_mode << '\n';
            } else if (key.compare("RATE_DECREASE_INTERVAL") == 0) {
                double v;
                conf >> v;
                rate_decrease_interval = v;
                std::cerr << "RATE_DECREASE_INTERVAL\t\t" << rate_decrease_interval << "\n";
            } else if (key.compare("MIN_RATE") == 0) {
                conf >> min_rate;
                std::cerr << "MIN_RATE\t\t" << min_rate << "\n";
            } else if (key.compare("FCT_OUTPUT_FILE") == 0) {
                conf >> fct_output_file;
                std::cerr << "FCT_OUTPUT_FILE\t\t" << fct_output_file << '\n';
            } else if (key.compare("HAS_WIN") == 0) {
                conf >> has_win;
                std::cerr << "HAS_WIN\t\t" << has_win << "\n";
            } else if (key.compare("GLOBAL_T") == 0) {
                conf >> global_t;
                std::cerr << "GLOBAL_T\t\t" << global_t << '\n';
            } else if (key.compare("MI_THRESH") == 0) {
                conf >> mi_thresh;
                std::cerr << "MI_THRESH\t\t" << mi_thresh << '\n';
            } else if (key.compare("VAR_WIN") == 0) {
                uint32_t v;
                conf >> v;
                var_win = v;
                std::cerr << "VAR_WIN\t\t" << v << '\n';
            } else if (key.compare("FAST_REACT") == 0) {
                uint32_t v;
                conf >> v;
                fast_react = v;
                std::cerr << "FAST_REACT\t\t" << v << '\n';
            } else if (key.compare("U_TARGET") == 0) {
                conf >> u_target;
                std::cerr << "U_TARGET\t\t" << u_target << '\n';
            } else if (key.compare("INT_MULTI") == 0) {
                conf >> int_multi;
                std::cerr << "INT_MULTI\t\t\t\t" << int_multi << '\n';
            } else if (key.compare("RATE_BOUND") == 0) {
                uint32_t v;
                conf >> v;
                rate_bound = v;
                std::cerr << "RATE_BOUND\t\t" << rate_bound << '\n';
            } else if (key.compare("DCTCP_RATE_AI") == 0) {
                conf >> dctcp_rate_ai;
                std::cerr << "DCTCP_RATE_AI\t\t\t\t" << dctcp_rate_ai << "\n";
            } else if (key.compare("PFC_OUTPUT_FILE") == 0) {
                conf >> pfc_output_file;
                std::cerr << "PFC_OUTPUT_FILE\t\t\t\t" << pfc_output_file << '\n';
            } else if (key.compare("LINK_DOWN") == 0) {
                conf >> link_down_time >> link_down_A >> link_down_B;
                std::cerr << "LINK_DOWN\t\t\t\t" << link_down_time << ' ' << link_down_A << ' '
                          << link_down_B << '\n';
            } else if (key.compare("KMAX_MAP") == 0) {
                int n_k;
                conf >> n_k;
                std::cerr << "KMAX_MAP\t\t\t\t";
                for (int i = 0; i < n_k; i++) {
                    uint64_t rate;
                    uint32_t k;
                    conf >> rate >> k;
                    rate2kmax[rate] = k;
                    std::cerr << ' ' << rate << ' ' << k;
                }
                std::cerr << '\n';
            } else if (key.compare("KMIN_MAP") == 0) {
                int n_k;
                conf >> n_k;
                std::cerr << "KMIN_MAP\t\t\t\t";
                for (int i = 0; i < n_k; i++) {
                    uint64_t rate;
                    uint32_t k;
                    conf >> rate >> k;
                    rate2kmin[rate] = k;
                    std::cerr << ' ' << rate << ' ' << k;
                }
                std::cerr << '\n';
            } else if (key.compare("PMAX_MAP") == 0) {
                int n_k;
                conf >> n_k;
                std::cerr << "PMAX_MAP\t\t\t\t";
                for (int i = 0; i < n_k; i++) {
                    uint64_t rate;
                    double p;
                    conf >> rate >> p;
                    rate2pmax[rate] = p;
                    std::cerr << ' ' << rate << ' ' << p;
                }
                std::cerr << '\n';
            } else if (key.compare("BUFFER_SIZE") == 0) {
                conf >> buffer_size;
                std::cerr << "BUFFER_SIZE\t\t\t\t" << buffer_size << '\n';
            } else if (key.compare("QLEN_MON_FILE") == 0) {
                conf >> qlen_mon_file;
                std::cerr << "QLEN_MON_FILE\t\t\t\t" << qlen_mon_file << '\n';
            } else if (key.compare("VOQ_MON_FILE") == 0) {
                conf >> voq_mon_file;
                std::cerr << "VOQ_MON_FILE\t\t\t\t" << voq_mon_file << '\n';
            } else if (key.compare("VOQ_MON_DETAIL_FILE") == 0) {
                conf >> voq_mon_detail_file;
                std::cerr << "VOQ_MON_DETAIL_FILE\t\t\t\t" << voq_mon_detail_file << '\n';
            } else if (key.compare("UPLINK_MON_FILE") == 0) {
                conf >> uplink_mon_file;
                std::cerr << "UPLINK_MON_FILE\t\t\t\t" << uplink_mon_file << '\n';
            } else if (key.compare("CONN_MON_FILE") == 0) {
                conf >> conn_mon_file;
                std::cerr << "CONN_MON_FILE\t\t\t\t" << conn_mon_file << '\n';
            } else if (key.compare("QLEN_MON_START") == 0) {
                conf >> qlen_mon_start;
                std::cerr << "QLEN_MON_START\t\t\t\t" << qlen_mon_start << '\n';
            } else if (key.compare("QLEN_MON_END") == 0) {
                conf >> qlen_mon_end;
                std::cerr << "QLEN_MON_END\t\t\t\t" << qlen_mon_end << '\n';
            } else if (key.compare("MULTI_RATE") == 0) {
                int v;
                conf >> v;
                multi_rate = v;
                std::cerr << "MULTI_RATE\t\t\t\t" << multi_rate << '\n';
            } else if (key.compare("SAMPLE_FEEDBACK") == 0) {
                int v;
                conf >> v;
                sample_feedback = v;
                std::cerr << "SAMPLE_FEEDBACK\t\t\t\t" << sample_feedback << '\n';
            } else if (key.compare("LOAD") == 0) {
                double v;
                conf >> v;
                load = v;
                std::cerr << "LOAD\t\t\t" << load << "\n";
            } else if (key.compare("ENABLE_IRN") == 0) {
                bool v;
                conf >> v;
                enable_irn = v;
                std::cerr << "ENABLE_IRN\t\t" << enable_irn << "\n";
            } else if (key.compare("RANDOM_SEED") == 0) {
                int v;
                conf >> v;
                random_seed = v;
                std::cerr << "RANDOM_SEED\t\t\t" << random_seed << "\n";
            }

            fflush(stdout);
        }
        conf.close();

    } else {
        std::cerr << "Error: require a config file\n";
        fflush(stdout);
        return 1;
    }

    /******************* READING CONFIG FILE IS DONE ***********************/

    if (ws31_c3r_reuse_tuple && lb_mode != 57) {
        std::cerr << "WS31_C3R_REUSE_TUPLE requires mode 57" << std::endl;
        return 2;
    }
    if (ws31_c3r_replay_stale && !ws31_c3r_reuse_tuple) {
        std::cerr << "WS31_C3R_REPLAY_STALE requires tuple reuse" << std::endl;
        return 2;
    }

    if (lb_mode==56) {
        if (!((ws31_c2_size_target_bytes==16384 && ws31_c2_size_cutoff==3) ||
              (ws31_c2_size_target_bytes==262144 && ws31_c2_size_cutoff==6))) {
            std::cerr << "WS31 C2 size control requires a registered D1 or D2 parameter pair" << std::endl;
            return 2;
        }
    } else if (ws31_c2_size_target_bytes || ws31_c2_size_cutoff) {
        std::cerr << "WS31 C2 size parameters require mode 56" << std::endl;
        return 2;
    }
    ws31::ConfigureStartSizeControl(ws31_c2_size_target_bytes,ws31_c2_size_cutoff);

    if (Ws31NativeRequested()) {
        try { Ws31NativeValidate(); }
        catch (const std::exception &e) { std::cerr << e.what() << std::endl; return 2; }
    }

    // Check the actual parsed configuration, even when invoking this binary
    // directly rather than through the guarded Python launcher.
    ws31::ValidateLabelProfile(ws31::LabelProfile(),lb_mode,Ws30V13TagTransform(),
        Ws30V13Env("WS30_COMPOSITION"),Ws30V13Env("WS30_LIFECYCLE"),
        Ws30V13Env("WS30_LIFE_PROFILE"),Ws30Level(),
        ws31::LabelRunContext(enable_pfc,enable_irn,cc_mode,topology_file,flow_file,
            ws21_heartbeat_fault_mode || ws23_pfc_probe_host>=0 || link_down_time ||
                error_rate_per_link!=0.0,
            ws18_admission || ws18_path || ws21_identity || ws21_feedback ||
                ws21_heartbeat || ws21_port_events || ws31::LabelDiagnosticEnvironment()));

    /**
     * Activate ns3 logging
     */
    LogComponentEnable("GENERIC_SIMULATION", LOG_LEVEL_DEBUG);

    /**
     * @brief Random seed setup
     */
    NS_LOG_INFO("Initialize random seed: " << random_seed);
    srand((unsigned)random_seed);
    SeedManager::SetSeed(random_seed);

    /**
     * @brief PFC/QCN setup
     */
    bool dynamicth = use_dynamic_pfc_threshold;
    Config::SetDefault("ns3::QbbNetDevice::PauseTime", UintegerValue(pause_time));
    Config::SetDefault("ns3::QbbNetDevice::QcnEnabled", BooleanValue(enable_qcn));
    Config::SetDefault("ns3::QbbNetDevice::DynamicThreshold", BooleanValue(dynamicth));
    Config::SetDefault("ns3::QbbNetDevice::QbbEnabled", BooleanValue(enable_pfc));

    if (cc_mode != 1 && lb_mode == 9) {
        std::cout << "Currently, ConWeave supports only DCQCN congestion control for RDMA. \nIf "
                     "you want to extend, the reordering delay at DstTor must be considered."
                  << std::endl;
        exit(1);
    }

    /**
     * @brief INT header setup
     */
    IntHop::multi = int_multi;
    // IntHeader::mode
    if (cc_mode == 7)  // timely, use ts
        IntHeader::mode = 1;
    else if (cc_mode == 3)  // hpcc, use int
        IntHeader::mode = 0;
    else  // others, no extra header
        IntHeader::mode = 5;

    if (Ws30CompositionEnabled() || Ws30V13Life()) {
        if (Ws30V14Enabled() && Ws30V14Profile()!=1 && Ws30V14Profile()!=2)
            NS_FATAL_ERROR("v14 lifecycle needs explicit pair/state profile");
        if (cc_mode!=1 || enable_pfc || !enable_irn)
            NS_FATAL_ERROR("WS-30 composition requires DCQCN, PFC=0, IRN=1");
        // run.py's bw=400 map starts at 80 Gbps. Freeze the diagnostic
        // 40-Gbps entry explicitly, using the same ECN thresholds as its
        // other rates; this branch is absent from every normal run.
        rate2kmin[40000000000ULL] = 100;
        rate2kmax[40000000000ULL] = 400;
        rate2pmax[40000000000ULL] = 0.2;
        std::cout << "WS30_COMPOSITION_ECN rate=40000000000 kmin=100 kmax=400 pmax=0.2" << std::endl;
    }

    /**
     * @brief open topology config, input-flows config.
     */
    topof.open(topology_file.c_str());
    if (!Ws31NativeRequested()) flowf.open(flow_file.c_str());
    uint32_t node_num, switch_num, link_num;
    if (!topof || (!Ws31NativeRequested() && !flowf)) {
        std::cerr << "INPUT_ERROR cannot open topology or flow file: " << topology_file
                  << " / " << flow_file << std::endl;
        return 1;
    }
    int64_t declared_flows=0;
    if (!(topof >> node_num >> switch_num >> link_num) ||
        (!Ws31NativeRequested() && !(flowf >> declared_flows)) ||
        node_num <= switch_num || link_num == 0 ||
        declared_flows < 0 || declared_flows > std::numeric_limits<uint32_t>::max()) {
        std::cerr << "INPUT_ERROR invalid topology or flow header" << std::endl;
        return 1;
    }
    if (!Ws31NativeRequested()) {
        flow_num = static_cast<uint32_t>(declared_flows);
        std::string header_remainder;
        std::getline(flowf, header_remainder);
        if (header_remainder.find_first_not_of(" \t\r") != std::string::npos) {
            std::cerr << "FLOW_INPUT_ERROR line 1: expected only a flow count" << std::endl;
            return 1;
        }
    }

    /*-------Parameter of Settings-------*/
    Settings::node_num = node_num;
    Settings::host_num = node_num - switch_num;
    Settings::switch_num = switch_num;
    Settings::lb_mode = lb_mode;
    SwitchNode::ConfigureGuardHash(guardhash_lambda, guardhash_tau_bytes,
                                   harm_gate_on_bytes, harm_gate_off_bytes);
    NS_ASSERT_MSG(lb_mode != 20 || (ws18_admission_rate_gbps > 0 && !ws18_output_file.empty()),
                  "WS-18 requires positive admission rate and an output file");
    SwitchNode::ConfigureWs18Path(lb_mode == 20 && ws18_path);
    if (ws21_feedback && (lb_mode != 20 || !ws21_identity))
        NS_FATAL_ERROR("WS-21 feedback requires mode 20 and path identity mapping");
    if (ws21_identity && (lb_mode != 20 || ws21_identity_output_file.empty()))
        NS_FATAL_ERROR("WS-21 identity diagnostic requires mode 20 and an output file");
    NS_ASSERT_MSG(!ws21_port_events ||
                      (lb_mode == 20 && !ws21_port_output_file.empty() &&
                       ws21_port_max_bytes >= 1024),
                  "WS-21 port events require mode 20, output file, and byte cap");
    SwitchNode::ConfigureWs21Identity(ws21_identity);
    SwitchNode::ConfigureWs21Feedback(ws21_feedback, ws21_feedback_interval_ns);
    if (ws21_heartbeat && lb_mode != 20)
        NS_FATAL_ERROR("WS-21 heartbeat requires mode 20");
    SwitchNode::ConfigureWs21Heartbeat(ws21_heartbeat, ws21_heartbeat_interval_ns,
                                       ws21_heartbeat_fault_mode, ws21_heartbeat_fault_tor,
                                       ws21_heartbeat_fault_port,
                                       ws21_heartbeat_fault_start_ns,
                                       ws21_heartbeat_fault_end_ns);
    Settings::packet_payload = packet_payload_size;
    // Settings::MTU = packet_payload_size + 48;  // for simplicity
    /*------------------------------------*/

    std::vector<uint32_t> node_type(node_num, 0);
    for (uint32_t i = 0; i < switch_num; i++) {
        uint32_t sid;
        topof >> sid;
        node_type[sid] = 1;
    }
    for (uint32_t i = 0; i < node_num; i++) {
        if (node_type[i] == 0)
            n.Add(CreateObject<Node>());
        else {
            Ptr<SwitchNode> sw = CreateObject<SwitchNode>();
            n.Add(sw);
            sw->SetAttribute("EcnEnabled", BooleanValue(enable_qcn));
        }
    }
    NS_LOG_INFO("Create nodes.");

    /*----------------------------------------*/

    InternetStackHelper internet;
    internet.Install(n);  // aggregate ipv4, ipv6, udp, tcp, etc

    //
    // Assign IP to each server
    //
    for (uint32_t i = 0; i < node_num; i++) {
        if (n.Get(i)->GetNodeType() == 0) {  // is server
            serverAddress.resize(i + 1);
            serverAddress[i] = Settings::node_id_to_ip(i);
        }
    }

    NS_LOG_INFO("Create channels.");

    //
    // Explicitly create the channels required by the topology.
    //
    Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();
    Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();
    rem->SetRandomVariable(uv);
    uv->SetStream(50);
    rem->SetAttribute("ErrorRate", DoubleValue(error_rate_per_link));
    rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));

    pfc_file = fopen(pfc_output_file.c_str(), Ws31NativeRequested()?"wx":"w");

    QbbHelper qbb;
    Ipv4AddressHelper ipv4;
    std::vector<std::pair<uint32_t, uint32_t>> link_pairs;  // src, dst link pairs
    const bool ws30StateTopology = topology_file == "config/ws30v14_state8.txt";
    std::set<std::pair<uint32_t, uint32_t>> ws30StateEdges;
    if (ws30StateTopology && (!Ws30V14Enabled() || Ws30V14Profile() != 2 ||
        node_num != 8 || switch_num != 4 || link_num != 8 ||
        (lb_mode != 0 && lb_mode != 33 && lb_mode != 35))) {
        NS_FATAL_ERROR("WS-30 state topology requires the qualified profile-2 E/Q12/U12 fixture");
    }
    for (uint32_t i = 0; i < link_num; i++) {
        uint32_t src, dst;
        std::string data_rate, link_delay;
        double error_rate;
        topof >> src >> dst >> data_rate >> link_delay >> error_rate;

        // The imported MoE topology has 10ns host links and 100ns fabric links.
        // pairRtt/pairBdp below use each link's actual QbbChannel delay.
        if (ws30StateTopology) {
            uint32_t a = std::min(src, dst), b = std::max(src, dst);
            bool hostLink = a < 4 && b == a + 4;
            bool fabricLink = (a == 4 && (b == 5 || b == 6)) ||
                              ((a == 5 || a == 6) && b == 7);
            bool slowLink = a == 4 && b == 5;
            if ((!hostLink && !fabricLink) || error_rate != 0 ||
                data_rate != (hostLink ? "400Gbps" : "40Gbps") ||
                link_delay != (slowLink ? "10000ns" : "1000ns") ||
                !ws30StateEdges.insert(std::make_pair(a, b)).second) {
                NS_FATAL_ERROR("WS-30 state link violates the frozen heterogeneous fixture");
            }
        } else if (topology_file != "config/topo_1280_400G_400G_OS1.txt")
            assert(std::to_string(one_hop_delay) + "ns" == link_delay);

        link_pairs.push_back(std::make_pair(src, dst));
        Ptr<Node> snode = n.Get(src), dnode = n.Get(dst);

        qbb.SetDeviceAttribute("DataRate", StringValue(data_rate));
        qbb.SetChannelAttribute("Delay", StringValue(link_delay));

        if (error_rate > 0) {
            Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();
            Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();
            rem->SetRandomVariable(uv);
            uv->SetStream(50);
            rem->SetAttribute("ErrorRate", DoubleValue(error_rate));
            rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
            qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
        } else {
            qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
        }

        fflush(stdout);

        // Assigne server IP
        // Note: this should be before the automatic assignment below (ipv4.Assign(d)),
        // because we want our IP to be the primary IP (first in the IP address list),
        // so that the global routing is based on our IP
        NetDeviceContainer d = qbb.Install(snode, dnode);
        if (snode->GetNodeType() == 0) {
            Ptr<Ipv4> ipv4 = snode->GetObject<Ipv4>();
            ipv4->AddInterface(d.Get(0));
            ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[src], Ipv4Mask(0xff000000)));
        }
        if (dnode->GetNodeType() == 0) {
            Ptr<Ipv4> ipv4 = dnode->GetObject<Ipv4>();
            ipv4->AddInterface(d.Get(1));
            ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[dst], Ipv4Mask(0xff000000)));
        }

        // used to create a graph of the topology
        nbr2if[snode][dnode].idx = DynamicCast<QbbNetDevice>(d.Get(0))->GetIfIndex();
        nbr2if[snode][dnode].up = true;
        nbr2if[snode][dnode].delay =
            DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(0))->GetChannel())
                ->GetDelay()
                .GetTimeStep();
        nbr2if[snode][dnode].bw = DynamicCast<QbbNetDevice>(d.Get(0))->GetDataRate().GetBitRate();
        nbr2if[dnode][snode].idx = DynamicCast<QbbNetDevice>(d.Get(1))->GetIfIndex();
        nbr2if[dnode][snode].up = true;
        nbr2if[dnode][snode].delay =
            DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(1))->GetChannel())
                ->GetDelay()
                .GetTimeStep();
        nbr2if[dnode][snode].bw = DynamicCast<QbbNetDevice>(d.Get(1))->GetDataRate().GetBitRate();

        // This is just to set up the connectivity between nodes. The IP addresses are useless
        char ipstring[16];
        Ipv4Address x;
        sprintf(ipstring, "10.%d.%d.0", i / 254 + 1, i % 254 + 1);
        ipv4.SetBase(ipstring, "255.255.255.0");
        ipv4.Assign(d);

        // setup PFC trace
        DynamicCast<QbbNetDevice>(d.Get(0))->TraceConnectWithoutContext(
            "QbbPfc", MakeBoundCallback(&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(0))));
        DynamicCast<QbbNetDevice>(d.Get(1))->TraceConnectWithoutContext(
            "QbbPfc", MakeBoundCallback(&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(1))));
    }

    std::cout << "(AVG) NIC RATE: " << get_nic_rate(n) << std::endl;

    /* Get IP address <-> NodeID pairs */
    Ipv4Address empty_ip;
    for (uint32_t i = 0; i < node_num; ++i) {
        if (n.Get(i)->GetNodeType() == 0) {  // is server
            if (serverAddress[i].IsEqual(empty_ip)) {
                printf("XXX ERROR %d\n", i);
                printf("size of serverAddress: %lu", serverAddress.size());
                NS_FATAL_ERROR("An end-host belongs to no link");
            }
        }
        Settings::hostId2IpMap[i] = serverAddress[i].Get();
        Settings::hostIp2IdMap[serverAddress[i].Get()] = i;
    }

    // config switch
    for (uint32_t i = 0; i < node_num; i++) {
        if (n.Get(i)->GetNodeType() == 1) {  // is switch
            Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
            uint32_t shift = 3;  // by default 1/8
            for (uint32_t j = 1; j < sw->GetNDevices(); j++) {
                Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(sw->GetDevice(j));
                // set ecn
                uint64_t rate = dev->GetDataRate().GetBitRate();
                NS_ASSERT_MSG(rate2kmin.find(rate) != rate2kmin.end(),
                              "must set kmin for each link speed");
                NS_ASSERT_MSG(rate2kmax.find(rate) != rate2kmax.end(),
                              "must set kmax for each link speed");
                NS_ASSERT_MSG(rate2pmax.find(rate) != rate2pmax.end(),
                              "must set pmax for each link speed");
                assert(rate2kmin.find(rate) != rate2kmin.end() &&
                       rate2kmax.find(rate) != rate2kmax.end() &&
                       rate2pmax.find(rate) != rate2pmax.end());
                sw->m_mmu->ConfigEcn(j, rate2kmin[rate], rate2kmax[rate], rate2pmax[rate]);
                // set pfc
                uint64_t delay =
                    DynamicCast<QbbChannel>(dev->GetChannel())->GetDelay().GetTimeStep();
                uint32_t headroom = rate * delay / 8 / 1000000000 * 2 + 2 * sw->m_mmu->MTU;
                sw->m_mmu->ConfigHdrm(j, headroom);
            }
            sw->m_mmu->ConfigNPort(sw->GetNDevices() - 1);
            sw->m_mmu->ConfigBufferSize(buffer_size * 1024 *
                                        1024);  // default 0, specify in run.py!!
            sw->m_mmu->node_id = sw->GetId();
            NS_LOG_INFO("Node %u : Broadcom switch (%u ports / %gMB MMU)\n" %
                        (i, sw->GetNDevices() - 1, sw->m_mmu->GetMmuBufferBytes() / 1000000.));
        }
    }

    fct_output = fopen(fct_output_file.c_str(), Ws31NativeRequested()?"wx":"w");
    if (lb_mode == 20) ws18_output = fopen(ws18_output_file.c_str(), "w");
    if (ws21_port_events) {
        ws21_port_output = fopen(ws21_port_output_file.c_str(), "w");
        NS_ASSERT_MSG(ws21_port_output, "WS-21 cannot open port-event output");
        SwitchNode::ConfigureWs21PortEvents(ws21_port_output, ws21_port_max_bytes);
    }
    if (!Ws31NativeRequested()) flow_input_stream = fopen(flow_input_file.c_str(), "w");
    if (cc_mode == 1 && !Ws31NativeRequested()) {
        cnp_output = fopen(cnp_output_file.c_str(), "w");
    }

    /**
     * @brief install RDMA driver (Mellanox parameters)
     *
     * [ClampTargetRate]clamp_tgt_rate (false) - when receiving a CNP, the target rate is always
     *updated to be the current rate
     *[-]clamp_tgt_rate_after_time_inc (true) - when receiving a CNP, the target rate is updated to
     *be the current rate also if the last rate increase event was due to the timer, and not only
     *due to the byte counter
     * [-]initial_alpha_value(1023) -
     * [RateDecreaseInterval]rate_reduce_monitor_period(4) - Minimal interval for rate reduction for
     *a flow. If a CNP is received during the interval, the flow rate is reduced at the beginning of
     *the next rate_reduce_monitor_period interval to (1-Alpha/Gd)*CurrentRate. rpg_gd is given as
     *log2(Gd), where Gd may only be powers of 2.
     * [-]rpg_gd(11) - If an CNP is received, the flow rate is reduced at the beginning of the next
     *rate_reduce_monitor_period interval to (1-Alpha/Gd)*CurrentRate.
     * -> in this simulator, (alpha / gd) ~ 0.5 setup, initially. We do not need rpg_gd parameter.
     * [RateOnFirstCnp]rate_to_set_on_first_cnp(0) - The rate that is set for the flow, upon first
     *CNP received, in Mbps. [RPTimer]rpg_time_reset(300us) - Time counter for rate increase event
     *[FastRecoveryTimes]rpg_threshold(1) - Number of rate increase events for switching between
     *Fast Recovery, Active Increase, Hyper Active Increase modes.
     * [AlphaResumInterval]dce_tcp_rtt(1) - Window for sampling of moving average calculation of
     *alpha
     * [-]dce_tcp_g(1019) - Weight of the new sampling in moving average calculation of alpha
     * [-]rpg_byte_reset(32767) - Byte counter for rate increase event
     * [-]rpg_min_dec_fac(50) -  Maximal factor by which the rate can be reduced (2 means that the
     *new rate can be divided by 2 at maximum)
     */

    // manually type BDP
    std::map<std::string, uint32_t> topo2bdpMap;
    topo2bdpMap[std::string("leaf_spine_128_100G_OS2")] = 104000;  // RTT=8320
    topo2bdpMap[std::string("fat_k8_100G_OS2")] = 156000;      // RTT=12480 --> all 100G links
    topo2bdpMap[std::string("fat_k4_100G_OS2")] = 156000;      // same three-tier link rates
    topo2bdpMap[std::string("topo_1280_400G_400G_OS1")] = 30000;  // 600ns * 400Gbps / 8
    if (Ws30CompositionEnabled() || Ws30V13Life())
        topo2bdpMap[std::string("ws30_composition8")] = 42200;  // 8440ns * 40Gbps / 8

    if (Ws30V14Enabled()) {
        topo2bdpMap[std::string("ws30v14_pair8")]=42200;
        // 2 * 13000 ns propagation + 440 ns serialization, at 40 Gbps.
        topo2bdpMap[std::string("ws30v14_state8")]=132200;
    }

    // topology_file
    bool found_topo2bdpMap = false;
    uint32_t irn_bdp_lookup = 0;
    for (auto pair : topo2bdpMap) {
        if (topology_file.find(pair.first) !=
            std::string::npos) {  // if topology file string includes the word
            irn_bdp_lookup = pair.second;
            found_topo2bdpMap = true;
            break;
        }
    }
    if (found_topo2bdpMap == false) {
        std::cout << __FILE__ << "(" << __LINE__ << ")"
                  << " ERROR - topo2bdpMap has no matched item with " << topology_file << std::endl;
        assert(false);
    }

    // rdmaHw config
    for (uint32_t i = 0; i < node_num; i++) {
        if (n.Get(i)->GetNodeType() == 0) {  // is server
            // create RdmaHw
            Ptr<RdmaHw> rdmaHw = CreateObject<RdmaHw>();
            if (ws31_c3r_replay_stale) rdmaHw->EnableWs31C3rReplayStale();
            rdmaHw->SetAttribute("ClampTargetRate", BooleanValue(clamp_target_rate));
            rdmaHw->SetAttribute("AlphaResumInterval", DoubleValue(alpha_resume_interval));
            rdmaHw->SetAttribute("RPTimer", DoubleValue(rp_timer));
            rdmaHw->SetAttribute("FastRecoveryTimes", UintegerValue(fast_recovery_times));
            rdmaHw->SetAttribute("EwmaGain", DoubleValue(ewma_gain));
            rdmaHw->SetAttribute("RateAI", DataRateValue(DataRate(rate_ai)));
            rdmaHw->SetAttribute("RateHAI", DataRateValue(DataRate(rate_hai)));
            rdmaHw->SetAttribute("L2BackToZero", BooleanValue(l2_back_to_zero));
            rdmaHw->SetAttribute("L2ChunkSize", UintegerValue(l2_chunk_size));
            rdmaHw->SetAttribute("L2AckInterval", UintegerValue(l2_ack_interval));
            rdmaHw->SetAttribute("CcMode", UintegerValue(cc_mode));
            rdmaHw->SetAttribute("RateDecreaseInterval", DoubleValue(rate_decrease_interval));
            rdmaHw->SetAttribute("MinRate", DataRateValue(DataRate(min_rate)));
            rdmaHw->SetAttribute("Mtu", UintegerValue(packet_payload_size));
            rdmaHw->SetAttribute("MiThresh", UintegerValue(mi_thresh));
            rdmaHw->SetAttribute("VarWin", BooleanValue(var_win));
            rdmaHw->SetAttribute("FastReact", BooleanValue(fast_react));
            rdmaHw->SetAttribute("MultiRate", BooleanValue(multi_rate));
            rdmaHw->SetAttribute("SampleFeedback", BooleanValue(sample_feedback));
            rdmaHw->SetAttribute("TargetUtil", DoubleValue(u_target));
            rdmaHw->SetAttribute("RateBound", BooleanValue(rate_bound));
            rdmaHw->SetAttribute("DctcpRateAI", DataRateValue(DataRate(dctcp_rate_ai)));
            rdmaHw->SetAttribute("IrnEnable", BooleanValue(enable_irn));
            // topo2bdpMap (e.g., longest BDP 25000: 8us * 25Gbps)
            rdmaHw->SetAttribute("IrnRtoHigh", TimeValue(MicroSeconds(320)));  // 1930
            rdmaHw->SetAttribute("IrnRtoLow", TimeValue(MicroSeconds(100)));   // 454
            rdmaHw->SetAttribute("IrnBdp", UintegerValue(irn_bdp_lookup));
            // Monitoring CNP Marking frequency of DCQCN
            if (cc_mode == 1 && !Ws31NativeRequested()) {
                Simulator::Schedule(NanoSeconds(cnp_mon_start), &cnp_freq_monitoring, cnp_output,
                                    rdmaHw);
            }

            // create and install RdmaDriver
            Ptr<RdmaDriver> rdma = CreateObject<RdmaDriver>();
            Ptr<Node> node = n.Get(i);
            rdma->SetNode(node);
            rdma->SetRdmaHw(rdmaHw);

            node->AggregateObject(rdma);
            rdma->Init();
            const bool completionConnected=rdma->TraceConnectWithoutContext("QpComplete",
                                             MakeBoundCallback(qp_finish, fct_output));
            if (Ws31NativeRequested() && !completionConnected) {
                std::cerr << "WS31_NATIVE_OS2 original QpComplete connection failed" << std::endl;
                Simulator::Destroy();
                return 2;
            }
        }
    }

    /**
     * @brief setup switch's CcMode and ACK with high priority
     */
    for (uint32_t i = 0; i < node_num; i++) {
        if (n.Get(i)->GetNodeType() == 1) {  // switch
            Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
            sw->SetAttribute("CcMode", UintegerValue(cc_mode));
            sw->SetAttribute("AckHighPrio", UintegerValue(1));
        }
    }

    /**
     * @brief setup routing
     */
    CalculateRoutes(n);
    SetRoutingEntries();

    /**
     * @brief get BDP and delay
     */
    maxRtt = maxBdp = 0;
    fprintf(stderr, "node_num=%d\n", node_num);
    for (uint32_t i = 0; i < node_num; i++) {
        if (n.Get(i)->GetNodeType() != 0) continue;
        for (uint32_t j = i + 1; j < node_num; j++) {
            if (n.Get(j)->GetNodeType() != 0) continue;
            uint64_t delay = pairDelay[n.Get(i)][n.Get(j)];
            uint64_t txDelay = pairTxDelay[n.Get(i)][n.Get(j)];
            uint64_t rtt = delay * 2 + txDelay;
            uint64_t bw = pairBw[n.Get(i)][n.Get(j)];
            uint64_t bdp = rtt * bw / 1000000000 / 8;
            pairBdp[n.Get(i)][n.Get(j)] = bdp;
            pairBdp[n.Get(j)][n.Get(i)] = bdp;
            pairRtt[n.Get(i)][n.Get(j)] = rtt;
            pairRtt[n.Get(j)][n.Get(i)] = rtt;

            if (ws30StateTopology) {
                fprintf(stderr, "WS30V14_ROUTE_METRIC src=%u dst=%u propagation_ns=%lu "
                    "serialization_ns=%lu rtt_ns=%lu bottleneck_bps=%lu bdp_bytes=%lu\n",
                    i, j, delay, txDelay, rtt, bw, bdp);
            }

            if (bdp > maxBdp) maxBdp = bdp;
            if (rtt > maxRtt) maxRtt = rtt;
        }
    }
    fprintf(stderr, "maxRtt: %lu, maxBdp: %lu\n", maxRtt, maxBdp);
    assert(maxBdp == irn_bdp_lookup);

    std::cout << "Configuring switches" << std::endl;
    /* config ToR Switch */
    for (auto &pair : link_pairs) {
        Ptr<Node> probably_host = n.Get(pair.first);
        Ptr<Node> probably_switch = n.Get(pair.second);

        // host-switch link
        if (probably_host->GetNodeType() == 0 && probably_switch->GetNodeType() == 1) {
            Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(probably_switch);
            sw->m_isToR = true;
            uint32_t hostIP = serverAddress[pair.first].Get();
            sw->m_isToR_hostIP.insert(hostIP);
            if (ws21_identity || lb_mode==51 || lb_mode==52 || lb_mode==57 ||
                Ws31NativeRequested()) {
                Settings::hostIp2SwitchId[hostIP] = sw->GetId();
                if (ws21_identity) SwitchNode::SetWs21HostTor(hostIP, sw->GetId());
            }
            if (ws21_port_events || ws21_heartbeat)
                sw->AddWs21HostPort(nbr2if.at(probably_switch).at(probably_host).idx);
            if (idxNodeToR.find(sw->GetId()) == idxNodeToR.end()) {
                idxNodeToR[sw->GetId()] = sw;
            };
        }
    }

    if (ws21_identity) BuildWs21IngressMapping();
    if (lb_mode==51 || lb_mode==52) BuildWs31OfanGroups();

    /* config load balancer's switches using ToR-to-ToR routing */
    if (lb_mode == 3 || lb_mode == 6 || lb_mode == 9) {  // Conga, Letflow, Conweave
        NS_LOG_INFO("Configuring Load Balancer's Switches");
        for (auto &pair : link_pairs) {
            Ptr<Node> probably_host = n.Get(pair.first);
            Ptr<Node> probably_switch = n.Get(pair.second);

            // host-switch link
            if (probably_host->GetNodeType() == 0 && probably_switch->GetNodeType() == 1) {
                Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(probably_switch);
                uint32_t hostIP = serverAddress[pair.first].Get();
                Settings::hostIp2SwitchId[hostIP] = sw->GetId();  // hostIP -> connected switch's ID
            }
        }

        // Conga: m_congaFromLeafTable, m_congaToLeafTable, m_congaRoutingTable
        // Letflow: m_letflowRoutingTable
        // Conweave: m_ConWeaveRoutingTable, m_rxToRId2BaseRTT
        for (auto i = nextHop.begin(); i != nextHop.end(); i++) {  // every node
            if (i->first->GetNodeType() == 1) {                    // switch
                Ptr<Node> nodeSrc = i->first;
                Ptr<SwitchNode> swSrc = DynamicCast<SwitchNode>(nodeSrc);  // switch
                uint32_t swSrcId = swSrc->GetId();

                if (swSrc->m_isToR) {
                    // printf("--- ToR Switch %d\n", swSrcId);

                    auto table1 = i->second;
                    for (auto j = table1.begin(); j != table1.end(); j++) {
                        Ptr<Node> dst = j->first;  // dst
                        uint32_t dstIP = Settings::hostId2IpMap[dst->GetId()];
                        uint32_t swDstId = Settings::hostIp2SwitchId[dstIP];  // Rx(dst)ToR

                        if (swSrcId == swDstId) {
                            continue;  // if in the same pod, then skip
                        }

                        if (lb_mode == 3) {
                            // initialize `m_congaFromLeafTable` and `m_congaToLeafTable`
                            swSrc->m_mmu->m_congaRouting
                                .m_congaFromLeafTable[swDstId];  // dynamically will be added in
                                                                 // conga
                            swSrc->m_mmu->m_congaRouting.m_congaToLeafTable[swDstId];
                        }

                        // construct paths
                        uint32_t pathId;
                        uint8_t path_ports[4] = {0, 0, 0, 0};  // interface is always large than 0
                        vector<Ptr<Node>> nexts1 = j->second;
                        for (auto next1 : nexts1) {
                            uint32_t outPort1 = nbr2if[nodeSrc][next1].idx;
                            auto nexts2 = nextHop[next1][dst];
                            if (nexts2.size() == 1 && nexts2[0]->GetId() == swDstId) {
                                // this destination has 2-hop distance
                                uint32_t outPort2 = nbr2if[next1][nexts2[0]].idx;
                                // printf("[IntraPod-2hop] %d (%d)-> %d (%d) -> %d -> %d\n",
                                // nodeSrc->GetId(), outPort1, next1->GetId(), outPort2,
                                // nexts2[0]->GetId(), dst->GetId());
                                path_ports[0] = (uint8_t)outPort1;
                                path_ports[1] = (uint8_t)outPort2;
                                pathId = *((uint32_t *)path_ports);
                                if (lb_mode == 3) {
                                    swSrc->m_mmu->m_congaRouting.m_congaRoutingTable[swDstId]
                                        .insert(pathId);
                                }
                                if (lb_mode == 6) {
                                    swSrc->m_mmu->m_letflowRouting.m_letflowRoutingTable[swDstId]
                                        .insert(pathId);
                                }
                                if (lb_mode == 9) {
                                    swSrc->m_mmu->m_conweaveRouting.m_ConWeaveRoutingTable[swDstId]
                                        .insert(pathId);
                                    swSrc->m_mmu->m_conweaveRouting.m_rxToRId2BaseRTT[swDstId] =
                                        one_hop_delay * 4;
                                }
                                continue;
                            }

                            for (auto next2 : nexts2) {
                                uint32_t outPort2 = nbr2if[next1][next2].idx;
                                auto nexts3 = nextHop[next2][dst];
                                if (nexts3.size() == 1 && nexts3[0]->GetId() == swDstId) {
                                    // this destination has 3-hop distance
                                    uint32_t outPort3 = nbr2if[next2][nexts3[0]].idx;
                                    // printf("[IntraPod-3hop] %d (%d)-> %d (%d) -> %d (%d) -> %d ->
                                    // %d\n", nodeSrc->GetId(), outPort1, next1->GetId(), outPort2,
                                    // next2->GetId(), outPort3, nexts3[0]->GetId(), dst->GetId());
                                    path_ports[0] = (uint8_t)outPort1;
                                    path_ports[1] = (uint8_t)outPort2;
                                    path_ports[2] = (uint8_t)outPort3;
                                    pathId = *((uint32_t *)path_ports);
                                    if (lb_mode == 3) {
                                        swSrc->m_mmu->m_congaRouting.m_congaRoutingTable[swDstId]
                                            .insert(pathId);
                                    }
                                    if (lb_mode == 6) {
                                        swSrc->m_mmu->m_letflowRouting
                                            .m_letflowRoutingTable[swDstId]
                                            .insert(pathId);
                                    }
                                    if (lb_mode == 9) {
                                        swSrc->m_mmu->m_conweaveRouting
                                            .m_ConWeaveRoutingTable[swDstId]
                                            .insert(pathId);
                                        swSrc->m_mmu->m_conweaveRouting.m_rxToRId2BaseRTT[swDstId] =
                                            one_hop_delay * 6;
                                    }
                                    continue;
                                }

                                for (auto next3 : nexts3) {
                                    uint32_t outPort3 = nbr2if[next2][next3].idx;
                                    auto nexts4 = nextHop[next3][dst];
                                    if (nexts4.size() == 1 && nexts4[0]->GetId() == swDstId) {
                                        // this destination has 4-hop distance
                                        uint32_t outPort4 = nbr2if[next3][nexts4[0]].idx;
                                        // printf("[IntraPod-4hop] %d (%d)-> %d (%d) -> %d (%d) ->
                                        // %d (%d) -> %d -> %d\n", nodeSrc->GetId(), outPort1,
                                        // next1->GetId(), outPort2, next2->GetId(), outPort3,
                                        // next3->GetId(), outPort4, nexts4[0]->GetId(),
                                        // dst->GetId());
                                        path_ports[0] = (uint8_t)outPort1;
                                        path_ports[1] = (uint8_t)outPort2;
                                        path_ports[2] = (uint8_t)outPort3;
                                        path_ports[3] = (uint8_t)outPort4;
                                        pathId = *((uint32_t *)path_ports);
                                        if (lb_mode == 3) {
                                            swSrc->m_mmu->m_congaRouting
                                                .m_congaRoutingTable[swDstId]
                                                .insert(pathId);
                                        }
                                        if (lb_mode == 6) {
                                            swSrc->m_mmu->m_letflowRouting
                                                .m_letflowRoutingTable[swDstId]
                                                .insert(pathId);
                                        }
                                        if (lb_mode == 9) {
                                            swSrc->m_mmu->m_conweaveRouting
                                                .m_ConWeaveRoutingTable[swDstId]
                                                .insert(pathId);
                                            swSrc->m_mmu->m_conweaveRouting
                                                .m_rxToRId2BaseRTT[swDstId] = one_hop_delay * 8;
                                        }
                                        continue;
                                    } else {
                                        printf("Too large topology?\n");
                                        assert(false);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // m_outPort2BitRateMap - only for Conga
        for (auto i = nextHop.begin(); i != nextHop.end(); i++) {  // every node
            if (i->first->GetNodeType() == 1) {                    // switch
                Ptr<Node> node = i->first;
                Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(node);  // switch
                uint32_t swId = sw->GetId();

                auto table = i->second;
                for (auto j = table.begin(); j != table.end(); j++) {
                    Ptr<Node> dst = j->first;  // dst
                    uint32_t dstIP = Settings::hostId2IpMap[dst->GetId()];
                    uint32_t swDstId = Settings::hostIp2SwitchId[dstIP];

                    for (auto next : j->second) {
                        uint32_t outPort = nbr2if[node][next].idx;
                        uint64_t bw = nbr2if[node][next].bw;
                        sw->m_mmu->m_congaRouting.SetLinkCapacity(outPort, bw);
                        // printf("Node: %d, interface: %d, bw: %lu\n", swId, outPort, bw);
                    }
                }
            }
        }

        // Constant setup, and switchInfo
        for (auto i = nextHop.begin(); i != nextHop.end(); i++) {  // every node
            if (i->first->GetNodeType() == 1) {
                Ptr<Node> node = i->first;
                Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(node);  // switch
                NS_LOG_INFO("Switch Info - ID:%u, ToR:%d\n" % (sw->GetId(), sw->m_isToR));
                if (lb_mode == 3) {
                    sw->m_mmu->m_congaRouting.SetConstants(conga_dreTime, conga_agingTime,
                                                           conga_flowletTimeout, conga_quantizeBit,
                                                           conga_alpha);
                    sw->m_mmu->m_congaRouting.SetSwitchInfo(sw->m_isToR, sw->GetId());
                }
                if (lb_mode == 6) {
                    sw->m_mmu->m_letflowRouting.SetConstants(letflow_agingTime,
                                                             letflow_flowletTimeout);
                    sw->m_mmu->m_letflowRouting.SetSwitchInfo(sw->m_isToR, sw->GetId());
                }
                if (lb_mode == 9) {
                    sw->m_mmu->m_conweaveRouting.SetConstants(
                        conweave_extraReplyDeadline, conweave_extraVOQFlushTime,
                        conweave_txExpiryTime, conweave_defaultVOQWaitingTime,
                        conweave_pathPauseTime, conweave_pathAwareRerouting);
                    sw->m_mmu->m_conweaveRouting.SetSwitchInfo(sw->m_isToR, sw->GetId());
                }
            }
        }

        // schedule conga timeout monitor
        if (lb_mode == 3) {  // CONGA
            Simulator::Schedule(Seconds(flowgen_stop_time + simulator_extra_time),
                                conga_history_print);
        }
        if (lb_mode == 6) {  // LETFLOW
            Simulator::Schedule(Seconds(flowgen_stop_time + simulator_extra_time),
                                letflow_history_print);
        }
        if (lb_mode == 9) {  // CONWEAVE
            Simulator::Schedule(Seconds(flowgen_stop_time + simulator_extra_time),
                                conweave_history_print);
        }
    }

    // populate routing tables (although we use our custom impl in switch_node.cc)
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    if (!Ws31NativeRequested()) {
        // maintain port number for each host
        for (uint32_t i = 0; i < node_num; i++) {
            if (n.Get(i)->GetNodeType() == 0) {
                portNumber[i] = 10000;  // each host use port number from 10000
                dportNumber[i] = 100;
            }
        }

        flow_input.idx = 0;
        port_per_host = new uint16_t[node_num - switch_num];
        if (flow_num > 0) {
            // generate flows
            ReadFlowInput();
            Simulator::Schedule(Seconds(0), &ScheduleFlowInputs, flow_input_stream);
        }
    }

    topof.close();
    if (Ws31NativeRequested()) return RunWs31NativeOs2();

    // schedule link down
    if (link_down_time > 0) {
        Simulator::Schedule(Seconds(flowgen_start_time) + MicroSeconds(link_down_time),
                            &TakeDownLink, n, n.Get(link_down_A), n.Get(link_down_B));
    }

    if (ws23_pfc_probe_host >= 0) {
        if (!enable_pfc || !enable_irn || lb_mode != 0 ||
            uint32_t(ws23_pfc_probe_host) >= Settings::host_num ||
            ws23_pfc_probe_pg >= QbbNetDevice::qCnt ||
            ws23_pfc_probe_start_ns == 0 ||
            ws23_pfc_probe_start_ns >= ws23_pfc_probe_end_ns ||
            ws23_pfc_probe_end_ns >= uint64_t((flowgen_stop_time - flowgen_start_time) * 1e9)) {
            NS_FATAL_ERROR("Invalid WS-23 PFC probe configuration");
        }
        Ptr<Node> host = n.Get(uint32_t(ws23_pfc_probe_host));
        Ptr<QbbNetDevice> switchPort;
        for (const auto &neighbor : nbr2if[host]) {
            if (neighbor.first->GetNodeType() != 1) continue;
            if (switchPort) NS_FATAL_ERROR("WS-23 probe host has multiple switch links");
            uint32_t port = nbr2if[neighbor.first][host].idx;
            switchPort = DynamicCast<QbbNetDevice>(neighbor.first->GetDevice(port));
        }
        if (!switchPort) NS_FATAL_ERROR("WS-23 probe host has no switch link");
        Simulator::Schedule(Seconds(flowgen_start_time) + NanoSeconds(ws23_pfc_probe_start_ns),
                            &Ws23InjectPfc, switchPort, uint32_t(ws23_pfc_probe_host),
                            ws23_pfc_probe_pg, 0U);
        Simulator::Schedule(Seconds(flowgen_start_time) + NanoSeconds(ws23_pfc_probe_end_ns),
                            &Ws23InjectPfc, switchPort, uint32_t(ws23_pfc_probe_host),
                            ws23_pfc_probe_pg, 1U);
    }

    if (lb_mode == 9) {
        voq_output = fopen(voq_mon_file.c_str(), "w");                // specific to ConWeave
        voq_detail_output = fopen(voq_mon_detail_file.c_str(), "w");  // specific to ConWeave
    }

    uplink_output = fopen(uplink_mon_file.c_str(), "w");  // common
    conn_output = fopen(conn_mon_file.c_str(), "w");      // common

    // update torId2UplinkIf, torId2DownlinkIf
    for (size_t ToRId = 0; ToRId < Settings::node_num; ToRId++) {
        Ptr<Node> node = n.Get(ToRId);
        if (node->GetNodeType() == 1) {  // switches
            auto swNode = DynamicCast<SwitchNode>(n.Get(ToRId));
            if (swNode->m_isToR) {  // TOR switch
                for (auto &nextNodeIf : nbr2if[node]) {
                    if (nextNodeIf.first->GetNodeType() ==
                        1) {  // nextNode is switch (i.e., uplink)
                        auto &vec = torId2UplinkIf[ToRId];
                        vec.push_back(
                            nextNodeIf.second.idx);  // record this uplink port (outDev index)
                        // printf("Sw %lu - uplink port %u\n", ToRId, nextNodeIf.second.idx);  //
                        // debugging
                    } else {
                        auto &vec = torId2DownlinkIf[ToRId];
                        vec.push_back(
                            nextNodeIf.second.idx);  // record this downlink port (outDev index)
                        // printf("Sw %lu - downlink port %u\n", ToRId, nextNodeIf.second.idx);  //
                        // debugging
                    }
                }
            }
        }
    }
    Simulator::Schedule(Seconds(flowgen_start_time), &periodic_monitoring, voq_output,
                        voq_detail_output, uplink_output, conn_output, &lb_mode);

    //
    // Now, do the actual simulation.
    //
    std::cout << "------------------------------------------" << std::endl;
    std::cout << "Running Simulation.\n";
    fflush(stdout);
    NS_LOG_INFO("Run Simulation.");
    Simulator::Schedule(Seconds(flowgen_start_time),
                        &stop_simulation_middle);  // check every 100us
    Simulator::Stop(Seconds(flowgen_stop_time + 10.0));
    if (ws21_port_events)
        for (const auto &entry : idxNodeToR)
            entry.second->RecordWs21PortBoundary('B');
    Ws30CompositionInstall(n, flowgen_start_time);
    Simulator::Run();
    if (ws31::StartMode(lb_mode)) {
        const ws31::StartCounters &s=ws31::StartData();
        if (s.launched+s.cancelled>s.demanded || s.finished>s.launched ||
            s.launchBytes+s.cancelBytes>s.demandBytes || s.finishBytes>s.launchBytes)
            NS_FATAL_ERROR("C2 request or byte accounting is inconsistent");
        std::cout << "WS31_C2_STATE demanded=" << s.demanded << " launched=" << s.launched
                  << " cancelled=" << s.cancelled << " finished=" << s.finished
                  << " pending=" << s.demanded-s.launched-s.cancelled
                  << " unfinished=" << s.launched-s.finished
                  << " demand_bytes=" << s.demandBytes << " launch_bytes=" << s.launchBytes
                  << " cancel_bytes=" << s.cancelBytes << " finish_bytes=" << s.finishBytes
                  << " waited=" << s.waited << " delay_sum_ns=" << s.delaySum
                  << " delay_max_ns=" << s.delayMax
                  << " eligible=" << s.eligible << " planned_waited=" << s.plannedWaited
                  << " planned_delay_sum_ns=" << s.plannedDelaySum
                  << " planned_delay_max_ns=" << s.plannedDelayMax
                  << " eligibility_hashes=" << s.eligibilityHashes
                  << " delay_hashes=" << s.delayHashes
                  << " size_comparisons=" << s.sizeComparisons
                  << " frozen_max_ns=500" << std::endl;
    }
    if (lb_mode == 9) Ws30CwPrint();
    Ws30CompositionFinish();
    for (uint32_t i=0; i<n.GetN(); ++i) {
        Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
        if (sw) sw->WriteWs30V13State();
    }
    if (ws21_port_events)
        for (const auto &entry : idxNodeToR)
            entry.second->RecordWs21PortBoundary('F');
    if (lb_mode == 20) {
        uint64_t released = 0, finished = 0, input_bytes = 0, finished_bytes = 0;
        for (const Ws18Flow &flow : ws18_flows) {
            released += flow.released;
            finished += flow.finished;
            input_bytes += flow.bytes;
            if (flow.finished) finished_bytes += flow.bytes;
        }
        std::cout << "WS18_CONSERVATION input=" << ws18_flows.size()
                  << " released=" << released << " finished=" << finished
                  << " input_bytes=" << input_bytes << " finished_bytes=" << finished_bytes
                  << std::endl;
        fclose(ws18_output);
    }

    if (ws21_identity) {
        FILE *identity = fopen(ws21_identity_output_file.c_str(), "w");
        if (!identity)
            NS_FATAL_ERROR("WS-21 cannot open identity output");
        fprintf(identity, "side tor src dst sport dport first_port packets upstream_ce first_ns last_ns inconsistent unmapped\n");
        for (uint32_t i = 0; i < node_num; ++i)
            if (n.Get(i)->GetNodeType() == 1)
                DynamicCast<SwitchNode>(n.Get(i))->WriteWs21Identity(identity);
        fclose(identity);
    }
    if (ws21_port_events) {
        SwitchNode::FinishWs21PortEvents();
        fclose(ws21_port_output);
    }
    SwitchNode::PrintWorkloadTagCounts();

    /*-----------------------------------------------------------------------------*/
    /*----- we don't need below. Just we can enforce to close this simulation. -----*/
    /*-----------------------------------------------------------------------------*/
    Simulator::Destroy();
    NS_LOG_INFO("Total number of packets: " << RdmaHw::nAllPkts);
    NS_LOG_INFO("Done.");
    endt = clock();
    std::cerr << (double)(endt - begint) / CLOCKS_PER_SEC << "\n";
}
