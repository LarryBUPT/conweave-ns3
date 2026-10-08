"""Inspect shortest-path fanout in the fixed WS-26 OS1 topology."""

from collections import Counter, deque
from pathlib import Path
import json
import random


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = ROOT / "config" / "topo_1280_400G_400G_OS1.txt"
SAMPLE_SEED = 26
SAMPLE_PAIRS = 100


def main():
    lines = TOPOLOGY.read_text(encoding="utf-8").splitlines()
    node_count, _, link_count = map(int, lines[0].split())
    switches = set(map(int, lines[1].split()))
    hosts = set(range(node_count)) - switches
    assert len(lines) - 2 == link_count
    graph = [[] for _ in range(node_count)]
    for line in lines[2:]:
        left, right = map(int, line.split()[:2])
        graph[left].append(right)
        graph[right].append(left)

    component = [-1] * node_count
    component_count = 0
    for first in range(node_count):
        if component[first] >= 0:
            continue
        queue = deque([first])
        component[first] = component_count
        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if component[neighbor] < 0:
                    component[neighbor] = component_count
                    queue.append(neighbor)
        component_count += 1

    host_groups = [[node for node in sorted(hosts) if component[node] == group]
                   for group in range(component_count)]
    shared_sources = (0, 4, 8, 12)
    shared_destinations = (32, 36, 40, 44)
    assert {graph[node][0] for node in shared_sources} == {1280}
    assert {graph[node][0] for node in shared_destinations} == {1281}
    assert component[1280] == component[1281]
    rng = random.Random(SAMPLE_SEED)
    fanout = Counter()
    for _ in range(SAMPLE_PAIRS):
        source = rng.choice(sorted(hosts))
        destination = rng.choice([node for node in host_groups[component[source]]
                                  if node != source])
        distance = [-1] * node_count
        distance[destination] = 0
        queue = deque([destination])
        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if distance[neighbor] < 0:
                    distance[neighbor] = distance[node] + 1
                    queue.append(neighbor)
        node = source
        while node != destination:
            options = [neighbor for neighbor in graph[node]
                       if distance[neighbor] == distance[node] - 1]
            assert options
            if node in switches:
                fanout[len(options)] += 1
            node = options[0]

    print(json.dumps({"sample_seed": SAMPLE_SEED, "sample_pairs": SAMPLE_PAIRS,
                      "connected_components": component_count,
                      "switch_fanout": dict(sorted(fanout.items()))}, sort_keys=True))
    assert set(fanout) == {1, 8}


if __name__ == "__main__":
    main()
