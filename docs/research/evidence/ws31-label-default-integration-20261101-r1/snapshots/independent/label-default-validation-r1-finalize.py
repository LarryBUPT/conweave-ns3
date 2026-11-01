"""Package completed default-off regressions using local evidence only."""
import datetime, hashlib, importlib.util, json, pathlib, re, subprocess, sys
sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent
PREFIX = 'label-default-validation-r1'
EVIDENCE = ROOT / (PREFIX + '-evidence')
SOURCE = ROOT.parents[4] / 'ws31-candidates-implementation'
PROJECT = ROOT.parents[5]

def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''): h.update(chunk)
    return h.hexdigest()
def dump(suffix, value):
    (ROOT / (PREFIX + '-' + suffix)).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def git(*args): return subprocess.check_output(['git', '-C', str(SOURCE), *args])

def observations(path, kind):
    hashes = {k: hashlib.sha256() for k in ('choice', 'route', 'combined', 'dedicated')}
    counts = {}
    with path.open('rb') as stream:
        for line in stream:
            assert not line.startswith(b'WS31_LABEL_')
            if line.startswith((b'WS30_CHOICE ', b'WS30_ROUTE ')):
                key = 'choice' if line.startswith(b'WS30_CHOICE ') else 'route'
                clean = re.sub(rb' uid=[^ \r\n]+', b'', line)
                hashes[key].update(clean); hashes['combined'].update(clean)
            if line.startswith(('WS31_' + kind.upper() + '_').encode()):
                hashes['dedicated'].update(line)
                key = line.split(b' ', 1)[0].decode('ascii'); counts[key] = counts.get(key, 0) + 1
    assert counts
    return {'hashes': {k: v.hexdigest() for k, v in hashes.items()}, 'dedicated_event_counts': counts}

