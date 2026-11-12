"""Neptune/Vulcan-style orbit task generator (family "orbit").

Planar N-body system: a central star and four known planets, plus an optional
outer body (state index PERT) that is massless in T0 and in the no_entity truth.
Integration runs in public units: distance AU, time unit ``tunit``, GM in
AU^3 per tunit^2.

- entity: the optional outer body has mass and perturbs the outer target planet.
- no_entity: an extra central radial force k / r^n acts on every planet; the
  target is the innermost planet, whose orbit precesses secularly.

Observables are heliocentric longitudes; the residual is observed minus T0 in
arcseconds. ``t0_model.py`` is generated from the numpy core of this module
(``_state_from_elements``, ``_initial_state``, ``_accel``, ``_integrate``,
``_longitudes``), so the public prediction and the truth law share one integrator.
"""

from __future__ import annotations

import inspect
import math
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicSpline

from abductbench.config import EvalPoints, Stage, TaskBundle, Truth, VariantConfig

ARCSEC_PER_RAD = 180.0 * 3600.0 / math.pi
DT_YR = 0.002  # Yoshida-4 step in years; relative energy error < 1e-6 over the window
TIME_YR = 10.0  # public data window in years
EXT_YR = 15.0  # integration horizon (extrapolation) in years
N_OBS = 40
PERT = 5  # state index of the optional outer body
_TARGET_PLANET = {Truth.ENTITY: 3, Truth.NO_ENTITY: 0}  # target planet, index 0..3

_STAGE_IDX = {s: i for i, s in enumerate(Stage)}
_TRUTH_IDX = {t: i for i, t in enumerate(Truth)}

# Known planets, inner to outer: semi-major axis (AU), eccentricity, mass / solar mass.
_PLANETS = (
    (0.387098, 0.205630, 1.6601e-7),
    (0.723332, 0.006772, 2.4478e-6),
    (1.000003, 0.016710, 3.0035e-6),
    (19.19126, 0.047168, 4.3627e-5),
)
_HIDDEN_A = 24.0  # AU, optional outer body (base value, scaled by stage and seed)
_HIDDEN_E = 0.01
_HIDDEN_Q = 6.0e-4  # mass / solar mass, base value
_K_BASE = 8.0e-6  # AU^(n+1) / yr^2, correction strength for stage (a)


@dataclass(frozen=True)
class _StageSpec:
    tick_yr: float  # years per public time unit
    tunit: str
    mu_star_yr: float  # GM of the star in AU^3 / yr^2
    star: str
    planets: tuple[str, str, str, str]
    hidden_mass: float  # multiplier on the base optional-body mass
    hidden_dist: float  # multiplier on the base optional-body distance
    n_corr: float  # exponent of the correction force k / r^n
    k_corr: float  # multiplier on _K_BASE


_REAL = ("Mercury", "Venus", "Earth", "Uranus")
_SPECS = {
    Stage.HISTORICAL: _StageSpec(1.0, "year", 4 * math.pi**2, "Sun", _REAL, 1.0, 1.0, 3.0, 1.0),
    Stage.OBFUSCATED: _StageSpec(0.5, "tick", 4 * math.pi**2, "primary",
                                 ("body 1", "body 2", "body 3", "body 4"), 1.0, 1.0, 3.0, 1.0),
    Stage.COUNTERFACTUAL: _StageSpec(1.0, "year", 4 * math.pi**2, "Sun", _REAL, 1.6, 1.1, 2.5, 0.6),
    Stage.SYNTHETIC: _StageSpec(1.0, "cycle", 9.0, "Vael",
                                ("Kessa", "Doru", "Ilin", "Brenn"), 0.7, 1.25, 4.0, 0.3),
}


# ---------------------------------------------------------------------------
# Numpy core. Functions copied into t0_model.py: keep them self-contained.
# ---------------------------------------------------------------------------


