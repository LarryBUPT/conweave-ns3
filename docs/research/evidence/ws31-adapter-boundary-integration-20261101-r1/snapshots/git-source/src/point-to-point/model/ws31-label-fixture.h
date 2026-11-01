#ifndef WS31_LABEL_FIXTURE_H
#define WS31_LABEL_FIXTURE_H

#include <cstdint>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include "ws31-start.h"

namespace ns3 { namespace ws31 {

// Test-only visibility; the QP's business label and demand origin never change.
struct VisibleLabel {
    uint32_t value;
    bool present;
    VisibleLabel(uint32_t v, bool p) : value(v), present(p) {}
};

inline unsigned ParseLabelProfile(const char *value) {
    if (!value || !*value) return 0;
    if (value[0]>='0' && value[0]<='3' && value[1]=='\0')
        return unsigned(value[0]-'0');
    throw std::invalid_argument("WS31_LABEL_PROFILE must be a single digit 0..3");
}
inline unsigned LabelProfile() {
    static const unsigned profile=ParseLabelProfile(std::getenv("WS31_LABEL_PROFILE"));
    return profile;
}
struct LabelRunContext {
    int pfc, irn;
    uint32_t ccMode;
    std::string topology, flow;
    bool fault, diagnostic;
    LabelRunContext(int p, int i, uint32_t cc, const std::string &topo,
                    const std::string &trace, bool f, bool d)
        : pfc(p), irn(i), ccMode(cc), topology(topo), flow(trace), fault(f), diagnostic(d) {}
};
inline bool LabelDiagnosticValue(const char *value) {
    return value && *value && std::string(value)!="0";
}
inline bool LabelDiagnosticEnvironment() {
    const char *keys[]={"WS13_DIAG","WS25_DIAG","WS28_TAIL_DIAG","IRN_PFC_DROP_DIAG",
        "WS23_RECOVERY_DIAG","WS26_MOE_HOP_DIAG","WS26_QUEUE_FRONT_DIAG",
        "WS26_TIME_PROBE","WS26_SEED97_TIME_DIAG"};
    for (const char *key : keys)
        if (LabelDiagnosticValue(std::getenv(key))) return true;
    return false;
}
inline void ValidateLabelProfile(unsigned profile, uint32_t mode, unsigned transform,
                                 unsigned composition, unsigned lifecycle,
                                 unsigned lifeProfile, unsigned observe,
                                 const LabelRunContext &context) {
    if (profile>3) throw std::invalid_argument("Unknown WS31 label profile");
    if (!profile) return;
    const std::string prefix="config/ws31_";
    const bool trace=context.flow.compare(0,prefix.size(),prefix)==0 &&
        context.flow.size()>prefix.size()+4 &&
        context.flow.compare(context.flow.size()-4,4,".txt")==0 &&
        context.flow.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-",
                                        7)==std::string::npos;
    if (mode<36 || mode>50 || transform || composition || lifecycle || lifeProfile ||
        observe!=2 || context.pfc!=0 || context.irn!=1 || context.ccMode!=1 ||
        context.topology!="config/leaf_spine_128_100G_OS2.txt" || !trace ||
        context.fault || context.diagnostic)
        throw std::invalid_argument("WS31 label fixture requires isolated WS31 mode and full observation");
}

inline VisibleLabel LabelAt(unsigned profile, uint32_t original, uint64_t demand,
                             uint64_t now, uint32_t sip, uint32_t dip,
                             uint16_t sport, uint16_t dport, unsigned transform=0) {
    if (profile>3 || (profile && transform))
        throw std::invalid_argument("Invalid or conflicting WS31 label intervention");
    if (!profile)
        return VisibleLabel(StartPolicyTag(original,transform), transform!=1);
    if (now<demand) throw std::invalid_argument("Label sample precedes original demand");
    const uint64_t elapsed=now-demand;
    if (profile==1 && elapsed<500) return VisibleLabel(0,false);
    const bool swap=(profile==2 && elapsed>=500) ||
                    (profile==3 && (StartHash(sip,dip,sport,dport)&3U)==0);
    return VisibleLabel(swap && (original==1 || original==2) ? 3-original : original,true);
}

}} // namespace ns3::ws31
#endif
