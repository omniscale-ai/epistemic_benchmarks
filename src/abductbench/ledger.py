"""Append-only measurement ledger for the mode-2 simulator.

A ledger lives in a directory holding ``log.jsonl``. The first line is
``{"budget": B}``, written when the ledger is created and never changed
afterwards. Every later line records one charged query::

    {"query_type": ..., "args": ..., "cost": ..., "remaining": ...}

The log is the only source of truth: ``remaining`` is recomputed from it on
every access. All reads and writes happen under an exclusive ``flock`` on the
log file, so concurrent processes cannot overspend.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
from collections.abc import Callable, Collection
from contextlib import contextmanager
from pathlib import Path
from typing import Any

LOG_NAME = "log.jsonl"
_TOL = 1e-9


class Ledger:
    """Budget ledger stored in ``path / 'log.jsonl'``.

    ``budget`` is used only when the ledger is created. Opening an existing
    ledger ignores it; with ``budget=None`` the ledger must already exist.
    """

    def __init__(self, path: Path, budget: float | None = None):
        self.path = Path(path)
        if budget is None:
            # Open-only mode (used by the simulator): the ledger must already exist.
            if not self.log_path.exists():
                raise FileNotFoundError(f"no ledger at {self.path}")
        else:
            if not (math.isfinite(budget) and budget > 0):
                raise ValueError(f"budget must be a positive finite number, got {budget!r}")
            self.path.mkdir(parents=True, exist_ok=True)
        with self._locked() as f:
            if not f.read().strip():
                if budget is None:
                    raise ValueError(f"ledger at {self.path} is empty")
                f.seek(0, 2)
                f.write(json.dumps({"budget": float(budget)}) + "\n")
                f.flush()

    @property
    def log_path(self) -> Path:
        return self.path / LOG_NAME

    @contextmanager
    def _locked(self):
        fd = os.open(self.log_path, os.O_RDWR | os.O_CREAT, 0o644)
        f = os.fdopen(fd, "r+", encoding="utf-8")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.seek(0)
            yield f
        finally:
            f.close()  # closing the file releases the flock

    @staticmethod
    def _parse(text: str) -> tuple[float, list[dict]]:
        lines = [json.loads(line) for line in text.splitlines() if line.strip()]
        if not lines or "budget" not in lines[0]:
            raise ValueError("ledger log is missing its budget line")
        return float(lines[0]["budget"]), lines[1:]

    def _state(self, f) -> tuple[float, list[dict], float]:
        f.seek(0)
        budget, entries = self._parse(f.read())
        spent = sum(float(e["cost"]) for e in entries)
        return budget, entries, budget - spent

    @property
    def remaining(self) -> float:
        with self._locked() as f:
            return self._state(f)[2]

    @property
    def entries(self) -> list[dict]:
        with self._locked() as f:
            return self._state(f)[1]

    def spend(
        self,
        query_type: str,
        cost: float,
        action: Callable[[int], tuple[dict | None, Any]],
    ) -> tuple[bool, Any]:
        """Charge ``cost`` and run ``action`` while holding the lock.

        ``action(n)`` receives ``n``, the number of queries already charged, and
        returns ``(log_args, result)``. It runs only if the cost is affordable;
        if it raises, nothing is charged. Returns ``(True, result)`` on success,
        ``(False, None)`` otherwise, with no state change.
        """
        if not (isinstance(cost, (int, float)) and math.isfinite(cost) and cost > 0):
            return False, None
        with self._locked() as f:
            _, entries, remaining = self._state(f)
            if cost > remaining + _TOL:
                return False, None
            log_args, result = action(len(entries))
            line = json.dumps(
                {
                    "query_type": query_type,
                    "args": log_args,
                    "cost": float(cost),
                    "remaining": remaining - cost,
                },
                sort_keys=True,
            )
            f.seek(0, 2)
            f.write(line + "\n")
            f.flush()
            return True, result

    def charge(self, query_type: str, cost: float, args: dict | None = None) -> bool:
        """Charge ``cost`` for ``query_type``. Returns False and changes nothing if unaffordable."""
        ok, _ = self.spend(query_type, cost, lambda _n: (args, None))
        return ok


def discriminating_fraction(log_path: Path, discriminating: Collection[str]) -> float:
    """Share of simulations spent on discriminating query types (each costs 1.0); 0.0 if nothing spent."""
    text = Path(log_path).read_text(encoding="utf-8")
    entries = [json.loads(line) for line in text.splitlines() if line.strip()][1:]
    total = sum(float(e["cost"]) for e in entries)
    if total <= 0:
        return 0.0
    disc = set(discriminating)
    spent = sum(float(e["cost"]) for e in entries if e["query_type"] in disc)
    return spent / total
