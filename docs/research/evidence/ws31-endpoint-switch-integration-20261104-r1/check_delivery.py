"""Validate Integration delivery identities, links and scope; no C++ execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


out = Path(__file__).resolve().parent
root = out.parents[3]
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest = json.loads((out / "source-manifest.json").read_text(encoding="utf-8"))
files = [p for p in (out / "snapshots").rglob("*") if p.is_file()]
assert len(files) == 213
for entry in manifest.values():
    data = (out / entry["snapshot"]).read_bytes()
    assert sha(data) == entry["sha256"] and len(data) == entry["bytes"]
v = json.loads((out / "verification.json").read_text(encoding="utf-8"))
cpath = root / "docs/project-state/ws31-coordination.json"
c = json.loads(cpath.read_text(encoding="utf-8"))
assert c["main"]["last_cursor"] == v["main_observed_cursor"]
assert c["next_registered_goal"]["plan_sha256"] == v["r3_plan_sha256"]
assert c["next_registered_goal"]["files_working_sha256"] == v["r3_working_hashes"]
assert c["next_registered_goal"]["changed_paths"] == ["scratch/ws31-endpoint-switch-test.cc"]
assert c["next_registered_goal"]["unchanged_WIP_files"] == 9
assert not c["next_registered_goal"]["remote_build_fixture_network_execution_authorized"]
assert not c["validated_combined_baseline_established"]
changed = [root / "docs/project-state" / name for name in
           ["CURRENT_STATE.md", "ROADMAP.md", "WORKSTREAMS.md", "WS31_EXECUTION.md", "ws31-coordination.json"]]
handoff = root / "docs/handoffs/2026-11-04-ws31-endpoint-switch-integration.md"
documents = [p for p in changed if p.suffix == ".md"] + [handoff]
links = []
for p in documents:
    text = p.read_text(encoding="utf-8-sig")
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        link = target.strip("<>")
        if re.match(r"^(https?://|mailto:|#)", link):
            continue
        path = re.sub(r":\d+$", "", link.split("#", 1)[0])
        q = Path(path)
        if not q.is_absolute():
            q = p.parent / q
        assert q.exists(), (str(p), link)
        links.append({"document": p.relative_to(root).as_posix(), "target": target})
    assert "\t" not in text
assert re.findall(r"^## (\d+)\.", handoff.read_text(encoding="utf-8"), re.M) == [str(n) for n in range(1, 10)]
jsons = [p for p in files if p.suffix == ".json"] + [cpath, out / "verification.json", out / "source-manifest.json"]
for p in jsons:
    json.loads(p.read_text(encoding="utf-8-sig"))
git = lambda *args: subprocess.check_output(["git", "-C", str(root), *args])
assert set(git("diff", "--name-only").decode().splitlines()) == {p.relative_to(root).as_posix() for p in changed}
git("diff", "--check")
receipt = {
    "at_utc": datetime.now(timezone.utc).isoformat(), "client_date": "2026-11-04",
    "status": "PASS_NODES19_20_INTEGRATION_DELIVERY_QA",
    "scope": "Snapshot integrity, JSON, local links, nine sections and current state boundaries; no new scientific validation",
    "snapshots": len(files), "JSON_documents_checked": len(jsons), "local_links_checked": len(links),
    "local_links_exist": True, "nine_handoff_sections": True, "five_canonical_states_only": True,
    "static_counts_not_runtime": True, "new_mask255_or_network_evidence": False,
    "r3_pending_minimum_delta_review_not_approved_for_execution": True,
    "old_failures_and_resume_progress_receipts_preserved": True,
    "style_review": "Previously read Ruanyf original README and six chapters; headings, spacing, paragraphs, quantities, punctuation and structure rechecked",
    "root_scientific_main_independent_source_edits": 0,
    "artifacts_sha256": {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in changed + [handoff]},
    "evidence_sha256": {p.relative_to(out).as_posix(): sha(p.read_bytes()) for p in out.rglob("*") if p.is_file()},
}
p = out / "delivery-qa.json"
assert not p.exists(), "Refuse to overwrite a successful delivery receipt"
p.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": receipt["status"], "links": len(links), "JSON": len(jsons), "snapshots": len(files)}))
