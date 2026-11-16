"""Execute agent-submitted model files in a sandbox and validate their output.

An agent model is a Python module with::

    MECHANISM = {...}            # menu condition: {"kind": "carrier", "mass": m} | {"kind": "loss"} | {"kind": "other", ...}
    DESCRIPTION = "..."          # optional free text
    def simulate(query: dict, n: int, seed: int) -> dict[str, array]

Execution: a child ``python -I -B`` inside ``bwrap`` (no network, no host filesystem except the
interpreter, a read-only copy of the model directory and a scratch output directory), with CPU
and address-space limits. Without bwrap, execution is refused unless ``allow_unsandboxed=True``
(local dry tests only); the mode used is reported with every result.
"""

from __future__ import annotations

import json
import math
import os
import resource
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from abductbench.episode import physics as ph

AGENT_ENV_DIR = Path(__file__).resolve().parents[3] / ".agent-venv"
CPU_LIMIT_S = 120
MEM_LIMIT_BYTES = 4 * 1024**3
WALL_LIMIT_S = 180
REQUIRED_KEYS = {
    "spectrum": ("kinetic_energy",),
    "calorimeter": ("deposited_energy",),
    "recoil_coincidence": ("kinetic_energy", "recoil_momentum"),
}

_CHILD = r'''
import importlib.util, json, os, sys, traceback
sys.dont_write_bytecode = True
import numpy as np
mod_path, in_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.append(os.path.dirname(mod_path))
res = {"status": "ok", "detail": "", "mechanism": None, "description": None, "outputs": []}
def plain(v):
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, float) and v != v:
        return None
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return repr(v)
try:
    spec = importlib.util.spec_from_file_location("agent_model", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mech = getattr(mod, "MECHANISM", None)
    res["mechanism"] = plain(mech) if isinstance(mech, dict) else None
    desc = getattr(mod, "DESCRIPTION", None)
    res["description"] = desc if isinstance(desc, str) else None
    req = json.load(open(in_path))
    for i, q in enumerate(req["queries"]):
        out = mod.simulate(dict(q), int(req["n"]), int(req["seed"]) + i)
        if not isinstance(out, dict):
            raise TypeError("simulate must return a dict of arrays")
        arrs = {str(k): np.asarray(v, dtype=float) for k, v in out.items()}
        np.savez(os.path.join(out_dir, f"q{i}.npz"), **arrs)
        res["outputs"].append(sorted(arrs))
except BaseException:
    res["status"] = "error"
    res["detail"] = traceback.format_exc()[-3000:]
json.dump(res, open(os.path.join(out_dir, "result.json"), "w"))
'''


class ModelError(Exception):
    """The model failed to import or run, or returned invalid output. Message is safe to show."""


@dataclass
class ModelOutput:
    mechanism: dict | None
    description: str | None
    samples: list[dict]  # one dict of public-unit arrays per query
    sandbox: str  # "bwrap" or "none"


def bwrap_available() -> bool:
    return shutil.which("bwrap") is not None


def agent_python() -> Path:
    py = AGENT_ENV_DIR / "bin" / "python"
    return py if py.exists() else Path(sys.executable)


SANDBOX_VENV = "/opt/venv"


def _python_binds(py: Path) -> tuple[list[str], str]:
    """Read-only binds for an interpreter and the interpreter path to use inside the sandbox.

    A venv is mounted at the neutral path /opt/venv (so no host directory above it, such as the
    repository, appears in the sandbox); the base installation it points to is mounted at its own path.
    """
    real = py.resolve()
    args = ["--ro-bind", str(real.parents[1]), str(real.parents[1])]
    # The venv's python link may point through a symlinked directory (uv): mount the installation
    # at that unresolved path too, so the link resolves inside the sandbox.
    link = py
    while link.is_symlink():
        target = Path(os.readlink(link))
        link = target if target.is_absolute() else link.parent / target
        if link.is_absolute() and link.parent.parent != real.parents[1] and link.parent.name == "bin":
            args += ["--ro-bind", str(real.parents[1]), str(link.parent.parent)]
    venv = py.parent.parent
    if (venv / "pyvenv.cfg").exists():
        args += ["--ro-bind", str(venv), SANDBOX_VENV]
        return args, f"{SANDBOX_VENV}/bin/{py.name}"
    return args, str(real)


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_S, CPU_LIMIT_S))
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT_BYTES, MEM_LIMIT_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _system_binds() -> list[str]:
    args = []
    for d in ("/usr", "/lib", "/lib64", "/bin"):
        if Path(d).exists():
            args += ["--ro-bind", d, d]
    return args


