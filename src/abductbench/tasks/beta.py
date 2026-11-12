"""Beta-decay task generator.

All physics is computed internally in MeV. Public files and the truth law use
public units (MeV for stages a and c; "unit U" = 0.5 MeV for stage b; "unit W" = 1 MeV for the
fictional stage d).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import partial

import numpy as np

from abductbench.config import EvalPoints, Stage, TaskBundle, Truth, VariantConfig
from abductbench.evaluate.oracle import beta_oracle

ALPHA = 1.0 / 137.036
N_EVENTS = 1000
WINDOW = (0.25, 1.2)  # public recorded kinetic-energy window, fraction of Q
EXT_BAND = (0.02, 1.5)  # held-out evaluation range, fraction of Q: [0.02, WINDOW[0]) and (WINDOW[1], 1.5]
GRID = 20001
NO_ENTITY_WEIGHTS = (0.8, 0.1, 0.1)  # resolution peak, energy-loss tail, backscatter shelf

_STAGE_IDX = {s: i for i, s in enumerate(Stage)}
_TRUTH_IDX = {t: i for i, t in enumerate(Truth)}


@dataclass(frozen=True)
class _Setup:
    stage: Stage
    Q: float  # MeV
    Z: int
    k: int
    M_d: float  # MeV
    M_p: float  # MeV
    m_e: float  # MeV, rest energy of the light particle
    m_X: float  # MeV, hidden mass (stage c only)
    scale: float  # MeV per public unit
    noise: float
    sigma: float  # MeV, detector resolution

    @property
    def renamed(self) -> bool:
        return self.stage is Stage.OBFUSCATED

    @property
    def names(self) -> dict[str, str]:
        if self.renamed:
            return {"parent": "source S", "daughter": "product D", "light": "particle A", "unit": "unit U"}
        if self.stage is Stage.SYNTHETIC:  # fictional vocabulary, distinct from stage b's names
            return {"parent": "emitter V", "daughter": "remnant R", "light": "quantum Y", "unit": "unit W"}
        return {"parent": "parent nucleus", "daughter": "daughter nucleus", "light": "electron", "unit": "MeV"}


def _setup(cfg: VariantConfig) -> _Setup:
    # Pair-level parameters depend only on (seed, mode) so that every stage and
    # both truths of a pair share the same Q and daughter mass.
    rng = np.random.default_rng([cfg.seed, cfg.mode])
    Q = float(rng.uniform(1.0, 2.5))
    Z = int(rng.integers(10, 60))
    k = int(rng.integers(2, 4))  # {2, 3}; used by stage d only
    M_d = float(rng.uniform(1500.0, 2500.0))

    stage = cfg.stage
    m_e = 0.30 if stage is Stage.SYNTHETIC else 0.511
    m_X = 0.3 * Q if stage is Stage.COUNTERFACTUAL else 0.0
    scale = 0.5 if stage is Stage.OBFUSCATED else 1.0
    return _Setup(
        stage=stage,
        Q=Q,
        Z=Z,
        k=k,
        M_d=M_d,
        M_p=M_d + Q + m_e,
        m_e=m_e,
        m_X=m_X,
        scale=scale,
        noise=cfg.noise,
        sigma=cfg.noise * Q,
    )


def _fermi_p(E: np.ndarray, m: float, Z: int) -> np.ndarray:
    """p * F(Z, E) with F = 2*pi*eta / (1 - exp(-2*pi*eta)), eta = alpha*Z*E/p.

    Finite at p -> 0 (the product tends to 2*pi*alpha*Z*E).
    """
    p = np.sqrt(np.maximum(E * E - m * m, 0.0))
    p_safe = np.maximum(p, 1e-12)
    x = 2.0 * math.pi * ALPHA * Z * E / p_safe
    return p_safe * x / (-np.expm1(-x))


def _raw_entity(T: np.ndarray, s: _Setup) -> np.ndarray:
    Q = s.Q
    dq = Q - T
    inside = (T >= 0) & (dq > 0)
    dq_c = np.where(inside, dq, 0.0)
    E = T + s.m_e
    if s.stage in (Stage.HISTORICAL, Stage.OBFUSCATED):
        f = _fermi_p(E, s.m_e, s.Z) * E * dq_c**2
    elif s.stage is Stage.COUNTERFACTUAL:
        p = np.sqrt(np.maximum(E * E - s.m_e**2, 0.0))
        pX = np.sqrt(np.maximum(dq_c**2 - s.m_X**2, 0.0))
        f = p * E * dq_c * pX
    else:  # SYNTHETIC: k massless hidden particles
        p = np.sqrt(np.maximum(E * E - s.m_e**2, 0.0))
        f = p * E * dq_c ** (3 * s.k - 1)
    return np.where(inside, f, 0.0)


def _raw_no_entity(T: np.ndarray, s: _Setup, thickness: float = 1.0) -> np.ndarray:
    # Degeneracy by design: the artifact line shape depends only on Q, sigma and the thickness. The
    # stage-specific constants (m_X in stage c, k in stage d) enter only the entity truth, so the
    # no_entity physics of beta stages a, c and d is the same artifact (only the vocabulary, the
    # light-particle mass and Q/sigma of the pair differ). Not redesigned in this wave.
    # thickness scales the energy-loss tail (length and weight); 1.0 is the generator's nominal target.
    Q, sig = s.Q, s.sigma
    lam = 0.1 * Q * thickness
    w_peak, w_tail, w_shelf = NO_ENTITY_WEIGHTS
    w_tail = w_tail * thickness
    peak = np.exp(-0.5 * ((T - Q) / sig) ** 2) / (sig * math.sqrt(2 * math.pi))
    tail = np.where(T <= Q, np.exp(np.minimum((T - Q) / lam, 0.0)) / lam, 0.0)
    shelf = np.where((T >= 0) & (T <= Q), 1.0 / Q, 0.0)
    f = w_peak * peak + w_tail * tail + w_shelf * shelf
    return np.where(T >= 0, f, 0.0)


def _raw(truth: Truth, T: np.ndarray, s: _Setup, thickness: float = 1.0) -> np.ndarray:
    # The hidden-carrier line shape does not depend on the target thickness.
    return _raw_entity(T, s) if truth is Truth.ENTITY else _raw_no_entity(T, s, thickness)


def _integrate(f: np.ndarray, x: np.ndarray) -> float:
    return float(np.sum((f[1:] + f[:-1]) * np.diff(x)) / 2.0)


def _gauss(d: np.ndarray, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * (d / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


def _smeared_entity_table(s: _Setup, n_t: int = 4001, n_x: int = 6001) -> tuple[np.ndarray, np.ndarray]:
    """Detector-seen entity density (raw spectrum convolved with the public Gaussian) on a grid.

    This is exactly the density of the generated events: T_true is drawn from the raw spectrum on
    its full support [0, Q] and T_obs = T_true + N(0, sigma). Returned in MeV, unnormalised.
    """
    t = np.linspace(0.0, s.Q, n_t)
    w = np.full(n_t, t[1] - t[0])
    w[0] = w[-1] = w[0] / 2.0
    ft = _raw_entity(t, s) * w
    x = np.linspace(-6.0 * s.sigma, max(s.Q + 6.0 * s.sigma, EXT_BAND[1] * s.Q), n_x)
    dens = np.empty(n_x)
    for i in range(0, n_x, 500):
        dens[i : i + 500] = _gauss(x[i : i + 500, None] - t[None, :], s.sigma) @ ft
    return x, dens


def _normalisation(truth: Truth, s: _Setup) -> float:
    if truth is Truth.ENTITY:
        x, dens = _smeared_entity_table(s)
        return _integrate(dens, x)
    grid = np.linspace(0.0, 1.5 * s.Q, GRID)
    return _integrate(_raw(truth, grid, s), grid)


def _domain_mev(truth: Truth, s: _Setup) -> tuple[float, float]:
    if truth is Truth.ENTITY:
        return (WINDOW[0] * s.Q, s.Q)  # public-window start up to endpoint Q
    return (s.Q - 3 * s.sigma, s.Q + 3 * s.sigma)  # resolution window around Q


def _make_truth_law(truth: Truth, s: _Setup):
    norm = _normalisation(truth, s)
    if truth is Truth.ENTITY:
        # Detector-seen density: raw spectrum convolved with the public resolution (as the events).
        xt, dt = _smeared_entity_table(s)

        def law_entity(T):
            T = np.asarray(T, dtype=float)
            return np.interp(T * s.scale, xt, dt, left=0.0, right=0.0) / norm * s.scale

        return law_entity

    def law(T):
        T = np.asarray(T, dtype=float)
        # density per public unit: f_U = f_MeV * (dT_MeV / dT_U) = f_MeV * scale
        return _raw(truth, T * s.scale, s) / norm * s.scale

    return law


def _sample_truth_mev(truth: Truth, s: _Setup, rng, n: int, thickness: float = 1.0) -> np.ndarray:
    lo, hi = WINDOW[0] * s.Q, WINDOW[1] * s.Q
    if truth is Truth.ENTITY:
        # Full support: events outside the window are smeared in and truncated after smearing.
        lo, hi = 0.0, s.Q
    grid = np.linspace(lo, hi, GRID)
    f = _raw(truth, grid, s, thickness)
    cdf = np.concatenate([[0.0], np.cumsum((f[1:] + f[:-1]) * np.diff(grid) / 2.0)])
    cdf /= cdf[-1]
    return np.interp(rng.random(n), cdf, grid)


def _events(truth: Truth, s: _Setup, rng, n: int = N_EVENTS) -> dict[str, np.ndarray]:
    lo, hi = WINDOW[0] * s.Q, WINDOW[1] * s.Q
    kept_T, kept_true = [], []
    got = 0
    while got < n:
        T_true = _sample_truth_mev(truth, s, rng, 2 * n)
        if truth is Truth.ENTITY:
            T_obs = T_true + rng.normal(0.0, s.sigma, size=T_true.shape)
        else:
            T_obs = T_true  # resolution is already part of the line shape
        ok = (T_obs >= lo) & (T_obs <= hi)
        kept_T.append(T_obs[ok])
        kept_true.append(T_true[ok])
        got += int(ok.sum())
    T_obs = np.concatenate(kept_T)[:n]
    T_true = np.concatenate(kept_true)[:n]

    # Two-body kinematics for the recoil, in the electron direction frame.
    p_e = np.sqrt(np.maximum((T_true + s.m_e) ** 2 - s.m_e**2, 0.0))
    if truth is Truth.NO_ENTITY:
        p_r = p_e
        angle = np.full(n, math.pi)
    else:
        dq = s.Q - T_true
        p_X = np.sqrt(np.maximum(dq**2 - s.m_X**2, 0.0)) if s.stage is Stage.COUNTERFACTUAL else dq
        phi = rng.uniform(0.0, 2 * math.pi, size=n)
        Sx = p_e + p_X * np.cos(phi)
        Sy = p_X * np.sin(phi)
        p_r = np.hypot(Sx, Sy)
        angle = np.arccos(np.clip(-Sx / np.maximum(p_r, 1e-12), -1.0, 1.0))

    E_r = np.sqrt(p_r**2 + s.M_d**2) - s.M_d
    E_r_obs = E_r * (1.0 + s.noise * rng.normal(size=n))
    angle_obs = np.degrees(angle) + 40.0 * s.noise * rng.normal(size=n)
    return {"T": T_obs, "E_r": E_r_obs, "angle": angle_obs}


def _fmt(x: float) -> str:
    return f"{x:.9g}"


def _events_csv(ev: dict[str, np.ndarray], s: _Setup) -> str:
    lines = ["kinetic_energy,recoil_energy,recoil_angle_deg"]
    for T, Er, ang in zip(ev["T"], ev["E_r"], ev["angle"]):
        lines.append(f"{_fmt(T / s.scale)},{_fmt(Er / s.scale)},{_fmt(ang)}")
    return "\n".join(lines) + "\n"


def _masses_csv(s: _Setup) -> str:
    n = s.names
    rows = [
        ("name", "mass", "unit"),
        (n["parent"], s.M_p / s.scale, n["unit"]),
        (n["daughter"], s.M_d / s.scale, n["unit"]),
        (n["light"], s.m_e / s.scale, n["unit"]),
    ]
    lines = [",".join(map(str, rows[0]))]
    lines += [f"{r[0]},{r[1]:.12g},{r[2]}" for r in rows[1:]]
    return "\n".join(lines) + "\n"


def _task_md(s: _Setup) -> str:
    n = s.names
    Q = s.Q / s.scale
    title = "energy spectrum of a decay" if s.stage is Stage.SYNTHETIC else "beta-decay energy spectrum"
    return f"""# Task: {title}

