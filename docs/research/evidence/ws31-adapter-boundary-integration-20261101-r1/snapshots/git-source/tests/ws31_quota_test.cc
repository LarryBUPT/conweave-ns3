#include "../src/point-to-point/model/ws31-quota.h"
#include <cassert>
#include <iostream>
using namespace ns3::ws31;
static QuotaKey K(unsigned n) { return QuotaKey(1,2,uint16_t(n),100); }
int main() {
    const std::vector<uint32_t> ports={8,7,6,5,4,3,2,1};
    auto empty=[](uint32_t) { return uint64_t(0); };
    QuotaAdmission q(10);
    auto bg=q.Admit(K(1),1,ports,7,7,0,100,false,empty);
    assert(bg.chosen==1 && bg.borrowed && !bg.restricted && q.liveBorrowed[2]==1);
    auto msg=q.Admit(K(2),2,ports,0,1,1,100,false,empty);
    assert(msg.restricted && msg.eligible==2 && msg.owner==2);
    assert(q.borrowedAtActivation[2]==1);
    auto retained=q.Admit(K(1),2,ports,0,0,2,200,false,empty);
    assert(retained.chosen==bg.chosen && retained.category==1 && retained.residual);
    assert(q.residualPackets==1 && q.residualWireBytes==200 && q.Conserved());
    auto next=q.Admit(K(3),1,ports,7,7,3,100,false,empty);
    assert(next.restricted && next.owner==1 && next.eligible==6);
    assert(q.Active(2,10) && !q.Active(2,11)); // exact idle boundary
    auto idle=q.Admit(K(4),1,ports,7,7,11,100,false,empty);
    assert(!idle.restricted && idle.borrowed);
    // Dormant route remains pinned; no false claim of reclaim on expiry.
    q.Expire(30); assert(q.liveBorrowed[2]==0 && q.Size()==4 && q.Conserved());
    auto late=q.Admit(K(1),1,ports,0,0,31,100,false,empty);
    assert(late.chosen==bg.chosen && !late.fresh);
    q.Erase(K(1)); assert(q.liveBorrowed[2]==0 && q.Conserved());
    auto reused=q.Admit(K(1),1,ports,0,0,32,100,false,empty);
    assert(reused.fresh && reused.chosen==8);
    QuotaAdmission hard(10);
    auto h=hard.Admit(K(1),1,ports,7,7,0,100,true,empty);
    assert(h.restricted && !h.borrowed && h.owner==1);
    auto unknown=hard.Admit(K(2),99,ports,7,7,1,100,true,empty);
    assert(!unknown.restricted && !unknown.borrowed && unknown.category==0 && unknown.chosen==1);
    auto single=hard.Admit(K(3),2,std::vector<uint32_t>{9},4,5,2,100,true,empty);
    assert(!single.restricted && single.chosen==9 && single.owner==0);
    auto load=[](uint32_t p) { return uint64_t(p==8?100:0); };
    QuotaAdmission queue;
    auto choose=queue.Admit(K(1),0,ports,0,1,0,100,false,load);
    assert(choose.chosen==7 && choose.q1==100 && choose.q2==0);
    assert(QuotaSizeClass(8192)==2 && QuotaSizeClass(8388608)==1 && QuotaSizeClass(1)==0);
    assert(queue.Conserved() && hard.Conserved());
    std::cout << "WS31_QUOTA_TEST PASS activation/borrowing/residual/pinning/expiry/reset/controls\n";
}
