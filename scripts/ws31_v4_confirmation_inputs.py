"""Freeze C2 v4 confirmation inputs before viewing pilot effects."""

import argparse
import hashlib
import json
from pathlib import Path

import ws31_demand_construct as frozen
import ws31_v4_pilot_inputs as pilot


SEEDS = tuple(range(5310201, 5310249))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bundle(family, seed):
    need(family in ("D1", "D2") and seed in SEEDS, "unregistered confirmation demand")
    online, evaluation, metadata = frozen.construct(family, seed)
    need(len(online) == len(evaluation) == 1120 and metadata["request_count"] == 1120,
         "confirmation construction count")
    online_bytes = frozen.csv_bytes(online, frozen.ONLINE_FIELDS)
    evaluation_bytes = frozen.csv_bytes(evaluation, frozen.EVAL_FIELDS)
    lines = ["{} K1 {} {} 1120 {} {} {} 1000 48".format(
        pilot.MAGIC, family, seed, metadata["t0_ns"], metadata["H_ns"], metadata["stop_ns"]),
        "PROTOCOL_SHA256 " + frozen.PROTOCOL_SHA,
        "CONSTRUCTOR_SHA256 " + pilot.CONSTRUCTOR_SHA]
    seen = set()
    for ordinal, (current, truth) in enumerate(zip(online, evaluation)):
        need(current["request_id"] == truth["request_id"] == ordinal and
             current["flow_id"] == ordinal and current["generation"] == 0 and
             current["policy_tag"] == truth["original_tag"], "request identity/tag")
        row = (ordinal, 0, current["src"], current["dst"],
               pilot.node_ip(current["src"]), pilot.node_ip(current["dst"]), current["pg"],
               current["payload_bytes"], current["demand_ns"], truth["original_tag"],
               1, current["policy_tag"], current["sport"], current["dport"], ordinal)
        key = (row[4], row[5], row[12], row[13])
        need(len(row) == len(pilot.FIELDS) and key not in seen, "route-key identity")
        seen.add(key)
        lines.append(" ".join(str(value) for value in row))
    native = ("\n".join(lines) + "\n").encode("ascii")
    costs = {str(mode): pilot.cost(online, family, mode) for mode in (43, 55, 56)}
    if family == "D1":
        need(costs["55"] == costs["56"], "D1 canonical size alias")
    manifest = dict(schema="ws31-c2-v4-confirmation-input-manifest-r1",
                    phase="CONFIRMATION", stage="K1", family=family, seed=seed,
                    request_count=1120, business_requests=96, background_requests=1024,
                    source_protocol_sha256=frozen.PROTOCOL_SHA,
                    verdict_protocol_v4_sha256=pilot.PROTOCOL_V4_SHA,
                    physical_constructor_sha256=pilot.CONSTRUCTOR_SHA,
                    start_header_sha256=pilot.START_HEADER_SHA,
                    generator_sha256=sha(Path(__file__).read_bytes()),
                    pilot_rule_helper_sha256=sha(Path(pilot.__file__).read_bytes()),
                    H_ns=metadata["H_ns"], stop_ns=metadata["stop_ns"], costs=costs,
                    files={
                        "online-current.csv": {"sha256": sha(online_bytes), "bytes": len(online_bytes)},
                        "evaluation-only.csv": {"sha256": sha(evaluation_bytes), "bytes": len(evaluation_bytes)},
                        "requests.native": {"sha256": sha(native), "bytes": len(native)},
                    }, simulator_invocations=0)
    files = {"online-current.csv": online_bytes, "evaluation-only.csv": evaluation_bytes,
             "requests.native": native,
             "manifest.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")}
    return files, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-confirmation", action="store_true", required=True)
    parser.parse_args()
    need(sha(Path(frozen.__file__).read_bytes()) == pilot.CONSTRUCTOR_SHA,
         "frozen physical constructor")
    source = Path(__file__).resolve().parents[1]
    header = (source / "src/point-to-point/model/ws31-start.h").read_bytes()
    need(sha(header.replace(b"\r\n", b"\n")) == pilot.START_HEADER_SHA,
         "frozen C2 rule source")
    root = source / "results/ws31-c2-v4-confirmation-inputs-r1"
    destinations = [(family, seed, root / "{}-{}".format(family, seed))
                    for family in ("D1", "D2") for seed in SEEDS]
    need(all(not target.exists() for _, _, target in destinations), "confirmation output exists")
    records = []
    for family, seed, target in destinations:
        files, manifest = bundle(family, seed)
        target.mkdir(parents=True, exist_ok=False)
        for name, raw in files.items():
            with (target / name).open("xb") as handle:
                handle.write(raw)
        records.append(dict(family=family, seed=seed, path=str(target),
                            manifest_sha256=sha(files["manifest.json"]), costs=manifest["costs"]))
    aggregate = {}
    for family in ("D1", "D2"):
        group = [record for record in records if record["family"] == family]
        totals = {str(mode): {metric: sum(record["costs"][str(mode)][metric] for record in group)
                              for metric in ("eligible", "planned_delay_sum_ns")}
                  for mode in (43, 55, 56)}
        ratios = {str(mode): {metric: totals[str(mode)][metric] / totals["43"][metric]
                              for metric in ("eligible", "planned_delay_sum_ns")}
                  for mode in (55, 56)}
        aggregate[family] = dict(total=totals, ratios_to_43=ratios,
                                 c_cost_gate=all(0.9 <= ratio <= 1.1
                                                 for item in ratios.values() for ratio in item.values()))
    receipt = dict(schema="ws31-c2-v4-confirmation-input-freeze-r1",
                   protocol_v4_sha256=pilot.PROTOCOL_V4_SHA,
                   constructor_sha256=pilot.CONSTRUCTOR_SHA,
                   generator_sha256=sha(Path(__file__).read_bytes()),
                   pilot_rule_helper_sha256=sha(Path(pilot.__file__).read_bytes()),
                   input_count=len(records), requests_per_input=1120, inputs=records,
                   aggregate_cost=aggregate, network_invocations=0,
                   effect_result=False, confirmation_released=False)
    with (root / "confirmation-freeze-receipt.json").open("xb") as handle:
        handle.write((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"inputs": len(records), "cost_gate":
                      {family: aggregate[family]["c_cost_gate"] for family in aggregate}}))


if __name__ == "__main__":
    main()
