"""Argument checks shared by the family query APIs."""

from __future__ import annotations

import math

import numpy as np

MAX_EVENTS_PER_QUERY = 500


def int_arg(args: dict, key: str, default: int, lo: int, hi: int) -> int:
    value = args.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise ValueError(f"argument {key!r} must be an integer from {lo} to {hi}")
    return value


def float_arg(args: dict, key: str) -> float:
    value = args.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"argument {key!r} must be a finite number")
    return float(value)


def call_index(args: dict) -> int:
    """Per-call counter assigned by the simulator; selects a fresh noise sub-seed."""
    n = args.get("_n", 0)
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("internal call index must be a non-negative integer")
    return n


def times_arg(args: dict, key: str, horizon: float) -> np.ndarray:
    """Times from a JSON list or {"start", "stop", "n"}; every value must lie in [0, horizon]."""
    spec = args.get(key)
    if isinstance(spec, dict):
        start = float_arg(spec, "start")
        stop = float_arg(spec, "stop")
        n = int_arg(spec, "n", 0, 1, MAX_EVENTS_PER_QUERY)
        times = np.linspace(start, stop, n)
    elif isinstance(spec, list) and spec:
        if len(spec) > MAX_EVENTS_PER_QUERY:
            raise ValueError(f"argument {key!r} has more than {MAX_EVENTS_PER_QUERY} times")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in spec):
            raise ValueError(f"argument {key!r} must contain only finite numbers")
        times = np.asarray(spec, dtype=float)
    else:
        raise ValueError(f"argument {key!r} must be a non-empty list of times or {{start, stop, n}}")
    if times.min() < 0.0 or times.max() > horizon:
        raise ValueError(f"times must lie in [0, {horizon:.6g}] in public time units")
    return times
