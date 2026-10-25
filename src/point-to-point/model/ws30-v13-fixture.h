#ifndef WS30_V13_FIXTURE_H
#define WS30_V13_FIXTURE_H
#include <cstdlib>
namespace ns3 {
// Explicit experiment interventions; all default to off, never inferred from tags.
inline unsigned Ws30V13Env(const char *name) {
    const char *p = std::getenv(name);
    return p && p[0]>='0' && p[0]<='4' && p[1]=='\0' ? unsigned(p[0]-'0') : 0U;
}
inline unsigned Ws30V13Life() { return Ws30V13Env("WS30_LIFECYCLE"); }
inline unsigned Ws30V13TagTransform() { return Ws30V13Env("WS30_TAG_TRANSFORM"); }
}
#endif
