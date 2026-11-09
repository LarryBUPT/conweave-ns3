"""Freeze the registered C2 v4 pilot inputs and ex ante C2 wait-cost gate."""

import argparse
import hashlib
import json
from pathlib import Path

import ws31_demand_construct as frozen


PROTOCOL_V4_SHA = "baf319eefea9d6eebe983bc8a8d00c6c8427f29e4570877a27c29fe1185a95dd"
CONSTRUCTOR_SHA = "261cee65f90dd72119694f00d93778e705ec59fa84b302984cc64000b1ebdc8d"
START_HEADER_SHA = "953cf53b0c726b5ef68ca6d5b8ea311b7682f8b8b03f54a7c6b0ff36af1574de"
SEEDS = tuple(range(5310151, 5310159))
MAGIC = "WS31_V2_DECL_R1"
FIELDS = ("request_id", "generation", "src", "dst", "src_ip", "dst_ip", "pg", "bytes",
          "demand_ns", "original_tag", "policy_present", "policy_tag", "sport", "dport", "flow_id")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def node_ip(node):
    need(0 <= node < 128, "host outside OS2")
    return 0x0B000001 + (node // 256) * 0x10000 + (node % 256) * 0x100


def route_hash(sip, dip, sport, dport, domain):
    words = (sip, dip, sport | (dport << 16))
    value = (2166136261 ^ domain) & 0xFFFFFFFF
    for word in words:
        for shift in (0, 8, 16, 24):
            value = ((value ^ ((word >> shift) & 255)) * 16777619) & 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x85EBCA6B) & 0xFFFFFFFF
    value ^= value >> 13
    return value


def cost(online, family, mode):
    eligible = waited = delay_sum = delay_max = 0
    for row in online:
        size = row["payload_bytes"]
        tag = row["policy_tag"]
        sip, dip = node_ip(row["src"]), node_ip(row["dst"])
        sport, dport = row["sport"], row["dport"]
        if mode == 43:
            yes = tag == 2
        elif mode == 55:
            yes = route_hash(sip, dip, sport, dport, 0x53C2A517) % 35 < 3
        elif mode == 56:
            target, cutoff = (16384, 3) if family == "D1" else (262144, 6)
            yes = size == target and route_hash(sip, dip, sport, dport, 0x53C2A517) % 35 < cutoff
        else:
            raise ValueError("unregistered C2 cost mode")
        if yes:
            eligible += 1
            delay = route_hash(sip, dip, sport, dport, 0x43C2A517) % 501
            delay_sum += delay
            waited += delay != 0
            delay_max = max(delay_max, delay)
    return dict(eligible=eligible, planned_waited=waited,
                planned_delay_sum_ns=delay_sum, planned_delay_max_ns=delay_max)


