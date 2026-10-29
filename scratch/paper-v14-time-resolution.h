#ifndef PAPER_V14_TIME_RESOLUTION_H
#define PAPER_V14_TIME_RESOLUTION_H
#include "ns3/nstime.h"
#include "ns3/type-id.h"
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
namespace ns3 {
inline const char *Pv14ResolutionName() {
    const char *value=std::getenv("PAPER_V14_TIME_RESOLUTION");
    return value ? value:"ns";
}
inline uint64_t Pv14TicksPerSecond() {
    return Time::GetResolution()==Time::FS ? 1000000000000000ULL:
           Time::GetResolution()==Time::PS ? 1000000000000ULL:1000000000ULL;
}
inline double Pv14MaximumSeconds() {
    return double(std::numeric_limits<int64_t>::max())/Pv14TicksPerSecond();
}
inline bool Pv14SubNanosecond() {return Time::GetResolution()!=Time::NS;}
inline bool Pv14InitializeResolution() {
    static bool attempted=false;
    if(attempted){std::cerr<<"PV14_TIME_ERROR repeated initialization\n";return false;}
    attempted=true;
    const std::string unit(Pv14ResolutionName());
    if(unit!="ns" && unit!="ps" && unit!="fs") {
        std::cerr<<"PV14_TIME_ERROR invalid resolution\n";return false;
    }
    if(Time::GetResolution()!=Time::NS) {
        std::cerr<<"PV14_TIME_ERROR unexpected prior resolution\n";return false;
    }
    if(unit=="ns") {
        // Preserve the legacy registry and allocation path under the default.
        std::cerr<<"PV14_TIME schema=1 resolution=ns ticks_per_second=1000000000 raw_fct_unit=ns precise_fct_unit=ticks default_audit=skipped converted=0 complete=1\n";
        return true;
    }
    const Time::Unit chosen=unit=="fs"?Time::FS:Time::PS;
    const int64_t factor=unit=="fs"?1000000:unit=="ps"?1000:1;
    struct Default {const TimeValue *value;int64_t ns;std::string name;bool sentinel;};
    std::vector<Default> defaults;
    for(uint32_t i=0;i<TypeId::GetRegisteredN();++i) {
        TypeId type=TypeId::GetRegistered(i);
        for(uint32_t j=0;j<type.GetAttributeN();++j) {
            TypeId::AttributeInformation attribute=type.GetAttribute(j);
            const TimeValue *value=dynamic_cast<const TimeValue*>(PeekPointer(attribute.initialValue));
            if(!value)continue;
            const int64_t n=value->Get().GetTimeStep();
            const bool sentinel=n==std::numeric_limits<int64_t>::min() || n==std::numeric_limits<int64_t>::max();
            if(!sentinel && (n>std::numeric_limits<int64_t>::max()/factor || n<std::numeric_limits<int64_t>::min()/factor)) {
                std::cerr<<"PV14_TIME_ERROR default out of range "<<type.GetName()<<"::"<<attribute.name<<"\n";return false;
            }
            defaults.push_back({value,n,type.GetName()+"::"+attribute.name,sentinel});
        }
    }
    // Convert registered pre-main Time objects exactly once, before scheduling.
    Time::SetResolution(chosen);
    for(const Default &entry:defaults) {
        const int64_t current=entry.sentinel?entry.value->Get().GetTimeStep():entry.value->Get().GetNanoSeconds();
        if(current!=entry.ns) {
            std::cerr<<"PV14_TIME_ERROR default conversion differs "<<entry.name<<"\n";return false;
        }
    }
    std::cout<<"PV14_TIME schema=1 resolution="<<unit<<" ticks_per_second="<<Pv14TicksPerSecond()
             <<" raw_fct_unit=ns precise_fct_unit=ticks defaults="<<defaults.size()<<" converted=1 complete=1\n";
    return true;
}
}
#endif