A {n["parent"]} at rest decays into a {n["daughter"]} and an {n["light"]}.
For a two-body decay with energy and momentum conservation, the prediction is that the
{n["light"]} kinetic energy is monoenergetic at the decay energy Q, where
Q = M(parent) - M(daughter) - rest energy of the {n["light"]} (about {_fmt(Q)} {n["unit"]}).

The measured spectrum of {n["light"]} kinetic energies, with the recoil data of each event,
is in `events.csv`. Masses are in `masses.csv`. Detector details are in `detector.md`.

Write a Python module `law.py` that defines:

- `DOMAIN = {{"energy_range": (lo, hi)}}`: the kinetic-energy interval, in {n["unit"]}, over
  which your law describes the measured spectrum.
- `law(T: np.ndarray) -> np.ndarray`: the detector-seen energy density of the {n["light"]} at
  kinetic energies `T` (in {n["unit"]}). It must accept a numpy array of any shape and return a
  non-negative array of the same shape.
- `MECHANISM`: a module-level dict with your hypothesis about the cause of the observed spectrum.
  Its `kind` must be exactly one of:
  - `"hidden_carriers"`, with keys `n_carriers` (integer: how many unobserved light particles share
    the decay energy) and `mass` (rest energy of each such particle, in {n["unit"]});
  - `"detector_response"`, with no other keys (the observed shape is produced by the measurement
    apparatus, not by unobserved particles);
  - `"other"`, with key `description` (free text).

