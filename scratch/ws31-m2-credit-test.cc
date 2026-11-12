#include "../src/point-to-point/model/ws31-m2-credit.h"

#include <iostream>
#include <stdexcept>

static void Require(bool value) {
    if (!value) throw std::runtime_error("WS31 M2 credit invariant failed");
}

int main() {
    using ns3::ws31::M2Credit;
    using ns3::ws31::M2Key;
    const M2Key first(1, 2, 100, 200, 3, 7);
    const M2Key nextGeneration(1, 2, 100, 200, 3, 8);
    M2Credit credit(100);

    credit.MarkPinned(first, 0, 10);
    Require(credit.TryReserve(first, 4, 11, 10, 40));
    Require(credit.Used(4) == 40 && credit.PendingCount() == 1);
    credit.FinishAdmission(11, true);
    Require(credit.PendingCount() == 0);
    Require(!credit.TryReserve(first, 4, 12, 10, 40));  // retransmission
    Require(credit.Acknowledge(first, 49) == 0);         // partial ACK
    Require(credit.Acknowledge(first, 50) == 40);
    Require(credit.Acknowledge(first, 50) == 0);         // duplicate ACK
    Require(credit.Used(4) == 0);

    Require(credit.TryReserve(first, 4, 13, 50, 80));
    credit.FinishAdmission(13, false);                  // queue refusal
    Require(credit.Used(4) == 0);
    Require(!credit.TryReserve(first, 4, 14, 50, 80));  // refused data is old

    Require(credit.TryReserve(nextGeneration, 4, 15, 0, 60));
    credit.FinishAdmission(15, true);
    Require(credit.Acknowledge(first, 1000) == 0);       // old identity
    Require(credit.Used(4) == 60);
    Require(!credit.TryReserve(nextGeneration, 4, 16, 60, 50)); // cap
    Require(credit.Used(4) == 60);
    Require(credit.Acknowledge(nextGeneration, 60) == 60);
    Require(credit.Used(4) == 0);
    Require(credit.PeakTotalUsed() == 80);
    std::cout << "WS31_M2_CREDIT_TEST pass" << std::endl;
}
