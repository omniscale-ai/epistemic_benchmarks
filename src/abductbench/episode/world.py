"""Hidden world and episode configuration for the decay-world episode.

A *world* is fixed by ``world_seed`` (public metadata + hidden carrier mass) and ``mechanism``.
The two mechanisms of one ``world_seed`` share every public quantity (masses, Q, resolutions,
initial measurement plan): only the hidden physics differs.

- ``carrier``: three-body decay with an unobserved neutral carrier of rest energy m_x; the source
  material loses very little energy.
- ``loss``: two-body decay (T0 holds); the source material loses a lot of energy. Its constants
  are *calibrated per world* so that the recorded spectrum at the nominal thickness is as close
  as possible (in KL) to the carrier world's spectrum of the same seed. This is the deliberate
  matched-pair construction that makes the initial observations ambiguous; it is documented in
  docs/episode-design.md and verified numerically (tests and ``baselines``), not assumed.

Seeds are separate: ``world_seed`` (world), ``obs_seed`` (all measurement noise), ``agent_rep``
(replicate of the agent run; never enters the data). The menu condition and the mechanism never
enter the observation RNG streams.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import numpy as np
from scipy import optimize

from abductbench.episode import physics as ph

EPISODE_VERSION = "decay-episode-0.1"
MECHANISMS = ("carrier", "loss")
FAMILY_MECHANISMS = {"decay": ("carrier", "loss"), "orbit": ("body", "force")}
CONDITIONS = ("ambiguous", "t0_sufficient", "no_measurement", "no_data")
N_INITIAL = 400
MAX_N = 400  # events per measurement
DEFAULT_BUDGET = 2
CARRIER_WORLD_MATERIAL = ph.Material(a=0.0, b=2.0, c=0.002)  # mean loss 0.004 Q at t = 1
UNIT_NAME = "unit E"  # public energy unit (fictional)

_STREAM_INITIAL, _STREAM_MEASURE, _STREAM_CHECK = 1, 2, 3


@dataclass(frozen=True)
class EpisodeConfig:
    world_seed: int
    mechanism: str
    obs_seed: int = 0
    agent_rep: int = 0
    condition: str = "ambiguous"
    menu: bool = True
    budget: int | None = None  # None: default for the condition
    unit_scale: float = 1.0  # multiplies every public energy (unit-invariance tests)
    version: str = EPISODE_VERSION
    family: str = "decay"  # "decay" (beta world) or "orbit"
    tools: bool = False  # orbit, menu only: ship exact simulators of both menu hypothesis kinds (workspace only)

    def __post_init__(self):
        if self.family not in FAMILY_MECHANISMS:
            raise ValueError(f"family must be one of {tuple(FAMILY_MECHANISMS)}")
        if self.tools and (self.family != "orbit" or not self.menu):
            raise ValueError("tools are defined for the orbit family with the menu only")
        mechs = FAMILY_MECHANISMS[self.family]
        if self.mechanism not in mechs:
            raise ValueError(f"mechanism must be one of {mechs}")
        if self.condition not in CONDITIONS:
            raise ValueError(f"condition must be one of {CONDITIONS}")
        if not (self.unit_scale > 0 and math.isfinite(self.unit_scale)):
            raise ValueError("unit_scale must be positive")

    @property
    def effective_budget(self) -> int:
        if self.budget is not None:
            return int(self.budget)
        return 0 if self.condition in ("no_measurement", "no_data") else DEFAULT_BUDGET

    def to_dict(self) -> dict:
        d = asdict(self)
        d["effective_budget"] = self.effective_budget
        return d

    @classmethod
    def from_dict(cls, d: dict) -> EpisodeConfig:
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**d)

    def paired(self) -> EpisodeConfig:
        """Same world seed, observation seed and condition; the opposite mechanism."""
        a, b = FAMILY_MECHANISMS[self.family]
        other = b if self.mechanism == a else a
        return EpisodeConfig(**{**asdict(self), "mechanism": other})


@dataclass(frozen=True)
class Shared:
    """Public quantities of a world seed (identical for both mechanisms)."""

    Q_pub: float  # public value of Q
    kin: ph.Kinematics
    m_x: float  # hidden: carrier rest energy (units of Q), used by the carrier world and the matching


def shared(world_seed: int, unit_scale: float = 1.0) -> Shared:
    rng = np.random.default_rng([world_seed, 7919])
    Q_pub = float(rng.uniform(0.8, 3.0)) * unit_scale
    m_light = float(rng.uniform(0.3, 1.0))
    m_daughter = float(rng.uniform(800.0, 1500.0))
    m_x = float(rng.uniform(0.0, 0.3))
    return Shared(Q_pub=Q_pub, kin=ph.Kinematics(m_light=m_light, m_daughter=m_daughter), m_x=m_x)


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    m = p > 1e-15
    return float(np.sum(p[m] * np.log(p[m] / np.maximum(q[m], 1e-15))))


@lru_cache(maxsize=256)
def matched_material(m_light: float, m_daughter: float, m_x: float) -> tuple[ph.Material, float]:
    """Loss-world material whose nominal spectrum best matches the carrier spectrum (min KL)."""
    kin = ph.Kinematics(m_light=m_light, m_daughter=m_daughter)
    target = ph.spectrum_probs(ph.Hypothesis("carrier", m_x, CARRIER_WORLD_MATERIAL), kin, 1.0)

    def obj(x):
        a, lb, lc = x
        if not (0.0 <= a <= 0.6 and -1.0 <= lb <= 3.0 and -5.0 <= lc <= 0.5):
            return 1e3
        h = ph.Hypothesis("two_body", 0.0, ph.Material(a, math.exp(lb), math.exp(lc)))
        return _kl(target, ph.spectrum_probs(h, kin, 1.0))

    best = None
    for a0 in (0.0, 0.8 * m_x, m_x):
        for b0 in (1.5, 2.5, 4.0):
            r = optimize.minimize(obj, [a0, math.log(b0), math.log(0.2)], method="Nelder-Mead",
                                  options={"maxiter": 2000, "xatol": 1e-5, "fatol": 1e-9})
            if best is None or r.fun < best.fun:
                best = r
    a, lb, lc = best.x
    return ph.Material(float(a), float(math.exp(lb)), float(math.exp(lc))), float(best.fun)


@dataclass
class World:
    cfg: EpisodeConfig
    sh: Shared = field(init=False)
    truth: ph.Hypothesis = field(init=False)
    match_kl: float | None = field(init=False, default=None)

    def __post_init__(self):
        self.sh = shared(self.cfg.world_seed, self.cfg.unit_scale)
        if self.cfg.mechanism == "carrier":
            self.truth = ph.Hypothesis("carrier", self.sh.m_x, CARRIER_WORLD_MATERIAL)
        else:
            mat, kl = matched_material(self.sh.kin.m_light, self.sh.kin.m_daughter, self.sh.m_x)
            self.truth = ph.Hypothesis("two_body", 0.0, mat)
            self.match_kl = kl

    # -- public view -------------------------------------------------------
    @property
    def kin(self) -> ph.Kinematics:
        return self.sh.kin

    @property
    def Q(self) -> float:
        return self.sh.Q_pub

    def public_metadata(self) -> dict:
        """Everything the agent is told about the setup, in public units. Same for both mechanisms."""
        Q, k = self.Q, self.kin
        return {
            "energy_unit": UNIT_NAME,
            "Q": Q,
            "mass_parent": k.m_parent * Q,
            "mass_daughter": k.m_daughter * Q,
            "mass_light": k.m_light * Q,
            "spectrometer_sigma": ph.SIGMA_SPEC * Q,
            "spectrometer_window": [ph.WINDOW[0] * Q, ph.WINDOW[1] * Q],
            "calorimeter_sigma": ph.SIGMA_CAL * Q,
            "recoil_relative_resolution": ph.RECOIL_REL_RES,
            "nominal_thickness": 1.0,
            "thickness_range": list(ph.THICKNESS_RANGE),
            "max_events_per_measurement": MAX_N,
        }

    def initial_plan(self) -> list[dict]:
        c = self.cfg.condition
        if c == "no_data":
            return []
        plan = [{"type": "spectrum", "thickness": 1.0, "n": self.cfg_n_initial}]
        if c == "t0_sufficient":
            plan.append({"type": "spectrum", "thickness": 2.5, "n": self.cfg_n_initial})
        return plan

    @property
    def cfg_n_initial(self) -> int:
        return N_INITIAL

    # -- measurement -------------------------------------------------------
    def to_public(self, sample: dict) -> dict:
        return {k: np.asarray(v, dtype=float) * self.Q for k, v in sample.items()}

    def to_internal(self, sample: dict) -> dict:
        return {k: np.asarray(v, dtype=float) / self.Q for k, v in sample.items()}

    def _rng(self, stream: int, idx: int) -> np.random.Generator:
        return np.random.default_rng([self.cfg.world_seed, self.cfg.obs_seed, stream, idx])

    def observe_initial(self) -> list[tuple[dict, dict]]:
        out = []
        for i, q in enumerate(self.initial_plan()):
            s = ph.sample_query(self.truth, self.kin, q, q["n"], self._rng(_STREAM_INITIAL, i))
            out.append((q, self.to_public(s)))
        return out

    def observe(self, query: dict, idx: int) -> dict:
        q = validate_measurement(query)
        s = ph.sample_query(self.truth, self.kin, q, q["n"], self._rng(_STREAM_MEASURE, idx))
        return self.to_public(s)

    def truth_sample(self, query: dict, n: int, seed: int = 0) -> dict:
        """Large truth sample for scoring (internal units). Independent of obs_seed."""
        mech = MECHANISMS.index(self.cfg.mechanism)
        rng = np.random.default_rng([self.cfg.world_seed, mech, _STREAM_CHECK, seed])
        return ph.sample_query(self.truth, self.kin, query, n, rng)


MEASUREMENT_TYPES = ("spectrum", "calorimeter")
HIDDEN_CHECK = {"type": "recoil_coincidence", "thickness": ph.CHECK_THICKNESS}


def validate_measurement(query: dict) -> dict:
    """Normalise and validate a measurement request from the menu. Raises ValueError."""
    if not isinstance(query, dict):
        raise ValueError("measurement must be a JSON object")
    qt = query.get("type")
    if qt not in MEASUREMENT_TYPES:
        raise ValueError(f"measurement type must be one of {MEASUREMENT_TYPES}")
    n = query.get("n", MAX_N)
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_N:
        raise ValueError(f"n must be an integer from 1 to {MAX_N}")
    if qt == "calorimeter":
        extra = set(query) - {"type", "n"}
        if extra:
            raise ValueError(f"unexpected keys for calorimeter: {sorted(extra)}")
        return {"type": "calorimeter", "n": n}
    t = query.get("thickness")
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
        raise ValueError("thickness must be a number")
    lo, hi = ph.THICKNESS_RANGE
    if not lo <= t <= hi:
        raise ValueError(f"thickness must lie in [{lo}, {hi}]")
    extra = set(query) - {"type", "n", "thickness"}
    if extra:
        raise ValueError(f"unexpected keys for spectrum: {sorted(extra)}")
    return {"type": "spectrum", "thickness": float(t), "n": n}


def config_json(cfg: EpisodeConfig) -> str:
    return json.dumps(cfg.to_dict(), sort_keys=True)
