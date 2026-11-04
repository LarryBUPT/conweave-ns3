// WIP real entry: parsed-context/full-input stage only. No network execution,
// guard installation, or drain certificate exists in this revision.
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "../src/point-to-point/model/ws31-endpoint-identity.h"
#include "../src/point-to-point/model/ws31-start.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <limits>
#include <cstdlib>
#include <cctype>
#include <set>
#include <vector>

#ifdef _WIN32
extern char **_environ;
#else
extern char **environ;
#endif

using namespace ns3;

namespace {
void Require(bool ok,const std::string &message) {
    if (!ok) throw std::invalid_argument(message);
}
std::vector<std::string> Words(const std::string &line) {
    std::istringstream in(line); std::vector<std::string> values; std::string value;
    while (in>>value) values.push_back(value);
    return values;
}
uint64_t Unsigned(const std::string &word,uint64_t limit,const char *field) {
    Require(!word.empty(),std::string("Empty endpoint input field: ")+field);
    uint64_t value=0;
    for (unsigned char c:word) {
        Require(c>='0' && c<='9',std::string("Non-decimal endpoint input field: ")+field);
        const uint64_t digit=c-'0';
        Require(digit<=limit && value<=(limit-digit)/10,
                std::string("Overflow in endpoint input field: ")+field);
        value=value*10+digit;
    }
    return value;
}
struct Configuration {
    uint32_t mode=0,cc=0,pfc=0,irn=0,mtu=0,observe=0,seed=0;
    uint64_t stopNs=0;
    std::string topology,flow;
};
struct Request {
    int32_t id=-1;
    uint32_t source=0,destination=0;
    ws31::EndpointLedger::Entry declared;
    uint64_t launchNs=0;
};
Configuration ReadConfiguration(const std::string &path) {
    std::ifstream in(path.c_str()); Require(in.is_open(),"Cannot open endpoint configuration");
    std::map<std::string,std::string> fields; std::string line;
    const std::set<std::string> allowed={"LB_MODE","CC_MODE","PFC","IRN","MTU",
        "OBSERVE","SEED","STOP_NS","TOPOLOGY","FLOW_FILE"};
    while (std::getline(in,line)) {
        const auto words=Words(line); if (words.empty()) continue;
        Require(words.size()==2 && allowed.count(words[0]),"Unknown or malformed endpoint configuration row");
        Require(fields.insert(std::make_pair(words[0],words[1])).second,
                "Repeated endpoint configuration key");
    }
    Require(in.eof() && fields.size()==allowed.size(),"Incomplete endpoint configuration");
    Configuration c;
    c.mode=Unsigned(fields.at("LB_MODE"),50,"LB_MODE");
    c.cc=Unsigned(fields.at("CC_MODE"),8,"CC_MODE");
    c.pfc=Unsigned(fields.at("PFC"),1,"PFC"); c.irn=Unsigned(fields.at("IRN"),1,"IRN");
    c.mtu=Unsigned(fields.at("MTU"),65535,"MTU");
    c.observe=Unsigned(fields.at("OBSERVE"),2,"OBSERVE");
    c.seed=Unsigned(fields.at("SEED"),std::numeric_limits<uint32_t>::max(),"SEED");
    c.stopNs=Unsigned(fields.at("STOP_NS"),1000000000ULL,"STOP_NS");
    c.topology=fields.at("TOPOLOGY"); c.flow=fields.at("FLOW_FILE");
    Require(c.mode>=33 && c.mode<=50 && c.cc==1 && c.pfc==0 && c.irn==1 &&
            c.mtu==1024 && c.observe==2 && c.seed>0 && c.stopNs>0 &&
            c.topology=="ws31_two_host_two_switch_v1",
            "Endpoint parsed context requires isolated mode33..50, CC1/PFC0/IRN1/MTU1024/observe2 and exact topology");
    const std::string prefix="config/ws31_endpoint_";
    Require(c.flow.compare(0,prefix.size(),prefix)==0 && c.flow.size()>prefix.size()+4 &&
            c.flow.compare(c.flow.size()-4,4,".txt")==0 &&
            c.flow.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-",7)==std::string::npos &&
            c.flow.find("..",7)==std::string::npos,
            "Endpoint FLOW_FILE must be a frozen config/ws31_endpoint_*.txt input");
    return c;
}
void CheckEnvironment(const Configuration &c) {
    const char *observe=std::getenv("WS30_OBSERVE");
    Require(c.observe==2 && observe && std::string(observe)=="2",
            "Endpoint actual observation environment differs from parsed context");
#ifdef _WIN32
    char **values=_environ;
#else
    char **values=environ;
#endif
    for (char **entry=values;entry && *entry;++entry) {
        const std::string item(*entry); const auto split=item.find('=');
        if (split==std::string::npos) continue;
        const std::string key=item.substr(0,split),value=item.substr(split+1);
        const bool workflow=key.size()>4 && key[0]=='W' && key[1]=='S' &&
            key[2]>='0' && key[2]<='9' && key[3]>='0' && key[3]<='9' && key[4]=='_';
        if (key=="WS30_OBSERVE") continue;
        const bool diagnostic=key.compare(0,8,"IRN_PFC_")==0;
        const bool hiddenConfiguration=key=="NS_ATTRIBUTE_DEFAULT" || key=="NS_GLOBAL_VALUE";
        Require(!hiddenConfiguration || value.empty(),
                "Endpoint entry refuses hidden ns-3 global/default configuration");
        Require(!(workflow || diagnostic) || value.empty() || value=="0",
                "Endpoint input stage refuses active inherited workflow/diagnostic/configuration environment");
    }
}
uint32_t ExpectedHostIp(uint32_t index) {
    Require(index<2,"Endpoint input contains a non-host node");
    return 0x0b000001U+(index<<8);
}
std::vector<Request> ReadAllRequests(const Configuration &c) {
    std::ifstream in(c.flow.c_str()); Require(in.is_open(),"Cannot open complete endpoint request input");
    std::string line; Require(bool(std::getline(in,line)),"Missing endpoint request count");
    const auto header=Words(line); Require(header.size()==1,"Malformed endpoint request-count header");
    const uint64_t rows=Unsigned(header[0],65536,"request_count");
    Require(rows>0,"Endpoint input has no requests");
    std::vector<Request> result; result.reserve(rows);
    std::map<ws31::EndpointKey,std::pair<uint64_t,uint64_t>> prior;
    uint32_t perHost[2]={0,0};
    // These are provisional, immutable declarations. Creating the actual
    // ledger generations remains a later event action; Declare is not Begin.
    auto ledger=std::make_shared<ws31::EndpointLedger>();
    Ws31EndpointIdentity manifest(ledger);
    for (uint64_t ordinal=0;ordinal<rows;++ordinal) {
        Require(bool(std::getline(in,line)),"Endpoint input ends before declared request count");
        const auto words=Words(line);
        // id generation src dst pg bytes demand_ns original_tag sport dport
        Require(words.size()==10,"Endpoint request must contain exactly ten columns");
        Request request;
        request.id=Unsigned(words[0],65535,"id");
        Require(uint64_t(request.id)==ordinal,"Endpoint IDs must equal full-input ordinal");
        auto &e=request.declared;
        e.generation=Unsigned(words[1],std::numeric_limits<uint64_t>::max(),"generation");
        request.source=Unsigned(words[2],1,"source"); request.destination=Unsigned(words[3],1,"destination");
        Require(request.source!=request.destination,"Endpoint source and destination must differ");
        const uint16_t pg=Unsigned(words[4],QbbNetDevice::qCnt-1,"pg");
        e.bytes=Unsigned(words[5],std::numeric_limits<uint32_t>::max(),"bytes");
        Require(e.bytes>0,"Endpoint request must have positive payload");
        e.demandNs=Unsigned(words[6],uint64_t(std::numeric_limits<int64_t>::max()),"demand_ns");
        e.originalTag=Unsigned(words[7],std::numeric_limits<uint32_t>::max(),"original_tag");
        const uint16_t sport=Unsigned(words[8],65535,"sport"),dport=Unsigned(words[9],65535,"dport");
        const uint32_t sip=ExpectedHostIp(request.source),dip=ExpectedHostIp(request.destination);
        e.tuple=ws31::EndpointKey(sip,dip,sport,dport,pg);
        e.resources.sourceNode=request.source; e.resources.destinationNode=request.destination;
        e.resources.txKey=RdmaHw::GetQpKey(dip,sport,dport,pg);
        e.resources.rxKey=RdmaHw::GetRxQpKey(sip,sport,dport,pg);
        const uint64_t wait=ws31::StartDelay(c.mode,e.originalTag,e.bytes,sip,dip,sport,dport);
        Require(e.demandNs<c.stopNs && wait<c.stopNs-e.demandNs,
                "Endpoint request launch reaches or exceeds parsed stop time");
        request.launchNs=e.demandNs+wait;
        auto old=prior.find(e.tuple);
        if (old==prior.end()) Require(e.generation==0,"First endpoint generation must be zero");
        else Require(old->second.first<std::numeric_limits<uint64_t>::max() &&
                     e.generation==old->second.first+1 && e.demandNs>old->second.second,
                     "Endpoint generation or demand order is invalid");
        Require(++perHost[request.source]<=ESTIMATED_MAX_FLOW_PER_HOST,
                "Retained sender slots exceed the production finished bitmap domain");
        manifest.Declare(request.id,e); // Includes packed-key/fourtuple alias checks.
        prior[e.tuple]=std::make_pair(e.generation,e.demandNs);
        result.push_back(request);
    }
    while (std::getline(in,line)) Require(Words(line).empty(),"Trailing undeclared endpoint request data");
    Require(in.eof(),"Endpoint request input read failed");
    manifest.Seal(rows); manifest.RequireHealthy();
    return result;
}
} // namespace

