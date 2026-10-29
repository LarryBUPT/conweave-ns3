#include "paper-v14-policy.h"
#include <cassert>
#include <iostream>
using namespace ns3;
int main() {
    unsigned tests=0;
    for (unsigned a=0;a<4;++a) for(unsigned b=0;b<4;++b) for(unsigned bit=0;bit<2;++bit) {
        unsigned x=Pv14TieMatched(2,7,a,b,bit);
        assert(x==(a==b?2:(bit?7:2))); ++tests;
        assert(Pv14TieMatched(2,2,a,b,bit)==2); ++tests;
    }
    for (unsigned a=0;a<3;++a) for(unsigned b=0;b<3;++b) for(unsigned c=0;c<3;++c) {
        std::vector<std::pair<uint32_t,uint64_t>> q={{2,a},{5,b},{7,c}};
        for(unsigned first : {2,5,7}) {
            uint64_t best=std::min(a,std::min(b,c));
            unsigned expected=0;
            for(auto x:q) if(x.second==best) {expected=x.first;break;}
            for(auto x:q) if(x.first==first && x.second==best) expected=first;
            do {assert(Pv14AllMinimum(first,q)==expected); ++tests;} while(std::next_permutation(q.begin(),q.end()));
        }
    }
    bool rejected=false;
    try {Pv14AllMinimum(3,{{2,0}});} catch(const std::runtime_error&) {rejected=true;}
    assert(rejected);++tests;
    rejected=false;try {Pv14AllMinimum(3,{});} catch(const std::runtime_error&) {rejected=true;}
    assert(rejected);++tests;
    std::cout << "PV14_POLICY_TEST passed=" << tests << std::endl;
}
