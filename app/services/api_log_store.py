from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any
import json


MAX_LOG_ENTRIES = 500
MAX_BODY_CHARS = 4000


class ApiLogStore:
    def __init__(self, max_entries: int = MAX_LOG_ENTRIES) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=max_entries)
        self._lock = Lock()

    def add(self, item: dict[str, Any]) -> None:
        clipped = dict(item)
        clipped["request_body"] = _clip(clipped.get("request_body"))
        clipped["response_body"] = _clip(clipped.get("response_body"))
        with self._lock:
            self._items.append(clipped)
        print(json.dumps({"api_post_log": clipped}, ensure_ascii=True))

    def list_newest_first(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._items))


def _clip(value: Any) -> Any:
    if value is None:
        return None
    text = json.dumps(value, ensure_ascii=True) if not isinstance(value, str) else value
    if len(text) <= MAX_BODY_CHARS:
        return value
    clipped_text = f"{text[:MAX_BODY_CHARS]}...[truncated]"
    try:
        return json.loads(clipped_text)
    except json.JSONDecodeError:
        return clipped_text


api_log_store = ApiLogStore()
