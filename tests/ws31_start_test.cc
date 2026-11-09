#include "../src/point-to-point/model/ws31-start.h"
#include <cassert>
#include <iostream>
#include <set>
using namespace ns3::ws31;
int main() {
    const uint32_t tags[] = {0,1,2,99,0xffffffffU};
    for (unsigned i=0; i<5; ++i) {
        const uint32_t tag=tags[i];
        assert(StartPolicyTag(tag,0)==tag);
        assert(StartPolicyTag(tag,1)==0);
        assert(StartPolicyTag(tag,2)==(tag==1 || tag==2 ? 3-tag : tag));
        assert(StartPolicyTag(tag,3)==tag);
    }
    std::set<uint64_t> delays;
    unsigned hashEligible = 0;
    for (unsigned p=1; p<60000; ++p) {
        const uint64_t d=StartDelay(43,2,8192,1,2,uint16_t(p),100);
        assert(d<=500 && d==StartDelay(43,2,1,1,2,uint16_t(p),100));
        assert(d==StartDelay(44,0,8388608,1,2,uint16_t(p),100));
        assert(d==StartDelay(45,0,8192,1,2,uint16_t(p),100));
        assert(StartDelay(43,1,8192,1,2,uint16_t(p),100)==0);
        assert(StartDelay(43,0,8192,1,2,uint16_t(p),100)==0);
        assert(StartDelay(43,99,8192,1,2,uint16_t(p),100)==0);
        assert(StartDelay(45,2,8388608,1,2,uint16_t(p),100)==0);
        assert(StartDelay(46,2,8192,1,2,uint16_t(p),100)==0);
        assert(StartDelay(33,2,8192,1,2,uint16_t(p),100)==0);
        assert(StartDelay(43,2,8192,1,2,uint16_t(p),100,0)==0);
        const bool eligible = StartHashEligible(1,2,uint16_t(p),100);
        hashEligible += eligible;
        const uint64_t hashDelay = StartDelay(55,0,1,1,2,uint16_t(p),100);
        assert(hashDelay == (eligible ? d : 0));
        assert(hashDelay == StartDelay(55,2,8192,1,2,uint16_t(p),100));
        assert(hashDelay == StartDelay(55,99,8388608,1,2,uint16_t(p),100));
        assert(StartDelay(55,2,8192,1,2,uint16_t(p),100,0)==0);
        // Removal suppresses class eligibility; swap transfers it from tag2
        // to tag1. Unknown labels never gain eligibility under either action.
        assert(StartDelay(43,StartPolicyTag(2,1),8192,1,2,uint16_t(p),100)==0);
        assert(StartDelay(43,StartPolicyTag(2,2),8192,1,2,uint16_t(p),100)==0);
        assert(StartDelay(43,StartPolicyTag(1,2),8192,1,2,uint16_t(p),100)==d);
        for (unsigned i=0; i<5; ++i) {
            for (unsigned transform=0; transform<=3; ++transform) {
                const uint32_t policyTag=StartPolicyTag(tags[i],transform);
                if (tags[i]!=1 && tags[i]!=2)
                    assert(StartDelay(43,policyTag,8192,1,2,uint16_t(p),100)==0);
                assert(StartDelay(44,policyTag,8388608,1,2,uint16_t(p),100)==d);
                assert(StartDelay(45,policyTag,8192,1,2,uint16_t(p),100)==d);
                assert(StartDelay(45,policyTag,8388608,1,2,uint16_t(p),100)==0);
                assert(StartDelay(46,policyTag,8192,1,2,uint16_t(p),100)==0);
            }
        }
        const uint64_t demand=2000000000, launch=demand+d, finish=launch+800;
        assert(finish-demand==d+800 && launch>=demand);
        delays.insert(d);
    }
    assert(delays.size()==501 && *delays.begin()==0 && *delays.rbegin()==500);
    assert(hashEligible>0 && hashEligible<59999);
    assert(StartMode(55) && !StartMode(56));
    assert(StartDelay(43,2,8192,1,2,3,4,0xffffffffU)<=0xffffffffULL);
    std::cout << "WS31_START_TEST PASS bounds/determinism/controls/fallback/demand-time/policy-tag\n";
}
