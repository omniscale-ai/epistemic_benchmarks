"""Episode protocol: register (forecast before measuring) -> measure -> ... -> final.

The orchestrator, not the agent, records forecasts: at ``register`` it snapshots the agent's
model files outside the workspace, runs every hypothesis model for the planned measurement and
stores the samples. ``measure`` performs exactly the registered measurement. Nothing about the
truth is returned to the agent at any step. The hidden check is never run here.

State directory (outside the workspace, never visible to an isolated agent)::

    config.json            episode config + manifest
    log.jsonl              append-only event log
    snapshots/<step>/      copy of the workspace ``models/`` at each register/final
    arrays/*.npz           initial data, forecasts, observations
"""

from __future__ import annotations

import json
import math
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from abductbench.episode import modelrun as mr
from abductbench.episode.families import family_of
from abductbench.episode.world import EpisodeConfig

N_FORECAST = 10000  # samples drawn from each hypothesis model for a registered forecast
MAX_REGISTRATIONS = 10
MAX_MODELS_BYTES = 2_000_000
VALIDATION_QUERIES = (
    {"type": "spectrum", "thickness": 0.5},
    {"type": "calorimeter"},
    {"type": "recoil_coincidence", "thickness": 1.0},
)


class ProtocolError(Exception):
    """A request the agent may fix and resend. The message never reveals the truth."""


@dataclass
class HypRecord:
    id: str
    role: str
    statement: str
    credence: float
    mechanism: dict | None
    model: mr.Model
    expected: str = ""
    forecast: dict | None = None  # public-unit samples for the registered measurement


@dataclass
class Step:
    kind: str  # "register" or "final"
    index: int
    hyps: list[HypRecord]
    undetermined: str
    measurement: dict | None = None  # register only
    observation: dict | None = None  # filled by measure (public units)
    predictive: mr.Model | None = None  # final only
    t: float = field(default_factory=time.time)


def _credence(x) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
        raise ProtocolError("credence must be a number in [0, 1]")
    return float(x)


def _text(d: dict, key: str, required: bool = True) -> str:
    v = d.get(key, "")
    if not isinstance(v, str) or (required and not v.strip()):
        raise ProtocolError(f"{key!r} must be a non-empty string")
    return v[:4000]