def run_model(
    model_dir: Path,
    module: str,
    queries: list[dict],
    n: int,
    seed: int,
    allow_unsandboxed: bool = False,
) -> ModelOutput:
    """Run ``model_dir/module`` for each query. Returns raw (unvalidated) arrays."""
    model_dir = Path(model_dir).resolve()
    if not (model_dir / module).is_file():
        raise ModelError(f"model file {module} not found")
    py = agent_python()
    with tempfile.TemporaryDirectory(prefix="abm-") as tmp:
        tmp = Path(tmp)
        out = tmp / "out"
        out.mkdir()
        (tmp / "child.py").write_text(_CHILD)
        (out / "in.json").write_text(json.dumps({"queries": queries, "n": int(n), "seed": int(seed)}))
        if bwrap_available():
            binds, inner_py = _python_binds(py)
            argv = [
                "bwrap", *_system_binds(), *binds,
                "--ro-bind", str(model_dir), "/model",
                "--ro-bind", str(tmp / "child.py"), "/child.py",
                "--bind", str(out), "/out",
                "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
                "--setenv", "OMP_NUM_THREADS", "1", "--setenv", "OPENBLAS_NUM_THREADS", "1",
                "--chdir", "/tmp",
                inner_py, "-I", "-B", "/child.py", f"/model/{module}", "/out/in.json", "/out",
            ]
            mode = "bwrap"
        elif allow_unsandboxed:
            argv = [str(py), "-I", "-B", str(tmp / "child.py"), str(model_dir / module), str(out / "in.json"), str(out)]
            mode = "none"
        else:
            raise RuntimeError("bwrap is not available; refusing to execute agent code without a sandbox")
        try:
            subprocess.run(argv, cwd=tmp, env={"PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1"},
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=WALL_LIMIT_S, preexec_fn=_limits, check=False)
        except subprocess.TimeoutExpired:
            raise ModelError(f"model timed out after {WALL_LIMIT_S} s") from None
        rp = out / "result.json"
        if not rp.exists():
            raise ModelError("model process died without a result (CPU or memory limit?)")
        res = json.loads(rp.read_text())
        if res["status"] != "ok":
            raise ModelError("model raised an exception:\n" + res["detail"])
        samples = []
        for i in range(len(queries)):
            with np.load(out / f"q{i}.npz") as z:
                samples.append({k: np.array(z[k]) for k in z.files})
    return ModelOutput(res["mechanism"], res["description"], samples, mode)


def validate_sample(query: dict, sample: dict, n: int, meta: dict) -> dict:
    """Check one simulated sample against the instrument's physical constraints (public units).

    Raises ModelError with a message that says what is wrong but nothing about the truth.
    """
    qt = query["type"]
    keys = REQUIRED_KEYS[qt]
    out = {}
    for k in keys:
        if k not in sample:
            raise ModelError(f"simulate({qt}) must return key {k!r}")
        a = np.asarray(sample[k], dtype=float)
        if a.shape != (n,):
            raise ModelError(f"simulate({qt})[{k!r}] must have shape ({n},), got {a.shape}")
        if not np.all(np.isfinite(a)):
            raise ModelError(f"simulate({qt})[{k!r}] contains non-finite values")
        out[k] = a
    lo, hi = meta["spectrometer_window"]
    if "kinetic_energy" in out:
        T = out["kinetic_energy"]
        if T.min() < lo - 1e-9 * abs(lo) or T.max() > hi + 1e-9 * abs(hi):
            raise ModelError("recorded kinetic energies must lie inside the spectrometer window")
    if "deposited_energy" in out:
        if out["deposited_energy"].min() < -6.0 * meta["calorimeter_sigma"]:
            raise ModelError("deposited energies far below zero are not physical")
    if "recoil_momentum" in out:
        if out["recoil_momentum"].min() < 0.0:
            raise ModelError("recoil momentum magnitudes must be non-negative")
    return out