def _state_from_elements(gm, a, e, varpi, L0):
    """Planar heliocentric position and velocity from elements at epoch (angles in radians)."""
    M = (L0 - varpi) % (2.0 * math.pi)
    E = M + e * math.sin(M)
    for _ in range(100):
        dE = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-15:
            break
    x = a * (math.cos(E) - e)
    y = a * math.sqrt(1.0 - e * e) * math.sin(E)
    n = math.sqrt(gm / a**3)
    r = a * (1.0 - e * math.cos(E))
    vx = -a * a * n * math.sin(E) / r
    vy = a * a * n * math.sqrt(1.0 - e * e) * math.cos(E) / r
    c, s = math.cos(varpi), math.sin(varpi)
    return np.array([c * x - s * y, s * x + c * y]), np.array([c * vx - s * vy, s * vx + c * vy])


def _initial_state(mu, elements):
    """Barycentric (x0, v0), each (N, 2), from heliocentric elements of bodies 1..N-1."""
    N = len(mu)
    X = np.zeros((N, 2))
    V = np.zeros((N, 2))
    for i in range(1, N):
        X[i], V[i] = _state_from_elements(mu[0] + mu[i], *elements[i - 1])
    M = mu.sum()
    X -= (mu[:, None] * X).sum(0) / M
    V -= (mu[:, None] * V).sum(0) / M
    return X, V


def _accel(X, mu, k, n):
    """Accelerations for a batch X (B, N, 2): pairwise gravity plus k / r^n about body 0."""
    N = X.shape[1]
    idx = np.arange(N)
    d = X[:, None, :, :] - X[:, :, None, :]  # d[b, i, j] = x_j - x_i
    r2 = np.einsum("bijk,bijk->bij", d, d)
    r2[:, idx, idx] = 1.0
    w = mu[:, None, :] * r2**-1.5
    w[:, idx, idx] = 0.0
    A = np.einsum("bij,bijk->bik", w, d)
    dr = X - X[:, :1, :]
    rr = np.sqrt(np.einsum("bik,bik->bi", dr, dr))
    rr[:, 0] = 1.0
    ext = -k[:, None, None] * dr * rr[..., None] ** (-(n + 1.0))
    ext[:, 0] = 0.0
    A = A + ext
    A[:, 0, :] -= np.einsum("bi,bik->bk", mu[:, 1:], ext[:, 1:]) / mu[:, :1]
    return A


def _integrate(mu, x0, v0, k, n, dt, n_steps):
    """Yoshida 4th-order symplectic integrator. Returns X, V of shape (n_steps + 1, B, N, 2)."""
    w1 = 1.0 / (2.0 - 2.0 ** (1.0 / 3.0))
    w0 = -(2.0 ** (1.0 / 3.0)) / (2.0 - 2.0 ** (1.0 / 3.0))
    cs = (w1 / 2.0, (w0 + w1) / 2.0, (w0 + w1) / 2.0, w1 / 2.0)
    ds = (w1, w0, w1)
    X = np.array(x0, dtype=float)
    V = np.array(v0, dtype=float)
    Xs = np.empty((n_steps + 1,) + X.shape)
    Vs = np.empty_like(Xs)
    Xs[0], Vs[0] = X, V
    for s in range(1, n_steps + 1):
        for c, dd in zip(cs[:3], ds):
            X = X + c * dt * V
            V = V + dd * dt * _accel(X, mu, k, n)
        X = X + cs[3] * dt * V
        Xs[s], Vs[s] = X, V
    return Xs, Vs


def _longitudes(X):
    """Heliocentric longitudes (radians) of bodies 1..N-1, from X of shape (S, B, N, 2)."""
    dx = X[..., 1:, :] - X[..., :1, :]
    return np.arctan2(dx[..., 1], dx[..., 0])


# Helpers below are not part of the public T0 model.


def _residuals(lam):
    """Wrapped longitude differences (arcsec) of batch rows 1.. against row 0: shape (S, B-1, N-1)."""
    d = lam[:, 1:, :] - lam[:, :1, :]
    return np.arctan2(np.sin(d), np.cos(d)) * ARCSEC_PER_RAD


