#ifndef WS30_V13_FIXTURE_H
#define WS30_V13_FIXTURE_H
#include <cstdlib>
namespace ns3 {
// Explicit experiment interventions; all default to off, never inferred from tags.
inline unsigned Ws30V13Env(const char *name) {
    const char *p = std::getenv(name);
    return p && p[0]>='0' && p[0]<='8' && p[1]=='\0' ? unsigned(p[0]-'0') : 0U;
}
inline bool Ws30V14Enabled() { return Ws30V13Env("WS30_LIFECYCLE")>=5; }
inline unsigned Ws30V13Life() { unsigned n=Ws30V13Env("WS30_LIFECYCLE"); return n>=5?n-4:n; }
inline unsigned Ws30V14Profile() { return Ws30V13Env("WS30_LIFE_PROFILE"); }
inline unsigned Ws30RoundBytes() { return Ws30V14Enabled() && Ws30V14Profile()==2?262144U:8192U; }
inline unsigned Ws30RoundIntervalNs() { return Ws30V14Enabled() && Ws30V14Profile()==2?10000000U:100000U; }
inline unsigned Ws30V13TagTransform() { return Ws30V13Env("WS30_TAG_TRANSFORM"); }
}
#endif