class Session:
    def __init__(self, cfg: EpisodeConfig, state_dir: Path | None = None, workspace: Path | None = None,
                 allow_unsandboxed: bool = False, manifest: dict | None = None):
        self.cfg = cfg
        self.fam = family_of(cfg)
        self.world = self.fam.world(cfg)
        self.meta = self.world.public_metadata()
        self.initial = self.world.observe_initial()
        self.steps: list[Step] = []
        self.n_measured = 0
        self.closed = False
        self.n_registrations = 0
        self.n_snapshots = 0
        self.state_dir = None if state_dir is None else Path(state_dir)
        self.workspace = None if workspace is None else Path(workspace)
        self.allow_unsandboxed = allow_unsandboxed
        if self.state_dir is not None:
            self.state_dir.mkdir(parents=True, exist_ok=False)
            (self.state_dir / "arrays").mkdir()
            (self.state_dir / "snapshots").mkdir()
            (self.state_dir / "config.json").write_text(
                json.dumps({"config": cfg.to_dict(), "manifest": manifest or {}}, indent=2, sort_keys=True))
            for i, (q, obs) in enumerate(self.initial):
                np.savez(self.state_dir / "arrays" / f"initial_{i}.npz", **obs)
            self._log("start", {"initial": [q for q, _ in self.initial]})

    # -- bookkeeping -------------------------------------------------------
    @property
    def budget_left(self) -> int:
        return self.cfg.effective_budget - self.n_measured

    @property
    def pending(self) -> Step | None:
        if self.steps and self.steps[-1].kind == "register" and self.steps[-1].observation is None:
            return self.steps[-1]
        return None

    def _log(self, event: str, payload: dict) -> None:
        if self.state_dir is None:
            return
        line = json.dumps({"t": time.time(), "event": event, **payload}, sort_keys=True, default=str)
        with open(self.state_dir / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def status(self) -> dict:
        return {
            "budget_left": self.budget_left,
            "closed": self.closed,
            "pending_measurement": None if self.pending is None else self.pending.measurement,
            "registrations": self.n_registrations,
            "measurements_done": self.n_measured,
        }

    def _snapshot(self, tag: str) -> Path | None:
        """Copy workspace/models (python files only) to the state dir; return the snapshot models dir."""
        if self.workspace is None or self.state_dir is None:
            return None
        src = self.workspace / "models"
        if not src.is_dir() or src.is_symlink():
            raise ProtocolError("models/ directory not found in the workspace")
        files = [p for p in src.iterdir() if p.suffix == ".py" and p.is_file() and not p.is_symlink()]
        if sum(p.stat().st_size for p in files) > MAX_MODELS_BYTES:
            raise ProtocolError("models/ is too large")
        self.n_snapshots += 1  # every attempt gets its own snapshot dir (a failed attempt leaves its copy)
        dst = self.state_dir / "snapshots" / f"{self.n_snapshots:03d}-{tag}" / "models"
        dst.mkdir(parents=True)
        for p in files:
            shutil.copyfile(p, dst / p.name)
        return dst

    def _resolve(self, ref, models: dict | None, snap: Path | None) -> mr.Model:
        if models is not None and ref in models:
            return models[ref]
        if not isinstance(ref, str) or not ref.startswith("models/") or "/" in ref[7:] or not ref.endswith(".py"):
            raise ProtocolError("model must be a path of the form models/<name>.py")
        if snap is None:
            raise ProtocolError("file models need a workspace")
        path = snap / ref[7:]
        if not path.is_file():
            raise ProtocolError(f"{ref} not found")
        return mr.Model(ref, path=path, allow_unsandboxed=self.allow_unsandboxed)

    def _hyps(self, raw, models, snap, need_alt: bool) -> list[HypRecord]:
        if not isinstance(raw, list) or not raw:
            raise ProtocolError("'hypotheses' must be a non-empty list")
        out, ids = [], set()
        for h in raw:
            if not isinstance(h, dict):
                raise ProtocolError("each hypothesis must be an object")
            hid = h.get("id")
            if not isinstance(hid, str) or not hid or hid in ids:
                raise ProtocolError("each hypothesis needs a unique string 'id'")
            ids.add(hid)
            role = h.get("role")
            if role not in ("current", "alternative"):
                raise ProtocolError("role must be 'current' or 'alternative'")
            out.append(HypRecord(hid, role, _text(h, "statement"), _credence(h.get("credence")), None,
                                 self._resolve(h.get("model"), models, snap)))
        if sum(1 for h in out if h.role == "current") != 1:
            raise ProtocolError("exactly one hypothesis must have role 'current'")
        if need_alt and not any(h.role == "alternative" for h in out):
            raise ProtocolError("at least one hypothesis must have role 'alternative'")
        if sum(h.credence for h in out) > 1.0 + 1e-6:
            raise ProtocolError("credences must sum to at most 1 (the rest is 'something else')")
        return out

    def _run(self, model: mr.Model, queries: list[dict], n: int, seed: int) -> list[dict]:
        try:
            samples = model.simulate_many([dict(q) for q in queries], n, seed)
            checked = [self.fam.validate_sample(q, s, n, self.meta) for q, s in zip(queries, samples)]
            if model.fn is None:
                model.mechanism = self.fam.validate_mechanism(model.mechanism, self.cfg.menu, self.meta)
            elif self.cfg.menu and model.mechanism is not None:
                model.mechanism = self.fam.validate_mechanism(model.mechanism, True, self.meta)
        except mr.ModelError as e:
            raise ProtocolError(f"{model.name}: {e}") from None
        return checked

    # -- protocol operations -----------------------------------------------
    def register(self, prereg: dict, models: dict | None = None) -> dict:
        if self.closed:
            raise ProtocolError("episode is closed")
        if self.budget_left <= 0:
            raise ProtocolError("no measurement budget left; submit the final answer")
        if self.n_registrations >= MAX_REGISTRATIONS:
            raise ProtocolError("too many registrations")
        if not isinstance(prereg, dict):
            raise ProtocolError("prereg must be a JSON object")
        try:
            meas = self.fam.validate_measurement(prereg.get("measurement"))
        except ValueError as e:
            raise ProtocolError(f"measurement: {e}") from None
        expected = prereg.get("expected")
        undetermined = _text(prereg, "undetermined")
        step_idx = len(self.steps)
        snap = None if models is not None else self._snapshot(f"{step_idx:02d}-register")
        hyps = self._hyps(prereg.get("hypotheses"), models, snap, need_alt=True)
        if not isinstance(expected, dict) or any(not isinstance(expected.get(h.id), str) or not expected[h.id].strip()
                                                  for h in hyps):
            raise ProtocolError("'expected' must map every hypothesis id to a non-empty description")
        for j, h in enumerate(hyps):
            h.expected = expected[h.id][:4000]
            h.forecast = self._run(h.model, [self.fam.model_query(meas)], self.fam.n_forecast,
                                   10_000 + 100 * step_idx + j)[0]
            h.mechanism = h.model.mechanism
        if self.pending is not None:  # replace an unconsumed registration (kept in the log)
            self.steps.pop()
        step = Step("register", step_idx, hyps, undetermined, measurement=meas)
        self.steps.append(step)
        self.n_registrations += 1
        if self.state_dir is not None:
            for h in hyps:
                np.savez(self.state_dir / "arrays" / f"forecast_{self.n_registrations:02d}_{h.id}.npz", **h.forecast)
        self._log("register", {"registration": self.n_registrations, "step": step_idx, "measurement": meas,
                               "undetermined": undetermined, "snapshot": None if snap is None else str(snap),
                               "hypotheses": [self._hyp_json(h) for h in hyps]})
        return {
            "registered": True,
            "measurement": meas,
            "forecast_summary": {h.id: _summary(h.forecast) for h in hyps},
        }

    def measure(self) -> tuple[dict, dict]:
        if self.closed:
            raise ProtocolError("episode is closed")
        step = self.pending
        if step is None:
            raise ProtocolError("register a forecast (prereg) before measuring")
        if self.budget_left <= 0:
            raise ProtocolError("no measurement budget left")
        obs = self.world.observe(step.measurement, self.n_measured)
        step.observation = obs
        self.n_measured += 1
        if self.state_dir is not None:
            np.savez(self.state_dir / "arrays" / f"observation_{self.n_measured:02d}.npz", **obs)
        self._log("measure", {"step": step.index, "measurement": step.measurement, "n_measured": self.n_measured})
        return step.measurement, obs

    def final(self, final: dict, models: dict | None = None) -> dict:
        if self.closed:
            raise ProtocolError("episode is closed")
        if not isinstance(final, dict):
            raise ProtocolError("final must be a JSON object")
        step_idx = len(self.steps) - (1 if self.pending is not None else 0)
        snap = None if models is not None else self._snapshot(f"{step_idx:02d}-final")
        hyps = self._hyps(final.get("hypotheses"), models, snap, need_alt=False)
        undetermined = _text(final, "undetermined")
        pred = self._resolve(final.get("predictive_model"), models, snap)
        for h in hyps:
            self._run(h.model, [self.fam.validation_queries[1]], 200, 7)
            h.mechanism = h.model.mechanism
        self._run(pred, [self.fam.model_query(q) if "n" in q else q for q in self.fam.validation_queries], 200, 11)  # validity only; not the hidden check
        if self.pending is not None:
            self.steps.pop()  # an unconsumed registration is superseded by the final answer
        self.steps.append(Step("final", step_idx, hyps, undetermined, predictive=pred))
        self.closed = True
        self._log("final", {"step": step_idx, "undetermined": undetermined,
                            "snapshot": None if snap is None else str(snap),
                            "predictive_model": pred.name, "hypotheses": [self._hyp_json(h) for h in hyps]})
        return {"accepted": True}

    @staticmethod
    def _hyp_json(h: HypRecord) -> dict:
        return {"id": h.id, "role": h.role, "statement": h.statement, "credence": h.credence,
                "expected": h.expected, "mechanism": h.mechanism, "model": h.model.name,
                "sandbox": h.model.sandbox}

    # -- data views --------------------------------------------------------
    def data_public(self) -> list[tuple[dict, dict]]:
        """Everything observed so far (initial + measured), public units."""
        out = list(self.initial)
        out += [(s.measurement, s.observation) for s in self.steps if s.kind == "register" and s.observation is not None]
        return out

    def data_until(self, step: Step) -> list[tuple[dict, dict]]:
        """Data available when ``step`` was submitted."""
        out = list(self.initial)
        for s in self.steps:
            if s is step:
                break
            if s.kind == "register" and s.observation is not None:
                out.append((s.measurement, s.observation))
        return out


def _summary(sample: dict) -> dict:
    return {k: {"mean": float(np.mean(v)), "std": float(np.std(v)),
                "q10_q50_q90": [float(x) for x in np.percentile(v, [10, 50, 90])]} for k, v in sample.items()}


def load_session(state_dir: Path, allow_unsandboxed: bool = False) -> Session:
    """Rebuild a finished session from its state dir (models from snapshots, arrays from npz)."""
    state_dir = Path(state_dir)
    conf = json.loads((state_dir / "config.json").read_text())
    s = Session(EpisodeConfig.from_dict(conf["config"]), state_dir=None, allow_unsandboxed=allow_unsandboxed)
    s.state_dir = state_dir
    events = [json.loads(x) for x in (state_dir / "log.jsonl").read_text().splitlines() if x.strip()]

    def model_of(snapshot: str | None, name: str) -> mr.Model:
        return mr.Model(name, path=Path(snapshot) / name[7:], allow_unsandboxed=allow_unsandboxed)

    def hyps_of(ev: dict, registration: int | None) -> list[HypRecord]:
        out = []
        for h in ev["hypotheses"]:
            rec = HypRecord(h["id"], h["role"], h["statement"], h["credence"], h["mechanism"],
                            model_of(ev["snapshot"], h["model"]), h.get("expected", ""))
            rec.model.mechanism = h["mechanism"]
            if registration is not None:
                with np.load(state_dir / "arrays" / f"forecast_{registration:02d}_{h['id']}.npz") as z:
                    rec.forecast = {k: np.array(z[k]) for k in z.files}
            out.append(rec)
        return out

    pending: Step | None = None
    for ev in events:
        if ev["event"] == "register":
            pending = Step("register", ev["step"], hyps_of(ev, ev["registration"]), ev["undetermined"],
                           measurement=ev["measurement"])
            s.n_registrations = ev["registration"]
        elif ev["event"] == "measure":
            s.n_measured = ev["n_measured"]
            with np.load(state_dir / "arrays" / f"observation_{s.n_measured:02d}.npz") as z:
                pending.observation = {k: np.array(z[k]) for k in z.files}
            s.steps.append(pending)
            pending = None
        elif ev["event"] == "final":
            s.steps.append(Step("final", ev["step"], hyps_of(ev, None), ev["undetermined"],
                                predictive=model_of(ev["snapshot"], ev["predictive_model"])))
            s.closed = True
    return s
