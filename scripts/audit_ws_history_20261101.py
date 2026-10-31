"""Audit project-memory coverage and existing evidence; never rerun simulation."""

import hashlib
import json
import pathlib
import re
import subprocess


REPO = pathlib.Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
EVIDENCE = REPO / "docs/research/evidence/ws-history-20261101"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_observation(path):
    def run(*args):
        r = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return {"exit_code": r.returncode, "output": r.stdout.strip(), "stderr": r.stderr.strip()}
    return {"path": str(path), "head": run("rev-parse", "HEAD"), "branch": run("branch", "--show-current"), "status": run("status", "--short")}


def main():
    inventory = json.loads((EVIDENCE / "thread-catalog.json").read_text(encoding="utf-8"))
    reads = []
    for path in sorted(EVIDENCE.glob("01*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if "ws_number" in item:
            reads.append((path, item))
    read_numbers = {item["ws_number"] for _, item in reads}
    assert read_numbers == set(range(1, 31)) - {29}, read_numbers
    assert all(item["ws_number"] != 29 for _, item in reads)
    assert inventory["active_pagination_complete"] and inventory["archived_pagination_complete"]

    states = {}
    table = (REPO / "docs/project-state/WORKSTREAMS.md").read_text(encoding="utf-8-sig")
    for line in table.splitlines():
        fields = [s.strip() for s in line.strip("|").split("|")]
        if fields and re.match(r"WS-\d+", fields[0]):
            num = int(re.match(r"WS-(\d+)", fields[0]).group(1))
            states.setdefault(num, []).append({"label": fields[0], "name": fields[1], "state": fields[2], "evidence": fields[3]})

    important = [
        "thesis/ws30-v13-formal-complete-main-verification.json",
        "thesis/ws30-v13-formal-stats-main-audit-r2.json",
        "thesis/ws30-v13-endpoint-all48-main-verification.json",
        "thesis/ws30-v13-w5-all36-main-verification-r1.json",
        "thesis/ws30-v13-rng-all48-raw-main-verification-r1.json",
        "thesis/ws30-v13-rng-full-node-main-audit-r1.json",
        "thesis/ws30-v13-review26-reconciliation-main-r1.json",
        "thesis/ws30-v13-reproducibility-index.md",
        "thesis/review-evidence/20261029-v14/p0-wave27-acceptance-main-r1.json",
        "workspace/ws30-attribution-audit/results/ws30-paper-v14-p0-full52-index-r1.json",
        "workspace/ws30-attribution-audit/docs/research/ws30-v12-evidence-synthesis-r1.md",
        "workspace/ws30-attribution-audit/docs/research/ws30-v12-scoped-recheck-r2.md",
        "workspace/ws26-classmix-validation/docs/handoffs/2026-10-11-88-ws26-third-signal-admission-design.md",
        "workspace/ws26-classmix-validation/docs/research/ws26-failure-cause-and-method-gate.md",
        "workspace/ws26-classmix-validation/docs/research/ws26-classlane4-pilot-r2-analysis.md",
        "workspace/ws27-guardhash-compare/docs/handoffs/2026-10-13-78-ws27-independent-confirmation.md",
        "workspace/ws27-guardhash-compare/docs/research/evidence/ws27-confirm-analysis.json",
        "workspace/ws28-classreserve-explanation/docs/research/ws28-final-acceptance-audit.md",
        "thesis/queuepin-v13-figure-revision-r12/icc-zh.md",
        "thesis/queuepin-v13-figure-revision-r12/ieee/main.tex",
        "thesis/queuepin-v13-figure-revision-r12/queuepin-icc-authors-r12.pdf",
        "thesis/queuepin-v13-figure-revision-r12/records/r12-main-verification.json",
    ]
    manifest = []
    for name in important:
        path = PROJECT / name
        assert path.is_file(), name
        manifest.append({"path": str(path), "relative_project_path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    expected = {
        "thesis/ws30-v13-rng-all48-raw-main-verification-r1.json": "ce011881bfba3aaad713ab73502710782f743195be6468c57a774778742f6399",
        "thesis/ws30-v13-rng-full-node-main-audit-r1.json": "e0dd2512c4ef17fffbd9f926cdc3f4d21b25a2a5a771d74e3b03fda2407e71da",
        "thesis/ws30-v13-review26-reconciliation-main-r1.json": "2bfa6de84394237ee34c898eeee5646a63fb9f4b488e39746e0e481ee7feaecf",
        "thesis/queuepin-v13-figure-revision-r12/queuepin-icc-authors-r12.pdf": "f16e2fa5e7873aa62acf6181c5f0eafc45a90dfd75d583fcc27dfed345563a0b",
    }
    for name, value in expected.items():
        assert digest(PROJECT / name) == value, name
    p0 = json.loads((PROJECT / "thesis/ws30-paper-v14-current.json").read_text(encoding="utf-8-sig"))
    assert p0["planned_performance_runs"] == 892
    assert p0["new_simulation_runs_main_accepted"] == 52
    assert p0["remaining_formal_runs"] == 840
    modules = [("P1", 360), ("P2", 72), ("P3", 32), ("P4", 24), ("P5", 32), ("P6", 64), ("P7", 32), ("P8", 16), ("P9", 48), ("P10", 120), ("P11", 40)]
    assert sum(count for _, count in modules) == 840

    coverage = []
    for num in range(1, 31):
        entries = [(p, i) for p, i in reads if i["ws_number"] == num]
        handoffs = sorted(str(p.relative_to(REPO)).replace("\\", "/") for p in (REPO / "docs/handoffs").glob("*.md") if re.search(rf"ws0?{num}(?!\d)", p.name, re.I))
        if num <= 6:
            aliases = {1:"2026-09-24-01-research-skills-navigation.md",2:"2026-09-24-02-research-discovery.md",3:"2026-09-24-03-reference-repositories.md",4:"2026-09-24-04-local-remote-workflow.md",5:"2026-09-24-05-baseline-fidelity.md",6:"2026-09-24-06-six-column-input-and-tags.md"}
            name = aliases[num]
            assert (REPO / "docs/handoffs" / name).is_file()
            handoffs = sorted(set(handoffs + ["docs/handoffs/"+name]))
        coverage.append({"ws_number":num,"thread_read":num!=29,"read_scope":"latest returned turns plus relevant handoff/source documents" if num!=29 else "metadata only; user explicitly deferred WS-29 and prohibited reading/waking it", "threads":[{"id":i["thread_id"],"title":i["title"],"evidence":str(p.relative_to(REPO)).replace("\\","/"),"has_older_turns":i.get("page",{}).get("hasMore")} for p,i in entries],"canonical_state_rows":states.get(num,[]),"canonical_handoffs":handoffs})
    body = {
        "observed_date":"2026-11-01", "scope":"Project-memory coverage audit, not a new numerical/raw replication and not an exhaustive message-by-message reading",
        "read_thread_count":len(reads),"covered_workstream_numbers":sorted(read_numbers),"deferred_metadata_only":[29],"coverage":coverage,
        "files":manifest,"existing_expected_hashes_match":True,
        "v14":{"planned":892,"accepted_P0":52,"not_executed":840,"modules":[{"module":m,"runs":n,"new_disposition":"not executed; removed from automatic WS-30 continuation by user-approved scope closure; only revisit under a separately justified new protocol"} for m,n in modules]},
        "git_observations":[git_observation(PROJECT/p) for p in ["workspace/LarryBUPT-conweave-ns3","workspace/ws26-classmix-validation","workspace/ws27-guardhash-compare","workspace/ws28-classreserve-explanation"]],
        "remote_access_performed":False,"new_simulation_performed":False,"ws29_body_read":False,"ws29_archived":False,
    }
    (EVIDENCE/"coverage-and-source-manifest.json").write_text(json.dumps(body,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report = [
        "# WS 系列历史覆盖审计", "", "核对日期：2026 年 11 月 1 日。", "",
        "活动目录与归档目录均已完整分页枚举。共读取 33 份相关对话最新两至三轮，覆盖 WS-01～28 与 WS-30；WS-29 按用户决定只登记元数据，正文未读取，不唤醒、不归档。早期没有 WS 编号的标题按原 Handoff 映射到 WS-01～05。", "",
        "本审计检查各工作流的最新结论、交接及权威入口是否覆盖，不声称逐条穷尽所有历史消息，也不重新验证所有原始数值。科学状态仍以固定源码和对应实验 ID 为准。", "",
        "## 1. 本次发现和修正", "",
        "1. 主仓库台账缺少 WS-26～29 的最新记录：补入 WS-26 用户暂停与未完成、WS-27/28 预设范围完成、WS-29 后置保留。",
        "2. WS-30 入口仍停在旧 v14 840 次 ACTIVE，未体现用户退出 v14、后续 v13 修订和初投稿：按 ADR-011 更新当前入口，旧快照和收据保留历史身份。",
        "3. 稿件导航仍指 v11：保留旧导航快照，改指 QueuePin r12；服务器 PDF 字节身份和 ORCID 未核事项单独承接。",
        "4. WS-01～25 已有权威台账和相关交接入口，本次最新对话审查未发现需要改判其科学结论的证据。各阶段已说明的未测范围保持未测，不因后续成功而回填。", "",
        "## 2. 逐工作流覆盖", "",
        "| 工作流 | 当前范围状态 | 对话证据 | 交接入口 |", "| --- | --- | --- | --- |",
    ]
    for row in coverage:
        num = row["ws_number"]
        state = "；".join(dict.fromkeys(x["state"] for x in row["canonical_state_rows"])) or "待补台账"
        threads = "；".join(f'[{x["title"].replace("|", "／")}](../research/evidence/ws-history-20261101/{x["id"]}.json)' for x in row["threads"]) if num != 29 else "两对话元数据保留，按用户要求未读正文"
        if num in [26,27,28]:
            handoff = "[补全交接](../handoffs/2026-11-01-ws26-ws28-history-reconciliation.md)"
        elif num == 29:
            handoff = "[后置决定](../decisions/ADR-011-ws30-closure-ws31-and-ws29-deferral.md)"
        elif num == 30:
            handoff = "[收束交接](../handoffs/2026-11-01-ws30-v13-closure.md)"
        else:
            handoff = "、".join(f'[交接 {i+1}](../../{p})' for i,p in enumerate(row["canonical_handoffs"]))
        report.append(f"| WS-{num:02d} | {state} | {threads} | {handoff} |")
    report += ["", "## 3. 审计证据与未完成项", "",
        "[目录清单](../research/evidence/ws-history-20261101/thread-catalog.json)保存枚举来源；[机器收据](../research/evidence/ws-history-20261101/coverage-and-source-manifest.json)包含实际源文件哈希、原 Git 状态和 v14 未执行模块。各对话 JSON 只保留范围、用户消息及最终回复，未保存推理过程。",
        "", "WS-26 的两个未跟踪草稿仍在其原工作树，未修改、提交或运行。WS-29 未读正文是明确保留范围，不宣称其科学工作已验收。WS-31 是新设研究，执行清单和主副登记另列，不计入本次 WS-01～30 历史读取数。",
        "", "本次只归档用户指定的两个 WS-30 实验对话；其它活动、暂停或已归档对话的状态不批量更改。重要用户决定、原实验 NO-GO 和未执行条件保持原身份。", ""]
    (REPO/"docs/project-state/WS_HISTORY_COVERAGE.md").write_text("\n".join(report),encoding="utf-8")
    print(json.dumps({"read_threads":len(reads),"covered_numbers":len(read_numbers),"deferred_metadata_only":[29],"verified_files":len(manifest),"remaining_v14_runs_not_executed":840},ensure_ascii=False))


if __name__ == "__main__":
    main()
