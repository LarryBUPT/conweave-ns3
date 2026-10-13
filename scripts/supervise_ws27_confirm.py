#!/usr/bin/env python3
"""Restart the resumable WS-27 confirmation controller after transient errors.

The controller reuses built sources, skips verified cells, and refuses to
overwrite an existing experiment ID or raw result, so restarting is safe.
"""
import datetime
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "results" / "ws27-confirm-supervisor.log"
OUT = ROOT / "results" / "ws27-confirm.log"
ERR = ROOT / "results" / "ws27-confirm.err.log"
MAX_ATTEMPTS = 60
DELAY_SECONDS = 180
IDLE_POLL_SECONDS = 60
IDLE_MAX_SECONDS = 3600


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def note(text):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("%s %s\n" % (stamp(), text))
        stream.flush()


def host_idle():
    """Return True when no remote simulation is running; None on transport error.

    The controller refuses to admit a batch while another simulation is active,
    so a restart has to wait for simulations from the interrupted batch to end.
    """
    try:
        result = subprocess.run([sys.executable, "scripts/remote_experiment.py", "check"],
                                cwd=str(ROOT), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True,
                                timeout=120)
    except subprocess.TimeoutExpired:
        return None
    if result.returncode:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("active_simulation_pids="):
            return not line.split("=", 1)[1].strip()
    return None


def wait_for_idle():
    deadline = time.monotonic() + IDLE_MAX_SECONDS
    while time.monotonic() < deadline:
        state = host_idle()
        if state:
            note("host idle")
            return True
        if state is None:
            note("host check unavailable; retry")
        time.sleep(IDLE_POLL_SECONDS)
    note("host never became idle within the wait window")
    return False


def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        wait_for_idle()
        note("attempt %d start" % attempt)
        with OUT.open("a", encoding="utf-8") as out, ERR.open("a", encoding="utf-8") as err:
            code = subprocess.call([sys.executable, "scripts/run_ws27_matrix.py",
                                    "confirm", "run"], cwd=str(ROOT), stdout=out, stderr=err)
        note("attempt %d exit=%d" % (attempt, code))
        if code == 0:
            note("completed")
            return 0
        time.sleep(DELAY_SECONDS)
    note("attempt limit reached")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
