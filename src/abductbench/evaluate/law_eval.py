"""Law evaluator: runs an agent's law.py in an isolated subprocess and scores it.

The agent module is executed by a child interpreter (``python -I``) with a hard
timeout, an empty temporary cwd, and a stripped environment. Inputs are passed as
``.npy`` files and results come back as ``result.json`` plus ``.npy`` arrays. Every
failure inside the child becomes a status; this module does not raise on agent code.

Limitations: the child is not a real sandbox. It is not network-isolated (only the
environment is stripped, so no proxies), and it can still touch absolute paths.
Hash seeding is not pinned: ``PYTHONHASHSEED`` is ignored under ``-I`` (which implies ``-E``).
The law directory is appended to ``sys.path`` so law.py can import sibling files; bytecode
writing is disabled so no ``__pycache__`` appears in the workspace.
"""

from __future__ import annotations

import ast
import json
import math
import os
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from abductbench.config import TaskBundle

Status = Literal["ok", "crash", "timeout", "bad_shape", "nonfinite", "missing"]

DETAIL_LIMIT = 2000

# Child program. Runs under `python -I -c`, so the cwd and the workspace are not on sys.path.
_RUNNER = r'''
import importlib.util, json, os, sys, traceback
sys.dont_write_bytecode = True
import numpy as np

law_path, in_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]


def write(status, detail="", domain=None, mechanism=None):
    with open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump({"status": status, "detail": detail, "domain": domain, "mechanism": mechanism}, f)


def _plain(v):
    if isinstance(v, dict):
        if not all(isinstance(k, str) for k in v):
            raise TypeError("non-string key")
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, np.ndarray):
        return _plain(v.tolist())
    if isinstance(v, np.generic):
        return _plain(v.item())
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        # NaN/inf (e.g. in an unscored extra key) must not make the whole MECHANISM malformed.
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    raise TypeError(type(v).__name__)


def read_mechanism(mod):
    """None: no MECHANISM. {"__malformed__": True}: present but not a JSON-able dict."""
    if not hasattr(mod, "MECHANISM"):
        return None
    try:
        raw = mod.MECHANISM
        if not isinstance(raw, dict):
            raise TypeError("not a dict")
        out = _plain(raw)
        json.dumps(out)
        return out
    except Exception:
        return {"__malformed__": True}


def read_domain(mod):
    if not hasattr(mod, "DOMAIN"):
        return None
    raw = mod.DOMAIN
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, val in raw.items():
        if not isinstance(key, str):
            continue
        try:
            lo, hi = tuple(val)
            ok = all(isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)
                     for v in (lo, hi))
            out[key] = [float(lo), float(hi)] if ok else None
        except Exception:
            out[key] = None
    return out


def main():
    # Let law.py import sibling modules from its own directory (e.g. a public t0_model.py).
    # Appended, not prepended: a workspace file must not shadow stdlib modules that law.py
    # imports lazily.
    sys.path.append(os.path.dirname(os.path.abspath(law_path)))
    try:
        spec = importlib.util.spec_from_file_location("law_under_test", law_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except BaseException:
        write("crash", traceback.format_exc())
        return
    domain = read_domain(mod)
    mechanism = read_mechanism(mod)  # read BEFORE law() is called, so every later failure keeps it
    fn = getattr(mod, "law", None)
    if not callable(fn):
        write("crash", "law.py does not define a callable `law`", domain, mechanism)
        return
    preds = {}
    for name in ("in_range", "extrapolation"):
        x = np.load(os.path.join(in_dir, name + ".npy"), allow_pickle=False)
        try:
            out = fn(x.copy())
        except BaseException:
            write("crash", traceback.format_exc(), domain, mechanism)
            return
        try:
            arr = np.asarray(out)
            if arr.dtype.kind not in "biuf" or arr.shape != x.shape:
                raise ValueError
        except Exception:
            write("bad_shape", f"law({name}) returned shape/type unsuitable for input shape {x.shape}", domain, mechanism)
            return
        arr = arr.astype(float)
        if not np.all(np.isfinite(arr)):
            write("nonfinite", f"law({name}) returned NaN or inf", domain, mechanism)
            return
        preds[name] = arr
    for name, arr in preds.items():
        np.save(os.path.join(out_dir, "pred_" + name + ".npy"), arr)
    write("ok", "ok", domain, mechanism)


main()
'''

