#include "../src/point-to-point/model/ws31-start.h"
#include <cassert>
#include <iostream>
#include <set>
using namespace ns3::ws31;
int main() {
    std::set<uint64_t> delays;
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
        const uint64_t demand=2000000000, launch=demand+d, finish=launch+800;
        assert(finish-demand==d+800 && launch>=demand);
        delays.insert(d);
    }
    assert(delays.size()==501 && *delays.begin()==0 && *delays.rbegin()==500);
    assert(StartDelay(43,2,8192,1,2,3,4,0xffffffffU)<=0xffffffffULL);
    std::cout << "WS31_START_TEST PASS bounds/determinism/controls/fallback/demand-time\n";
}
