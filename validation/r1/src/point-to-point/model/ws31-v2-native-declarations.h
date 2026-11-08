#ifndef WS31_V2_NATIVE_DECLARATIONS_H
#define WS31_V2_NATIVE_DECLARATIONS_H

// Declaration codec only: no ns-3 object, event, QP, tag producer or execution gate.
#include <cstdint>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace ws31v2 {
static const char *const ProtocolSha = "5d676baeb674f488fe25686207be3fb9925b007d238c1fa1f340e04d1c9310c8";
static const char *const ConstructorSha = "261cee65f90dd72119694f00d93778e705ec59fa84b302984cc64000b1ebdc8d";

inline void Need(bool ok, const char *message) {
    if (!ok) throw std::invalid_argument(std::string("WS31 declaration: ")+message);
}
inline std::vector<std::string> Words(const std::string &line) {
    std::istringstream in(line); std::vector<std::string> values; std::string word;
    while (in>>word) values.push_back(word);
    return values;
}
inline uint64_t Number(const std::string &word) {
    Need(!word.empty() && (word.size()==1 || word[0]!='0'), "non-canonical integer");
    uint64_t value=0, limit=std::numeric_limits<uint64_t>::max();
    for (unsigned char c:word) {
        Need(c>='0' && c<='9', "non-decimal integer");
        uint64_t digit=c-'0';
        Need(value<=(limit-digit)/10, "integer overflow");
        value=value*10+digit;
    }
    return value;
}
inline uint32_t NodeIp(uint32_t node) {
    Need(node<128, "host outside OS2");
    return 0x0b000001U+(node/256)*0x00010000U+(node%256)*0x00000100U;
}

struct Declaration {
    int32_t id;
    uint64_t generation;
    uint32_t source, destination, sourceIp, destinationIp;
    uint16_t pg;
    uint32_t bytes;
    uint64_t demandNs;
    uint32_t originalTag;
    bool policyPresent;
    uint32_t policyTag;
    uint16_t sport, dport, flowId;
};
struct DeclaredInput {
    std::string family;
    uint64_t seed, t0, horizon, stop, referenceWireBytes;
    std::vector<Declaration> requests;
};

