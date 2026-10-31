#include "../src/point-to-point/model/ws31-budget.h"
#include <cassert>
#include <iostream>

using namespace ns3::ws31;
static Key K(unsigned n) { return Key(1,2,uint16_t(n),100); }
int main() {
    BudgetLedger b(3,2);
    assert(b.Insert(K(1),2,8192,1000,48,0,100));
    assert(b.Pressure(2,0)==8192+9*48);
    b.Observe(K(1),0,1000,1);
    assert(b.Pressure(2,1)==7192+8*48);
    const uint64_t original=b.Pressure(2,1);
    b.Observe(K(1),0,1000,2); // duplicate
    assert(b.Pressure(2,2)==original && b.duplicatePackets==1);
    b.Observe(K(1),2000,1000,3); // a hole is not counted as delivered
    assert(b.Pressure(2,3)==6192+7*48);
    b.Observe(K(1),500,2000,4); // overlap joins intervals; only 1000 novel bytes
    assert(b.Pressure(2,4)==5192+6*48 && b.Conserved());
    b.Observe(K(1),4000,100,5);
    b.Observe(K(1),6000,100,6); // third disjoint range: prediction retires
    assert(b.Size()==0 && b.rangeFallbacks==1 && b.Pressure(2,6)==0);
    assert(b.Insert(K(2),3,1000,1000,48,10,10));
    b.Observe(K(2),0,500,11,false); // activity-only matched control
    assert(b.Pressure(3,19)==1048);
    assert(b.Pressure(3,20)==0 && b.expired==1 && b.Conserved());
    b.Observe(K(2),500,500,21); // expiry does not re-arm prediction
    assert(b.Size()==0);
    assert(b.Insert(K(3),2,1000,1000,48,30,100));
    b.Erase(K(3)); // tuple lifecycle reset, including deadline index
    assert(b.Insert(K(3),3,1000,1000,48,31,100));
    assert(b.Pressure(2,31)==0 && b.Pressure(3,31)==1048 && b.Conserved());
    b.Observe(K(3),0,1000,32);
    assert(b.Size()==0 && b.Pressure(3,32)==0);
    BudgetLedger cap(1,8);
    assert(cap.Insert(K(1),2,100,1000,48,0,10));
    assert(!cap.Insert(K(2),3,100,1000,48,0,10) && cap.capacityFallbacks==1);
    cap.Observe(K(1),(uint64_t(1)<<32)-10,100,1);
    assert(cap.Size()==0 && cap.rangeFallbacks==1);
    assert(cap.Insert(K(2),3,100,1000,48,1,10));
    assert(cap.Conserved());
    assert(Add(~uint64_t(0),1)==~uint64_t(0));
    ObservedMemory m;
    m.Observe(2,1000,0,100);
    assert(m.Value(2,50,100)==500 && m.Value(2,100,100)==0);
    m.Observe(2,500,50,100);
    assert(m.Value(2,50,100)==1000 && m.Value(2,150,100)==0);
    std::cout << "WS31_BUDGET_TEST PASS duplicate/hole/overlap/expiry/capacity/reuse/framing/decay\n";
}