def _energy(mu, k, n, X, V):
    """Total energy, shape (S, B): kinetic, pairwise gravity, and the k / r^n potential."""
    T = 0.5 * np.einsum("bi,sbik,sbik->sb", mu, V, V)
    N = X.shape[2]
    idx = np.arange(N)
    d = X[:, :, None, :, :] - X[:, :, :, None, :]
    r = np.sqrt(np.einsum("sbijk,sbijk->sbij", d, d))
    r[..., idx, idx] = np.inf
    U = -0.5 * np.einsum("bi,sbij,bj->sb", mu, 1.0 / r, mu)
    dr = X - X[:, :, :1, :]
    rr = np.sqrt(np.einsum("sbik,sbik->sbi", dr, dr))
    rr[..., 0] = 1.0
    Uext = -np.einsum("bi,sbi->sb", mu[:, 1:], k[None, :, None] / ((n - 1.0) * rr[..., 1:] ** (n - 1.0)))
    return T + U + Uext


@dataclass(frozen=True)
class _Universe:
    spec: _StageSpec
    names: tuple[str, ...]  # star, four planets
    mu_base: np.ndarray  # (6,) public GM; index PERT is the optional outer body
    elements: np.ndarray  # (5, 4): a, e, varpi, L0 of bodies 1..5, public units
    k: float  # correction strength, public units
    n: float
    dt: float  # public time per step
    tick: float  # years per public time unit
    target_planet: int  # index 0..3 into the four planets

    def n_steps(self, t_yr: float) -> int:
        return int(round(t_yr / DT_YR))


def _universe(cfg: VariantConfig) -> _Universe:
    spec = _SPECS[cfg.stage]
    rng = np.random.default_rng([cfg.seed, cfg.mode])
    phases = rng.uniform(0.0, 2.0 * math.pi, size=(5, 2))
    k_jit = rng.uniform(0.8, 1.2)
    m_jit = rng.uniform(0.8, 1.25)
    a_jit = rng.uniform(0.95, 1.05)

    tick = spec.tick_yr
    mu_star = spec.mu_star_yr * tick**2
    hidden_a = _HIDDEN_A * spec.hidden_dist * a_jit
    hidden_q = _HIDDEN_Q * spec.hidden_mass * m_jit
    mu = [mu_star] + [spec.mu_star_yr * q * tick**2 for _, _, q in _PLANETS]
    mu.append(spec.mu_star_yr * hidden_q * tick**2)
    el = [[a, e, phases[i, 0], phases[i, 1]] for i, (a, e, _) in enumerate(_PLANETS)]
    el.append([hidden_a, _HIDDEN_E, phases[4, 0], phases[4, 1]])
    return _Universe(
        spec=spec,
        names=(spec.star,) + spec.planets,
        mu_base=np.array(mu),
        elements=np.array(el),
        k=_K_BASE * spec.k_corr * k_jit * tick**2,
        n=spec.n_corr,
        dt=DT_YR / tick,
        tick=tick,
        target_planet=_TARGET_PLANET[cfg.truth],
    )


def _truth_batch(u: _Universe, truth: Truth):
    """Batch rows: row 0 is T0 (no optional body, no correction); row 1 is the truth."""
    mu = np.stack([u.mu_base.copy(), u.mu_base.copy()])
    mu[0, PERT] = 0.0
    k = np.zeros(2)
    if truth is Truth.NO_ENTITY:
        mu[1, PERT] = 0.0
        k[1] = u.k
    return mu, k


