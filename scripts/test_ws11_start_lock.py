#!/usr/bin/env python3
"""Remote Linux preflight for locked admission and known process ancestry."""
import importlib.util
import multiprocessing
import os
import time

WORKER_PATH = '/home/fnl/lzy/.research-workflow/remote_worker.py'


def load_worker():
    spec = importlib.util.spec_from_file_location('remote_worker_ws11', WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contender(queue):
    worker = load_worker()
    with worker.simulation_start_lock():
        entered = time.monotonic()
        time.sleep(0.4)
        exited = time.monotonic()
    queue.put((entered, exited))


def main():
    worker = load_worker()
    queue = multiprocessing.Queue()
    processes = [multiprocessing.Process(target=contender, args=(queue,))
                 for _ in range(2)]
    for process in processes:
        process.start()
    spans = sorted([queue.get(timeout=5) for _ in processes])
    for process in processes:
        process.join(timeout=5)
        assert process.exitcode == 0
    assert spans[0][1] <= spans[1][0], 'Admits overlapped under lock'
    known = worker.running_workers()
    active = worker.active_simulations()
    unknown = [pid for pid in active if not any(worker.descendant_of(int(pid), owner)
               for _, owner in known)]
    assert not unknown, 'Unowned ns-3 processes: %s' % unknown
    print('LOCK_SERIALIZED known_workers=%d active_simulation_processes=%d' %
          (len(known), len(active)))


if __name__ == '__main__':
    main()