# Minimal environment for the child. Proxy variables are deliberately absent.
# PYTHONHASHSEED is not set: under -I (implies -E) the variable is ignored anyway.
_CHILD_ENV = {
    "PYTHONDONTWRITEBYTECODE": "1",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
}


@dataclass
class LawResult:
    status: Status
    nrmse_in: float | None = None
    nrmse_extrap: float | None = None
    n_params_proxy: int | None = None
    domain_score: float | None = None
    detail: str = ""
    # Declared MECHANISM as plain JSON data. None = law.py defines none (or the law did not run).
    # {"__malformed__": True} = defined but not a JSON-serialisable dict.
    mechanism: dict | None = None


def _trim(text: str) -> str:
    if len(text) <= DETAIL_LIMIT:
        return text
    marker = "...[truncated]\n"
    return marker + text[-(DETAIL_LIMIT - len(marker)):]


def _fail(status: Status, detail: str, mechanism: dict | None = None) -> LawResult:
    return LawResult(status=status, detail=_trim(detail), mechanism=mechanism)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass


def _run_child(law_path: Path, timeout_s: float, root: Path, in_dir: Path, out_dir: Path):
    """Run the child. Returns (result_dict, "", None) on success, else (None, detail, "timeout"|"crash")."""
    cwd = root / "cwd"
    cwd.mkdir()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-c", _RUNNER, str(law_path), str(in_dir), str(out_dir)],
        cwd=str(cwd),
        env=dict(_CHILD_ENV),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        _, err = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        proc.communicate()
        return None, f"law.py exceeded {timeout_s} s", "timeout"
    finally:
        _kill_group(proc)  # reaps stray grandchildren; harmless if the group is already gone
    stderr_text = err.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        return None, f"child exited with code {proc.returncode}:\n{stderr_text}", "crash"
    result_path = out_dir / "result.json"
    if not result_path.is_file():
        return None, f"child produced no result:\n{stderr_text}", "crash"
    return json.loads(result_path.read_text(encoding="utf-8")), "", None


def _iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def _domain_score(bundle: TaskBundle, domain) -> float:
    """Mean IoU over the keys of bundle.true_domain. Missing or malformed entries score 0."""
    if domain is None or not bundle.true_domain:
        return 0.0
    scores = []
    for key, true_iv in bundle.true_domain.items():
        agent = domain.get(key) if isinstance(domain, dict) else None
        if agent is None:
            scores.append(0.0)
            continue
        lo, hi = agent
        if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo):
            scores.append(0.0)
            continue
        scores.append(_iou((lo, hi), (float(true_iv[0]), float(true_iv[1]))))
    return float(sum(scores) / len(scores))


def _trapz(y: np.ndarray, x: np.ndarray) -> float:
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


EX_RANGE_FLOOR = 0.05  # range_ex is at least this fraction of range_in


def _range_or_one(y: np.ndarray) -> float:
    rng = float(np.max(y) - np.min(y)) if len(y) else float("nan")
    return rng if math.isfinite(rng) and rng > 0 else 1.0


