#!/usr/bin/env python3
"""Derive immutable small correctness traces from the frozen WS-25 preflight input."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "ws25_preflight_seed20262501.txt"


def main():
    lines = SOURCE.read_text(encoding="ascii").splitlines()
    rows = [line.split() for line in lines[1:]]
    if int(lines[0]) != len(rows) or any(len(row) != 6 for row in rows):
        raise RuntimeError("Unexpected frozen WS-25 preflight input")
    outputs = {
        "config/ws25_v1fix_mixed8.txt": rows,
        "config/ws25_v1fix_background4.txt": [row for row in rows if row[5] == "1"],
        "config/ws25_v1fix_moe4.txt": [row for row in rows if row[5] == "2"],
        "config/ws25_v1fix_unclassified8.txt": [row[:5] + ["0"] for row in rows],
        "config/ws25_v1fix_legacy5.txt": [row[:5] for row in rows],
    }
    for relative, selected in outputs.items():
        if not selected:
            raise RuntimeError("Empty correctness input: " + relative)
        path = ROOT / relative
        text = str(len(selected)) + "\n" + "".join(" ".join(row) + "\n" for row in selected)
        if path.exists() and path.read_text(encoding="ascii") != text:
            raise RuntimeError("Refuse to overwrite changed correctness input: " + relative)
        path.write_text(text, encoding="ascii", newline="\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print("%s %s %d" % (relative, digest, len(selected)))


if __name__ == "__main__":
    main()
