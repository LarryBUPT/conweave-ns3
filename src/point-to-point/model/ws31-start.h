#ifndef WS31_START_H
#define WS31_START_H

#include <cstdint>

namespace ns3 { namespace ws31 {

inline bool StartMode(uint32_t mode) { return (mode >= 43 && mode <= 46) || mode == 55 || mode == 56; }

struct StartSizeControl {
    uint64_t targetBytes=0;
    uint32_t cutoff=0;
};
inline StartSizeControl &StartSizeData() { static StartSizeControl c; return c; }
inline void ConfigureStartSizeControl(uint64_t targetBytes, uint32_t cutoff) {
    StartSizeData().targetBytes=targetBytes;
    StartSizeData().cutoff=cutoff;
}

// Match the packet-label intervention without changing the business label
// retained by the QP and completion metrics. Missing packet tags read as zero.
inline uint32_t StartPolicyTag(uint32_t tag, unsigned transform) {
    if (transform == 1) return 0;
    if (transform == 2 && (tag == 1 || tag == 2)) return 3-tag;
    return tag;
}

// Fixed, byte-order-independent tuple hash; consumes no simulator RNG draws.
inline uint32_t StartHash(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport) {
    const uint32_t words[3] = {sip, dip, uint32_t(sport) | (uint32_t(dport) << 16)};
    uint32_t h = 2166136261U ^ 0x43c2a517U;
    for (unsigned i=0; i<3; ++i)
        for (unsigned j=0; j<4; ++j) { h ^= (words[i] >> (8*j)) & 255U; h *= 16777619U; }
    h ^= h >> 16; h *= 0x85ebca6bU; h ^= h >> 13;
    return h;
}

// The category-blind eligibility draw uses a separate hash domain from delay.
inline uint32_t StartEligibilityHash(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport) {
    const uint32_t words[3] = {sip, dip, uint32_t(sport) | (uint32_t(dport) << 16)};
    uint32_t h = 2166136261U ^ 0x53c2a517U;
    for (unsigned i=0; i<3; ++i)
        for (unsigned j=0; j<4; ++j) { h ^= (words[i] >> (8*j)) & 255U; h *= 16777619U; }
    h ^= h >> 16; h *= 0x85ebca6bU; h ^= h >> 13;
    return h;
}

inline bool StartHashEligible(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport) {
    return StartEligibilityHash(sip,dip,sport,dport) % 35U < 3U;
}

struct StartDecision {
    bool eligible=false;
    uint64_t delayNs=0;
    uint32_t eligibilityHashes=0, delayHashes=0, sizeComparisons=0;
};
inline StartDecision DecideStart(uint32_t mode, uint32_t tag, uint64_t size,
                                 uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport,
                                 uint32_t maxNs=500) {
    StartDecision result;
    if (mode==43) result.eligible=tag==2;
    else if (mode==44) result.eligible=true;
    else if (mode==45) { result.sizeComparisons=1; result.eligible=size==8192; }
    else if (mode==55) {
        result.eligibilityHashes=1;
        result.eligible=StartHashEligible(sip,dip,sport,dport);
    } else if (mode==56) {
        result.sizeComparisons=1;
        const StartSizeControl &c=StartSizeData();
        if (size==c.targetBytes) {
            result.eligibilityHashes=1;
            result.eligible=StartEligibilityHash(sip,dip,sport,dport)%35U<c.cutoff;
        }
    }
    if (result.eligible && maxNs) {
        result.delayHashes=1;
        result.delayNs=uint64_t(StartHash(sip,dip,sport,dport))%(uint64_t(maxNs)+1);
    }
    return result;
}
inline uint64_t StartDelay(uint32_t mode, uint32_t tag, uint64_t size,
                           uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport,
                           uint32_t maxNs=500) {
    return DecideStart(mode,tag,size,sip,dip,sport,dport,maxNs).delayNs;
}

// Process-local accounting only. No decision uses these observations.
struct StartCounters {
    uint64_t demanded=0, launched=0, cancelled=0, finished=0;
    uint64_t demandBytes=0, launchBytes=0, cancelBytes=0, finishBytes=0;
    uint64_t waited=0, delaySum=0, delayMax=0;
    uint64_t eligible=0, plannedWaited=0, plannedDelaySum=0, plannedDelayMax=0;
    uint64_t eligibilityHashes=0, delayHashes=0, sizeComparisons=0;
};
inline StartCounters &StartData() { static StartCounters s; return s; }

}} // namespace ns3::ws31
#endif
