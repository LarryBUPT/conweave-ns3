#!/usr/bin/env python3
"""Verify WS-26 per-QP signal qualification logs and identity joins."""

import argparse
import itertools
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


QUALIFICATION_COLUMNS = (
    "decision_ns src_tor dst_tor src_id dst_id src_ip dst_ip sport dport tag selected_port "
    "ecmp_port candidate_port candidate_queue_bytes cache_present sequence "
    "window_end_ns generated_ns received_ns sample_packets ce_packets "
    "window_age_ns generated_age_ns received_age_ns"
).split()
IDENTITY_COLUMNS = (
    "side tor src dst sport dport first_port packets upstream_ce first_ns last_ns "
    "inconsistent unmapped"
).split()
MAX_LOG_BYTES = 64 * 1024 * 1024


def fail(message):
    raise ValueError(message)


def load_qualification(path, expected_feedback):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_LOG_BYTES:
        fail("qualification log exceeds the 64 MiB contract")
    try:
        lines = raw.decode("ascii").splitlines(keepends=True)
    except UnicodeDecodeError as error:
        fail("qualification log is not ASCII: {}".format(error))
    if len(lines) < 3:
        fail("qualification log is incomplete")
    feedback_match = re.fullmatch(r"# feedback_enabled=([01])\n", lines[0])
    if not feedback_match:
        fail("qualification feedback header is missing or malformed")
    feedback_enabled = int(feedback_match.group(1))
    if feedback_enabled != expected_feedback:
        fail("feedback header does not match the expected arm")
    if lines[1].strip().split() != QUALIFICATION_COLUMNS:
        fail("qualification column header mismatch")
    footer_match = re.fullmatch(r"# rows=(\d+) payload_bytes=(\d+)\n", lines[-1])
    if not footer_match:
        fail("qualification footer is missing or malformed")
    rows_expected, payload_bytes_expected = map(int, footer_match.groups())
    payload = "".join(lines[:-1]).encode("ascii")
    if len(payload) != payload_bytes_expected:
        fail("payload byte count mismatch")

    groups = defaultdict(list)
    observed_rows = 0
    for line_number, line in enumerate(lines[2:-1], 3):
        if not line.endswith("\n"):
            fail("unterminated qualification row at line {}".format(line_number))
        values = line.split()
        if len(values) != len(QUALIFICATION_COLUMNS):
            fail("column count mismatch at line {}".format(line_number))
        row = dict(zip(QUALIFICATION_COLUMNS, map(int, values)))
        if row["tag"] != 2:
            fail("qualification row is not a MoE QP at line {}".format(line_number))
        if row["src_id"] == row["dst_id"]:
            fail("same-ToR QP was recorded at line {}".format(line_number))
        if row["cache_present"] not in (0, 1):
            fail("invalid cache_present at line {}".format(line_number))
        if not feedback_enabled and row["cache_present"]:
            fail("feedback-off arm contains a cached report at line {}".format(line_number))
        if not row["cache_present"]:
            absent_fields = (
                "sequence", "window_end_ns", "generated_ns", "received_ns",
                "sample_packets", "ce_packets", "window_age_ns",
                "generated_age_ns", "received_age_ns",
            )
            if any(row[field] != 0 for field in absent_fields):
                fail("missing report has nonzero data at line {}".format(line_number))
            if feedback_enabled:
                # A missing cache entry is retained as missing; it is not a zero-CE report.
                pass
        else:
            if row["sample_packets"] <= 0 or not 0 <= row["ce_packets"] <= row["sample_packets"]:
                fail("invalid report sample counts at line {}".format(line_number))
            decision = row["decision_ns"]
            end, generated, received = (
                row["window_end_ns"], row["generated_ns"], row["received_ns"]
            )
            if not end <= generated <= received <= decision:
                fail("report timestamps are out of order at line {}".format(line_number))
            if row["window_age_ns"] != decision - end:
                fail("window age mismatch at line {}".format(line_number))
            if row["generated_age_ns"] != decision - generated:
                fail("generation age mismatch at line {}".format(line_number))
            if row["received_age_ns"] != decision - received:
                fail("delivery age mismatch at line {}".format(line_number))
        qkey = (row["src_id"], row["dst_id"], row["sport"], row["dport"])
        groups[qkey].append(row)
        observed_rows += 1

    if observed_rows != rows_expected:
        fail("footer row count mismatch")
    if not groups:
        fail("no MoE QPs were recorded")
    for qkey, rows in groups.items():
        candidates = {row["candidate_port"] for row in rows}
        if len(rows) != 8 or len(candidates) != 8:
            fail("QP {} does not have eight unique candidate rows".format(qkey))
        shared = ("decision_ns", "src_tor", "dst_tor", "src_ip", "dst_ip", "tag", "selected_port", "ecmp_port")
        for field in shared:
            if len({row[field] for row in rows}) != 1:
                fail("QP {} has inconsistent {}".format(qkey, field))
        if rows[0]["selected_port"] not in candidates or rows[0]["ecmp_port"] not in candidates:
            fail("QP {} selected/ECMP port is outside the candidate set".format(qkey))
        if rows[0]["src_ip"] == rows[0]["dst_ip"]:
            fail("QP {} has identical source and destination addresses".format(qkey))
    return raw, feedback_enabled, groups