int main(int argc,char **argv) {
    try {
        Require(argc==3 || argc==4,"Usage: ws31-endpoint-network-test --config FILE [--validate-input-only]");
        Require(std::string(argv[1])=="--config","Endpoint entry requires explicit --config");
        const bool inputOnly=argc==4 && std::string(argv[3])=="--validate-input-only";
        Require(argc==3 || inputOnly,"Unknown endpoint entry option");
        // Complete parsing precedes any simulator, Node, device, driver, guard
        // installation, AddQueuePair, or scheduled request construction.
        const auto config=ReadConfiguration(argv[2]); CheckEnvironment(config);
        const auto requests=ReadAllRequests(config);
        Require(inputOnly,"Endpoint network entry WIP: actual topology/binder/callback/event gates not yet implemented");
        std::cout << "WS31_ENDPOINT_INPUT_ONLY rows=" << requests.size()
                  << " mode=" << config.mode << " cc=" << config.cc
                  << " pfc=" << config.pfc << " irn=" << config.irn
                  << " mtu=" << config.mtu << " observe=" << config.observe
                  << " seed=" << config.seed << " stop_ns=" << config.stopNs
                  << " actual_objects=0 network=0 full_runtime_G1=0" << std::endl;
        for (const auto &r:requests)
            std::cout << "WS31_ENDPOINT_INPUT_ROW id=" << r.id << " generation=" << r.declared.generation
                      << " source=" << r.source << " destination=" << r.destination
                      << " bytes=" << r.declared.bytes << " tag=" << r.declared.originalTag
                      << " demand_ns=" << r.declared.demandNs << " launch_ns=" << r.launchNs
                      << " tx_key=" << r.declared.resources.txKey << " rx_key=" << r.declared.resources.rxKey << std::endl;
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "WS31_ENDPOINT_ENTRY_REFUSED reason=\"" << e.what() << "\"" << std::endl;
        return 2;
    }
}
