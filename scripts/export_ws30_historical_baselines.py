"""Export absolute and ECMP-paired WS-25/27/28 baselines with nominal intervals."""
import csv
import hashlib
import json
import random
import re
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
MODES=['fecmp','drill','conga','letflow','conweave','classreserve']
def interval(values,seed):
    rng=random.Random(seed)
    draws=sorted(statistics.median(rng.choices(values,k=len(values))) for _ in range(10000))
    return [draws[250],draws[9750]]
def main():
    audit=EV/'ws30-historical-raw-audit.json';data=json.loads(audit.read_text())
    rows=[dict(r,cohort='old' if r['group']=='ws25' else 'main') for r in data['cells']
          if r['group'] in ['ws25','ws27','ws28native'] and r['mode'] in MODES]
    assert len(rows)==288
    folders={'ws25':'ws25-first-paper','ws27':'ws27-guardhash-compare',
             'ws28native':'ws28-classreserve-explanation'}
    branches=[]
    for r in rows:
        if r['mode'] not in ['conga','letflow','conweave']:continue
        logpath=ROOT.parent/folders[r['group']]/'results'/r['id']/'logs/config.log'
        text=logpath.read_text(encoding='utf-8',errors='replace')
        names=({"flowlet_timeouts":r"Number of flowlet's timeout:(\d+)"}
               if r['mode']!='conweave' else {
                   'rtt_replies':r"Number of INIT's Reply sent \(RTT_REPLY\):(\d+)",
                   'notify':r'Number of NOTIFY Sent:(\d+)',
                   'reroute':r'Number of Rerouting:(\d+)',
                   'ooo_enqueued':r'Number of OoO enqueued pkts:(\d+)',
                   'voq_flush':r'Number of VOQ Flush Total:(\d+)'})
        counts={}
        for key,pattern in names.items():
            found=re.findall(pattern,text);assert len(found)==1,(r['id'],key)
            counts[key]=int(found[0])
        branches.append({'cohort':r['cohort'],'mode':r['mode'],'id':r['id'],
                         'log_sha256':hashlib.sha256(logpath.read_bytes()).hexdigest(),'counts':counts})
    summary=[]
    for gi,cohort in enumerate(['old','main']):
        for mi,mode in enumerate(MODES):
            group=[r for r in rows if r['cohort']==cohort and r['mode']==mode];assert len(group)==24
            result={'cohort':cohort,'mode':mode,'n':24}
            for index,field in enumerate(['moe_batch_us','background_p99_us','moe_change_pct','bg_change_pct']):
                vals=[r[field] for r in group]
                result[field+'_median']=statistics.median(vals)
                result[field+'_nominal_95pct']=interval(vals,20263010+gi*100+mi*10+index)
            result['moe_improved']=sum(r['moe_change_pct']<0 for r in group)
            result['background_gt3']=sum(r['bg_change_pct']>3 for r in group)
            result['background_improved']=sum(r['bg_change_pct']<0 for r in group)
            summary.append(result)
    branchsummary=[]
    for cohort in ['old','main']:
        for mode in ['conga','letflow','conweave']:
            group=[r for r in branches if r['cohort']==cohort and r['mode']==mode]
            branchsummary.append({'cohort':cohort,'mode':mode,'n':len(group),
                                  'counts':{k:{'sum':sum(r['counts'][k] for r in group),
                                               'nonzero_cells':sum(r['counts'][k]>0 for r in group)}
                                            for k in group[0]['counts']}})
    result={'raw_audit_sha256':hashlib.sha256(audit.read_bytes()).hexdigest(),
            'bootstrap_draws':10000,'bootstrap_seed_base':20263010,
            'scope':'192 background; each cohort n=24; nominal descriptive intervals; cohorts not pooled',
            'summary':summary,'branch_summary':branchsummary,'branch_receipts':branches,'cells':rows}
    out=EV/'ws30-historical-baseline-export.json'
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    csvrows=[]
    for row in summary:
        flat={}
        for k,v in row.items():
            if isinstance(v,list):flat[k+'_low'],flat[k+'_high']=v
            else:flat[k]=v
        csvrows.append(flat)
    with (EV/'ws30-historical-baseline-summary.csv').open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    lines=['# WS-30 历史基线双侧数据表','',
           '2026 年 10 月 24 日。每组 24 个独立需求，192 背景档。区间均为按需求重采样 10,000 次的名义 95% 描述区间。绝对值是跨需求中位数；变化先在同需求内以 ECMP 为分母，再跨需求取中位数。两组分别汇总。','']
    for cohort,label in [('old','WS-25 旧组'),('main','WS-27／28 主组')]:
        lines += ['## '+label,'',
                  '| 方法 | 批时间 μs［区间］ | 背景 P99 μs［区间］ | 批时间变化［区间］ | 背景 P99 变化［区间］ | 背景超 +3% |',
                  '| --- | ---: | ---: | ---: | ---: | ---: |']
        for row in [r for r in summary if r['cohort']==cohort]:
            def fmt(field,suffix=''):
                a,b=row[field+'_nominal_95pct'];v=row[field+'_median']
                return f'{v:.3f}{suffix}［{a:.3f}, {b:.3f}］'
            lines.append('| '+row['mode']+' | '+fmt('moe_batch_us')+' | '+fmt('background_p99_us')+' | '+
                         fmt('moe_change_pct','%')+' | '+fmt('bg_change_pct','%')+' | '+str(row['background_gt3'])+'/24 |')
        lines.append('')
    lines += ['## 实际动态分支','',
              '| 输入组 | 方法 | 分支：累计次数／非零格数 |','| --- | --- | --- |']
    for r in branchsummary:
        counts='；'.join(f'{k}：{v["sum"]}／{v["nonzero_cells"]}/24' for k,v in r['counts'].items())
        lines.append(f'| {r["cohort"]} | {r["mode"]} | {counts} |')
    lines += ['',
              'flowlet timeout 或中途换路为零只表示本负载中该分支未触发，不等于整个算法与 ECMP 相同。ConWeave 的初始回复和通知计数单列，防止把零 reroute 误写成整个机制没有运行。ECMP、DRILL 和 ClassReserve 的分派与 raw 身份由历史审计核验；旧日志没有可供直接复算的独立 DRILL 决策次数，不能填零。',
              '',
              '完整实验 ID、FCT／trace／日志哈希、每输入值和分支收据见 [JSON](evidence/ws30-historical-baseline-export.json)；用于制表的扁平数据见 [CSV](evidence/ws30-historical-baseline-summary.csv)。本表重算区间采用独立、固定的重采样种子，可能与历史报告最后几位不同，不改写历史分析和判据。',
              '',
              'ClassReserve 在旧、新组的中位数均位于 DRILL 与其余原生基线之间。两组公共分母统一后，原先所谓“整体排序反转”不成立；效应幅度差异和单输入代价仍保留。']
    dest=ROOT/'docs/research/ws30-historical-baseline-tables.md'
    with dest.open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps({'cells':len(rows),'summary_rows':len(summary),'branch_receipts':len(branches)}))
if __name__=='__main__':main()