def score_predictions(bundle: TaskBundle, pred_in, pred_ex) -> tuple[float, float]:
    """NRMSE on in-range and extrapolation points, each normalised by its own truth range.

    Family rule: a bundle whose true_domain has an "energy_range" key is the BETA family
    (decay density). Its truth and prediction are both normalized so that the trapezoid
    integral over the sorted union of evaluated points is 1. Otherwise (ORBIT family)
    values are compared raw.

    ``NRMSE_in = rms(pred - truth over in_range) / range_in`` and
    ``NRMSE_ex = rms(pred - truth over extrapolation) / range_ex``, with
    ``range_* = max(truth) - min(truth)`` over that region only (so a large extrapolation
    signal does not compress the in-window metric). A non-finite or zero range falls back to
    1.0 (``range_in``). ``range_ex`` is floored at ``EX_RANGE_FLOOR * range_in`` (0.05): for beta the truth in
    the held-out energy bands can be nearly flat, and a near-zero range would blow the metric up.
    (A zero or non-finite ``range_ex`` is thus replaced by the floor, not by 1.0.)
    """
    ep = bundle.eval_points()
    x_in = np.asarray(ep.in_range, dtype=float)
    x_ex = np.asarray(ep.extrapolation, dtype=float)
    t_in = np.asarray(bundle.truth_law(x_in), dtype=float)
    t_ex = np.asarray(bundle.truth_law(x_ex), dtype=float)
    p_in = np.asarray(pred_in, dtype=float)
    p_ex = np.asarray(pred_ex, dtype=float)

    if "energy_range" in bundle.true_domain:
        x = np.concatenate([x_in, x_ex])
        t = np.concatenate([t_in, t_ex])
        p = np.concatenate([p_in, p_ex])
        order = np.argsort(x, kind="stable")
        xs = x[order]
        area_t = _trapz(t[order], xs)
        area_p = _trapz(p[order], xs)
        if math.isfinite(area_t) and area_t > 0:
            t_in, t_ex = t_in / area_t, t_ex / area_t
        if math.isfinite(area_p) and area_p > 0:
            p_in, p_ex = p_in / area_p, p_ex / area_p

    range_in = _range_or_one(t_in)
    rng_ex = float(np.max(t_ex) - np.min(t_ex)) if len(t_ex) else 0.0
    range_ex = max(rng_ex if math.isfinite(rng_ex) else 0.0, EX_RANGE_FLOOR * range_in)
    nrmse_in = float(np.sqrt(np.mean((p_in - t_in) ** 2)) / range_in)
    nrmse_ex = float(np.sqrt(np.mean((p_ex - t_ex) ** 2)) / range_ex)
    return nrmse_in, nrmse_ex


_nrmse_pair = score_predictions  # backward-compatible private alias


def _n_params_proxy(source: str) -> int:
    return sum(1 for _ in ast.walk(ast.parse(source)))


def evaluate_law(bundle: TaskBundle, law_path: Path, timeout_s: float = 20.0) -> LawResult:
    law_path = Path(law_path)
    if not law_path.is_file():
        return _fail("missing", f"no law file at {law_path}")
    try:
        source = law_path.read_bytes().decode("utf-8", errors="replace")
    except OSError as exc:
        return _fail("crash", f"cannot read law.py: {exc}")

    try:
        with tempfile.TemporaryDirectory(prefix="law_eval_") as tmp:
            root = Path(tmp)
            in_dir = root / "in"
            out_dir = root / "out"
            in_dir.mkdir()
            out_dir.mkdir()
            ep = bundle.eval_points()
            np.save(in_dir / "in_range.npy", np.asarray(ep.in_range, dtype=float), allow_pickle=False)
            np.save(in_dir / "extrapolation.npy", np.asarray(ep.extrapolation, dtype=float), allow_pickle=False)
            try:
                result, detail, forced = _run_child(law_path, timeout_s, root, in_dir, out_dir)
            except OSError as exc:
                return _fail("crash", f"could not start child interpreter: {exc}")
            if forced == "timeout":
                return _fail("timeout", detail)
            if forced == "crash":
                return _fail("crash", detail)
            if result["status"] != "ok":
                # The child reads MECHANISM before calling law(), so the mechanism axis is kept
                # whenever the child got that far (it is None for import-time failures).
                return _fail(result["status"], result["detail"], result.get("mechanism"))
            pred_in = np.load(out_dir / "pred_in_range.npy", allow_pickle=False)
            pred_ex = np.load(out_dir / "pred_extrapolation.npy", allow_pickle=False)
            nrmse_in, nrmse_ex = score_predictions(bundle, pred_in, pred_ex)
            return LawResult(
                status="ok",
                nrmse_in=nrmse_in,
                nrmse_extrap=nrmse_ex,
                n_params_proxy=_n_params_proxy(source),
                domain_score=_domain_score(bundle, result["domain"]),
                detail="ok",
                mechanism=result.get("mechanism"),
            )
    except SyntaxError as exc:
        return _fail("crash", f"cannot parse law.py: {exc}")
    except Exception as exc:  # evaluator must not raise on agent output
        return _fail("crash", f"evaluator error: {type(exc).__name__}: {exc}")
