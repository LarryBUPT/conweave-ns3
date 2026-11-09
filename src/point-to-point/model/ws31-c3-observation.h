#ifndef WS31_C3_OBSERVATION_H
#define WS31_C3_OBSERVATION_H

#include <cstdint>

namespace ns3 {

// The simulator runs these observation callbacks serially. One counter shared
// by all translation units preserves order when events have the same time.
inline uint64_t NextWs31C3ObservationEvent() {
    static uint64_t next=0;
    return ++next;
}

inline uint64_t NextWs31C3DeliveryToken() {
    static uint64_t next=0;
    return ++next;
}

}

#endif
