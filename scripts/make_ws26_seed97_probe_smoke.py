#!/usr/bin/env python3
"""Create a small fixed trace that hits one selected QP from each class."""

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/ws26_seed97_probe_smoke.txt"


def main():
    rows = [(896, 628, 3, 8388608, "2.000000000", 1)]
    rows.extend((0, 1128, 3, 8192, "2.000000000", 2) for _ in range(59))
    rows.append((0, 1144, 3, 8192, "2.000000000", 2))
    content = str(len(rows)) + "\n" + "".join(
        " ".join(map(str, row)) + "\n" for row in rows)
    if OUTPUT.exists() and OUTPUT.read_text(encoding="ascii") != content:
        raise RuntimeError("Refusing to replace an existing smoke trace")
    with OUTPUT.open("w", encoding="ascii", newline="\n") as stream:
        stream.write(content)
    print("flows=%d sha256=%s" % (
        len(rows), hashlib.sha256(content.encode("ascii")).hexdigest()))


if __name__ == "__main__":
    main()