def bundle(family, seed):
    need(family in ("D1", "D2") and seed in SEEDS, "unregistered pilot demand")
    online, evaluation, metadata = frozen.construct(family, seed)
    need(len(online) == len(evaluation) == 1120 and metadata["request_count"] == 1120,
         "pilot construction count")
    online_bytes = frozen.csv_bytes(online, frozen.ONLINE_FIELDS)
    evaluation_bytes = frozen.csv_bytes(evaluation, frozen.EVAL_FIELDS)
    lines = ["{} K1 {} {} 1120 {} {} {} 1000 48".format(
        MAGIC, family, seed, metadata["t0_ns"], metadata["H_ns"], metadata["stop_ns"]),
        "PROTOCOL_SHA256 " + frozen.PROTOCOL_SHA,
        "CONSTRUCTOR_SHA256 " + CONSTRUCTOR_SHA]
    seen = set()
    previous = -1
    for ordinal, (current, truth) in enumerate(zip(online, evaluation)):
        need(current["request_id"] == truth["request_id"] == ordinal and
             current["flow_id"] == ordinal and current["generation"] == 0 and
             current["policy_tag"] == truth["original_tag"], "request identity/tag")
        need(current["demand_ns"] >= previous and current["sport"] == 10000 + ordinal,
             "request time/port")
        previous = current["demand_ns"]
        row = (ordinal, 0, current["src"], current["dst"],
               node_ip(current["src"]), node_ip(current["dst"]), current["pg"],
               current["payload_bytes"], current["demand_ns"], truth["original_tag"],
               1, current["policy_tag"], current["sport"], current["dport"], ordinal)
        need(len(row) == len(FIELDS) and (row[4], row[5], row[12], row[13]) not in seen,
             "route-key identity")
        seen.add((row[4], row[5], row[12], row[13]))
        lines.append(" ".join(str(value) for value in row))
    native = ("\n".join(lines) + "\n").encode("ascii")
    costs = {str(mode): cost(online, family, mode) for mode in (43, 55, 56)}
    if family == "D1":
        need(costs["55"] == costs["56"], "D1 size-control canonical alias")
    manifest = dict(schema="ws31-c2-v4-pilot-input-manifest-r1", phase="PILOT", stage="K1",
                    family=family, seed=seed, request_count=1120, business_requests=96,
                    background_requests=1024, source_protocol_sha256=frozen.PROTOCOL_SHA,
                    verdict_protocol_v4_sha256=PROTOCOL_V4_SHA,
                    physical_constructor_sha256=CONSTRUCTOR_SHA,
                    start_header_sha256=START_HEADER_SHA,
                    generator_sha256=sha(Path(__file__).read_bytes()),
                    H_ns=metadata["H_ns"], stop_ns=metadata["stop_ns"],
                    costs=costs, files={
                        "online-current.csv": {"sha256": sha(online_bytes), "bytes": len(online_bytes)},
                        "evaluation-only.csv": {"sha256": sha(evaluation_bytes), "bytes": len(evaluation_bytes)},
                        "requests.native": {"sha256": sha(native), "bytes": len(native)},
                    }, technical_only=False, simulator_invocations=0)
    files = {"online-current.csv": online_bytes, "evaluation-only.csv": evaluation_bytes,
             "requests.native": native,
             "manifest.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")}
    return files, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-pilot", action="store_true", required=True)
    args = parser.parse_args()
    need(args.write_pilot, "explicit pilot input action")
    need(sha(Path(frozen.__file__).read_bytes()) == CONSTRUCTOR_SHA, "frozen physical constructor")
    implementation = Path(__file__).resolve().parents[1]
    header_bytes = (implementation / "src/point-to-point/model/ws31-start.h").read_bytes()
    need(sha(header_bytes.replace(b"\r\n", b"\n")) == START_HEADER_SHA,
         "frozen C2 rule source")
    root = implementation / "results/ws31-c2-v4-pilot-inputs-r1"
    destinations = [(family, seed, root / "{}-{}".format(family, seed))
                    for family in ("D1", "D2") for seed in SEEDS]
    need(all(not target.exists() for _, _, target in destinations), "pilot output exists")
    summary = []
    for family, seed, target in destinations:
        files, manifest = bundle(family, seed)
        target.mkdir(parents=True, exist_ok=False)
        for name, raw in files.items():
            with (target / name).open("xb") as handle:
                handle.write(raw)
        summary.append(dict(family=family, seed=seed, path=str(target),
                            manifest_sha256=sha(files["manifest.json"]), costs=manifest["costs"]))
    aggregate = {}
    for family in ("D1", "D2"):
        group = [item for item in summary if item["family"] == family]
        total = {str(mode): {metric: sum(item["costs"][str(mode)][metric] for item in group)
                             for metric in ("eligible", "planned_delay_sum_ns")}
                 for mode in (43, 55, 56)}
        ratios = {str(mode): {metric: total[str(mode)][metric] / total["43"][metric]
                              for metric in ("eligible", "planned_delay_sum_ns")}
                  for mode in (55, 56)}
        aggregate[family] = dict(total=total, ratios_to_43=ratios,
                                 c_cost_gate=all(0.9 <= ratio <= 1.1
                                                 for item in ratios.values() for ratio in item.values()))
    receipt = dict(schema="ws31-c2-v4-pilot-input-freeze-r1", protocol_v4_sha256=PROTOCOL_V4_SHA,
                   constructor_sha256=CONSTRUCTOR_SHA, generator_sha256=sha(Path(__file__).read_bytes()),
                   input_count=len(summary), requests_per_input=1120, inputs=summary,
                   aggregate_cost=aggregate, network_invocations=0,
                   c_cost_gate_is_only_ex_ante_matching=True,
                   effect_result=False, confirmation_released=False)
    with (root / "pilot-freeze-receipt.json").open("xb") as handle:
        handle.write((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"inputs": len(summary), "cost_gate":
                      {family: aggregate[family]["c_cost_gate"] for family in aggregate}}))


if __name__ == "__main__":
    main()
