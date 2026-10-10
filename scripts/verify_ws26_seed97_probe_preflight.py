#!/usr/bin/env python3
"""Check that the seed 97 probe selects exactly the preregistered QPs."""

import hashlib
import re
from pathlib import Path

from verify_ws26_moe_hop_diagnostic import topology_maps, trace_qps


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/research/ws26-seed97-time-aligned-diagnostic-design.md"
HEADER = ROOT / "src/point-to-point/model/ws26-seed97-probe.h"
TRACE = ROOT / "config/ws26_seed20262697_b192.txt"
TOPOLOGY = ROOT / "config/topo_1280_400G_400G_OS1.txt"
SMOKE = ROOT / "config/ws26_seed97_probe_smoke.txt"
TRACE_SHA256 = "58bbc2d8ca78753c5e6e2fee119341ea94c8ee76cbad58e013c93707833ee3ca"
TOPOLOGY_SHA256 = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SMOKE_SHA256 = "e6e55714818d84971d831ad9dc39e37e0a4cea7eb5ce5636eeb28dc94bd439bd"
QUAD = re.compile(r"(\d+)→(\d+):(\d+)/(\d+)")
HEADER_QUAD = re.compile(r"\{(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\}")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if digest(TRACE) != TRACE_SHA256 or digest(TOPOLOGY) != TOPOLOGY_SHA256:
        raise RuntimeError("Seed 97 trace or topology changed")
    expected = trace_qps(TRACE)
    _, _, host_tors, _ = topology_maps(TOPOLOGY)
    rows = []
    for line in DESIGN.read_text(encoding="utf-8").splitlines():
        if not (line.startswith("| 背景 |") or line.startswith("| MoE |")):
            continue
        identities = [tuple(map(int, match)) for match in QUAD.findall(line)]
        if len(identities) != 2:
            raise RuntimeError("Each design row needs one target and one control")
        rows.append((1 if line.startswith("| 背景 |") else 2, *identities))
    if len(rows) != 12 or sum(row[0] == 1 for row in rows) != 6:
        raise RuntimeError("Expected six background and six MoE comparisons")

    targets = [row[1] for row in rows]
    controls = [row[2] for row in rows]
    if len(set(targets)) != 12 or len(set(controls)) != 11 or set(targets) & set(controls):
        raise RuntimeError("Target/control identities or reuse differ from design")
    selected = set(targets + controls)
    header = [tuple(map(int, match)) for match in HEADER_QUAD.findall(
        HEADER.read_text(encoding="utf-8"))]
    if len(header) != 23 or set(header) != selected:
        raise RuntimeError("Compiled selection differs from the frozen design table")

    for tag, target, control in rows:
        for key in (target, control):
            data = expected.get(key)
            if data is None or data["tag"] != tag or data["start_ns"] != 2000000000:
                raise RuntimeError("Target/control absent from trace or has wrong class/time: %r" % (key,))
            if data["size"] != (8388608 if tag == 1 else 8192):
                raise RuntimeError("Target/control size differs from the design: %r" % (key,))
        if host_tors[target[1]] != host_tors[control[1]]:
            raise RuntimeError("Control does not share destination ToR: %r" % (target,))
    if digest(SMOKE) != SMOKE_SHA256:
        raise RuntimeError("Fixed smoke trace changed")
    smoke = trace_qps(SMOKE)
    if (len(smoke) != 61 or set(smoke) & selected !=
            {(896, 628, 10000, 100), (0, 1144, 10059, 100)}):
        raise RuntimeError("Smoke must hit exactly one selected QP from each class")
    print("seed97_preflight=PASS targets=12 unique_controls=11 selected=23 trace_sha256=" +
          TRACE_SHA256)


if __name__ == "__main__":
    main()
