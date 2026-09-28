"""Check the mode-20 diagnostic's per-QP source/destination path identity.

Both inputs must be raw files from the same experiment ID. This does not
validate feedback delivery or mechanism performance.
"""

import argparse
import json
from pathlib import Path


def read_host_tors(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    node_count, switch_count, link_count = map(int, lines[0].split())
    switches = set(map(int, lines[1].split()))
    if len(switches) != switch_count or len(lines) - 2 != link_count:
        raise ValueError("topology header/count mismatch")
    host_tors = {}
    for line in lines[2:]:
        a, b = map(int, line.split()[:2])
        if a not in switches and b in switches:
            if a in host_tors and host_tors[a] != b:
                raise ValueError("host has multiple ToRs")
            host_tors[a] = b
        elif b not in switches and a in switches:
            if b in host_tors and host_tors[b] != a:
                raise ValueError("host has multiple ToRs")
            host_tors[b] = a
    if len(host_tors) != node_count - switch_count:
        raise ValueError("host-to-ToR map is incomplete")
    return host_tors


def read_ws18(path):
    flows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        values = [int(value) for value in line.split()]
        if len(values) != 12:
            raise ValueError("WS18 row must have 12 columns")
        flow_id, src, dst, sport, dport, tag, size, demand, release, finish, wait, total = values
        key = (src, dst, sport, dport)
        if key in flows or release - demand != wait or finish - demand != total:
            raise ValueError("duplicate QP or invalid WS18 timing")
        flows[key] = {"id": flow_id, "tag": tag, "size": size,
                      "demand": demand, "release": release, "finish": finish}
    ids = sorted(flow["id"] for flow in flows.values())
    if ids != list(range(len(ids))):
        raise ValueError("WS18 input IDs are not contiguous")
    return flows


def read_identity(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    expected = ("side tor src dst sport dport first_port packets upstream_ce "
                "first_ns last_ns inconsistent unmapped")
    if not lines or lines[0] != expected:
        raise ValueError("identity header mismatch")
    observations = {"source": {}, "destination": {}}
    for line in lines[1:]:
        fields = line.split()
        if len(fields) != 13 or fields[0] not in observations:
            raise ValueError("identity row must have 13 columns and a valid side")
        values = [int(value) for value in fields[1:]]
        tor, src, dst, sport, dport, port, packets, ce, first, last, bad, missing = values
        key = (src, dst, sport, dport)
        group = observations[fields[0]]
        if key in group:
            raise ValueError("duplicate identity QP/side")
        group[key] = {"tor": tor, "port": port, "packets": packets,
                      "ce": ce, "first": first, "last": last,
                      "inconsistent": bad, "unmapped": missing}
    return observations


def verify(ws18_path, identity_path, topology_path):
    flows = read_ws18(ws18_path)
    host_tors = read_host_tors(topology_path)
    cross_flows = {key: flow for key, flow in flows.items()
                   if host_tors[key[0]] != host_tors[key[1]]}
    observations = read_identity(identity_path)
    errors = []
    for side, rows in observations.items():
        if set(rows) != set(cross_flows):
            errors.append(f"{side}: expected {len(cross_flows)} QPs, got {len(rows)}; "
                          f"missing={len(set(cross_flows) - set(rows))}, "
                          f"extra={len(set(rows) - set(cross_flows))}")
    ce_total = 0
    for key, flow in cross_flows.items():
        source = observations["source"].get(key)
        destination = observations["destination"].get(key)
        if source is None or destination is None:
            continue
        for side, row in (("source", source), ("destination", destination)):
            if (row["port"] <= 0 or row["packets"] <= 0 or
                    row["ce"] > row["packets"] or
                    row["first"] < flow["release"] or
                    row["last"] < row["first"] or row["last"] > flow["finish"] or
                    row["inconsistent"] or row["unmapped"]):
                errors.append(f"QP {flow['id']}: invalid {side} observation")
        if (source["tor"] != host_tors[key[0]] or
                destination["tor"] != host_tors[key[1]] or
                source["port"] != destination["port"]):
            errors.append(f"QP {flow['id']}: source/destination path mismatch")
        if source["first"] > destination["first"]:
            errors.append(f"QP {flow['id']}: destination preceded source")
        ce_total += destination["ce"]
    return {"complete": not errors, "qp_count": len(flows),
            "cross_tor_qps": len(cross_flows),
            "source_qps": len(observations["source"]),
            "destination_qps": len(observations["destination"]),
            "upstream_ce_packets": ce_total, "errors": errors[:20]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ws18", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--topology", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.ws18, args.identity, args.topology)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["complete"] else 1)


if __name__ == "__main__":
    main()
