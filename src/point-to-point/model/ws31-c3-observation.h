#ifndef WS31_C3_OBSERVATION_H
#define WS31_C3_OBSERVATION_H

#include <cstdint>
#include <map>
#include <utility>

#include "ns3/packet.h"
#include "ns3/ptr.h"

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

// SwitchNotifyDequeue has already verified the source-ToR UDP header. Carry
// that observation across the device/channel calls without parsing it again.
inline std::map<const Packet*,std::pair<uint32_t,uint32_t> >& Ws31C3SourcePackets() {
    static std::map<const Packet*,std::pair<uint32_t,uint32_t> > packets;
    return packets;
}

inline void MarkWs31C3SourcePacket(Ptr<const Packet> packet, uint32_t node,
                                   uint32_t port) {
    Ws31C3SourcePackets()[PeekPointer(packet)]=std::make_pair(node,port);
}

inline bool IsWs31C3SourcePacket(Ptr<const Packet> packet, uint32_t node,
                                 uint32_t port) {
    const auto it=Ws31C3SourcePackets().find(PeekPointer(packet));
    return it!=Ws31C3SourcePackets().end() && it->second.first==node &&
           it->second.second==port;
}

inline void ForgetWs31C3SourcePacket(Ptr<const Packet> packet) {
    Ws31C3SourcePackets().erase(PeekPointer(packet));
}

}

#endif
