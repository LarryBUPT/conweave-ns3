# ADR-002：包/流混合作为场景，跨类损害作为先决问题

状态：Accepted as research direction，机制仍待证伪。日期：2026-09-24。

## Decision

学位论文主线保持“包级与流级/flowlet 选路共存时的负载均衡机制”。先以 MixTax 测量逐包流量是否给有序流量造成额外代价；只有出现稳定、可解释的损害，才评估 HarmGate/GuardHash 等保护性选路机制。

## Rationale

用户明确研究中心是负载均衡机制。定向检索显示，按流类别使用不同粒度以及路径隔离已有 FAMG、APS、FLB 等近邻；仅做分类与切换粒度难以支持独立创新。跨类损害是否存在、现有强基线是否已解决，均需同模型实验回答。

## Alternatives considered

- 直接实现开题中的分类、队列阈值与喷洒：新颖性重合高，且尚无跨类损害证据。
- 以 PartialWeave 为主线：部分部署选点可研究，但偏离用户明确的混合选路中心。
- 立即实现 GuardHash：现阶段缺六列/tag 通路、双轨语义和先决现象证据。

## Consequences

MixTax 是诊断实验，不预设论文贡献。GuardHash 是待验证草案而非定案；没有跨类损害或不能胜过强基线时，应停止独立机制论文主张。详细假设和近邻边界见论文项目 `docs/research/08-mixed-granularity-discovery.md`、`11-mixhash-inspired-lb-only-discovery.md`。
