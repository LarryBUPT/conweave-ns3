#ifndef IRN_PFC_TIMEOUT_H
#define IRN_PFC_TIMEOUT_H

#include "ns3/nstime.h"

namespace ns3 {

// PFC enablement alone does not say whether the sender's priority is paused.
// Give a resumed priority one complete RTO before treating silence as loss.
inline Time
IrnPfcTimeoutDeferral (Time now, Time rto, bool paused,
                       bool hasResumed, Time lastResume)
{
  if (paused)
    {
      return rto;
    }
  if (hasResumed && now < lastResume + rto)
    {
      return lastResume + rto - now;
    }
  return Time (0);
}

} // namespace ns3

#endif // IRN_PFC_TIMEOUT_H
