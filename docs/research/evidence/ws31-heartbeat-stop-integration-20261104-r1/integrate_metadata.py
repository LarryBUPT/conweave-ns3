import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
NOW = datetime.now(timezone.utc).isoformat()
HANDOFF = "docs/handoffs/2026-11-04-ws31-heartbeat-stop-integration.md"
EVIDENCE = OUT.relative_to(ROOT).as_posix()
STATE_FILES = [
    "docs/project-state/CURRENT_STATE.md",
    "docs/project-state/ROADMAP.md",
    "docs/project-state/WORKSTREAMS.md",
    "docs/project-state/WS31_EXECUTION.md",
    "docs/project-state/ws31-coordination.json",
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def new_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

def edit(relative, changes):
    path = ROOT / relative
    original = path.read_bytes()
    newline = "\r\n" if b"\r\n" in original else "\n"
    content = original.decode("utf-8").replace("\r\n", "\n")
    for old, replacement in changes:
        assert content.count(old) == 1, (relative, old, content.count(old))
        content = content.replace(old, replacement)
    path.write_bytes(content.replace("\n", newline).encode("utf-8"))

source_receipt = ROOT / "docs/research/ws31/main/evidence/finite-screen-heartbeat-stop-r1.json"
source_status = ROOT / "docs/research/ws31/main/current-status.json"
receipt = json.loads(source_receipt.read_text(encoding="utf-8-sig"))
main_status = json.loads(source_status.read_text(encoding="utf-8-sig"))
assert receipt["operation"] == "delete" and receipt["tool_result"] == "deleted"
assert receipt["hold_preserved"] and receipt["original_correctness_and_validation_obligations_preserved_incomplete"]
assert main_status["heartbeat_monitor"]["status"] == "DELETED_AFTER_FINITE_SCREEN_HOLD_RETAINED"
config = Path("C:/Users/Administrator/.codex/automations/ws-31/automation.toml")
assert not config.exists(), "Unexpected live automation; stop metadata integration"
platform = json.loads((OUT / "platform-observations.json").read_text(encoding="utf-8"))
assert len(platform["archived_threads_current"]) == 5
snapshot = json.loads(platform["ws31_compact_snapshot"]["content"][0]["text"])["polls"][0]
assert snapshot["thread"]["status"]["type"] == "idle"
cursor = snapshot["cursor"]
before_sha = {p: sha(ROOT / p) for p in STATE_FILES}
coord_path = ROOT / STATE_FILES[-1]
coord = json.loads(coord_path.read_text(encoding="utf-8-sig"))
original_goal = copy.deepcopy(coord["next_registered_goal"])
original_independent = copy.deepcopy(coord["independent"])
original_status = coord["status"]
assert original_status == "HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION"
old_heartbeat = copy.deepcopy(coord["heartbeat"])
assert old_heartbeat["status"] == "ACTIVE"
for source in [source_receipt, source_status]:
    target = OUT / "snapshots" / source.name
    target.parent.mkdir(exist_ok=True)
    with target.open("xb") as stream:
        stream.write(source.read_bytes())
new_json(OUT / "heartbeat-before.json", old_heartbeat)
new_json(OUT / "automation-absence.json", {
    "observed_at_utc": NOW,
    "path": str(config),
    "exists": config.exists(),
    "directory_exists": config.parent.exists(),
    "automation_tool_view_returned_machine_readable_state": False,
    "independent_observation": "Expected automation.toml absent; corroborates main deletion receipt, not a fresh delete action",
    "recreated_or_mutated_by_integration": False,
})
(OUT / ".gitattributes").write_text("* -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\nsnapshots/** -whitespace\n", encoding="utf-8")

edit(STATE_FILES[0], [
    ("心跳已实际补入本 HOLD，保留原周期与静默规则。", "`ws-31` 心跳已由主对话删除；Integration 已核删除收据和本地配置缺失，见[运行状态同步](../handoffs/2026-11-04-ws31-heartbeat-stop-integration.md)。未经新指示不重建，HOLD 与全部未完成义务保持。"),
    ("当前为 `ACTIVE_REVIEW_INFORMED_RESCOPING_CANDIDATE_ENGINEERING_PAUSED`", "外评后的研究范围记录为 `ACTIVE_REVIEW_INFORMED_RESCOPING_CANDIDATE_ENGINEERING_PAUSED`，当前执行状态以上方 HOLD 为准"),
    ("`ws-31` 心跳已通过应用工具实际更新并回读保存文件，保留 ACTIVE、原主对话和 30 分钟周期，只改变任务范围及更新时间。", "历史上，`ws-31` 心跳曾通过应用工具更新为有限范围，保留当时 ACTIVE、原主对话和 30 分钟周期；这些原配置仍作为历史证据保留。主对话随后于 2026 年 11 月 4 日 12:12:42 UTC 记录删除完成，当前不再有该心跳配置。"),
])
edit(STATE_FILES[1], [("工程、测试、效果与远端继续暂缓，心跳已加入 HOLD。", "工程、测试、效果与远端继续暂缓；[心跳已删除](../handoffs/2026-11-04-ws31-heartbeat-stop-integration.md)，未经新指示不重建，HOLD 保持。")])
edit(STATE_FILES[2], [("副沿已知 idle14，无新派发，心跳已写 HOLD，无新基线", "副沿已知 idle14，无新派发；[心跳已删除](../handoffs/2026-11-04-ws31-heartbeat-stop-integration.md)，未经新指示不重建，HOLD 保持，无新基线")])
edit(STATE_FILES[3], [
    ("当前状态：ACTIVE_REVIEW_INFORMED_RESCOPING_CANDIDATE_ENGINEERING_PAUSED。", "当前执行状态：`HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION`；研究范围沿用外评后的暂停安排。"),
    ("本次心跳不授予恢复权。", "删除心跳不改变恢复门槛。"),
    ("`ws-31` 原 30 分钟 ACTIVE 心跳已通过应用工具补入本 HOLD 并回读，目标仍为主对话；不因本轮完成而自动开启下一轮分析或工程。唯一副沿已知文档终态 idle cursor `d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:14`，无新派发。Integration 只观察主 idle cursor `f13c4cd1-6458-4d58-888a-76f78e636578:3`。", "`ws-31` 心跳已由主对话删除，Integration 已核[删除收据与配置缺失](../handoffs/2026-11-04-ws31-heartbeat-stop-integration.md)。原 30 分钟 ACTIVE 配置保留为历史，未经新指示不重建，也不自动开启下一轮分析或工程。唯一副沿已知文档终态 idle cursor `d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:14`，无新派发；Integration 本次只观察主 idle cursor `" + cursor + "`。"),
])
coord.setdefault("heartbeat_scope_history", []).append(old_heartbeat)
coord["heartbeat"] = {
    "automation_id": "ws-31",
    "target_thread_id": coord["main"]["thread_id"],
    "status": "DELETED_AFTER_FINITE_SCREEN_HOLD_RETAINED",
    "interval_minutes": None,
    "former_interval_minutes": 30,
    "deleted_at_utc_reported_by_main": receipt["at_utc"],
    "main_deletion_receipt": source_receipt.relative_to(ROOT).as_posix(),
    "integration_verification": EVIDENCE + "/verification.json",
    "policy_source": HANDOFF,
    "configuration_absent_independently_observed": True,
    "recreate_without_new_instruction": False,
    "finite_scope_completed": True,
    "no_automatic_continuation": True,
    "unfinished_scientific_obligations_retained": True,
    "workstream_closed_or_archived": False,
}
coord["main"]["last_cursor"] = cursor
coord["main"]["last_observed_status"] = "idle after finite screen and heartbeat deletion; HOLD retained"
coord.setdefault("material_event_history", []).append(copy.deepcopy(coord["last_material_event"]))
coord["last_material_event"] = {
    "date": "2026-11-04",
    "kind": "HEARTBEAT_DELETION_INTEGRATED_HOLD_RETAINED",
    "record": HANDOFF,
    "verification": EVIDENCE + "/verification.json",
    "scientific_scope_changed": False,
    "new_engineering_runtime_acceptance": False,
    "new_network_acceptance": False,
    "new_baseline_established": False,
    "user_decision_required": False,
}
coord["integration_observed_utc"] = NOW
coord["last_updated_date"] = "2026-11-04"
assert coord["next_registered_goal"] == original_goal
assert coord["independent"] == original_independent
assert coord["status"] == original_status
coord_path.write_text(json.dumps(coord, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

handoff_text = """# WS-31 心跳删除后的运行状态同步

日期：2026 年 11 月 4 日。本次只同步运行状态，并复核 WS-26～WS-28 的既有归档。

## 1. 本对话目标

Integration 接收 WS-31 主对话的删除交接，将权威记录中的 ACTIVE 心跳改为已删除。科学任务范围沿用[有限筛查后的 HOLD](2026-11-04-ws31-finite-screen-hold.md)。

## 2. 已确认的项目事实

主对话的[原删除收据](../research/ws31/main/evidence/finite-screen-heartbeat-stop-r1.json)记录：2026 年 11 月 4 日 12:12:42 UTC，应用工具删除 `ws-31` 并返回 deleted。主状态的 `heartbeat_monitor` 同样记为已删除。Integration 独立观察预期的本地 `automation.toml` 不存在；只读 view 返回展示卡片，没有可解析的存在状态，因此不将其作为独立删除认证。

## 3. 已完成工作

保存原收据、主状态的原字节快照及本次 compact 观察；更新五份权威状态。删除前的 ACTIVE 配置追加到协调登记的历史，旧收据不改写。当前归档目录仍包含 WS-26 主、副、WS-27 原对话与续对话、WS-28 原对话；沿用[既有归档交接](2026-11-01-ws26-ws28-archive.md)，未重复归档。

## 4. 已形成的设计决策

有限筛查完成后，重复 HOLD 轮询没有可行动的监测目标。停止心跳不取消科学义务，不等于 WS-31 闭环或归档；未经新指示不重建自动续作。

## 5. 当前状态

执行状态保持 `HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION`。Integration 仍在个人 fork 的 `feature/ws23-ws24-evidence-integration` 分支。本次未编辑科学实现、主副原材料或实验输出，未访问远端，未派发任务。

## 6. 未解决问题

19 个 WIP 及身份、自然完成／取消、saved RX、history、共享协议、真实两代网络、独立 V0、匹配消融、业务／背景双侧效果和成本均保持未完成。WS-26 仍为用户暂停的历史阶段归档，不追认完整科学范围完成；WS-27、WS-28 保持约定范围完成。

## 7. 后续推荐动作

等待新需求／观测证据或明确范围更新，再确定有必要且有边界的下一动作。工程或远端恢复仍须存活候选理由、新契约、固定独立计划、资源门及明确范围更新。当前不重复分析、扫参、造配置／输入或接线。

## 8. 与其他工作流的关系

WS-29 继续后置，未读取或唤醒；WS-31 主、副不归档。WS-26～WS-28 原始证据、草稿和未执行事项保留。本次是运行记录同步，没有新的科学节点，不重复原始数据或文献分析。

## 9. CONTEXT SNAPSHOT

`ws-31` 心跳已删除，HOLD 保持，未经新指示不重建。科学义务和 WIP 全部保留；没有新组合基线。核验、来源指纹和当前平台观察见[本次收据](../research/evidence/ws31-heartbeat-stop-integration-20261104-r1/verification.json)。
"""
with (ROOT / HANDOFF).open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(handoff_text)
assert not config.exists()
new_json(OUT / "verification.json", {
    "at_utc": NOW,
    "status": "PASS_OPERATIONAL_METADATA_INTEGRATION_ONLY",
    "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "main_deletion_receipt": {"path": str(source_receipt), "sha256": sha(source_receipt)},
    "main_status": {"path": str(source_status), "sha256": sha(source_status), "heartbeat_monitor": main_status["heartbeat_monitor"]},
    "automation_config_absent": not config.exists(),
    "main_idle_cursor": cursor,
    "archived_targets_observed": len(platform["archived_threads_current"]),
    "archive_actions_repeated": False,
    "prior_heartbeat_preserved_in_history": coord["heartbeat_scope_history"][-1] == old_heartbeat,
    "HOLD_unchanged": coord["status"] == original_status,
    "next_registered_goal_unchanged": coord["next_registered_goal"] == original_goal,
    "independent_record_unchanged_no_direct_poll": coord["independent"] == original_independent,
    "scientific_source_results_WIP_modified_by_this_operation": False,
    "raw_or_scientific_audits_repeated": False,
    "unfinished_obligations_retained": True,
    "new_dispatch_or_remote_execution": False,
    "source_receipt_and_status_unchanged": all(sha(p) == sha(OUT / "snapshots" / p.name) for p in [source_receipt, source_status]),
    "before_sha256": before_sha,
    "after_sha256": {p: sha(ROOT / p) for p in STATE_FILES + [HANDOFF]},
    "style_check": "Original README and all six Ruanyf chapters read; headings, spacing, paragraphs, quantities, punctuation and structure checked.",
})
print(json.dumps({"status": "metadata_integrated", "evidence": EVIDENCE, "main_cursor": cursor, "archive_targets": 5}, ensure_ascii=False))
