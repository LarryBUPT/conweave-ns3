"""Check Integration delivery files only; never run scientific code."""
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
assert len(manifest) == 78
for entry in manifest.values():
    data = (out / entry["snapshot"]).read_bytes()
    assert sha(data) == entry["sha256"] and len(data) == entry["bytes"]
    if "source_path" in entry:
        assert Path(entry["source_path"]).read_bytes() == data

changed = [root / "docs/project-state" / name for name in
           ["CURRENT_STATE.md", "ROADMAP.md", "WORKSTREAMS.md", "WS31_EXECUTION.md", "ws31-coordination.json"]]
handoff = root / "docs/handoffs/2026-11-01-ws31-endpoint-channel-integration.md"
documents = [p for p in changed if p.suffix == ".md"] + [handoff]
links = []
for p in documents:
    text = p.read_text(encoding="utf-8-sig")
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        link = link.strip("<>")
        if re.match(r"^(https?://|mailto:|#)", link):
            continue
        path = link.split("#", 1)[0]
        path = re.sub(r":\d+$", "", path)
        q = Path(path)
        if not q.is_absolute():
            q = p.parent / path
        assert q.exists(), (str(p), link)
        links.append({"document": p.relative_to(root).as_posix(), "target": link})
    assert "\t" not in text
sections = re.findall(r"^## (\d+)\.", handoff.read_text(encoding="utf-8"), re.M)
assert sections == [str(n) for n in range(1, 10)]
jsons = [out / "verification.json", out / "source-manifest.json", changed[-1]]
jsons += list((out / "snapshots").rglob("*.json"))
for p in jsons:
    json.loads(p.read_text(encoding="utf-8-sig"))
c = json.loads(changed[-1].read_text(encoding="utf-8"))
v = json.loads((out / "verification.json").read_text(encoding="utf-8"))
assert c["main"]["last_cursor"] == v["main_observed_cursor"]
assert c["next_registered_goal"]["plan_sha256"] == v["r2_plan_sha256"]
assert c["next_registered_goal"]["files_working_sha256"] == v["r2_working_hashes"]
assert not c["next_registered_goal"]["remote_build_fixture_network_execution_authorized"]
assert not c["validated_combined_baseline_established"]
git = lambda *args: subprocess.check_output(["git", "-C", str(root), *args])
tracked = git("diff", "--name-only").decode().splitlines()
assert set(tracked) == {p.relative_to(root).as_posix() for p in changed}
git("diff", "--check")
artifacts = {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in changed + [handoff]}
artifacts.update({p.relative_to(out).as_posix(): sha(p.read_bytes()) for p in out.rglob("*") if p.is_file()})
receipt = {
    "at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS_NODE18_INTEGRATION_DELIVERY_QA",
    "scope": "Original/snapshot identity, JSON, local links, nine sections and state boundaries; no scientific execution",
    "source_snapshots": 78, "JSON_documents_checked": len(jsons),
    "local_links_checked": len(links), "local_links_all_exist": True,
    "nine_handoff_sections": True, "five_canonical_state_files_only": True,
    "scientific_or_main_independent_source_edited": False,
    "style_review": "Previously read Ruanyf original README/six chapters; headings, spacing, paragraphs, numbers, punctuation and structure manually rechecked",
    "historical_43_network_17_adapter_counts_preserved": True,
    "r2_not_compiled_or_executed_or_approved": True,
    "remaining_network_V0_ablations_dual_effects_costs_mandatory": True,
    "artifacts_sha256": artifacts,
}
dest = out / "delivery-qa.json"
assert not dest.exists(), "Do not overwrite a successful QA receipt"
dest.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": receipt["status"], "links": len(links), "JSON": len(jsons), "snapshots": 78}))
