"""Select a fixed small mixed trace for six-arm routing correctness checks."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPO = ROOT / "config/topo_1280_400G_400G_OS1.txt"
SOURCE = ROOT / "config/ws25_seed20262501_b192.txt"
OUTPUT = ROOT / "config/ws25_preflight_seed20262501.txt"


def main():
    with TOPO.open() as source:
        _, _, link_count = map(int, source.readline().split())
        source.readline()
        host_tor = {}
        for _ in range(link_count):
            left, right, *_ = source.readline().split()
            a, b = int(left), int(right)
            if a < 1280 and b >= 1280:
                host_tor[a] = b
            elif b < 1280 and a >= 1280:
                host_tor[b] = a
    rows = SOURCE.read_text(encoding="ascii").splitlines()[1:]
    selected = []
    for tag in (1, 2):
        for same_tor in (True, False):
            matches = [row for row in rows if int(row.split()[5]) == tag and
                       (host_tor[int(row.split()[0])] == host_tor[int(row.split()[1])]) == same_tor]
            assert len(matches) >= 2, (tag, same_tor)
            selected.extend(matches[:2])
    data = (str(len(selected)) + "\n" + "\n".join(selected) + "\n").encode("ascii")
    if OUTPUT.exists() and OUTPUT.read_bytes() != data:
        raise ValueError("refusing to replace preflight trace")
    OUTPUT.write_bytes(data)
    print("{} {}".format(OUTPUT.name, hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
