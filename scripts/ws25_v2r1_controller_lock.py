"""Keep the v2r1 correctness and screen controllers mutually exclusive locally."""
from contextlib import contextmanager
from pathlib import Path

LOCK = Path(__file__).resolve().parents[1] / "results/ws25-v2r1-controller.lock"


@contextmanager
def exclusive():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+b") as stream:
        stream.seek(0)
        try:
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except ImportError:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("Another v2r1 controller holds the local lock") from error
        try:
            yield
        finally:
            stream.seek(0)
            if "msvcrt" in locals():
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
