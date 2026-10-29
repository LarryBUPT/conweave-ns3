// Standalone clock/default/serialization qualification, not a network run.
#include "../scratch/paper-v14-time-resolution.h"
#include "ns3/data-rate.h"
#include "ns3/object.h"
#include <iostream>
#include <string>
static ns3::Time early=ns3::MicroSeconds(5);
namespace ns3 {
class ClockRangeProbe:public Object {
public:
    Time value;
    static TypeId GetTypeId() {
        static TypeId id=TypeId("ns3::Pv14ClockRangeProbe").SetParent<Object>()
          .AddConstructor<ClockRangeProbe>()
          .AddAttribute("LongDefault","Range counterexample",TimeValue(Seconds(10000)),
                        MakeTimeAccessor(&ClockRangeProbe::value),MakeTimeChecker());
        return id;
    }
};
}

int main(int argc,char**argv) {
    if(argc>1 && std::string(argv[1])=="overflow")ns3::ClockRangeProbe::GetTypeId();
    if(!ns3::Pv14InitializeResolution())return 2;
    if(early.GetNanoSeconds()!=5000)return 3;
    if(argc>1 && std::string(argv[1])=="repeat")return ns3::Pv14InitializeResolution()?4:0;
    ns3::DataRate rate(400000000000ULL);
    const unsigned sizes[]={43,60,240,1048};
    for(unsigned bytes:sizes) {
        const ns3::Time duration=ns3::Seconds(rate.CalculateTxTime(bytes));
        std::cout<<"PV14_TIME_ENTRY bytes="<<bytes<<" ticks="<<duration.GetTimeStep()
                 <<" physical_ns="<<duration.GetNanoSeconds()<<"\n";
    }
    std::cout<<"PV14_TIME_ENTRY_COMPLETE early_ns="<<early.GetNanoSeconds()<<" stop12s_fits="
             <<(12.0<ns3::Pv14MaximumSeconds())<<" network_runs=0\n";
}
