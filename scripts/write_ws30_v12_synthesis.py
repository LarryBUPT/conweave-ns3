"""Write the Chinese v12 handoff and review ledger from the final numeric package."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research/evidence/ws30-v12-r1'
DOC=ROOT/'docs/research'


def rows(name):return list(csv.DictReader((DATA/name).open(encoding='utf-8')))
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
def save(name,value):(DATA/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def markdown(headers,values):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in values])
def ci(row):return f"{float(row['median_pct']):+.3f}% [{float(row['ci_low_pct']):+.3f}, {float(row['ci_high_pct']):+.3f}]"


def main():
    estimates=rows('figure-estimates.csv')
    def stat(fam,cond,contrast,metric):return next(r for r in estimates if (r['family'],r['condition'],r['contrast'],r['metric'])==(fam,cond,contrast,metric))
    # Each source review item retains its own identifier even when the remedy is shared.
    review=[]
    def item(reviewer,key,request,status,evidence,action):review.append({'reviewer':reviewer,'item':key,'request':request,'status':status,'evidence':evidence,'v12_action_or_remaining_boundary':action})
    item('R1','W1','类别机制与框架收益归因','证据齐备，待正文落实','F3、F4、F5；C16/Q16；A/B 全部条件效应','将主贡献定位于首包队列信息与 QP 决策粒度；类别仅陈述规则响应及未识别的效果增量。')
    item('R1','W2','同候选不读队列随机对照','已完成','R16/H16、Q16/R16、Q16/H16 共 72 个需求层对比','报告随机硬币与候选盐分离；随机二选一不等于经典选负载较小者。')
    item('R1','W3','原生动态动作与公平比较','覆盖有界，待正文落实','D2、D3；CONGA/LetFlow 0 timeout；ConWeave RTT/notify 与 reroute 分列','按实测行为解释原生结果；不保留对动态换路能力的一般优越性主张。激活新负载为条件项，未运行。')
    item('R1','W4','近邻工作、标签与缓存可实现性','实现说明齐备，硬件未测','固定源码；related-work-mapping.json；DRILL 引用收据','明示 trace 标签、共享队列字节记账、无容量界的模拟缓存；不以简化仿制品冒充 DiffFlow 基线。')
    item('R1','W5','负载广度','条件项未运行','D1 的固定合成输入、单拓扑及共同传输契约','限定主张范围；未做周期训练、故障、异构拓扑或生产 trace 推广。')
    r2=[
        ('P0-1','重写标题、摘要、引言、结论','证据齐备，正文待整合','claims.json；F1～F5','主对话完成全文一致性，不把类别权重写成已证明的收益来源。'),
        ('P0-2','候选、队列、出口固定消融','已完成','F2 八臂、F3 九项对比、H12 技术等价','这是受控策略对比；不做可相加的整体收益百分比拆分。'),
        ('P0-3','公平动态基线与 DRILL 引用','覆盖有界，正文待落实','D2/D3；DRILL DOI 核验；U16 另列','动态激活矩阵未运行，历史 DRILL 独立恢复计数缺失；不能用 U16 填补或宣称优于完整动态机制。'),
        ('P0-4','新独立组、跨组披露','已完成','D1、F1；24 新需求；96/96 同输入桥接','四组分别呈现；修正旧表分母误读；无总体合池值。'),
        ('P0-5','工程线来源与逐输入风险','已完成','per-input-risk-summary.csv；D2；F2','+3% 是既定中位工程线，不是逐输入保证、生产 SLO 或统计非劣效。'),
        ('P0-6','实验与外推范围','证据齐备，正文待整合','D1；claims.json','说明 ns-3、合成 QP、本地信息、PFC=0/IRN=1、无硬件或训练步验证。'),
        ('P1-1','设计理由','证据齐备，正文待整合','F3；严格小则换、平局保首；QP 固定规则','首包与队列信息有相应对照；两候选和权重 1 是冻结设计，不宣称理论最优。'),
        ('P1-2','微观队列、评分、改路与恢复','已完成预设范围','F5 全部队列事件；D3；WS-28 三个批尾时序','完整下游等待总体分布未采集，不将三例选择诊断外推为全体流机制因果。'),
        ('P1-3','标签、Q_bg、缓存容量和老化','实现说明齐备，部署未测','implementation-contract.json','标签为 ns-3 PacketTag；std::map 精确键，无容量上限、老化或替换；不写硬件线速和容量已验证。'),
        ('P1-4','相关工作对比','材料齐备，正文待整合','related-work-mapping.json；reference-review.json','覆盖局部/下游/全局信息与粒度、状态和部署前提；主对话核对最终引用与文字。'),
        ('P1-5','贡献逐项对应实验','材料齐备，正文待整合','claims.json：C1/C2/C3','以队列信息增量、决策粒度代价、类别条件检验组织贡献。'),
        ('P1-6','DRILL 文献、实现与乱序代价','部分覆盖，保留缺失','D2 原生结果；DRILL 引用；D3 缺失字段','历史 DRILL 恢复计数未观测。U16 是固定首次候选对的独立策略，不能当作 DRILL 实测恢复量。'),
        ('P2-1','更多拓扑','条件项未运行','D1','不声称跨拓扑、故障或非对称泛化。'),
        ('P2-2','更多流大小、尾部分位与集合规模','补充指标已交付，扩展未运行','secondary-metrics.csv；load64-outlier-audit.json','交付已有输入的 P50/P95/P99/最大值；未扩大背景集合或扫描流长。'),
        ('P2-3','增加同组 seed 至 48','条件项未运行','F1 四组各 24；新组 24','先占和同步相关，不计作 48 个独立需求；不事后合池代替原门槛。'),
        ('P2-4','权重扫描','条件项未运行','A/B、C16/Q16、F5','保留固定权重的结果，不为收益追加权重搜索。'),
        ('P2-5','PFC 敏感性','条件项未运行','共同 DCQCN、PFC=0、IRN=1 配置','这是受控公共传输条件；没有敏感性数据，不能断言真实部署必须采用此配置。'),
        ('P2-6','硬件或 P4 原型','条件项未运行','implementation-contract.json','只陈述软件状态和记账语义；不填 ASIC 字节数、吞吐或时延。'),
        ('P2-7','真实 MoE trace','条件项未运行','D1、生成器哈希','只称合成 MoE 通信批次，不称真实训练 trace 或训练加速。'),
        ('P2-8','配对检验和多重比较','按描述性契约交付','F3 九项名义区间；package.json','不使用显著性标签或 p 值；若后续增加标签，须按事前契约对九项 MoE 符号检验统一 Holm 校正。'),
        ('P2-9','64 背景档离群点','已完成复核','load64-outlier-audit.json；128 条配对背景 FCT','seed 20262744，P99 为 1044.10412→520.77116 μs；保留全部点，不据单输入指定唯一拥塞原因。'),
        ('P2-10','表注列机制执行状态','材料齐备，正文待整合','D3-native-dynamic.json','将零 timeout/reroute 的范围与非零控制反馈一同列出。')]
    for key,request,status,evidence,action in r2:item('R2',key,request,status,evidence,action)
    item('R2','11.1','旧 WS-25 联合 NO-GO','历史判断保留','D1；阶段 1 差异审计','旧组的双侧至少 5% 与 17/24 门槛未达；不借 +3% 新工程线重判。')
    item('R2','11.3','WS-27 原为三候选比较','历史范围保留','历史 456 格索引包括其他候选；本文数据聚焦预定 ClassReserve 第一课题','不声称 ClassReserve 是唯一测试候选；不把未展示的选择过程冒充额外独立确认。')
    for key,request,status,evidence,action in [
        ('W1','类别与贡献定位','证据齐备，正文待落实','F3/F4/F5','先占与组成均完成；保留规则响应，收缩类别收益主张。'),
        ('W2','标签、计数、缓存','实现说明齐备，部署未测','implementation-contract.json','准确交代仿真元数据和缓存生命周期，不虚构 DSCP 编码或硬件老化策略。'),
        ('W3','背景预填充或错峰','已完成','72 格先占、12 格组成；F4/F5','20 μs 固定提前和四种组成条件分别报告；不挑选有利提前量。'),
        ('W4','ECMP 哈希和 DRILL 恢复','哈希已核验，恢复范围有界','H12/E 路径与 FCT 等价；H16/E、Q12/E；D3','H16 保留历史键差异；U16 非 DRILL，历史 DRILL 恢复量留缺失。'),
        ('W5','DRILL、模拟器和相关工作引用','材料齐备，正文待落实','DRILL 引用核验；基线数据流审计；related-work-mapping.json','主对话补实际模拟器来源和 HPN/全局反馈路线对照；引用不替代实验效果。')]:item('R3',key,request,status,evidence,action)
    corrections=[
        ('A0B0 完全类别无关','A0B0/M16 仍对两类采用不同选择；A0B1/Q16 统一评分但保留键差异；Q12 才统一键与评分。','固定源码与八臂设计'),
        ('区间跨零证明类别无效或收益必由共同组件产生','跨零表示未识别稳定增量，未设置等效界；队列与固定作用由新增受控对比识别。','F3/F4'),
        ('三条原生基线等同 ECMP、全部机制没运行','零动态分支不等价逐包转发相同；ConWeave 的 RTT 回复与通知在 24/24 格出现，旧组有 1 格 reroute。','D3-native-dynamic.json'),
        ('两组原生排序完全反转','旧表曾用 ClassReserve/各方法，主表用各方法/ECMP。统一 ECMP 分母后两组均为 DRILL 批时间最短、ClassReserve 次之。','阶段 1 与 D2'),
        ('64 条背景的 P99 就是最大值','线性 P99 为第 63、64 个排序值的 0.63/0.37 加权；192 条为第 190、191 个值的 0.91/0.09 加权。','原始 quantile 与 outlier 审计'),
        ('背景越多改善越大即可排除哈希解释','负载相关性单独不足以排除键、候选和队列共同变化；H16/R16/Q16、Q12 的对照补足识别。','F3'),
        ('逐交换机固定不可能得到稳定端到端路径','静态拓扑中各跳固定可形成稳定路径，22 格完整包路径已重建；正式矩阵保留逐交换机 QP 汇总，不冒充全包端到端重放。','技术路径收据、D3'),
        ('658638 是独立端到端 QP 数','该值为跨格累计的（交换机，QP）出口变化记录数；重传包、接收 gap 和换口次数也各有不同计数单位。','正式观测器与 D3')]
    claims=[
        {'id':'C1','status':'可写入正文','claim':'相同首次候选与 QP 固定条件下，总队列信息相对不读队列的分配具有可测增量。','evidence':'Q16/R16、Q16/H16，F3，24 新需求','scope':'固定合成输入和共同传输；不是两候选理论最优证明。'},
        {'id':'C2','status':'可写入正文','claim':'统一两类候选键与评分的 Q12 仍缩短同步批次，改善不依赖额外类别队列权重。','evidence':'Q12/E，F2/F3','scope':'19/24 批时间下降；背景中位工程线与逐输入风险同时报告。'},
        {'id':'C3','status':'可写入正文','claim':'保留首次候选对时逐包重比队列的 U16 在本输入中使两侧时间劣化，并伴随换口、接收 gap 和重传。','evidence':'U16/Q16，F3、D3','scope':'U16 保留候选状态，不是无状态或原生 DRILL；不量化缓存容量或单一恢复因素的中介贡献。'},
        {'id':'C4','status':'可写入正文并限定','claim':'类别权重在相等总队列、不同组成下改变首包选择，但同步、先占和组成数据未识别批次或背景 P99 的稳定增量。','evidence':'C16/Q16；F4/F5；A/B 表','scope':'不是等效性或类别永远无用的结论；组成只有四种固定条件。'},
        {'id':'C5','status':'可写入正文并限定','claim':'完整方案在四组各 24 份独立需求中，MoE 配对中位变化均为负；幅度和逐输入背景代价随组变化。','evidence':'F1，D1/D2，risk CSV','scope':'不合池、不只选 −6.899% 作总体值；旧联合 NO-GO 不变。'},
        {'id':'C6','status':'需收缩','claim':'背景被保护、所有输入安全、普遍优于原生动态方法','evidence':'背景逐输入越线、原生分支覆盖和 DRILL 缺失恢复计数','scope':'改写为给定公共配置中的双侧结果和中位工程约束；没有生产 SLO 或非劣效证明。'},
        {'id':'C7','status':'不可外推','claim':'真实训练加速、硬件线速或容量、通用端到端保序、任意故障与分布泛化','evidence':'单拓扑、合成 QP、软件 PacketTag/std::map、条件矩阵覆盖','scope':'本节点没有这些测量。'},
        {'id':'C8','status':'需收缩','claim':'三个批尾反例证明类别权重或背景排队唯一导致整批劣化','evidence':'WS-28 选定最高序号包的局部逐跳轨迹','scope':'只报告批尾身份切换和局部等待；未走路径、发送速率与全体等待反事实未测。'}]
    implementation={
        'source_sha':'1ef424749e3c551dd788d0a709bd8e21c7cc89c9',
        'label':'sixth trace column -> RdmaClient WorkloadTag -> QP m_workload_tag -> ns-3 PacketTag; not a verified on-wire DSCP/BTH classification protocol',
        'queue':'shared output queue; per-switch/output/tag current bytes incremented/decremented on actual enqueue/dequeue/drop events; no class-specific physical queue is implied',
        'cache_key':'exact (source IP,destination IP,UDP source port,UDP destination port); UDP checked outside lookup',
        'cache_storage':'C16/Q16/M16 use two per-class std::map objects; Q12/H/R/U use the shared m_ws30Pairs map. No fixed hardware capacity, timeout, aging or eviction; a transport tuple reuses its corresponding entry.',
        'scope':'one static-topology simulation with unique generated transport tuples; no long-running tuple-reuse or hardware-overflow validation',
        'candidate_key':'legacy MoE 16 bytes including first observed seq; background 12 bytes; Q12 and H12 use 12 bytes for both classes',
        'tie':'second only on strict lower score; ties keep first; identical candidates collapse',
        'H12':'technical arm equivalent to E for route signatures and FCT; not a ninth formal effect arm',
        'U16':'retains first candidate pair and re-evaluates only chosen output; still stores candidate state; distinct from native DRILL',
        'path_coverage':'22 technical full-log cells reconstruct complete accepted packet paths from topology; formal main/lead are switch-QP path summaries; fixture probe is fully traced',
        'hardware_metrics':None}
    save('claims.json',claims);save('review-acceptance.json',review);save('fact-corrections.json',corrections);save('implementation-contract.json',implementation)
    reviewpaths={'R1':ROOT.parents[1]/'paper review/workbuddy+hy4preview/v11-review.md',
                 'R2':ROOT.parents[1]/'paper review/claude+dsv4.1flash/v11-review.md',
                 'R3':ROOT.parents[1]/'paper review/dsh+dsv4pro/v11-review.md'}
    save('review-sources.json',{k:{'path':str(p),'sha256':sha(p)} for k,p in reviewpaths.items()})
    with (DATA/'review-acceptance.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=list(review[0]));w.writeheader();w.writerows(review)

    label={'old':'旧组','main_history':'历史主组','factorial':'独立 A/B 组','new':'新归因组'}
    cohort_table=[]
    for c in label:
        m,b=stat('F1',c,'Full/E','moe_batch'),stat('F1',c,'Full/E','background_p99')
        cohort_table.append([label[c],ci(m),m['lower_n']+'/24',ci(b),b['over_3pct_n']+'/24'])
    arm_table=[]
    for a in ['E','H16','R16','Q16','C16','U16','Q12','M16']:
        m,b=stat('F2','synchronous',a+'/E','moe_batch'),stat('F2','synchronous',a+'/E','background_p99')
        arm_table.append([a,ci(m),m['lower_n']+'/24',ci(b),b['over_3pct_n']+'/24'])
    attribution=[]
    for c in ['H16/E','R16/H16','Q16/R16','Q16/H16','U16/Q16','Q12/E','Q16/Q12','C16/Q16','Q16/M16']:
        attribution.append([c,ci(stat('F3','synchronous',c,'moe_batch')),ci(stat('F3','synchronous',c,'background_p99'))])
    timing=[]
    for c in ['Q16/E','C16/E','C16/Q16']:
        for condition in ['synchronous','lead20us']:
            timing.append([c,'同步' if condition=='synchronous' else '背景提前 20 μs',ci(stat('F4',condition,c,'moe_batch')),ci(stat('F4',condition,c,'background_p99'))])
    factorial=rows('factorial-estimates.csv');factors=[]
    factor_arm_stats=rows('factorial-arm-estimates.csv');factor_arm_table=[]
    for mode,label in [('cr-a0-b0','A0B0'),('cr-a1-b0','A1B0'),('cr-a0-b1','A0B1'),('cr-a1-b1','A1B1')]:
        m=next(r for r in factor_arm_stats if r['mode']==mode and r['metric']=='moe_batch');b=next(r for r in factor_arm_stats if r['mode']==mode and r['metric']=='background_p99')
        factor_arm_table.append([label,ci(m),m['lower_n']+'/24',ci(b),b['over_3pct_n']+'/24'])
    for contrast in dict.fromkeys(r['contrast'] for r in factorial):
        m=next(r for r in factorial if r['contrast']==contrast and r['metric']=='moe_batch');b=next(r for r in factorial if r['contrast']==contrast and r['metric']=='background_p99')
        unit={'percent':'%','percentage points':'百分点','100 ln ratio of ratios':'100×对数比差'}[m['unit']]
        fmt=lambda r:f"{float(r['median_pct']):+.3f} [{float(r['ci_low_pct']):+.3f}, {float(r['ci_high_pct']):+.3f}]"
        factors.append([contrast,unit,fmt(m),fmt(b)])
    native=[]
    for r in rows('D2-native-baselines.csv'):
        f=lambda n:f"{float(r[n+'_median']):+.3f}% [{float(r[n+'_ci_low']):+.3f}, {float(r[n+'_ci_high']):+.3f}]"
        native.append(['旧组' if r['cohort']=='old' else '历史主组',r['method'],f('batch_change_pct'),f('background_change_pct'),r['background_gt3']+'/24'])
    intro='''# WS-30 面向 v12 的跨阶段证据综合包

记录日期：2026 年 10 月 25 日。本包供主对话整合中文 v12 正文，覆盖阶段 1/2、主矩阵 192 格、先占 72 格、组成 12 格，以及 WS-28 第一课题的原生比较、A/B 和批尾诊断。实际分析上下文已核实为 GPT-6.1 Sol / Medium。

新增归因对照支持把本地队列信息用于 QP 首包分配：同候选、同出口固定条件下，Q16 相对随机二选一的 R16 缩短批次。统一候选键与评分的 Q12 也改善批次。撤去所选出口固定的 U16 则使批次和背景 P99 同时变慢，并伴随实际换口和恢复代价。类别额外权重在定向组成中确实改变首包决策，但同步、背景提前 20 μs 与组成数据没有识别出它的稳定时间增量。以上结论各有不同的受控对比与适用范围。

## 1. 流程、统计与交付范围

本次只分析既有本地数据，没有启动新远端实验。对 1,050 个成功 ID 重新核对了 FCT、输入和拓扑哈希；对主矩阵与先占的 264 格，另从 4,376,064 条原始流重建身份、字节、类别原点、FCT、分位数和批尾身份。1050 个 ID 包含历史 456 格、WS-30 的 438 个独立成功实验、WS-28 的 12 格批尾诊断及既有负载曲线的 144 个补充格。共享角色按 ID 去重，不能把它们都当效果重复。

WS-30 的 438 个成功 ID 为阶段 2 的 148 个、组成技术验收 14 个及正式主矩阵/先占/组成 276 个。阶段 2 的 32+24+96 格包含 4 个桥接预检重用。相对最初预算，组成另增加了已获准的 14 格正确性验收；不将这些技术格计入需求效果。另列 6 个保留失败 ID 和 1 个未运行构建，失败流子集均未进入效果估计。运行器曾安全暂停和降载恢复，成功 ID 未重跑；主矩阵未知进程原快照缺少完整归属字段，先占快照虽有 UID/PPID 等信息，进一步归属仍未明。相关原始收据见[实验资源索引](evidence/ws30-v12-r1/D4-experiments.json)及各节点报告。

效果定义为每个需求内 `100×(候选/参照−1)`，再跨需求取中位数。四组各有 24 个独立需求，分别汇总；同一新需求的同步和先占是相关条件，组成是四种固定控制条件。所有图表的点、分母、单位与原始 ID 见[逐点 CSV](evidence/ws30-v12-r1/figure-points.csv)。名义 95% 区间采用需求层有放回重采样 10,000 次，统一固定随机种子 20263003、按需求 seed 排序和相同索引矩阵；重复出现的同一对照现在使用同一区间。历史端点保留在 `archived_ci_*` 列与旧文件中，未修改历史判据。未添加显著性标签或等效性结论。

## 2. D1 与 F1：独立输入组及回归桥接

四组需求 seed 分别为 20262521～20262544、20262721～20262744、20262921～20262944 和 20263021～20263044。同步 192 背景档均含 16,384 条 8 KiB MoE QP 与 192 条 8 MiB 背景 QP，总载荷 1,744,830,464 B。相同需求生成规则、拓扑和公共传输契约没有使四组变成同一输入；端点、碰撞与批尾不同。旧组与历史主组的生成器文件哈希为 `00c5e525…`，A/B 组与新组为 `0739571b…`：后者只增加选择输出背景档位的参数和合法性检查，随机调用与需求构建逻辑不变；完整源文件差异已按此核对。文件逐字节相同与需求规则相同分别记录。完整源码 SHA、原点、输入及判据见[D1 表](evidence/ws30-v12-r1/D1-cohorts.csv)。

旧组 SHA 为 `ce699df`，历史主组为 `ee236f2`，A/B 组为 `955d26b`，新归因组为 `1ef4247`。四组同步 192 档共同采用 400 Gbps、DCQCN、PFC=0、IRN=1、9 MiB 缓冲和 ns-3 seed 1；需求生成 seed 才是独立重复单位。显式 trace 决定实际提供需求，运行参数 `netload=10` 不能写成实测负载为 10%。阶段 1 已核对生成器、ClassReserve/ECMP/DRILL 的相关函数和公共配置；阶段 2 的 96 格在新 SHA 下分别重放旧组与历史主组的 E/C16，完整 FCT 哈希全部对应历史值。该结果排除了这 96 个固定输入上可见的输出变化，不证明所有未测输入或其他原生方法的二进制等价。

旧组的联合门槛是两侧中位至少下降 5%、各有至少 17/24 输入改善，其原 NO-GO 保留。后续 +3% 为背景配对 P99 变化中位数的工程线；它不是逐输入保证、生产 SLO 或统计非劣效。
'''
    text=intro+'\n'+markdown(['独立组','MoE 批次变化［名义 95% 区间］','批次下降输入','背景 P99 变化［区间］','背景 >+3%'],cohort_table)+'''

![F1 四组独立需求](figures/ws30-v12-r1/F1-four-cohorts.png)

F1 图注：每组每面板 24 个完整输入点；菱形为组内配对中位数，横线为需求层名义 95% bootstrap 区间。两面板分别为 MoE 批时间和背景 P99；负值表示时间下降。四组从不合池，虚线为历史工程参考 +3%，不能将旧组按新线改判。点源为 `figure-points.csv` 的 F1；绝对 ECMP 基准和六方法结果另见 D2。

## 3. F2/F3：框架归因、严格类别无关臂与逐输入风险

E 为 ECMP。H16 固定历史首候选，不读队列；R16 用独立哈希硬币在相同两个候选中选择。Q16 对两类读总队列，但保留历史的 MoE 16 字节/背景 12 字节键；C16 为完整 A1B1；M16 为 A0B0，背景只取首候选。Q12 将两类候选键统一为 12 字节并统一总队列评分。U16 保存 Q16 相同的首次候选对，但每包重新比较所选出口，仍有候选状态。
'''+ '\n'+markdown(['臂 / E','MoE 批次变化［区间］','下降输入','背景 P99 变化［区间］','背景 >+3%'],arm_table)+'''

![F2 八臂双侧结果](figures/ws30-v12-r1/F2-eight-arms.png)

F2 图注：新组 24 个需求，每臂均与同需求 E 配对，所有点保留；菱形和横线定义同 F1。两面板各有 8×24 个点，包含 E 的零变化参考。背景 +3% 虚线只用于该预设中位工程约束；逐输入越线数见表和[完整风险清单](evidence/ws30-v12-r1/per-input-risk-summary.csv)。不能因 C16 的中位变化接近零忽略其 7/24 输入越线。

![F3 主归因图](figures/ws30-v12-r1/F3-main-attribution.png)

F3 图注：九个事前冻结对照，各面板每行 24 个完整需求点，共 9×24 个点。对照右侧为分母，横轴为配对变化百分比。保留正、负和零值，菱形为中位数，横线为名义 95% 需求层区间，无多重比较显著性标记。U16/Q16 只改变出口重决策粒度并保留候选对；Q16/M16 是背景自身选路规则 B 的开关，不命名为一般类别信息效应。
'''+ '\n'+markdown(['对照','MoE 批次变化［区间］','背景 P99 变化［区间］'],attribution)+'''

Q16/R16 和 Q16/H16 在该新组中提供了队列信息相对不读队列选择的增量证据。Q12/E 表明观察不限于历史类别键。H16/E 本身也改变了部分输入的两侧结果，故完整方案相对 E 的全部变化不能只归给队列权重。九项估计不能相加成可加的收益份额。

U16 相对 Q16 的两侧时间均增加。正式观测累计记录 658,638 个发生出口变化的（交换机，QP）记录、3,614,093 次换口、471,101 个实际重传包和 225,961 次接收序号 gap；这些不是同一种计数单位。其余七臂相应换口、重传和 gap 计数为零。U16 是独立策略对照，不是原生 DRILL，也不能用来证明缓存容量、硬件开销或恢复机制的唯一中介贡献。

## 4. A/B、F4 与 F5：类别规则和时序条件

旧 A/B 数据来自另一组 24 个需求。A 控制 MoE 评分额外背景字节，B 控制背景首包是否按两候选总队列改路。A0B0 仍在 MoE 与背景之间采用不同选择规则；A0B1 仅统一评分，历史键差异仍在。Q12 才同时统一候选键与评分。四臂相对同需求 ECMP 的完整结果如下，240 个逐输入双侧点和 ID 见[factorial-arm-points.csv](evidence/ws30-v12-r1/factorial-arm-points.csv)。
'''+ '\n'+markdown(['旧 A/B 臂 / E','MoE 中位［区间］','批次下降输入','背景 P99 中位［区间］','背景 >+3%'],factor_arm_table)+ '\n\n'+markdown(['旧 A/B 条件对比','单位','MoE 中位［区间］','背景 P99 中位［区间］'],factors)+'''

旧百分比交互是逐输入两个条件百分比效应的差，单位为百分点；对数交互另按 `100×ln[(A1B1/A0B1)/(A1B0/A0B0)]` 计算。两者分别命名，不相互冒充。所有旧组件区间跨零不证明零效应或等效性；新组 Q16/M16 的背景增量也不能外推成跨组统一的 B 收益。

![F4 类别与时序综合图](figures/ws30-v12-r1/F4-class-and-timing.png)

F4 图注：相同 24 个新需求分别处于同步和背景提前 20 μs 两个相关条件。每面板六行、每行 24 个配对点；灰色为同步、蓝色为先占。MoE 的批次原点分别为 2.000000 s 和 2.000020 s，背景保持逐 QP 起点。菱形和区间定义同 F1。不能将两种条件当作 48 个独立需求。
'''+ '\n'+markdown(['对照','条件','MoE 批次变化［区间］','背景 P99 变化［区间］'],timing)+'''

C16/Q16 在两种条件下均未识别清晰时间增量；先占相对同步的同需求对数比交互也跨零，逐点和区间另见[timing 文件](evidence/ws30-v12-r1/timing-interaction-estimates.json)。在 C16 的逐交换机新 QP、不同候选比较事件中，含背景的比例从 32.392% 降至 25.970%，两种评分选择不一致的比例从 4.727% 降至 3.851%。提前 20 μs 没有增加这两个观测比例；不能事后把“先占必然提高类别信号”写成已知原因。

组成使用独立的 8 节点受控拓扑，主机接入为 400 Gbps，两个候选出口为 40 Gbps，与 1280 主机主矩阵分别解释。实验调度器同时暂停两个出口以建立真实积压；公共传输仍为 PFC=0、IRN=1。

![F5 首包选择](figures/ws30-stage3-composition-r1/probe-choice.png)

F5 首包图注：每个单元为一个正式组成格的实际探针出口。两候选均为 65,536 B 真实积压，方向 0 的背景字节为端口 2/3 上 65,536/0 B，方向 1 相反。E 始终选 3，Q16 平局保留首候选 2，C16 随组成选 3/2；每个探针的 16 个包保持该出口。四种控制条件各一次仿真，不画抽样区间。

![F5 真实队列与完成时序](figures/ws30-v12-r1/F5-composition-queue-timing.png)

F5 队列图注：每面板叠加 6 个正式格×2 个真实出口的完整队列轨迹，共 12 条曲线；按实际探针选择归一为所选/另一出口，不作跨运行均值。保留全部 6,528 个队列事件，重叠曲线完整保存在[F5 原始点表](evidence/ws30-v12-r1/F5-queue-events.csv)。横轴从完整标签 2 批次原点 2.000000 s 起算，单位 μs；纵轴为 KiB。探针到达与暂停释放分别在 21.020 μs、22 μs。

最后预填在 2,000,003,500 ns 入队；探针整列在 2,000,021,320 ns 入队完毕，暂停解除前没有出队。后续背景首包在 2,000,023,019 ns 入队。完整标签 2 包括两个预填 QP 与探针，12 格批时间均为 45.665 μs，探针自身 FCT 均为 25.665 μs；同条件三臂背景 P99 相同。持续背景的方向 0 C16/Q16、方向 1 C16/E 各有 16 条背景 QP 变快、16 条变慢、2 条不变，最不利增加 3.345 μs（16.916%）。这说明规则响应和局部代价可以被观察到，却没有在该夹具转化为批时间或 P99 改善。完整 252 条 FCT、逐流差和四种条件数值见[组成报告](ws30-stage3-composition-node-report-r1.md)。

## 5. D2/D3：原生比较、实现前提和路径覆盖
'''+ '\n'+markdown(['组','方法','MoE 相对 ECMP［区间］','背景 P99 相对 ECMP［区间］','背景 >+3%'],native)+'''

绝对 ECMP 批时间中位数为旧组 18.022 μs、历史主组 18.540 μs，背景 P99 分别为 1,680.833 μs、1,614.923 μs。所有方法的绝对值和区间在[D2 CSV](evidence/ws30-v12-r1/D2-native-baselines.csv)中，288 个逐输入值有 raw/ID 锚点。两组均是 DRILL 的批时间最短、ClassReserve 次之；原先“整体排序反转”来自比较分母误读，效应幅度差异本身仍保留。

CONGA、LetFlow 两组 flowlet timeout 均为 0。ConWeave 旧组 RTT 回复/通知/换路累计为 11,884,225/12,574/1，历史主组为 11,833,940/12,894/0；旧组 1 格发生换路和 VOQ 动作，主组没有。零换路不能写成整个方法没有运行，也不等价 ECMP 的逐包路径。该原生表只描述公共配置中的实测结果；未运行激活动态机制的新负载，不保留对完整动态能力的一般优越性结论。

DRILL 在两组批时间改善更大，背景 P99 中位增加 +4.620%/+8.388%，属于双侧权衡。本次另检查了[48 份原生 DRILL 日志](evidence/ws30-v12-r1/native-drill-observation-audit.json)，均没有独立逐 QP 恢复观测行；其重传/gap 字段留缺失，不能以 CNP、零或 U16 的计数替代。DRILL 引用已核验为 SIGCOMM 2017，DOI `10.1145/3098822.3098839`，作者版 PDF 的阅读范围是引用与逐包局部队列比较，尚未完成候选库逐页精读。

当前类别标签来自 trace 第六列，经 QP 保存为 ns-3 PacketTag；未验证线上 DSCP/BTH 分类协议。Q_bg 是共享出口队列的逐包类别字节记账，不表示分类物理队列。缓存用源/目的 IP 与 UDP 源/目的端口的精确键和 `std::map`，没有固定硬件容量、老化或淘汰策略；当前输入使用唯一生成的传输元组。正文只能据此说明软件实现与部署前提，不能声称已验证线速、ASIC 占用或长期元组复用。

22 个技术全日志格已按拓扑重建每个被接受数据包从首跳至末跳的路径，固定臂未出现端到端路径变化，U16 的变化分支已覆盖，H12 与 E 的路径签名和 FCT 相同。正式主矩阵与先占使用逐交换机 QP 汇总，不能称为全部正式包的完整路径重放。稳定静态拓扑内每跳固定与技术实测共同支持路径保持；它不构成任意故障或真实 RNIC 的保序保证。详细语义与缺失项见[D3](evidence/ws30-v12-r1/D3-new-arm-actions.csv)和[实现契约](evidence/ws30-v12-r1/implementation-contract.json)。

## 6. WS-28 第一课题及背景尾部风险

WS-28 的三个已揭盲劣化输入均发生批尾 QP 身份切换。ClassReserve 新批尾最高序号目标包的最长单跳等待分别为 seed 20262725 的 6,179 ns、20262729 的 6,905 ns、20262739 的 6,571 ns；入队前背景字节分别为 97,464、167,680、99,560 B。对应 12 个探针开关格的 FCT 与原格一致。首包评分、下游末包等待和整批变化属于不同对象与时刻；这里没有未走路径的反事实或完整发送速率轨迹，不能将局部等待直接当作整批劣化，更不能唯一归因于 A/B。完整逐跳点、ID 和原图入口见[WS-28 分析](ws28-factorial-and-tail-analysis.md)。

第一课题的两种 P95 必须分开：每输入内 16,384 条 MoE 单流 P95 的配对变化中位数为 −1.012%；24 个输入级批时间的跨输入 P95 变化为 −6.888%。它们均不替代 −6.899% 的原主指标。本包对新组另交付单流 P50/P95/P99、背景 P95/P99/最大值、跨需求批时间 P95 和全部批尾身份，见[补充指标 CSV](evidence/ws30-v12-r1/secondary-metrics.csv)。

64 背景档的 −50.123% P99 离群点为 seed 20262744，ECMP/C16 的 P99 为 1044.10412/520.77116 μs，P95 为 785.09080/517.12645 μs；两臂全部 64 条背景 FCT 均保留。P99 是第 63、64 个排序值的 0.63/0.37 加权，不能叫最大值。该单输入结果保留在图点和[128 行尾部数据](evidence/ws30-v12-r1/load64-outlier-background-flows.csv)中；仅凭 FCT 排序不能指定唯一网络原因。

## 7. v12 主张、评审验收与剩余项

正文可围绕三个有对应对照的发现组织：首包队列信息的增量、QP 重决策粒度的双侧代价、类别规则的条件检验。四组整体结果是输入相关的支持证据，类别加权在规则层可触发、在业务时间层未识别稳定增量。逐输入风险与原生执行状态应与中位数一起出现。可写入、需收缩与不可外推的逐条主张见[claims.json](evidence/ws30-v12-r1/claims.json)。

三份 review 的各编号项分别保留映射；另纠正 A0B0 类别语义、跨零即无效、零换路即 ECMP、排序分母、P99、负载相关性和计数单位等事实误读。完整状态见[评审验收表](ws30-v12-review-acceptance-r1.md)。证据已经补齐的项与尚待正文实现的项分开；动态激活负载、真实 trace、硬件、权重扫描等未运行项保持明确状态。

本 WS 的已冻结实验与 F1～F5、D1～D4 数据交付均有对应入口。主对话仍须完成中文 v12 的标题、摘要、机制、图注、引用、结论与全文一致性审校，并验收本包；本分支保持 WS-30 ACTIVE，不按全文闭环归档。当前没有发现需要补跑远端仿真的预设技术缺格。

## 8. 图表、原始身份与参考复核入口

- [数据包清单](evidence/ws30-v12-r1/package.json)：各统计单位、CI 算法、原始文件输入哈希。
- [全部 ID 与资源](evidence/ws30-v12-r1/D4-experiments.json)：成功角色去重、失败和未运行构建、raw 路径与 SHA-256。
- [图源](../../scripts/plot_ws30_v12_package.py)、[数据构建](../../scripts/build_ws30_v12_package.py)：没有仿真启动入口。
- [图表契约与 QA](figures/ws30-v12-r1/qa.json)：逐面板完整点、对齐、碰撞、字体和最终尺寸检查。
- [参考借鉴复核](evidence/ws30-v12-r1/reference-review.json)：固定论文版本、PDF/技术分析/核验记录哈希、适用条件和不能外推的结论。

本重要节点从候选 README 与 reading-log 进入，复核了 DiffFlow、SeqBalance、LetFlow、ConWeave、Gemma、SGLB、HULA，以及 DRILL 的引用与机制记录。借鉴点分别为类别与粒度分离、最大完成聚合、适应机会、动态分支忠实性、下游信息与重排成本、全局反馈和状态规模、逐跳探测，以及逐包局部队列比较。它们没有构成本项目收益证据或新机制准入。候选技术附件中的“本项目”是撰写时的历史语境，当前机制差异以本次固定源码的首包 QP 路由为准。
'''
    (DOC/'ws30-v12-evidence-synthesis-r1.md').write_text(text,encoding='utf-8')
    reviewtext='''# WS-30 三份 review 与 v12 验收清单

日期：2026 年 10 月 25 日。R1 为 workbuddy+hy4preview，R2 为 claude+dsv4.1flash，R3 为 dsh+dsv4pro。三份原文 SHA-256 见 [review-sources.json](evidence/ws30-v12-r1/review-sources.json)。审稿意见提出问题，事实判断以源码、ID 和 raw 为准。下表不把“数据已交付”写成“v12 已修改完毕”。

'''+markdown(['评审编号','要求','当前状态','证据','v12 动作与边界'],[[r['reviewer']+' '+r['item'],r['request'],r['status'],r['evidence'],r['v12_action_or_remaining_boundary']] for r in review])+'''

## 事实修正

'''+markdown(['评审中的说法','核验后的结论','证据'],corrections)+'''

## 必做交付验收

| 项目 | 验收状态 | 身份入口 |
| --- | --- | --- |
| 阶段 1 历史差异与输入 | 456 格及 72 输入的既有审计保留，本包重新核对使用的 raw 哈希 | 历史审计、D1/D2/D4 |
| 阶段 2 正确性、pilot、桥接 | 32/32、24/24、96/96；去重 148 成功，原失败记录保留 | 阶段 2 报告与 D4 |
| 阶段 3 技术组成验收 | 14/14，原失败与未运行构建另列 | correctness combined、D4 |
| 主矩阵、先占、组成 | 192/192、72/72、12/12；原始记录、原点、路径和两侧结果分别核验 | F2/F3、F4、F5 |
| F1 四组独立需求 | 4×24×2 个完整双侧点，组别和 ECMP 分母明确 | figure-points/estimates.csv |
| F2 八臂与 F3 九个组件对比 | 8×24×2、9×24×2 个完整点；重复对照统一 CI | F2、F3 图源与 QA |
| F4 类别与时序 | 3 对照×2 条件×24×2 个点；同需求相关条件，原点独立 | timing-interactions、F4 |
| F5 组成队列/选择/完成 | 12 个 ID、两出口、全部 6528 队列事件、252 条 FCT；无需求层重复推断 | F5、组成节点完整数据 |
| D1～D4 | 输入契约、原生双侧、动态/恢复/路径覆盖、全部 ID/资源 | ws30-v12-r1 目录 |
| 参考复核与图表 QA | 固定版本和借鉴边界记录；自动检查与逐面板目视确认 | reference-review.json、qa.json |
| 中文 v12 全文整合与最终验收 | 待主对话完成 | 主对话承接标题、摘要、方法、引用、图注、结论一致性 |

动态激活矩阵、硬件/P4、生产 SLO、真实训练和范围扩展保持未执行状态。它们不是已完成的实验，也不被写成原生动态能力或部署收益的证据。当前预设实验没有技术缺格；若主对话选择保留超出现有范围的主张，须另决定其证据需求。WS-30 保持 ACTIVE，待本包验收和全文整合。
'''
    (DOC/'ws30-v12-review-acceptance-r1.md').write_text(reviewtext,encoding='utf-8')
    print(json.dumps({'review_items':len(review),'fact_corrections':len(corrections),'claims':len(claims)},ensure_ascii=False))


if __name__=='__main__':main()