def verify_identity(path, groups):
    lines = Path(path).read_text(encoding="ascii").splitlines()
    if not lines or lines[0].split() != IDENTITY_COLUMNS:
        fail("identity column header mismatch")
    identity = {}
    for line_number, line in enumerate(lines[1:], 2):
        if not line or line.startswith("#"):
            continue
        values = line.split()
        if len(values) != len(IDENTITY_COLUMNS):
            fail("identity column count mismatch at line {}".format(line_number))
        row = dict(zip(IDENTITY_COLUMNS, values))
        key = (row["side"],) + tuple(int(row[field]) for field in
                                      ("src", "dst", "sport", "dport"))
        if key in identity:
            fail("duplicate identity row {}".format(key))
        identity[key] = row

    for qkey, rows in groups.items():
        src, dst, sport, dport = qkey
        first = rows[0]
        expected = first["selected_port"]
        for side, tor in (("source", first["src_tor"]), ("destination", first["dst_tor"])):
            key = (side, src, dst, sport, dport)
            row = identity.get(key)
            if row is None:
                fail("missing {} identity for QP {}".format(side, qkey))
            if int(row["tor"]) != tor or int(row["first_port"]) != expected:
                fail("{} identity route mismatch for QP {}".format(side, qkey))
            if int(row["packets"]) <= 0 or int(row["inconsistent"]) != 0 or int(row["unmapped"]) != 0:
                fail("{} identity coverage/integrity failure for QP {}".format(side, qkey))


