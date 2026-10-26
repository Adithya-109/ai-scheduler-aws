"""Append-only JSON-lines log of every dispatch: the decision, the features,
and what actually happened. ``train_model.py --log`` learns from it."""
from __future__ import annotations

import json
import os
import threading
import time


class DecisionLog:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def record(self, **fields) -> None:
        fields.setdefault("ts", time.time())
        line = json.dumps(fields, default=float, separators=(",", ":"))
        with self._lock, open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def read(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out