`MECHANISM` is checked automatically. The points at which `law` is scored include energies outside
the recorded window (below it and above it), so `law` must be defined there too.
"""


def _detector_md(s: _Setup) -> str:
    n = s.names
    u = n["unit"]
    lo, hi = WINDOW[0] * s.Q / s.scale, WINDOW[1] * s.Q / s.scale
    lines = [
        "# Detector and measurement notes",
        "",
        f"- Kinetic energy of the {n['light']}: recorded in {u}.",
        f"- Energy resolution: Gaussian, 1 sigma = {_fmt(s.sigma / s.scale)} {u}.",
        f"- Recorded kinetic-energy window: {_fmt(lo)} to {_fmt(hi)} {u}.",
        f"- Recoil energy of the {n['daughter']}: recorded in {u}, relative resolution {_fmt(s.noise)}.",
        f"- Recoil angle: angle in degrees between the {n['daughter']} direction and the "
        f"{n['light']} direction, resolution {_fmt(40.0 * s.noise)} degrees (1 sigma).",
        f"- Rest energy of the {n['light']}: {_fmt(s.m_e / s.scale)} {u}.",
        f"- Events recorded: {N_EVENTS}.",
    ]
    if s.stage in (Stage.HISTORICAL, Stage.OBFUSCATED):
        lines.append(f"- Charge of the {n['daughter']}: Z = {s.Z}.")
        lines.append("- Fine-structure constant: alpha = 1/137.036.")
    return "\n".join(lines) + "\n"


def _eval_points(truth: Truth, s: _Setup, n: int) -> EvalPoints:
    # in_range: the public recorded window. extrapolation: the held-out bands below and above it,
    # which are neither in events.csv nor reachable by any query.
    q, scale = s.Q, s.scale
    in_range = np.linspace(WINDOW[0] * q, WINDOW[1] * q, n) / scale
    low = np.linspace(EXT_BAND[0] * q, WINDOW[0] * q, n // 4, endpoint=False) / scale
    high = np.linspace(WINDOW[1] * q, EXT_BAND[1] * q, n // 4 + 1)[1:] / scale
    return EvalPoints(in_range=in_range, extrapolation=np.concatenate([low, high]))


def _true_mechanism(truth: Truth, s: _Setup) -> dict:
    """Ground-truth mechanism in public energy units."""
    if truth is Truth.NO_ENTITY:
        return {"kind": "detector_response"}
    tol = {"mass_abs": 0.1 * float(s.Q / s.scale)}  # 0.1 Q in public energy units
    if s.stage is Stage.SYNTHETIC:
        return {"kind": "hidden_carriers", "n_carriers": s.k, "mass": 0.0, "tolerance": tol}
    return {"kind": "hidden_carriers", "n_carriers": 1, "mass": float(s.m_X / s.scale), "tolerance": tol}


def build_beta(cfg: VariantConfig) -> TaskBundle:
    s = _setup(cfg)
    truth = cfg.truth
    rng = np.random.default_rng([cfg.seed, cfg.mode, _STAGE_IDX[cfg.stage], _TRUTH_IDX[truth]])
    ev = _events(truth, s, rng)
    lo, hi = _domain_mev(truth, s)

    public_files = {
        "task.md": _task_md(s),
        "events.csv": _events_csv(ev, s),
        "masses.csv": _masses_csv(s),
        "detector.md": _detector_md(s),
    }
    return TaskBundle(
        public_files=public_files,
        truth_law=_make_truth_law(truth, s),
        eval_points=lambda: _eval_points(truth, s, cfg.n_points),
        true_domain={"energy_range": (lo / s.scale, hi / s.scale)},
        entity=truth is Truth.ENTITY,
        rubric_id=f"beta-{truth.value}-{cfg.stage.value}",
        discriminating_queries=frozenset({"recoil_correlation", "target_thickness_scan"}),
        oracle_family=partial(beta_oracle, truth=truth, stage=cfg.stage),
        true_mechanism=_true_mechanism(truth, s),
    )


# ---------------------------------------------------------------------------
# Mode-2 query API. Results are generated from the same process as the public
# files, with a fresh sub-seed per call (cfg, query tag, call index).
# ---------------------------------------------------------------------------

_QUERY_TAG = {"events": 101, "recoil_correlation": 102, "target_thickness_scan": 103}
THICKNESS_LEVELS = (0.5, 1.0, 2.0)  # relative to the nominal target thickness
SCAN_EVENTS = N_EVENTS
SCAN_BINS = 10
EVENT_COLUMNS = ["kinetic_energy", "recoil_energy", "recoil_angle_deg"]


def _query_rng(cfg: VariantConfig, tag: int, call: int, sub: int = 0):
    return np.random.default_rng(
        [cfg.seed, cfg.mode, _STAGE_IDX[cfg.stage], _TRUTH_IDX[cfg.truth], tag, call, sub]
    )


def row_count(query_type: str, args: dict) -> int | None:
    """Rows of one answer (validates the per-call size cap); None for queries without a row count."""
    from abductbench.tasks._query_util import int_arg

    if query_type == "events":
        return int_arg(args, "n", 100, 1, 500)
    return None


def query_help(cfg: VariantConfig) -> str:
    """Lines for task.md describing the beta query types (no truth-revealing content)."""
    light = _setup(cfg).names["light"]
    return "\n".join(
        [
            "- `events`: optional `n` (integer 1 to 500, default 100): "
            f"new events from the same measurement, columns {', '.join(EVENT_COLUMNS)} on the same scale as `events.csv`.",
            "- `recoil_correlation`: optional `n` (integer 1 to 500, default 200): statistics "
            f"comparing {light} and recoil momenta for `n` new events, plus a sample of 10 rows.",
            "- `target_thickness_scan`: no arguments: energy spectrum summaries at three "
            "target thicknesses.",
        ]
    )


def query(cfg: VariantConfig, query_type: str, args: dict) -> dict:
    from abductbench.tasks._query_util import call_index, int_arg

    s = _setup(cfg)
    call = call_index(args)
    scale = s.scale

    if query_type == "events":
        n = int_arg(args, "n", 100, 1, 500)
        ev = _events(cfg.truth, s, _query_rng(cfg, _QUERY_TAG[query_type], call), n)
        rows = [[float(T / scale), float(Er / scale), float(a)] for T, Er, a in zip(ev["T"], ev["E_r"], ev["angle"])]
        return {"columns": EVENT_COLUMNS, "rows": rows}

    if query_type == "recoil_correlation":
        n = int_arg(args, "n", 200, 1, 500)
        ev = _events(cfg.truth, s, _query_rng(cfg, _QUERY_TAG[query_type], call), n)
        p_e = np.sqrt(np.maximum(ev["T"] * (ev["T"] + 2.0 * s.m_e), 0.0))
        p_r = np.sqrt(np.maximum(ev["E_r"] * (ev["E_r"] + 2.0 * s.M_d), 0.0))
        mismatch = (p_r - p_e) / np.maximum(p_e, 1e-12)
        k = min(10, n)
        rows = [[float(T / scale), float(Er / scale), float(a)] for T, Er, a in zip(ev["T"][:k], ev["E_r"][:k], ev["angle"][:k])]
        return {
            "n_events": n,
            "mismatch_mean": float(np.mean(mismatch)),
            "mismatch_std": float(np.std(mismatch)),
            "mismatch_rms": float(np.sqrt(np.mean(mismatch**2))),
            "columns": EVENT_COLUMNS,
            "sample_rows": rows,
        }

    if query_type == "target_thickness_scan":
        return _thickness_scan(cfg, s, call)

    raise ValueError(f"unknown query type {query_type!r}")


def _thickness_scan(cfg: VariantConfig, s: _Setup, call: int) -> dict:
    lo, hi = WINDOW[0] * s.Q, WINDOW[1] * s.Q
    scale = s.scale
    edges_mev = np.linspace(lo, hi, SCAN_BINS + 1)
    summaries = []
    for th in THICKNESS_LEVELS:
        # Independent measurement noise per thickness; the underlying shape is shared.
        rng = _query_rng(cfg, _QUERY_TAG["target_thickness_scan"], call, sub=int(round(th * 10)))
        T_true = _sample_truth_mev(cfg.truth, s, rng, SCAN_EVENTS, thickness=th)
        if cfg.truth is Truth.ENTITY:
            T_obs = T_true + rng.normal(0.0, s.sigma, size=T_true.shape)
        else:
            T_obs = T_true  # resolution is already part of the line shape
        inside = (T_obs >= lo) & (T_obs <= hi)
        kept = T_obs[inside]
        counts, _ = np.histogram(kept, bins=edges_mev)
        summaries.append(
            {
                "thickness": float(th),
                "n_events": int(SCAN_EVENTS),
                "n_in_window": int(inside.sum()),
                "mean": float(np.mean(kept) / scale) if kept.size else None,
                "std": float(np.std(kept) / scale) if kept.size else None,
                "line_fraction": float(np.mean(np.abs(T_obs - s.Q) <= 3 * s.sigma)),
                "tail_fraction": float(np.mean(T_obs < s.Q - 3 * s.sigma)),
                "histogram": [int(c) for c in counts],
            }
        )
    return {"units": s.names["unit"], "bin_edges": [float(e / scale) for e in edges_mev], "summaries": summaries}