def _t0_source(u: _Universe) -> str:
    funcs = (_state_from_elements, _initial_state, _accel, _integrate, _longitudes)
    core = "\n\n".join(inspect.getsource(f) for f in funcs)
    consts = (
        f"TUNIT = {u.spec.tunit!r}\n"
        f"DT = {u.dt!r}\n"
        f"STAR = {u.names[0]!r}\n"
        f"PLANETS = {list(u.names[1:])!r}\n"
        f"GM_STAR = {float(u.mu_base[0])!r}\n"
        f"GM_PLANETS = {[float(x) for x in u.mu_base[1:5]]!r}\n"
        f"ELEMENTS = {[[float(x) for x in row] for row in u.elements[:4]]!r}\n"
    )
    head = '''"""Newtonian T0 predictor for the orbit task (numpy and scipy only).

predict_longitudes(t) integrates the star and the known planets listed in
known_bodies.csv from their elements at t = 0. It returns, for each planet, the
predicted heliocentric longitude in degrees (0 to 360) at the times t. Time is
in the public time unit (TUNIT), distance in AU, GM in AU^3 per TUNIT^2.
"""

import math

import numpy as np
from scipy.interpolate import CubicSpline

'''
    tail = '''

def predict_longitudes(t):
    t = np.asarray(t, dtype=float)
    n_steps = max(1, int(math.ceil(float(np.max(t)) / DT)))
    mu = np.array([[GM_STAR] + GM_PLANETS])
    x0, v0 = _initial_state(mu[0], np.array(ELEMENTS))
    X, _ = _integrate(mu, x0[None], v0[None], np.zeros(1), 3.0, DT, n_steps)
    lam = np.unwrap(_longitudes(X)[:, 0, :], axis=0)
    grid = np.arange(n_steps + 1) * DT
    return {name: np.degrees(CubicSpline(grid, lam[:, j])(t)) % 360.0 for j, name in enumerate(PLANETS)}
'''
    return head + consts + "\n\n" + core + tail