def validate_mechanism(mech: dict | None, menu: bool, Q: float) -> dict | None:
    """Validate the MECHANISM declaration. Menu condition: kind from the menu with valid parameters."""
    if not menu:
        return None if mech is None else {"description": str(mech.get("description", ""))[:2000]}
    if not isinstance(mech, dict) or mech.get("kind") not in ("carrier", "loss", "other"):
        raise ModelError('MECHANISM must be a dict with kind "carrier", "loss" or "other"')
    if mech["kind"] == "carrier":
        m = mech.get("mass")
        if isinstance(m, bool) or not isinstance(m, (int, float)) or not math.isfinite(m) or not 0.0 <= m < Q:
            raise ModelError("carrier MECHANISM needs 'mass': rest energy in [0, Q) in the public unit")
        return {"kind": "carrier", "mass": float(m)}
    if mech["kind"] == "loss":
        return {"kind": "loss"}
    return {"kind": "other", "description": str(mech.get("description", ""))[:2000]}


class Model:
    """A hypothesis model the protocol can query: agent file (sandboxed) or in-process callable."""

    def __init__(self, name: str, *, path: Path | None = None, fn=None, mechanism: dict | None = None,
                 description: str | None = None, allow_unsandboxed: bool = False):
        if (path is None) == (fn is None):
            raise ValueError("exactly one of path or fn")
        self.name = name
        self.path = None if path is None else Path(path)
        self.fn = fn
        self.mechanism = mechanism
        self.description = description
        self.allow_unsandboxed = allow_unsandboxed
        self.sandbox = "in-process" if fn is not None else None

    def simulate_many(self, queries: list[dict], n: int, seed: int) -> list[dict]:
        if self.fn is not None:
            return [self.fn(dict(q), n, seed + i) for i, q in enumerate(queries)]
        res = run_model(self.path.parent, self.path.name, queries, n, seed, self.allow_unsandboxed)
        self.mechanism, self.description, self.sandbox = res.mechanism, res.description, res.sandbox
        return res.samples


def hypothesis_fn(h: ph.Hypothesis, kin: ph.Kinematics, Q: float):
    """In-process model (public units) for a physics hypothesis: used by baselines and tests."""

    def fn(query: dict, n: int, seed: int) -> dict:
        rng = np.random.default_rng(seed)
        s = ph.sample_query(h, kin, query, n, rng)
        k = len(next(iter(s.values())))
        if 0 < k < n:  # exposure cap reached: resample the recorded events to n draws of the same law
            idx = rng.integers(0, k, n)
            s = {key: v[idx] for key, v in s.items()}
        return {key: v * Q for key, v in s.items()}

    return fn


def mixture_fn(parts: list[tuple[float, object]]):
    """In-process mixture of model functions with weights (a hedged predictive model)."""
    w = np.array([p for p, _ in parts], dtype=float)
    w = w / w.sum()

    def fn(query: dict, n: int, seed: int) -> dict:
        rng = np.random.default_rng([seed, 99])
        counts = rng.multinomial(n, w)
        chunks = [f(query, int(c), seed + 17 * i) for i, ((_, f), c) in enumerate(zip(parts, counts)) if c > 0]
        out = {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0]}
        perm = rng.permutation(n)
        return {k: v[perm] for k, v in out.items()}

    return fn