def summarize(groups, feedback_enabled):
    qps = len(groups)
    both = {5: 0, 10: 0, 20: 0}
    different_ratio = 0
    ecmp_alternative_distinguishable = 0
    different_ratio_by_age = {5: 0, 10: 0, 20: 0}
    ecmp_alternative_by_age = {5: 0, 10: 0, 20: 0}
    report_ages = {"window": [], "generated": [], "received": []}
    qps_any_report = 0
    qps_any_report_pair = 0
    qps_any_single_report_pair = 0
    for rows in groups.values():
        by_port = {row["candidate_port"]: row for row in rows}
        present_ports = [row["candidate_port"] for row in rows if row["cache_present"]]
        if present_ports:
            qps_any_report += 1
        if len(present_ports) >= 2:
            qps_any_report_pair += 1
        if 0 < len(present_ports) < 8:
            qps_any_single_report_pair += 1
        for row in rows:
            if row["cache_present"]:
                report_ages["window"].append(row["window_age_ns"])
                report_ages["generated"].append(row["generated_age_ns"])
                report_ages["received"].append(row["received_age_ns"])
        for age_us in both:
            age_ns = age_us * 1000
            if any(all(by_port[p]["cache_present"] and
                       by_port[p]["window_age_ns"] <= age_ns
                       for p in pair)
                   for pair in itertools.combinations(by_port, 2)):
                both[age_us] += 1
        def ratios_differ(a, b, age_limit_ns=None):
            if not (a["cache_present"] and b["cache_present"]):
                return False
            if age_limit_ns is not None and (
                a["window_age_ns"] > age_limit_ns or b["window_age_ns"] > age_limit_ns
            ):
                return False
            return a["ce_packets"] * b["sample_packets"] != \
                b["ce_packets"] * a["sample_packets"]

        pairs = list(itertools.combinations(by_port, 2))
        if any(ratios_differ(by_port[a], by_port[b]) for a, b in pairs):
            different_ratio += 1
        ecmp = by_port[rows[0]["ecmp_port"]]
        alternatives = [row for row in rows if row["candidate_port"] != ecmp["candidate_port"]]
        if any(ratios_differ(ecmp, row) for row in alternatives):
            ecmp_alternative_distinguishable += 1
        for age_us in different_ratio_by_age:
            limit_ns = age_us * 1000
            if any(ratios_differ(by_port[a], by_port[b], limit_ns) for a, b in pairs):
                different_ratio_by_age[age_us] += 1
            if any(ratios_differ(ecmp, row, limit_ns) for row in alternatives):
                ecmp_alternative_by_age[age_us] += 1
    return {
        "feedback_enabled": feedback_enabled,
        "moe_qps": qps,
        "candidate_rows": qps * 8,
        "qps_with_no_cached_report": qps - qps_any_report,
        "qps_with_any_cached_report": qps_any_report,
        "qps_with_any_single_report_candidate_pair": qps_any_single_report_pair,
        "qps_with_two_or_more_cached_candidate_reports": qps_any_report_pair,
        "qps_with_any_valid_report_pair_by_age_us": both,
        "qps_with_any_different_ce_ratio_pair": different_ratio,
        "qps_with_different_ce_ratio_pair_by_age_us": different_ratio_by_age,
        "qps_with_ecmp_vs_alternative_ce_ratio_difference": ecmp_alternative_distinguishable,
        "qps_with_ecmp_vs_alternative_ce_ratio_difference_by_age_us": ecmp_alternative_by_age,
        "qp_candidate_cache_observations": len(report_ages["window"]),
        "candidate_age_buckets_by_clock_us": {
            clock: {
                "le_5us": sum(age <= 5000 for age in ages),
                "5_10us": sum(5000 < age <= 10000 for age in ages),
                "10_20us": sum(10000 < age <= 20000 for age in ages),
                "gt_20us": sum(age > 20000 for age in ages),
            }
            for clock, ages in report_ages.items()
        },
        "candidate_report_window_age_ns": {
            "min": min(report_ages["window"]) if report_ages["window"] else None,
            "median": sorted(report_ages["window"])[len(report_ages["window"]) // 2] if report_ages["window"] else None,
            "max": max(report_ages["window"]) if report_ages["window"] else None,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--identity", required=True, type=Path)
    parser.add_argument("--feedback-enabled", required=True, type=int, choices=(0, 1))
    parser.add_argument("--expected-moe-qps", type=int)
    args = parser.parse_args()
    try:
        raw, feedback_enabled, groups = load_qualification(
            args.qualification, args.feedback_enabled
        )
        verify_identity(args.identity, groups)
        summary = summarize(groups, feedback_enabled)
        if args.expected_moe_qps is not None and summary["moe_qps"] != args.expected_moe_qps:
            fail("expected {} MoE QPs, found {}".format(
                args.expected_moe_qps, summary["moe_qps"]
            ))
        summary["qualification_bytes"] = len(raw)
        print(json.dumps(summary, sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError) as error:
        print("WS-26 qualification verification failed: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
