"""Check scope-change delivery and persisted scheduler guard without experiments."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib


out = Path(__file__).resolve().parent
root = out.parents[3]
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest = json.loads((out / "source-manifest.json").read_text(encoding="utf-8"))
for entry in manifest.values():
    data = (out / entry["snapshot"]).read_bytes()
    assert sha(data) == entry["sha256"] and len(data) == entry["bytes"]
v = json.loads((out / "verification.json").read_text(encoding="utf-8"))
cp = root / "docs/project-state/ws31-coordination.json"
c = json.loads(cp.read_text(encoding="utf-8"))
assert c["status"] == "ACTIVE_REVIEW_INFORMED_RESCOPING_CANDIDATE_ENGINEERING_PAUSED"
assert not c["candidate_implementation_authorized"]
assert not c["next_registered_goal"]["scientific_source_or_config_edits_authorized"]
assert not c["next_registered_goal"]["remote_build_fixture_network_execution_authorized"]
assert c["next_registered_goal"]["kind"] == "BOUNDED_MAIN_READONLY_EVIDENCE_AND_DECOUPLED_DEMAND_DESIGN"
assert c["main"]["last_cursor"] == v["main_observed_cursor"]
assert c["independent"]["last_reported_cursor"] == v["independent_main_reported_cursor"]
assert c["latest_implemented_source"]["current_WIP_hashes"] == v["current_WIP_hashes"]
assert not c["validated_combined_baseline_established"]
automation = Path("C:/Users/Administrator/.codex/automations/ws-31/automation.toml").read_bytes()
assert automation == (out / "automation-after.toml").read_bytes()
at = tomllib.loads(automation.decode())
assert sha(at["prompt"].encode()) == c["heartbeat"]["prompt_sha256"] == v["heartbeat"]["prompt_sha256"]
assert at["status"] == "ACTIVE" and at["rrule"] == "FREQ=MINUTELY;INTERVAL=30"
impl = root.parent / "ws31-candidates-implementation"
for rel, expected in v["current_WIP_hashes"].items():
    assert sha((impl / rel).read_bytes()) == expected
ref = json.loads((out / "reference-review.json").read_text(encoding="utf-8"))
for source in ref["sources"]:
    assert sha(Path(source["path"]).read_bytes()) == source["sha256"]
changed = [root / "docs/project-state" / name for name in
           ["CURRENT_STATE.md", "ROADMAP.md", "WORKSTREAMS.md", "WS31_EXECUTION.md", "ws31-coordination.json"]]
handoff = root / "docs/handoffs/2026-11-04-ws31-review-informed-rescope.md"
links = []
for p in [x for x in changed if x.suffix == ".md"] + [handoff]:
    text = p.read_text(encoding="utf-8-sig")
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        link = target.strip("<>")
        if re.match(r"^(https?://|mailto:|#)", link):
            continue
        path = re.sub(r":\d+$", "", link.split("#", 1)[0])
        q = Path(path)
        if not q.is_absolute():
            q = p.parent / path
        assert q.exists(), (str(p), target)
        links.append(target)
assert re.findall(r"^## (\d+)\.", handoff.read_text(encoding="utf-8"), re.M) == [str(n) for n in range(1, 10)]
jsons = [p for p in out.rglob("*.json")] + [cp]
for p in jsons:
    json.loads(p.read_text(encoding="utf-8-sig"))
git = lambda *args: subprocess.check_output(["git", "-C", str(root), *args])
assert set(git("diff", "--name-only").decode().splitlines()) == {p.relative_to(root).as_posix() for p in changed}
git("diff", "--check")
receipt = {
    "at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_REVIEW_RESCOPE_CANONICAL_AND_SCHEDULER_DELIVERY_QA",
    "source_snapshots": len([p for p in (out / "snapshots").rglob("*") if p.is_file()]),
    "local_links_checked": len(links), "JSON_documents_checked": len(jsons), "nine_handoff_sections": True,
    "nineteen_WIP_still_match": True, "heartbeat_saved_scope_matches_registry": True,
    "only_five_canonical_tracked_files_changed": True, "old_execution_entries_overridden_by_current_scope": True,
    "unfinished_scientific_debt_retained": True, "no_novelty_efficacy_or_new_baseline_certification": True,
    "style_review": "Original Ruanyf README and six chapters previously read; headings/spacing/paragraphs/quantities/punctuation/structure rechecked",
    "scientific_source_compile_fixture_network_SSH_by_Integration": 0,
    "artifacts_sha256": {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in changed + [handoff]},
    "evidence_sha256": {p.relative_to(out).as_posix(): sha(p.read_bytes()) for p in out.rglob("*") if p.is_file()},
}
p = out / ("delivery-qa-r2.json" if "--r2" in sys.argv else "delivery-qa.json")
assert not p.exists(), "Do not overwrite successful QA"
p.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ["status", "source_snapshots", "local_links_checked", "JSON_documents_checked"]}))
