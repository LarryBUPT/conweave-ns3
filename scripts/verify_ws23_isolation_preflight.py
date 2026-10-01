#!/usr/bin/env python3
"""Check six new-SHA diagnostic off/on pilot cells before the 18-cell matrix."""

import argparse
import json

from verify_ws23_isolation_pilot import inspect, require


SOURCE_TRACE_SHA = "379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863"
OLD_FECMP_FCT_SHA = "4c415e30d3a25529f12b7c9af54a2c29f000ee7b0412c12cce494cb4ceb4dfdd"
MODES = ("fecmp", "shortq2", "guardhash")
ENTRY = {
    "seed": 0, "scenario": "mix", "path": "config/ws23_crossclass_bg_plus_3x4MiB.txt",
    "sha256": SOURCE_TRACE_SHA, "flow_count": 4, "payload_bytes": 20 * 1024 * 1024,
    "flows": [{"source": i, "destination": i + 24,
               "bytes": (8 if i == 0 else 4) * 1024 * 1024} for i in range(4)],
}


def pilot_id(mode, diagnostic, revision=1):
    if revision == 1:
        stamp, label = "20261001-1740%02d", "ws23-pilot"
    elif revision == 2:
        stamp, label = "20261001-1515%02d", "ws23-pilot2"
    else:
        raise ValueError("unknown preflight revision")
    return (stamp + "-%s-%s-%s") % (
        MODES.index(mode) * 2 + diagnostic, label, mode,
        "on" if diagnostic else "off")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--revision", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    results = {}
    for mode in MODES:
        pair = [inspect(ENTRY, mode, args.source_sha,
                        pilot_id(mode, d, args.revision), d)
                for d in (0, 1)]
        require(pair[0]["fct_sha256"] == pair[1]["fct_sha256"],
                mode + " diagnostic changed FCT")
        if mode == "fecmp":
            require(pair[0]["fct_sha256"] == OLD_FECMP_FCT_SHA,
                    "new-SHA ECMP drifted from old synthetic input")
        else:
            require(pair[0]["route"]["two_candidates"] > 0 and
                    pair[0]["route"]["scored"] > 0,
                    mode + " dynamic route path did not run")
        results[mode] = {"ids": [item["id"] for item in pair],
                         "fct_sha256": pair[0]["fct_sha256"],
                         "route": pair[0]["route"]}
    print(json.dumps({"source_sha": args.source_sha, "pilot_revision": args.revision,
                      "pilot_cells": 6,
                      "modes": results}, indent=2))


if __name__ == "__main__":
    main()
