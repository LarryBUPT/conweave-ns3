import copy,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
E=OUT.relative_to(ROOT).as_posix();H="docs/handoffs/2026-11-08-ws31-native-recovery-integration.md"
V=json.loads((OUT/"verification.json").read_text(encoding="utf-8"))
PL=json.loads((OUT/"platform-observations.json").read_text(encoding="utf-8"))
POLL=json.loads(PL["main_snapshot"]["content"][0]["text"])["polls"][0]
STATUS="ACTIVE_NATIVE_ENTRY_R2_ACCEPTED_NEXT_G2_BOUNDED_DESIGN_REQUIRED"
FILES=["docs/project-state/CURRENT_STATE.md","docs/project-state/ROADMAP.md","docs/project-state/WORKSTREAMS.md","docs/project-state/WS31_EXECUTION.md","docs/project-state/ws31-coordination.json"]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p:sha(ROOT/p) for p in FILES}
def replace(path,old,new):
    p=ROOT/path;b=p.read_bytes();nl="\r\n" if b"\r\n" in b else "\n";s=b.decode("utf-8").replace("\r\n","\n")
    assert s.count(old)==1,(path,old[:80],s.count(old))
    p.write_bytes(s.replace(old,new).replace("\n",nl).encode("utf-8"))
current="""## 当前阶段（2026-11-08）

WS-31 已按 11 月 8 日的新直接用户指令恢复，当前为 `ACTIVE_NATIVE_ENTRY_R2_ACCEPTED_NEXT_G2_BOUNDED_DESIGN_REQUIRED`，见[恢复节点整合](../handoffs/2026-11-08-ws31-native-recovery-integration.md)与[真实用户消息](../research/evidence/ws31-native-recovery-integration-20261108-r1/user-instruction.json)。原主、副各一项 Codex 原生心跳均为 ACTIVE、30 分钟，ID 分别为 `ws-31`、`ws-31-2`；实际创建收据、回读和配置哈希已核。当前不据配置存在宣称已观察到定时触发。11 月 4 日的 HOLD、删除和压缩纠错保留为历史，不覆盖本次新授权。

旧 R1 构建失败与完整失败材料保留，主修复了验收消费者的清单字段；源码仅一行 Waf 头导出修复。新固定源 `21b440985f90d2081438e435ef640adc9f43a42d` 的 R2 ID `20261108-152638-ws31-native-entry-r2` 已完成一次完整 `-j2` 构建和 20 个非网络对象案例。Integration 从本地独核 R1 的 65 raw／25 归档成员、R2 的 202 raw／147 归档成员、4,870 个 Git／源码归档与终态指纹、24 条实际命令、4,482 条包记录、两输入及 ELF／36 项目库；没有执行科学代码、构建、夹具、仿真或 SSH。

R2 完成事件是北京时间 15:36:38.050986，主完整验收观察是 15:47:06.250075，Integration 观察另存[本次收据](../research/evidence/ws31-native-recovery-integration-20261108-r1/verification.json)。主已显式释放有限约束；唯一副沿主报告 completed／idle cursor `3dadc2c4-3e49-4c0c-9ee1-13940917f98a:136`，未新派发。下一步由原主形成剩余 G2 的有界设计及独立单目标计划；已终态 R1／R2 不由心跳重跑。

通过范围仅限入口工程。OS2／framing、完整完成／共享协议、真实超时两代、独立 V0、匹配消融、业务／背景双侧效果与成本均未完成；历史 43 网络、17 适配器与本次 20 对象案例分列，无新组合基线。群端附加检查因桌面缺 `CC_SESSION_KEY` 失败，原生监督检查实际通过；不据此要求用户补 Codex 权限。原 WIP、Ofan 暂缓、六基线、WS-29 后置及旧控制器边界保持。下方历史“当前”与下一步均限于其记录日期，不能恢复旧任务或覆盖新状态。

## 历史阶段（2026-11-04）"""
replace(FILES[0],"## 当前阶段（2026-11-04）",current)
road="""## 2026-11-08 当前执行路线

1. [原生恢复节点](../handoffs/2026-11-08-ws31-native-recovery-integration.md)已由主验并经 Integration 本地核对。新直接用户恢复指令覆盖旧 HOLD；原主 `ws-31` 与唯一副 `ws-31-2` 两项监督均为 ACTIVE／30 分钟。旧删除收据和历史归档保持，不重复归档。
2. 固定源 `21b4409…` 的 R2 一次完整构建与 20 个非网络对象案例终态已验，原 R1 失败保留。原主下一步梳理剩余 G2 的生命周期、OS2／framing 和共享协议，形成有界设计及唯一副计划；新执行仍须固定源／输入／计划及资源门，已终态 R1／R2 不重跑。
3. 独立 V0、匹配消融、双侧效果及成本仍必做，功能案例不作效果样本；没有新组合基线。Ofan 暂缓、六既有基线、WS-29 后置、旧 WIP 和控制器边界不变。Integration 维护权威状态，不接管科学执行。

## 历史执行路线（2026-11-04）"""
replace(FILES[1],"## 2026-11-04 当前执行路线",road)
replace(FILES[2],"更新：2026-11-04。","更新：2026-11-08。")
p=ROOT/FILES[2];old=next(x for x in p.read_text(encoding="utf-8").splitlines() if x.startswith("| WS-31 |"))
row="| WS-31 | 类别感知机制与原生入口验证 | "+STATUS+" | [恢复整合](../handoffs/2026-11-08-ws31-native-recovery-integration.md)：新授权与两项原生 30 分钟监督已核；R1 失败保留；固定 21b 源 R2 一次完整构建、20 非网络对象案、4,482 包记录及完整来源主验／Integration 本地核对 | 下一步原主形成剩余 G2 有界设计和独立计划；已终态 R1／R2 不重跑。OS2／framing／完成／共享协议／真实两代／V0／消融／双侧效果／成本未完，无新基线；原 WIP、Ofan、六基线、WS-29 后置不变 |"
replace(FILES[2],old,row)
replace(FILES[3],"建立日期：2026 年 11 月 1 日。范围更新：2026 年 11 月 4 日。当前执行状态：`HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION`；研究范围沿用外评后的暂停安排。","建立日期：2026 年 11 月 1 日。范围更新：2026 年 11 月 8 日。当前执行状态：`"+STATUS+"`。")
section="""## 0. 当前执行范围：原生监督恢复后的 G2 有界设计

原主 11 月 8 日 15:16:20.167 的[真实用户指令](../research/evidence/ws31-native-recovery-integration-20261108-r1/user-instruction.json)重新授权内部监督、当前故障修复和继续推进，覆盖下方历史 HOLD。两项原生心跳均已创建并回读：主 `ws-31`、副 `ws-31-2`，ACTIVE／30 分钟；原创建时间、实际配置与核验范围见[整合交接](../handoffs/2026-11-08-ws31-native-recovery-integration.md)。不因摘要保留旧 HOLD 而撤销新授权，也不因本阶段通过而自动取消剩余义务。

R1 失败材料完整保留；主修复验收消费者读取字段后，独立接受失败来源并显式释放。副审／主验通过的一行 Waf 头导出修复形成固定源 `21b440985f90d2081438e435ef640adc9f43a42d`、个人分支 `experiment/ws31-native-entry-r2`。R2 ID `20261108-152638-ws31-native-entry-r2` 一次完整构建和 20 个非网络对象案例已主验，Integration 独核全部 202 raw／147 归档成员、4,870 个 Git／源码归档与终态指纹、24 实际命令和 4,482 包记录，输入／ELF／36 库与一次性 gate 对应。完成事件、主验收观察与 Integration 观察分别记录。

主已显式释放 R2 的有限约束。唯一副沿主报告 idle cursor `3dadc2c4-3e49-4c0c-9ee1-13940917f98a:136`，无新派发；Integration 不直查副或接管远端。当前下一目标为原主梳理剩余 G2 的有界设计，尚无下一个执行计划。新执行须固定源码、输入、唯一副计划与资源门；两条监督均不得重跑已终态 R1／R2。

OS2、实际 framing、完整完成及共享协议、真实超时与两代边界、独立 V0、匹配消融、业务／背景双侧效果和实际成本仍未完成。20 对象案例不并入历史 43 格网络或 17 例适配器；无新基线。群端检查缺少 `CC_SESSION_KEY` 的原失败与原生监督核验通过分列，不伪造群身份或要求用户放宽权限。原 WIP、Ofan 暂缓、六基线、后置 WS-29 和旧控制器边界保持。

## 历史执行范围（2026-11-04）：外评后的有限筛查"""
replace(FILES[3],"## 0. 当前执行范围：外评后的有限筛查",section)
coord_path=ROOT/FILES[4];d=json.loads(coord_path.read_text(encoding="utf-8-sig"))
old=copy.deepcopy(d)
d["status"]=STATUS;d["last_updated_date"]="2026-11-08";d["integration_observed_utc"]=V["integration_observed_at_utc"]
d.setdefault("heartbeat_scope_history",[]).append(copy.deepcopy(d["heartbeat"]))
d["heartbeat"]={"automation_id":"ws-31","deputy_automation_id":"ws-31-2","target_thread_id":d["main"]["thread_id"],"status":"ACTIVE_TWO_NATIVE_HEARTBEATS_READBACK_VERIFIED","interval_minutes":30,"timers":V["timers"],"source":"docs/research/ws31/main/evidence/native-supervision-r2/native-acceptance.json","verification":E+"/verification.json","actual_native_create_and_view":True,"integration_did_not_create_update_or_delete":True,"automatic_continuation_authorized":True,"completed_R1_R2_must_not_rerun":True,"old_deletion_history_preserved":True}
d.setdefault("scope_authorization_history",[]).append(copy.deepcopy(d["scope_authorization"]))
d["scope_authorization"]={"thread_id":d["main"]["thread_id"],"turn_id":V["user_authorization"]["turn_id"],"event_time_utc":V["user_authorization"]["event_time_utc"],"evidence":E+"/user-instruction.json","current_scope":"New explicit user authorization for native supervision, bounded failure repair and continuation. R1/R2 terminal; next remaining G2 bounded design required before new execution.","overrides_Nov4_HOLD_for_newly_authorized_work":True,"does_not_close_or_cancel_unfinished_science":True,"unbounded_effect_matrix_or_old_controller_authorized":False}
d["candidate_implementation_authorized"]=True
d["current_scope_precedence"]="November8 actual direct user recovery instruction and current frozen stage gates override historical November4 HOLD/deletion. R1/R2 terminal; next bounded design before a distinct execution plan. All historical receipts and unfinished obligations retained."
d["research_scope_status"]=STATUS
d["experiment_gate"]="ACTIVE_BOUNDED_CONTINUATION: R1/R2 accepted terminal, no replay. Original main must design remaining G2 and fix a distinct source/input/single-deputy plan plus resource gates before new execution. No scientific effect or baseline acceptance."
d.setdefault("registered_goal_history",[]).append(copy.deepcopy(d["next_registered_goal"]))
d["next_registered_goal"]={"kind":"MAIN_BOUNDED_G2_DESIGN_BEFORE_NEW_EXECUTION_PLAN","status":"MAIN_DESIGN_NEXT_BOUNDED_G2_TARGET_NO_EXECUTION_PLAN_YET","owner":d["main"]["thread_id"],"source":H,"main_status_snapshot":next(x["snapshot"] for p,x in json.loads((OUT/"source-manifest.json").read_text(encoding="utf-8")).items() if p.endswith("/main/current-status.json")),"next":"Map remaining lifecycle/OS2/framing/shared-protocol requirements and freeze the next bounded design plus sole independent plan.","new_execution_plan_fixed":False,"restart_R1_R2_authorized":False,"new_sole_independent_dispatch_by_Integration":False,"unfinished_correctness_V0_ablations_dual_effects_costs_retained":True}
d["main"]["last_cursor"]=POLL["cursor"];d["main"]["last_observed_status"]="idle after native recovery r2 accepted; next bounded G2 design"
d["independent"]["last_reported_cursor"]="3dadc2c4-3e49-4c0c-9ee1-13940917f98a:136"
d["independent"]["last_reported_state"]="Main-reported completed/idle native-entry R2; no new dispatch or direct Integration poll"
d.setdefault("foreground_background_coordination_history",[]).append(copy.deepcopy(d["foreground_background_coordination"]))
d["foreground_background_coordination"]={"main_observed":"idle "+POLL["cursor"],"independent_known_last_reported":"completed/idle 3dadc2c4-3e49-4c0c-9ee1-13940917f98a:136","rule":"Original main owns next bounded design and any single-target dispatch; active deputy not duplicated, terminal R1/R2 never restarted by timer.","root_restarted_jobs":False,"next_execution_plan_fixed":False,"old_driver_restart_authorized":False}
d.setdefault("implemented_source_history",[]).append(copy.deepcopy(d["latest_implemented_source"]))
d["latest_implemented_source"]={"sha":V["fixed_source"],"parent_sha":V["source_parent"],"branch":"experiment/ws31-native-entry-r2","purpose":"One-line declarations Waf header export; native entry bounded object validation","validation":"R2 one full -j2 build and20 nonnetwork object cases accepted by main and independently locally checked by Integration; no transport completion or scientific efficacy acceptance.","fixed_source_not_claim_of_mutable_checkout_HEAD":True,"original_WIP_preservation":"Main/deputy complete published4870/original4868 byte audits bound in snapshots; original WIP preserved.","last_network_validated_source":old["latest_implemented_source"]["last_network_validated_source"],"network_validation_scopes":old["latest_implemented_source"]["network_validation_scopes"],"new_network_approval_scope":"None supplied by this Integration handoff; distinct bounded design/frozen plan/resource gates required"}
d.setdefault("material_event_history",[]).append(copy.deepcopy(d["last_material_event"]))
d["last_material_event"]={"date":"2026-11-08","kind":"NATIVE_SUPERVISION_RESTORED_AND_R2_BOUNDED_ENTRY_ACCEPTED","record":H,"verification":E+"/verification.json","completed_event_time_utc":V["completed_event_time_utc"],"main_acceptance_observed_at_utc":V["main_acceptance_observed_at_utc"],"integration_observed_at_utc":V["integration_observed_at_utc"],"new_engineering_runtime_acceptance":True,"new_network_acceptance":False,"new_baseline_established":False,"user_decision_required":False}
d["last_verified_native_entry_recovery_checkpoint"]={"source":V["fixed_source"],"run_id":"20261108-152638-ws31-native-entry-r2","actual_fullbuilds":1,"actual_nonnetwork_object_cases":20,"independently_checked_packet_rows":4482,"verification":E+"/verification.json","main_acceptance":"docs/research/ws31/main/evidence/native-supervision-r2/r2-terminal-main-acceptance.json","source_archive_Git_and_terminal_paths":4870,"complete_G2":False,"new_baseline":False,"intermediate_native_lexical_policy_stages_full_Integration_reacceptance":False}
assert d["validated_combined_baseline_established"]==old["validated_combined_baseline_established"]==False
assert d["deferred_ws29"]==old["deferred_ws29"]
coord_path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
with (OUT/"authority-transition.json").open("x",encoding="utf-8") as f:json.dump({"observed_at_utc":datetime.now(timezone.utc).isoformat(),"before_sha256":before,"after_sha256":{p:sha(ROOT/p) for p in FILES},"new_state":STATUS,"old_HOLD_and_deleted_heartbeat_preserved_in_history":True,"new_authorization_source":E+"/user-instruction.json","only_five_authority_files_changed":True},f,ensure_ascii=False,indent=2);f.write("\n")
(OUT/".gitattributes").write_text("* -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\nsnapshots/** -whitespace\n",encoding="utf-8")
print(json.dumps({"status":STATUS,"main_cursor":POLL["cursor"],"authority_files":len(FILES)},ensure_ascii=False))
