#ifndef WORKLOAD_TAG_H
#define WORKLOAD_TAG_H

#include <ns3/tag.h>

namespace ns3 {

// Input workload label only. It does not grant packet reordering capability.
class WorkloadTag : public Tag {
  public:
    WorkloadTag();
    static TypeId GetTypeId(void);
    TypeId GetInstanceTypeId(void) const override;
    uint32_t GetSerializedSize(void) const override;
    void Serialize(TagBuffer buffer) const override;
    void Deserialize(TagBuffer buffer) override;
    void Print(std::ostream &os) const override;
    void SetValue(uint32_t value);
    uint32_t GetValue(void) const;

  private:
    uint32_t m_value;
};

} // namespace ns3

#endif
