#!/usr/bin/env python3
"""Summarize actual ConWeave reorder-VOQ samples without zero padding."""
import collections
import csv
import hashlib
import json
from pathlib import Path

from analyze_result import percentile

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs/research/evidence/ws25-v1fix-formal-analysis.json"
OUT = ROOT / "docs/research/evidence/ws25-v1fix-formal-conweave-voq.csv"
FIGURES = ROOT / "docs/research/figures/ws25-v1fix-formal-voq"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw_id = str(meta["raw_directory"])
    if not raw_id.isdigit():
        raise RuntimeError("Invalid raw directory: " + cell["id"])
    raw = folder / "raw" / raw_id
    path = raw / (raw_id + "_out_voq.txt")
    per_dst = raw / (raw_id + "_out_voq_per_dst.txt")
    if not path.is_file() or path.is_symlink() or not per_dst.is_file() or per_dst.is_symlink():
        raise RuntimeError("Missing or linked ConWeave VOQ raw: " + cell["id"])
    queue_values, packet_values = [], []
    previous = {}
    times = set()
    with path.open("r", encoding="ascii") as source:
        for line in source:
            fields = line.rstrip().split(",")
            if len(fields) != 4:
                raise RuntimeError("Malformed VOQ raw row: " + cell["id"])
            timestamp, tor, queues, packets = map(int, fields)
            if queues < 0 or packets < 0 or (tor in previous and timestamp <= previous[tor]):
                raise RuntimeError("Invalid VOQ sample: " + cell["id"])
            previous[tor] = timestamp
            times.add(timestamp)
            queue_values.append(queues)
            packet_values.append(packets)
    if not queue_values or len(previous) != 160 or len(times) < 2:
        raise RuntimeError("Incomplete ConWeave VOQ sampling: " + cell["id"])
    queue_values.sort()
    packet_values.sort()
    per_dst_rows = 0
    with per_dst.open("r", encoding="ascii") as source:
        for line in source:
            fields = line.rstrip().split(",")
            if len(fields) != 4 or any(int(value) < 0 for value in fields):
                raise RuntimeError("Malformed VOQ-per-destination row: " + cell["id"])
            per_dst_rows += 1
    row = {"id": cell["id"], "seed": cell["seed"], "background_flows": cell["background"],
           "source_sha": cell["source_sha"], "trace_sha256": cell["trace_sha256"],
           "voq_path": str(path.relative_to(ROOT)).replace("\\", "/"),
           "voq_sha256": sha(path), "per_dst_sha256": sha(per_dst),
           "sample_rows": len(queue_values), "sampled_tors": len(previous),
           "sampled_timestamps": len(times), "nonzero_queue_samples": sum(x > 0 for x in queue_values),
           "nonzero_packet_samples": sum(x > 0 for x in packet_values),
           "max_voq_count": queue_values[-1], "max_voq_packets": packet_values[-1],
           "p50_voq_count": percentile(queue_values, 50),
           "p99_voq_count": percentile(queue_values, 99),
           "p50_voq_packets": percentile(packet_values, 50),
           "p99_voq_packets": percentile(packet_values, 99),
           "per_dst_raw_rows": per_dst_rows}
    return row, packet_values


def esc(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_heatmap(rows):
    by_key = {(row["seed"], row["background_flows"]): row for row in rows}
    width, height = 760, 1020
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="1020" viewBox="0 0 760 1020">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#1f2937}.title{font-size:21px;font-weight:700}.axis{font-size:13px}.note{font-size:12px;fill:#4b5563}</style>',
        '<text class="title" x="25" y="34">ConWeave 重排 VOQ：每格采样最大排队包数</text>',
        '<text class="note" x="25" y="56">24 个需求 seed × 4 个背景档；每格都来自有效原始采样，0 表示实测采样值为零</text>',
    ]
    levels = (0, 64, 128, 192)
    for index, level in enumerate(levels):
        x = 185 + index * 128
        lines.append('<text class="axis" text-anchor="middle" x="%d" y="93">背景 %d</text>' % (x, level))
    for index, seed in enumerate(range(20262521, 20262545)):
        y = 104 + index * 35
        lines.append('<text class="axis" text-anchor="end" x="103" y="%.2f">%d</text>' % (y + 22, seed))
        for j, level in enumerate(levels):
            row = by_key[seed, level]
            value = row["max_voq_packets"]
            x = 121 + j * 128
            color = "#eef2f7" if value == 0 else "#f59e0b"
            lines.append('<rect x="%d" y="%d" width="120" height="31" fill="%s" stroke="#cbd5e1"><title>%s | %d 个实际采样 | 非零 %d 个</title></rect>' %
                         (x, y, color, esc(row["id"]), row["sample_rows"], row["nonzero_packet_samples"]))
            lines.append('<text class="axis" text-anchor="middle" x="%d" y="%d">%d</text>' %
                         (x + 60, y + 21, value))
    lines.append('<text class="note" x="25" y="983">VOQ 是 ConWeave 接收侧重排缓存，不是交换机 MMU 物理队列。</text>')
    lines.append('<text class="note" x="25" y="1003">图值为采样最大值；短暂事件可能落在采样间隔之间，具体事件见 per-dst raw。</text>')
    lines.append('</svg>')
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / "conweave-voq-max-packets-24seed.svg"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    cells = [cell for cell in data["cells"] if cell["mode"] == "conweave"]
    if len(cells) != 96:
        raise RuntimeError("Missing ConWeave formal cells")
    rows = [summarize(cell)[0] for cell in cells]
    rows.sort(key=lambda row: (row["seed"], row["background_flows"]))
    with OUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    render_heatmap(rows)
    print("conweave_voq_cells=%d nonzero_cells=%d" %
          (len(rows), sum(row["max_voq_packets"] > 0 for row in rows)))


if __name__ == "__main__":
    main()
