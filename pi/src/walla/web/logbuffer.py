"""Ring-buffer logging handler so the dashboard can show recent log lines."""

import collections
import logging
import threading


class RingBufferHandler(logging.Handler):
    def __init__(self, capacity: int = 500):
        super().__init__()
        self._buf: collections.deque = collections.deque(maxlen=capacity)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        with self._lock:
            self._buf.append(
                {
                    "time": record.created,
                    "level": record.levelname,
                    "name": record.name,
                    "message": msg,
                }
            )

    def tail(self, n: int = 100) -> list[dict]:
        with self._lock:
            if n >= len(self._buf):
                return list(self._buf)
            return list(self._buf)[-n:]