inline DeclaredInput ReadDeclarations(std::istream &in) {
    std::string line;
    Need(bool(std::getline(in,line)), "missing header");
    const auto header=Words(line);
    Need(header.size()==10 && header[0]=="WS31_V2_DECL_R1" && header[1]=="K0", "schema/stage");
    DeclaredInput input;
    input.family=header[2];
    Need(input.family=="D1" || input.family=="D2", "family");
    input.seed=Number(header[3]);
    const uint64_t count=Number(header[4]);
    input.t0=Number(header[5]); input.horizon=Number(header[6]); input.stop=Number(header[7]);
    Need(input.seed>=5310001 && input.seed<=5310008 && count==1120, "K0 seed/count");
    Need(input.t0==2005000000ULL && input.horizon==(input.family=="D1"?550400ULL:4671488ULL), "reference times");
    const uint64_t tail=input.horizon*10>10000000ULL?input.horizon*10:10000000ULL;
    Need(input.stop==input.t0+input.horizon+tail &&
         input.stop<=uint64_t(std::numeric_limits<int64_t>::max()), "stop time");
    Need(Number(header[8])==1000 && Number(header[9])==48, "reference framing");
    Need(bool(std::getline(in,line)), "missing protocol");
    auto words=Words(line);
    Need(words.size()==2 && words[0]=="PROTOCOL_SHA256" && words[1]==ProtocolSha, "protocol identity");
    Need(bool(std::getline(in,line)), "missing constructor");
    words=Words(line);
    Need(words.size()==2 && words[0]=="CONSTRUCTOR_SHA256" && words[1]==ConstructorSha, "constructor identity");
    std::set<std::tuple<uint32_t,uint32_t,uint16_t,uint16_t> > keys;
    std::map<std::pair<uint32_t,uint32_t>,uint64_t> sourceCounts, destinationCounts, sizes;
    std::map<std::pair<uint64_t,uint32_t>,uint64_t> waves;
    std::map<uint32_t,uint32_t> fixedSize;
    input.referenceWireBytes=0;
    uint64_t previous=0;
    input.requests.reserve(1120);
    for (uint64_t ordinal=0;ordinal<count;++ordinal) {
        Need(bool(std::getline(in,line)), "truncated requests"); words=Words(line);
        Need(words.size()==15, "row width");
        uint64_t v[15]; for (size_t i=0;i<15;++i) v[i]=Number(words[i]);
        Need(v[0]==ordinal && v[14]==ordinal && v[1]==0, "identity/order/generation");
        Need(v[2]<16 && v[3]>=64 && v[3]<80, "endpoint range");
        Need(v[4]==NodeIp(uint32_t(v[2])) && v[5]==NodeIp(uint32_t(v[3])), "IP binding");
        Need(v[6]==3 && v[12]>0 && v[12]<=65535 && v[13]>0 && v[13]<=65535, "PG/ports");
        Need(v[8]>=input.t0 && v[8]<input.t0+input.horizon && v[8]>=previous, "demand/order");
        previous=v[8];
        Need(v[9]==1 || v[9]==2, "original class");
        Need(v[10]<=1 && v[11]<=std::numeric_limits<uint32_t>::max(), "policy encoding");
        Need(v[10]!=0 || v[11]==0, "absent policy must be canonical0");
        Need(v[7]==16384 || (input.family=="D2" && v[7]==262144), "size");
        Declaration r={int32_t(v[0]),v[1],uint32_t(v[2]),uint32_t(v[3]),uint32_t(v[4]),uint32_t(v[5]),
                       uint16_t(v[6]),uint32_t(v[7]),v[8],uint32_t(v[9]),v[10]!=0,uint32_t(v[11]),
                       uint16_t(v[12]),uint16_t(v[13]),uint16_t(v[14])};
        Need(keys.insert(std::make_tuple(r.sourceIp,r.destinationIp,r.sport,r.dport)).second, "duplicate route key");
        ++sourceCounts[std::make_pair(r.originalTag,r.source)];
        ++destinationCounts[std::make_pair(r.originalTag,r.destination)];
        ++sizes[std::make_pair(r.originalTag,r.bytes)];
        input.referenceWireBytes+=r.bytes+48*((uint64_t(r.bytes)+999)/1000);
        if (input.family=="D1" && r.originalTag==2) {
            bool wave=false;
            for (uint64_t k=0;k<6;++k) if (r.demandNs==input.t0+k*input.horizon/6) wave=true;
            Need(wave, "D1 wave time"); ++waves[std::make_pair(r.demandNs,r.source)];
        }
        if (input.family=="D2") {
            const auto item=fixedSize.insert(std::make_pair(r.source,r.bytes));
            Need(item.second || item.first->second==r.bytes, "D2 common source size");
            Need((r.bytes==16384)==(r.destination<72), "D2 destination size half");
        }
        input.requests.push_back(r);
    }
    Need(!std::getline(in,line), "extra request row");
    Need(in.eof() && !in.bad(), "input read failure");
    for (uint32_t tag=1;tag<=2;++tag) {
        const uint64_t expected=tag==1?64:6;
        for (uint32_t src=0;src<16;++src) Need(sourceCounts[std::make_pair(tag,src)]==expected, "source class margins");
        for (uint32_t dst=64;dst<80;++dst) Need(destinationCounts[std::make_pair(tag,dst)]==expected, "destination class margins");
    }
    if (input.family=="D1") {
        for (uint64_t k=0;k<6;++k) for (uint32_t src=0;src<16;++src)
            Need(waves[std::make_pair(input.t0+k*input.horizon/6,src)]==1, "D1 wave sources");
    } else {
        Need(sizes[std::make_pair(1,16384)]==512 && sizes[std::make_pair(1,262144)]==512 &&
             sizes[std::make_pair(2,16384)]==48 && sizes[std::make_pair(2,262144)]==48, "D2 class sizes");
    }
    Need(input.horizon==(8*input.referenceWireBytes+279)/280, "reference byte arithmetic");
    return input;
}
} // namespace ws31v2
#endif
