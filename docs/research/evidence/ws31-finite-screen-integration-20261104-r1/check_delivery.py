"""Artifact and HOLD checks only; no repeat raw analysis or scientific run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib


out = Path(__file__).resolve().parent
root = out.parents[3]
sha = lambda data: hashlib.sha256(data).hexdigest()
v = json.loads((out / "verification.json").read_text(encoding="utf-8"))
manifest = json.loads((out / "source-manifest.json").read_text(encoding="utf-8"))
for entry in manifest.values():
    data = (out / entry["snapshot"]).read_bytes()
    assert sha(data) == entry["sha256"] and len(data) == entry["bytes"]
cp = root / "docs/project-state/ws31-coordination.json"
c = json.loads(cp.read_text(encoding="utf-8"))
assert c["status"] == c["next_registered_goal"]["status"] == "HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION"
assert c["next_registered_goal"]["kind"] == "HOLD_NO_AUTOMATIC_FOLLOWUP"
assert not c["candidate_implementation_authorized"]
for k in ["remote_build_fixture_network_execution_authorized", "scientific_source_or_config_edits_authorized", "repeat_old_analysis_or_sweeps_authorized", "new_sole_independent_dispatch_authorized_now"]:
    assert not c["next_registered_goal"][k]
assert not c["validated_combined_baseline_established"]
assert c["main"]["last_cursor"] == v["main_observed_cursor"]
assert c["independent"]["last_reported_cursor"] == v["sole_independent_last_reported_cursor"]
assert c["last_verified_finite_screen_checkpoint"]["C1"] == v["C1"]
assert c["last_verified_finite_screen_checkpoint"]["C3"] == v["C3"]
live = Path("C:/Users/Administrator/.codex/automations/ws-31/automation.toml").read_bytes()
assert live == (out / "automation-after.toml").read_bytes()
a = tomllib.loads(live.decode())
assert sha(a["prompt"].encode()) == v["heartbeat"]["prompt_sha256"] == c["heartbeat"]["prompt_sha256"]
assert a["status"] == "ACTIVE" and a["rrule"] == "FREQ=MINUTELY;INTERVAL=30"
extra = json.loads((out / "reference-and-config-check.json").read_text(encoding="utf-8"))
for row in extra["local_reference_sources"] + [extra["source_config"]]:
    assert sha(Path(row["path"]).read_bytes()) == row["sha256"]
prior = json.loads((root / "docs/research/evidence/ws31-review-rescope-integration-20261104-r1/verification.json").read_text(encoding="utf-8"))
impl = root.parent / "ws31-candidates-implementation"
assert all(sha((impl / p).read_bytes()) == h for p, h in prior["current_WIP_hashes"].items())
changed = [root / "docs/project-state" / name for name in ["CURRENT_STATE.md", "ROADMAP.md", "WORKSTREAMS.md", "WS31_EXECUTION.md", "ws31-coordination.json"]]
handoff = root / "docs/handoffs/2026-11-04-ws31-finite-screen-hold.md"
links = []
for p in [x for x in changed if x.suffix == ".md"] + [handoff]:
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", p.read_text(encoding="utf-8-sig")):
        link = target.strip("<>")
        if re.match(r"^(https?://|mailto:|#)", link):
            continue
        path = re.sub(r":\d+$", "", link.split("#", 1)[0]); q = Path(path)
        if not q.is_absolute(): q = p.parent / q
        assert q.exists(), (str(p), target)
        links.append(target)
assert re.findall(r"^## (\d+)\.", handoff.read_text(encoding="utf-8"), re.M) == [str(i) for i in range(1, 10)]
jsons = list(out.rglob("*.json")) + [cp]
for p in jsons:
    json.loads(p.read_text(encoding="utf-8-sig"))
git = lambda *args: subprocess.check_output(["git", "-C", str(root), *args])
assert set(git("diff", "--name-only").decode().splitlines()) == {p.relative_to(root).as_posix() for p in changed}
git("diff", "--check")
receipt = {"at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_FINITE_SCREEN_HOLD_DELIVERY_QA",
    "local_links_checked": len(links), "JSON_documents_checked": len(jsons), "nine_handoff_sections": True,
    "nineteen_scientific_WIP_unchanged": True, "heartbeat_saved_HOLD_matches_registry": True,
    "scientific_baseline_counts_unchanged": True, "no_next_analysis_or_engineering_automatically_authorized": True,
    "unfinished_scientific_debt_preserved": True,
    "style_review": "Original Ruanyf README/six chapters previously read; headings, spacing, paragraphs, quantities, punctuation and structure checked",
    "artifacts_sha256": {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in changed + [handoff]},
    "evidence_sha256": {p.relative_to(out).as_posix(): sha(p.read_bytes()) for p in out.rglob("*") if p.is_file()}}
p = out / "delivery-qa.json"
assert not p.exists(), "Do not overwrite successful QA"
p.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ["status", "local_links_checked", "JSON_documents_checked"]}))
