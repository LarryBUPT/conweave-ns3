"""Verify a same-SHA WS-21 identity/port-event diagnostic pair."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from verify_ws21_identity import verify as verify_identity
from verify_ws21_port_events import verify as verify_port_events


TRACE_SHA = "4e7d0e6a68e3230e8960a174e570a0a788c191fa0b44922408867b02c25782cc"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SOURCE_SHA = "f94a4ab20b905878d2b739bae346b52492ac5f94"
EXPECTED_FLOWS = 40
EXPECTED_BYTES = 33849344


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_cell(root, experiment_id):
    base = root / experiment_id
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    if meta["status"] != "SUCCEEDED" or meta["git_commit"] != SOURCE_SHA:
        raise ValueError(f"{experiment_id}: status or source SHA mismatch")
    if (meta["parameters"]["lb"] != "ws18" or meta["parameters"]["pfc"] != 0 or
            meta["parameters"]["irn"] != 1 or meta["parameters"]["ws18_admission"] != 0 or
            meta["parameters"]["ws18_path"] != 0 or meta["seed"] != 1):
        raise ValueError(f"{experiment_id}: experiment parameters mismatch")
    raw_id = str(meta["raw_directory"])
    raw = base / "raw" / raw_id
    return base, meta, raw, raw_id


def verify_pair(root, off_id, on_id):
    off_base, off, off_raw, off_raw_id = load_cell(root, off_id)
    on_base, on, on_raw, on_raw_id = load_cell(root, on_id)
    for side, meta, base, flags in (
            ("off", off, off_base, (0, 0)), ("on", on, on_base, (1, 1))):
        params = meta["parameters"]
        if (int(params.get("ws21_identity", 0)), int(params.get("ws21_port_events", 0))) != flags:
            raise ValueError(f"{side}: diagnostic flags mismatch")
        if digest(base / "config" / "traffic_trace.txt") != TRACE_SHA:
            raise ValueError(f"{side}: trace SHA mismatch")
        if digest(base / "config" / "topology.txt") != TOPOLOGY_SHA:
            raise ValueError(f"{side}: topology SHA mismatch")
    if off["git_commit"] != on["git_commit"]:
        raise ValueError("paired cells use different source commits")
    off_fct = off_raw / f"{off_raw_id}_out_fct.txt"
    on_fct = on_raw / f"{on_raw_id}_out_fct.txt"
    off_ws18 = off_raw / f"{off_raw_id}_out_ws18.txt"
    on_ws18 = on_raw / f"{on_raw_id}_out_ws18.txt"
    fct_hashes = [digest(path) for path in (off_fct, on_fct)]
    ws18_hashes = [digest(path) for path in (off_ws18, on_ws18)]
    if fct_hashes[0] != fct_hashes[1] or ws18_hashes[0] != ws18_hashes[1]:
        raise ValueError("diagnostic changed FCT or WS18 timing raw")
    rows = on_ws18.read_text(encoding="utf-8").splitlines()
    bytes_total = sum(int(line.split()[6]) for line in rows)
    if len(rows) != EXPECTED_FLOWS or bytes_total != EXPECTED_BYTES:
        raise ValueError(f"completion/byte mismatch: {len(rows)} flows, {bytes_total} bytes")
    identity = verify_identity(
        on_ws18, on_raw / f"{on_raw_id}_out_ws21_identity.txt",
        on_base / "config" / "topology.txt")
    ports = verify_port_events(on_raw / f"{on_raw_id}_out_ws21_port.txt", on_ws18)
    if not identity["complete"] or not ports["complete"]:
        raise ValueError("identity or port-event validation failed")
    log = (on_raw / "config.log").read_text(encoding="utf-8", errors="replace")
    overflow = re.search(r"WS21_PORT_EVENTS events=(\d+) bytes=(\d+) overflow=(\d+)", log)
    if not overflow or int(overflow.group(3)) != 0:
        raise ValueError("missing or nonzero WS-21 port-event overflow receipt")
    return {"complete": True, "source_sha": SOURCE_SHA,
            "off_id": off_id, "on_id": on_id, "flow_count": len(rows),
            "bytes": bytes_total, "fct_sha256": fct_hashes[0],
            "ws18_sha256": ws18_hashes[0], "identity": identity,
            "port_events": ports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--off", required=True)
    parser.add_argument("--on", required=True)
    args = parser.parse_args()
    result = verify_pair(args.results, args.off, args.on)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