def _eval_points(u: _Universe, n: int) -> EvalPoints:
    t_end = TIME_YR / u.tick
    in_range = np.linspace(0.0, t_end, n)
    extrapolation = np.linspace(t_end, EXT_YR / u.tick, n // 4 + 1)[1:]
    return EvalPoints(in_range=in_range, extrapolation=extrapolation)


def _fmt_deg(x: float) -> str:
    return f"{x:.9f}"


def build_orbit(cfg: VariantConfig) -> TaskBundle:
    u = _universe(cfg)
    truth = cfg.truth
    tgt = u.target_planet
    others = [j for j in range(4) if j != tgt]
    rng = np.random.default_rng([cfg.seed, cfg.mode, _STAGE_IDX[cfg.stage], _TRUTH_IDX[truth]])
    noise = rng.normal(0.0, cfg.noise, size=(4, N_OBS))  # arcsec, one row per planet

    # One batched integration: row 0 is T0, row 1 is the truth.
    mu, k = _truth_batch(u, truth)
    x0, v0 = _initial_state(u.mu_base, u.elements)
    n_steps = u.n_steps(EXT_YR)
    X, _ = _integrate(mu, np.stack([x0, x0]), np.stack([v0, v0]), k, u.n, u.dt, n_steps)
    lam = _longitudes(X)  # (S, 2, 4)
    res = _residuals(lam)[:, 0, :]  # (S, 4) arcsec
    lam0 = np.unwrap(lam[:, 0, :], axis=0)
    grid = np.arange(n_steps + 1) * u.dt
    res_spl = [CubicSpline(grid, res[:, j]) for j in range(4)]
    lam0_spl = [CubicSpline(grid, lam0[:, j]) for j in range(4)]

    t_obs = np.linspace(TIME_YR / N_OBS, TIME_YR, N_OBS) / u.tick
    obs_lon = lam0_spl[tgt](t_obs) + res_spl[tgt](t_obs) / ARCSEC_PER_RAD + noise[tgt] / ARCSEC_PER_RAD
    target_csv = ["body,time,longitude_deg"]
    target_csv += [
        f"{u.names[1 + tgt]},{t:.10g},{_fmt_deg(float(np.degrees(l) % 360.0))}" for t, l in zip(t_obs, obs_lon)
    ]
    other_csv = ["body,time,residual_arcsec"]
    for j in others:
        obs_res = res_spl[j](t_obs) + noise[j]
        other_csv += [f"{u.names[1 + j]},{t:.10g},{r:.6f}" for t, r in zip(t_obs, obs_res)]

    known_csv = ["name,gm,semi_major_axis,eccentricity,longitude_of_perihelion_deg,mean_longitude_epoch_deg"]
    known_csv.append(f"{u.names[0]},{float(u.mu_base[0]):.12g},,,,")
    for j in range(4):
        a, e, varpi, L0 = u.elements[j]
        known_csv.append(
            f"{u.names[1 + j]},{float(u.mu_base[1 + j]):.12g},{a:.9g},{e:.9g},"
            f"{math.degrees(varpi) % 360.0:.9f},{math.degrees(L0) % 360.0:.9f}"
        )

    target_name = u.names[1 + tgt]
    a_t, e_t = u.elements[tgt][0], u.elements[tgt][1]
    radius_range = (a_t * (1.0 - e_t), a_t * (1.0 + e_t))
    t_window = (0.0, TIME_YR / u.tick)
    task_md = _task_md(u, target_name, t_window, radius_range)

    public_files = {
        "task.md": task_md,
        "target_positions.csv": "\n".join(target_csv) + "\n",
        "other_residuals.csv": "\n".join(other_csv) + "\n",
        "known_bodies.csv": "\n".join(known_csv) + "\n",
        "t0_model.py": _t0_source(u),
    }

    law_spl = res_spl[tgt]

    def truth_law(t):
        return law_spl(np.asarray(t, dtype=float))

    return TaskBundle(
        public_files=public_files,
        truth_law=truth_law,
        eval_points=lambda: _eval_points(u, cfg.n_points),
        true_domain={"time_range": t_window, "radius_range": radius_range},
        entity=truth is Truth.ENTITY,
        rubric_id=f"orbit-{truth.value}-{cfg.stage.value}",
        discriminating_queries=frozenset({"search_region", "other_body_residuals"}),
    )


def _task_md(u: _Universe, target: str, t_window, radius_range) -> str:
    tunit = u.spec.tunit
    star = u.names[0]
    planets = ", ".join(u.names[1:])
    return f"""# Task: longitude residuals of a target body

A planar Newtonian system: a central star ({star}) and four known bodies ({planets}).
Positions are heliocentric ecliptic longitudes. Units: time in {tunit}; distance in AU;
GM (gravitational parameter) in AU^3 per {tunit}^2.

The predicted motion, T0, is Newtonian gravity between the star and the known bodies in
`known_bodies.csv`, with the orbital elements given there at epoch t = 0. `t0_model.py`
implements it: `predict_longitudes(t)` returns the predicted heliocentric longitude in
degrees, for each planet, at the times `t` (a numpy array in {tunit}).

The observed longitudes of the target body **{target}** (`target_positions.csv`) deviate
from the T0 prediction. Residuals of the other known bodies relative to T0 are in
`other_residuals.csv`, in arcseconds (observed minus predicted, wrapped to +/-180 degrees).

Files:
- `known_bodies.csv`: star and planets, GM, and elements at epoch.
- `target_positions.csv`: body, time, observed longitude (degrees), for the target.
- `other_residuals.csv`: body, time, residual (arcseconds), for the other planets.
- `t0_model.py`: the T0 predictor (numpy and scipy).

Write a Python module `law.py` that defines:

- `DOMAIN = {{"time_range": (lo, hi), "radius_range": (lo, hi)}}`: the time interval, in {tunit},
  and the range of heliocentric distances, in AU, over which your law describes the residuals
  of {target}.
- `law(t: np.ndarray) -> np.ndarray`: the longitude residual of {target} relative to T0, in
  arcseconds, at times `t` (in {tunit}). It accepts an array of any shape and returns an array
  of the same shape.
"""
