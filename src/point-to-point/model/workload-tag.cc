#include "workload-tag.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED(WorkloadTag);

WorkloadTag::WorkloadTag() : m_value(0) {}
TypeId WorkloadTag::GetTypeId(void) {
    static TypeId tid = TypeId("ns3::WorkloadTag").SetParent<Tag>().AddConstructor<WorkloadTag>();
    return tid;
}
TypeId WorkloadTag::GetInstanceTypeId(void) const { return GetTypeId(); }
uint32_t WorkloadTag::GetSerializedSize(void) const { return 4; }
void WorkloadTag::Serialize(TagBuffer buffer) const { buffer.WriteU32(m_value); }
void WorkloadTag::Deserialize(TagBuffer buffer) { m_value = buffer.ReadU32(); }
void WorkloadTag::Print(std::ostream &os) const { os << m_value; }
void WorkloadTag::SetValue(uint32_t value) { m_value = value; }
uint32_t WorkloadTag::GetValue(void) const { return m_value; }

} // namespace ns3
