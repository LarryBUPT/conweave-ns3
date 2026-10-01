#!/usr/bin/env python3
"""Audit the WS-23 arrival-order correction against the original Git inputs."""

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OLD_SHA = "b3d8d30826dd4550f5667d4cab2a3b4004c3cf22"
MANIFEST = "docs/research/evidence/ws23-isolation-demand-manifest.json"


def old_bytes(path):
    return subprocess.check_output(["git", "show", OLD_SHA + ":" + path], cwd=str(ROOT))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def records(data, path):
    lines = data.decode("ascii").splitlines()
    count = int(lines[0])
    assert count == len(lines) - 1, path
    parsed = [line.split() for line in lines[1:]]
    assert all(len(row) == 6 for row in parsed), path
    assert len(set(lines[1:])) == count, path
    arrivals = [Decimal(row[4]) for row in parsed]
    assert len(set(arrivals)) == count, path + " duplicate arrival"
    return lines[1:], arrivals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    before = json.loads(old_bytes(MANIFEST))
    after = json.loads((ROOT / MANIFEST).read_bytes())
    assert {k: v for k, v in before.items() if k != "entries"} == {
        k: v for k, v in after.items() if k != "entries"}
    assert len(before["entries"]) == len(after["entries"]) == 6
    results = []
    for prior, current in zip(before["entries"], after["entries"]):
        assert {k: v for k, v in prior.items() if k != "sha256"} == {
            k: v for k, v in current.items() if k != "sha256"}
        path = current["path"]
        original = old_bytes(path)
        revised = (ROOT / path).read_bytes()
        old_rows, old_arrivals = records(original, path)
        new_rows, new_arrivals = records(revised, path)
        assert digest(original) == prior["sha256"], path
        assert digest(revised) == current["sha256"], path
        assert Counter(old_rows) == Counter(new_rows), path + " changed flow content"
        assert new_arrivals == sorted(new_arrivals), path + " unsorted arrivals"
        assert (original == revised) == (current["scenario"] == "bg"), path
        assert current["scenario"] == "bg" or old_arrivals != sorted(old_arrivals), path
        results.append({"seed": current["seed"], "scenario": current["scenario"],
                        "path": path, "old_sha256": digest(original),
                        "new_sha256": digest(revised), "flow_count": len(new_rows),
                        "flow_multiset_equal": True, "arrival_non_decreasing": True,
                        "arrival_values_unique": True})
    report = {"original_git_commit": OLD_SHA, "original_manifest_sha256": digest(old_bytes(MANIFEST)),
              "revised_manifest_sha256": digest((ROOT / MANIFEST).read_bytes()),
              "background_byte_identical": True, "mixed_only_reordered": True,
              "entries": results}
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
