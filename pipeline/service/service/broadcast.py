from __future__ import annotations

import queue
import threading
from typing import Any, Dict, Iterable


class AlertBroadcaster:
    """
    In-process best-effort fanout for new alerts (for SSE/WebSocket demo).
    Not durable: if a client disconnects, it should fall back to HTTP /alerts polling.
    """

    def __init__(self, *, max_queue_size: int = 200):
        self._max_queue_size = int(max_queue_size)
        self._lock = threading.Lock()
        self._subs: set[queue.Queue[Dict[str, Any]]] = set()

    def subscribe(self) -> queue.Queue[Dict[str, Any]]:
        q: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=self._max_queue_size)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q: queue.Queue[Dict[str, Any]]) -> None:
        with self._lock:
            self._subs.discard(q)

    def publish(self, alert: Dict[str, Any]) -> None:
        with self._lock:
            subs: Iterable[queue.Queue[Dict[str, Any]]] = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(alert)
            except queue.Full:
                # Drop oldest to keep "most recent" behavior.
                try:
                    _ = q.get_nowait()
                except Exception:
                    pass
                try:
                    q.put_nowait(alert)
                except Exception:
                    pass
