#include "../src/point-to-point/model/ws31-label-fixture.h"
#include <cassert>
#include <iostream>
using namespace ns3::ws31;

int main() {
    assert(ParseLabelProfile(nullptr)==0 && ParseLabelProfile("0")==0);
    assert(ParseLabelProfile("3")==3);
    for (const char *s : {"4","-1","01","1x"," 1"}) {
        bool rejected=false;
        try { ParseLabelProfile(s); } catch (const std::invalid_argument &) { rejected=true; }
        assert(rejected);
    }
    for (uint32_t tag : {0U,1U,2U,7U,99U}) {
        const auto normal=LabelAt(0,tag,1000,1000,1,2,3,4);
        assert(normal.present && normal.value==tag);
        const auto removed=LabelAt(0,tag,1000,1000,1,2,3,4,1);
        assert(!removed.present && removed.value==0);
        const auto swapped=LabelAt(0,tag,1000,1000,1,2,3,4,2);
        assert(swapped.present && swapped.value==((tag==1 || tag==2)?3-tag:tag));
        const auto before=LabelAt(1,tag,1000,1499,1,2,3,4);
        const auto at=LabelAt(1,tag,1000,1500,1,2,3,4);
        assert(!before.present && before.value==0 && at.present && at.value==tag);
        assert(LabelAt(2,tag,1000,1499,1,2,3,4).value==tag);
        assert(LabelAt(2,tag,1000,1500,1,2,3,4).value==swapped.value);
    }
    unsigned wrong=0, correct=0;
    for (unsigned port=1;port<=64;++port) {
        const auto a=LabelAt(3,1,1000,1000,0x0b000001,0x0b004001,port,100);
        const auto b=LabelAt(3,1,9000,9999,0x0b000001,0x0b004001,port,100);
        assert(a.present && b.present && a.value==b.value);
        if (a.value==2) ++wrong; else { assert(a.value==1); ++correct; }
    }
    assert(wrong && correct); // A bucket does not promise an exact25% small sample.
    bool rejected=false;
    try { LabelAt(1,1,1000,999,1,2,3,4); } catch (const std::invalid_argument &) { rejected=true; }
    assert(rejected);
    rejected=false;
    try { LabelAt(1,1,1000,1000,1,2,3,4,1); } catch (const std::invalid_argument &) { rejected=true; }
    assert(rejected);
    ValidateLabelProfile(1,36,0,0,0,0,2);
    ValidateLabelProfile(0,0,2,1,4,0,0);
    for (unsigned kind=0;kind<7;++kind) {
        rejected=false;
        try { ValidateLabelProfile(kind==6?4:1,kind==0?35:43,kind==1,kind==2,
                                   kind==3,kind==4,kind==5?1:2); }
        catch (const std::invalid_argument &) { rejected=true; }
        assert(rejected);
    }
    std::cout << "WS31_LABEL_TEST PASS visibility/boundary/presence/unknown/hash/conflicts" << std::endl;
}