def main():
    r = read(ROOT / (PREFIX + '-receipt.json')); plan = read(ROOT / (PREFIX + '-frozen-plan.json'))
    assert r['status'] == 'COMPLETE_FOR_THREE_DEFAULT_OFF_NETWORK_REGRESSIONS_ONLY'
    assert r['network_runs_started'] == 3 and r['core_tests_executed'] == r['sync_commands'] == r['deploy_commands'] == 0
    assert 'error' not in r and all(c['status'] == 'PASS' for c in r['cells'])
    prepared = read(ROOT / (PREFIX + '-preparation.json'))
    for name, h in prepared['files'].items():
        if name != PREFIX + '-finalize.py': assert sha(ROOT / name) == h
    assert sha(ROOT / (PREFIX + '-frozen-plan.json')) == r['plan_sha256'] == 'a81e95af15bba097c8ce900348c260a58c8b2a10416b204380c217331f1d7b4e'
    builds = read(ROOT / (PREFIX + '-all-builds-verified.json')); source_map = builds[0]['source_hashes']
    assert len(builds) == 3
    for path, h in source_map.items(): assert hashlib.sha256(git('show', r['source_sha'] + ':' + path)).hexdigest() == h
    tree = git('ls-tree', '-r', r['source_sha'])
    assert (ROOT / (PREFIX + '-source-git-tree.txt')).read_bytes() == tree
    spec = importlib.util.spec_from_file_location('default_identity_verifier', ROOT / (PREFIX + '-verifier.py'))
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    cells = []; totalfiles = 0; totalsupport = 0
    for c, p, built in zip(r['cells'], plan['cells'], builds):
        assert c['id'] == p['id'] == built['id']
        kind = c['id'].rsplit('-', 1)[1]; folder = EVIDENCE / c['id']; target = folder / 'results'
        manifest = read(folder / 'remote-manifest.json')
        assert manifest['source_head'] == r['source_sha'] and manifest['source_hashes'] == built['source_hashes'] == source_map
        assert manifest['binary_sha256'] == built['binary_sha256'] == c['binary_sha256']
        for rel, info in manifest['files'].items():
            path = target / rel
            assert path.stat().st_size == info['bytes'] and sha(path) == info['sha256']; totalfiles += 1
        meta = read(target / 'metadata.json')
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == r['source_sha']
        assert meta['parameters']['ws31_label_profile'] == 0 and meta['concurrency_cap'] == 1
        off = ('ws30_tag_transform', 'ws30_composition', 'ws30_lifecycle', 'ws30_life_profile',
               'ws21_heartbeat_fault_mode', 'ws21_heartbeat', 'ws21_feedback', 'ws21_identity',
               'ws13_diag', 'ws25_diag', 'ws28_tail_diag', 'ws18_admission', 'ws18_path')
        assert all(meta['parameters'].get(k, 0) == 0 for k in off)
        assert meta['build_mode'] == 'optimized' and meta['cpu_jobs'] == 2
        config = dict(line.split(None, 1) for line in (target / 'config/config.txt').read_text(encoding='ascii').splitlines() if line.strip())
        # The fixed worker passes profile0 through the simulation environment;
        # it is recorded in metadata rather than serialized into config.txt.
        assert config['WS21_HEARTBEAT_FAULT_MODE'] == '0'
        fct = next((target / 'raw').glob('*/*_out_fct.txt')); log = next((target / 'raw').glob('*/config.log'))
        v = verifier.verify(target / 'config/traffic_trace.txt', fct, log)
        assert v == c['acceptance']['all_input_verifier']
        assert v['flows'] == p['flow_count'] and v['payload_bytes'] == p['payload_bytes']
        assert read(folder / 'acceptance.json') == c['acceptance'] and read(folder / 'default-regression.json') == c['regression']
        refroot = (ROOT / 'c2-label-validation-r1-evidence/attempt2' if kind == 'c2' else ROOT / 'main-mode-dynamic-r1-evidence') / p['reference_id'] / 'results'
        refmeta = read(refroot / 'metadata.json'); assert refmeta['git_commit'] == p['reference_sha']
        reffct = next((refroot / 'raw').glob('*/*_out_fct.txt')); reflog = next((refroot / 'raw').glob('*/config.log'))
        assert fct.read_bytes() == reffct.read_bytes()
        obs = observations(log, kind); assert obs == observations(reflog, kind)
        for key in ('choice', 'route', 'combined'): assert obs['hashes'][key] == c['acceptance']['ordered_hashes'][key]
        assert obs['hashes']['dedicated'] == c['regression']['dedicated_all_events_and_states']['sha256']
        for rel in ('config/traffic_trace.txt', 'config/topology.txt'): assert (target / rel).read_bytes() == (refroot / rel).read_bytes()
        buildtext = (target / 'logs/build.log').read_text(encoding='utf-8')
        assert "'build' finished successfully" in buildtext
        tasks = re.findall(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]', buildtext)
        support = {f.name: sha(f) for f in folder.iterdir() if f.is_file()}; totalsupport += len(support)
        cells.append({'id': c['id'], 'status': 'PASS', 'results_path': str(target), 'reference_path': str(refroot),
                      'reference_id': p['reference_id'], 'reference_sha': p['reference_sha'], 'flows': v['flows'], 'payload_bytes': v['payload_bytes'],
                      'fct_sha256': sha(fct), 'config_sha256': sha(target / 'config/config.txt'), 'binary_sha256': c['binary_sha256'],
                      'result_files': manifest['files'], 'source_hashes': source_map, 'supporting_files': support,
                      'observations': obs, 'regression': c['regression'], 'queue': c['acceptance']['queue'], 'path': c['acceptance']['path'],
                      'build_tasks': max(int(y) for x, y in tasks), 'build_duration': re.findall(r"'build' finished successfully \(([^)]+)\)", buildtext),
                      'warnings': [line for line in buildtext.splitlines() if 'warning:' in line], 'run_resources': c['resource_samples']})
    refs = read(ROOT / (PREFIX + '-reference-integrity-before.json'))
    assert refs == read(ROOT / (PREFIX + '-reference-integrity-after.json')) and all(sha(pathlib.Path(p)) == h for p, h in refs.items())
    commands = r['commands']; bc = [c for c in commands if c['operation'] == 'guarded-build']; rc = [c for c in commands if c['operation'] == 'guarded-run']
    assert len(bc) == len(rc) == 3 and all(c['exit_code'] == 0 for c in commands)
    assert max(c['end_utc'] for c in bc) < min(c['start_utc'] for c in rc)
    assert [c['cell'] for c in rc] == [c['id'] for c in plan['cells']]
    assert read(ROOT / (PREFIX + '-sources-established.json'))['all3_fixed_source_copies_verified']
    assert read(ROOT / (PREFIX + '-guards-released.json'))['status'] == 'RELEASED'
    dump('phase-order.json', {'status': 'PASS', 'all_three_builds_before_any_run': True, 'build_commands': bc, 'run_commands': rc,
                             'serial_runs': 'Driver waits for terminal, transfer and acceptance before the next run', 'all_guards_released': True})
    res = r['build_resource_samples']
    assert not res['other_user_seen'] and not res['unknown_project_seen'] and res['max_sampled_cc1plus_count'] <= 6
    integrity = {'status': 'PASS', 'cells': 3, 'failures': 0, 'completed_records': sum(c['flows'] for c in cells),
                 'completed_payload_bytes': sum(c['payload_bytes'] for c in cells), 'result_files_checked': totalfiles,
                 'support_files_checked': totalsupport, 'unique_fixed_source_blobs': len(source_map), 'source_map_entries': 3 * len(source_map),
                 'source_tree_entries': len(tree.splitlines()), 'reference_files_rechecked': len(refs), 'source_maps_before_after_equal': True,
                 'new_remote_actions_by_finalizer': 0, 'old_tests_or_reference_runs': 0,
                 'source_head_observed': git('rev-parse', 'HEAD').decode().strip(), 'source_status_observed': git('status', '--porcelain').decode(),
                 'main_independent_mechanism_replay': 'Separate main review required', 'model_switch': 'No switch performed or claimed; no switching interface available'}
    assert integrity['completed_records'] == 312 and integrity['completed_payload_bytes'] == 605945856
    dump('integrity.json', integrity)
    candidate = PROJECT / '参考文献/候选'
    refpaths = [candidate / p for p in ('README.md', 'reading-log.md', 'papers/diffflow-2016/analysis-technical.md', 'papers/diffflow-2016/verification.md')]
    dump('reference-review.json', {'sources': {str(p): sha(p) for p in refpaths},
        'version': 'DiffFlow arXiv:1604.05107v1; 6 pages; archived PDF SHA256 f552fcb75a0cec582286db0032c81660ff161fe475609ae5e79ad7075a0ae164',
        'borrowing': 'Distinguish original business truth, classifier visibility and actual decision activation point',
        'applicability': 'Default-off compatibility requires unchanged original packet labels and complete pre-existing decision/state streams',
        'difference': 'DiffFlow advertises sampled long-flow identity and enables spraying after rule installation. This node keeps labels unchanged and tests pinned-QP candidates with profile0.',
        'observed_evidence': 'Three fixed-source default-off regressions; full FCT, ordered CHOICE/ROUTE retaining tags, and all dedicated event/state bytes equal fixed references',
        'not_extrapolated': ['No dynamic detection latency or classification error acceptance', 'No adapter lifecycle, independent V0, two-sided effects or cost acceptance', 'No author performance transferred and no new combined baseline'],
        'priority': 'Fixed Git source and each original experiment raw data remain final evidence'})
    rows = '\n'.join('| ' + c['id'].rsplit('-', 1)[1].upper() + ' | ' + c['reference_id'] + ' | ' + str(c['flows']) + ' | ' + format(c['payload_bytes'], ',') + ' | PASS |' for c in cells)
    report = f'''# 标签默认关闭三格回归报告

日期：2026 年 11 月 1 日。固定 `{r['source_sha']}` 的 C1／C2／C3 默认关闭回归 3/3 PASS，共 312 条完成记录、605,945,856 B。三格完整 FCT、保留 tag 的有序 CHOICE／ROUTE，以及各候选全部专属事件与状态均与固定参考一致。

## 1. 冻结范围与执行

计划 SHA-256 为 `{r['plan_sha256']}`。每格使用 104 条原请求、`ws31_correctness_r1.txt`、OS2 100 Gbps 拓扑、seed 1、PFC 0、IRN 1、DCQCN、9 MiB 缓冲和 `ws30_observe=2`。`ws31_label_profile=0`，旧标签变换、组合、生命周期和故障关闭。

个人 fork 的已推送固定提交、缓存 origin／引用／树／干净状态、新 ID、旧进程与资源门通过后，复用既有缓存和 worker。没有 fetch、deploy、核心或参考重跑。三个隔离 optimized `-j2` 全量构建全部验收后，串行运行 C1→C2→C3；见[顺序证据]({PREFIX}-phase-order.json)。

## 2. 原始回归结果

| 模式 | 只读参考 ID | 完成数 | 载荷 B | 结果 |
| --- | --- | ---: | ---: | --- |
{rows}

每格原请求身份、原需求起点、字节和实际包标签均核对。完整 FCT 按原始字节比较；CHOICE／ROUTE 只移除 uid，保留 tag。C1 评分与状态、C2 demand／launch／finish 与状态、C3 route 与状态分别对全部原始事件流计算哈希，逐项等于参考；不按抽样或最终汇总代替。没有 `WS31_LABEL_*` 观测。

队列入／出账守恒，丢弃、拒收和账本违规为 0，QP 内没有端口变化。C2 的 104 条 demand／launch／finish 按原始需求起点核对，原有等待规则与参考保持。旧参考文件哈希在运行前后和交付时保持一致。主对话另行独立重放机制，本副不把自身回归验收写作主验。

## 3. 完整性与资源

{totalfiles} 份远程结果、{totalsupport} 份支持文件、每格 {len(source_map)} 个固定 Git 对象及 {len(tree.splitlines()):,} 项完整树已核，构建前／运行后源码映射和二进制一致。三格构建均为 1,464 项，警告和用时保留在[最终索引]({PREFIX}-index.json)。

构建每 5 秒采样，共 {res['sample_count']} 次；最大采样编译前端数 {res['max_sampled_cc1plus_count']}，最高负载 {res['max_sampled_load_1m']:.2f}，最低可用内存约 {res['min_sampled_available_gib']:.3f} GiB，磁盘余量约 {res['min_sampled_free_gib']:,.3f} GiB。未采到其他用户或未知项目作业。仿真串行、每 2 秒采样；这些数字为采样界值。当前工具没有模型切换接口，本次未执行或声称模型切换。

## 4. 结论与承接

本节点完成新标签源码默认关闭的网络兼容性验证。profiles 1／2／3 的早晚构包和部分错误覆盖、SwitchNode／RdmaClient 生命周期与异常适配器、独立 C1 V0、三候选双侧效果及状态／运行成本继续由主对话总计划承接。新组合基线尚未形成。

已从候选 README 和 reading-log 复核 DiffFlow v1 技术与核验记录，借鉴原业务真值、分类可见性和生效位置的区分。该论文的抽样广告与喷洒机制不同于本轮固定 QP 回归，作者结果不代替本轮 raw；见[节点复核]({PREFIX}-reference-review.json)。全部源码／入口／环境约束已有释放收据。本副停止新增执行，等待下一单目标。
'''
    (ROOT / (PREFIX + '-report.md')).write_text(report, encoding='utf-8')
    handoff = f'''# 标签默认关闭回归九节交接

日期：2026 年 11 月 1 日。来源副对话 `01a19323-2201-7b23-a0f1-905c71496d38`，接收主对话 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。

## 1. 本对话目标

按冻结计划完成新标签源码的 C1／C2／C3 默认关闭网络回归。旧参考只读，不扩展动态标签或生命周期验证。

## 2. 已确认的项目事实

固定源 `{r['source_sha']}`，计划 SHA-256 `{r['plan_sha256']}`。三个 ID 前缀 `20261101-124500-ws31-labeldef-r1-`，后缀 c1、c2、c3。每格 104 请求、201,981,952 B，profile 0。

## 3. 已完成工作

新 ID／缓存／源码／作业／资源门通过后，三份隔离全构建先行，全部通过再串行仿真。3/3 PASS，共 312 条完成记录、605,945,856 B。身份、需求、标签、FCT、有序路由、专属事件和状态均验，见[报告]({PREFIX}-report.md)。

## 4. 已形成的设计决策

兼容性按完整 FCT 和全部专属事件流比较；有序 CHOICE／ROUTE 仅删除 uid，保留实际 tag。沿用原始身份、输入及需求起点。使用旧参考而不重复运行，源与参数未为回归结果调整。

## 5. 当前状态

`COMPLETE FOR THREE DEFAULT-OFF NETWORK REGRESSIONS ONLY`。{totalfiles} 份结果、{totalsupport} 份支持文件、{len(source_map)} 个唯一固定对象和 {len(tree.splitlines()):,} 项树已核。固定副本及全部 guarded run 均已建立，算法／入口／环境约束释放。实现 checkout 的观察值单独保存在[完整性记录]({PREFIX}-integrity.json)，不以未来 HEAD 替代本轮固定源。

## 6. 未解决问题

主对话独立机制重放待验。动态 profiles 1／2／3、适配器生命周期及异常、独立 V0、双侧效果和成本仍待完成；本轮不建立新组合基线。

## 7. 后续推荐动作

主对话先核本轮索引、原始记录及独立机制重放，再冻结早晚构包与部分错误小输入及下一单目标。执行入口为主计划 `label-default-validation-r1.json` 和其 verifier；本副不自动扩格。

## 8. 与其他工作流的关系

只写本轮 independent 前缀及证据目录。没有修改算法、worker、controller、环境、主文档或权威状态，未提交／推送；核心、参考和 Ofan/RR 未重跑，WS-29 未访问。完整科学范围由主对话继续承接。

## 9. CONTEXT SNAPSHOT

固定 2ed7d342 的 C1／C2／C3 默认关闭三格全部 PASS。三份 optimized `-j2` 构建先于串行网络运行；312 条完成、605,945,856 B。FCT、保留 tag 的有序事件及全部专属状态精确恢复参考，未出现标签观测。固定源、输入、二进制、资源和 raw 哈希见[最终索引]({PREFIX}-index.json)。主独验与动态／生命周期／效果成本继续 ACTIVE。
'''
    (ROOT / (PREFIX + '-handoff.md')).write_text(handoff, encoding='utf-8')
    deps = ['c2-label-validation-r1-attempt2-driver.py', 'main-mode-dynamic-r1-driver.py', 'zero-control-pilot-r1-driver.py']
    docs = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in ROOT.glob(PREFIX + '-*') if p.is_file() and p.name not in (PREFIX + '-index.json', PREFIX + '-qa.json')}
    dump('index.json', {'status': r['status'], 'source_sha': r['source_sha'], 'plan_sha256': r['plan_sha256'], 'verification': integrity,
                        'cells': cells, 'documents': docs, 'dependencies': {n: sha(ROOT / n) for n in deps}, 'references': refs,
                        'resources': res, 'main_acceptance': 'SEPARATE_MAIN_RAW_REPLAY_REQUIRED', 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    for n, info in docs.items(): assert sha(ROOT / n) == info['sha256']
    links = []
    for text in (report, handoff):
        for rel in re.findall(r'\]\(([^)]+)\)', text): assert (ROOT / rel).exists(); links.append(rel)
    assert len(re.findall(r'^## \d\.', handoff, re.M)) == 9
    dump('qa.json', {'status': 'PASS', 'index_sha256': sha(ROOT / (PREFIX + '-index.json')), 'documents_rechecked': len(docs),
                     'support_files_rechecked': totalsupport, 'links_checked': len(links), 'handoff_sections': 9,
                     'scope': 'Default-off compatibility only; separate main replay and dynamic/lifecycle/V0/effects/cost pending',
                     'style': 'Original ruanyf README and six chapters previously read; headings, spacing, paragraphs, values, punctuation and structure reviewed',
                     'new_remote_actions': 0, 'new_tests_or_runs': 0, 'all_guards_released': True})
    print(json.dumps({'status': 'PASS', 'index_sha256': sha(ROOT / (PREFIX + '-index.json')), 'qa_sha256': sha(ROOT / (PREFIX + '-qa.json')), 'verification': integrity}, ensure_ascii=False))

if __name__ == '__main__': main()
