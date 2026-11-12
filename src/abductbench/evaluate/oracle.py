"""Reference solver ("oracle") for contamination control.

Each stage gets an oracle that knows the functional family of its true law and
fits only the constants that are not given in the public files. The oracle
receives ``bundle.public_files`` and the evaluation points; it never calls
``bundle.truth_law`` and never reads generator parameters. Its family structure
(which shape the stage uses)
is passed in by the generator as keyword arguments at construction time.

Two entry points:

- ``beta_oracle`` / ``orbit_oracle``: the ``oracle_family(public_files, eval_x)``
  callables stored on ``TaskBundle.oracle_family``.
- ``oracle_scores(cfg)`` and ``normalize(result, oracle)``: scoring with the same
  metric as the law evaluator, and agent/oracle ratios.

Beta: the spectrum is public up to the constants fitted below. Q, the detector
resolution and the window come from the public files. Stage c fits the hidden
mass m_X and stage d the exponent k of the phase-space factor, by maximum
likelihood on the public kinetic energies, after applying the public Gaussian
resolution for the entity truth. The no-entity line shape is fitted (peak
weight fixed at 1, tail/shelf weights and tail width free) to the same events.

Orbit: the T0 integrator is the public ``t0_model.py``, executed as source. The
entity oracle fits the outer body (mass ratio, semi-major axis, phase) with a
batched grid search and Levenberg-Marquardt. The no-entity oracle fits the
correction amplitude and the exponent n (bounded 1.5 to 5, two starts) from the public data;
it is given no stage constant.
"""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass
from functools import partial

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares, minimize, minimize_scalar

from abductbench.config import Stage, Truth, VariantConfig
from abductbench.evaluate.law_eval import LawResult, score_predictions

# Floor on the oracle nrmse used to normalise agent scores. It is tied to finite-sample noise:
# with ~1000 events the best achievable nrmse is a few 1e-3 to 1e-2, so an oracle that matches
# the generating law almost exactly must not turn tiny agent errors into huge ratios.
NOISE_FLOOR = 1e-2
ALPHA = 1.0 / 137.036
FIT_MAX_NFEV = 100
N_BOUNDS = (1.5, 5.0)  # bounds on the fitted correction-force exponent
N_STARTS = (2.5, 4.0)  # restarts for the exponent
ARCSEC_PER_RAD = 180.0 * 3600.0 / math.pi


@dataclass(frozen=True)
class OracleScores:
    nrmse_in: float
    nrmse_extrap: float


@dataclass(frozen=True)
class NormalizedScores:
    rel_in: float | None
    rel_extrap: float | None


def normalize(result: LawResult, oracle: OracleScores) -> NormalizedScores:
    """Agent NRMSE divided by oracle NRMSE, with the oracle floored at NOISE_FLOOR."""
    if result.status != "ok" or result.nrmse_in is None or result.nrmse_extrap is None:
        return NormalizedScores(rel_in=None, rel_extrap=None)
    return NormalizedScores(
        rel_in=result.nrmse_in / max(oracle.nrmse_in, NOISE_FLOOR),
        rel_extrap=result.nrmse_extrap / max(oracle.nrmse_extrap, NOISE_FLOOR),
    )


def oracle_scores(cfg: VariantConfig) -> OracleScores:
    # Imported here: abductbench.tasks imports this module's family solvers, so a
    # top-level import would be circular.
    from abductbench.tasks import build_task

    bundle = build_task(cfg)
    ep = bundle.eval_points()
    n_in = len(ep.in_range)
    x = np.concatenate([np.asarray(ep.in_range, float), np.asarray(ep.extrapolation, float)])
    pred = np.asarray(bundle.oracle_family(bundle.public_files, x), dtype=float)
    nrmse_in, nrmse_ex = score_predictions(bundle, pred[:n_in], pred[n_in:])
    return OracleScores(nrmse_in=nrmse_in, nrmse_extrap=nrmse_ex)


def _text(value: str | bytes) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _csv_rows(text: str) -> list[list[str]]:
    return [row for row in csv.reader(io.StringIO(text)) if row]


# ---------------------------------------------------------------------------
# Beta decay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _BetaPublic:
    Q: float
    m_e: float
    sigma: float
    lo: float
    hi: float
    Z: int | None
    T: np.ndarray  # observed kinetic energies, public units


def _beta_public(files) -> _BetaPublic:
    masses = _csv_rows(_text(files["masses.csv"]))[1:]  # parent, daughter, light
    M_p, M_d, m_e = (float(r[1]) for r in masses[:3])
    det = _text(files["detector.md"])
    sigma = float(re.search(r"1 sigma = ([-+0-9.eE]+)", det).group(1))
    win = re.search(r"window: ([-+0-9.eE]+) to ([-+0-9.eE]+)", det)
    z = re.search(r"Z = (\d+)", det)
    events = _csv_rows(_text(files["events.csv"]))[1:]
    return _BetaPublic(
        Q=M_p - M_d - m_e,
        m_e=m_e,
        sigma=sigma,
        lo=float(win.group(1)),
        hi=float(win.group(2)),
        Z=int(z.group(1)) if z else None,
        T=np.array([float(r[0]) for r in events]),
    )


def _fermi_p(E: np.ndarray, m: float, Z: int) -> np.ndarray:
    """p * F(Z, E), F = 2*pi*eta / (1 - exp(-2*pi*eta)), eta = alpha*Z*E/p."""
    p = np.sqrt(np.maximum(E * E - m * m, 0.0))
    p_safe = np.maximum(p, 1e-12)
    x = 2.0 * math.pi * ALPHA * Z * E / p_safe
    return p_safe * x / (-np.expm1(-x))


def _entity_shape(T: np.ndarray, pub: _BetaPublic, stage: Stage, p: float | None) -> np.ndarray:
    """Unsmeared entity density in public units. p is m_X (stage c) or k (stage d)."""
    dq = pub.Q - T
    inside = (T >= 0) & (dq > 0)
    dq_c = np.where(inside, dq, 0.0)
    E = T + pub.m_e
    if stage in (Stage.HISTORICAL, Stage.OBFUSCATED):
        f = _fermi_p(E, pub.m_e, pub.Z) * E * dq_c**2
    elif stage is Stage.COUNTERFACTUAL:
        pe = np.sqrt(np.maximum(E * E - pub.m_e**2, 0.0))
        px = np.sqrt(np.maximum(dq_c**2 - p**2, 0.0))
        f = pe * E * dq_c * px
    else:  # SYNTHETIC: exponent 3k - 1 from k massless hidden particles
        pe = np.sqrt(np.maximum(E * E - pub.m_e**2, 0.0))
        f = pe * E * dq_c ** (3.0 * p - 1.0)
    return np.where(inside, f, 0.0)


def _noentity_shape(T: np.ndarray, pub: _BetaPublic, a2: float, a3: float, lam: float) -> np.ndarray:
    """Line shape: unit-weight resolution peak, plus tail (weight a2) and shelf (weight a3)."""
    Q = pub.Q
    peak = np.exp(-0.5 * ((T - Q) / pub.sigma) ** 2) / (pub.sigma * math.sqrt(2 * math.pi))
    inside = (T >= 0) & (T <= Q)
    tail = np.where(inside, np.exp(np.minimum((T - Q) / lam, 0.0)) / lam, 0.0)
    shelf = np.where(inside, 1.0 / Q, 0.0)
    return np.where(T >= 0, peak + a2 * tail + a3 * shelf, 0.0)


class _Smearing:
    """Precomputed Gaussian resolution kernels on the public window."""

    def __init__(self, pub: _BetaPublic, n_t: int = 801, n_grid: int = 401):
        # True (pre-resolution) energies span the full support [0, Q]; only observations are windowed.
        self.t = np.linspace(0.0, pub.Q, n_t)
        h = self.t[1] - self.t[0]
        self.w = np.full(n_t, h)
        self.w[0] = self.w[-1] = h / 2.0
        self.Tg = np.linspace(pub.lo, pub.hi, n_grid)
        self.K_ev = _gauss(pub.T[:, None] - self.t[None, :], pub.sigma)
        self.K_g = _gauss(self.Tg[:, None] - self.t[None, :], pub.sigma)

    def nll(self, f_t: np.ndarray) -> float:
        fw = f_t * self.w
        dens_ev = self.K_ev @ fw
        dens_g = self.K_g @ fw
        norm = float(np.sum(0.5 * (dens_g[1:] + dens_g[:-1]) * np.diff(self.Tg)))
        if not (math.isfinite(norm) and norm > 0):
            return math.inf
        return float(-np.sum(np.log(np.maximum(dens_ev / norm, 1e-300))))


def _gauss(d: np.ndarray, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * (d / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


def _nll_plain(f_fn, pub: _BetaPublic) -> float:
    Tg = np.linspace(pub.lo, pub.hi, 4001)
    fg = f_fn(Tg)
    norm = float(np.sum(0.5 * (fg[1:] + fg[:-1]) * np.diff(Tg)))
    fe = np.maximum(f_fn(pub.T), 1e-300)
    if not (math.isfinite(norm) and norm > 0):
        return math.inf
    return float(-np.sum(np.log(fe / norm)))


def _refine_1d(objective, lo: float, hi: float, n_grid: int = 41) -> float:
    grid = np.linspace(lo, hi, n_grid)
    vals = np.array([objective(g) for g in grid])
    i = int(np.argmin(vals))
    a = grid[max(i - 1, 0)]
    b = grid[min(i + 1, n_grid - 1)]
    res = minimize_scalar(objective, bounds=(a, b), method="bounded", options={"xatol": 1e-7})
    return float(res.x) if res.fun <= vals[i] else float(grid[i])


def fit_beta_constants(public_files, *, truth: Truth, stage: Stage) -> dict[str, float]:
    """Fit the constants that the public files do not give, for one beta stage and truth."""
    pub = _beta_public(public_files)
    if truth is Truth.ENTITY:
        if stage is Stage.COUNTERFACTUAL:
            sm = _Smearing(pub)
            obj = lambda mX: sm.nll(_entity_shape(sm.t, pub, stage, mX))  # noqa: E731
            return {"m_X": _refine_1d(obj, 0.0, 0.85 * pub.Q)}
        if stage is Stage.SYNTHETIC:
            sm = _Smearing(pub)
            obj = lambda k: sm.nll(_entity_shape(sm.t, pub, stage, k))  # noqa: E731
            return {"k": _refine_1d(obj, 1.0, 5.0)}
        return {}  # Fermi family: Z, Q and m_e are all public
    # No-entity line shape, fitted directly to the (unsmeared) events.

    def obj(theta):
        a2, a3, lam = math.exp(theta[0]), math.exp(theta[1]), math.exp(theta[2])
        return _nll_plain(lambda T: _noentity_shape(T, pub, a2, a3, lam), pub)

    res = minimize(obj, x0=np.log([0.2, 0.2, 0.2 * pub.Q]), method="Nelder-Mead",
                   options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
    a2, a3, lam = (float(math.exp(v)) for v in res.x)
    return {"a2": a2, "a3": a3, "lam": lam}


def _smear_entity(x: np.ndarray, pub: _BetaPublic, stage: Stage, p: float | None) -> np.ndarray:
    """Detector-seen entity density at x: the shape convolved with the public Gaussian resolution."""
    t = np.linspace(0.0, pub.Q, 4001)
    w = np.full(t.size, t[1] - t[0])
    w[0] = w[-1] = w[0] / 2.0
    ft = _entity_shape(t, pub, stage, p) * w
    flat = x.ravel()
    out = np.empty(flat.size)
    for i in range(0, flat.size, 500):
        out[i : i + 500] = _gauss(flat[i : i + 500, None] - t[None, :], pub.sigma) @ ft
    return out.reshape(x.shape)


def beta_oracle(public_files, eval_x, *, truth: Truth, stage: Stage) -> np.ndarray:
    """Oracle prediction of the detector-seen density at eval_x (public units)."""
    x = np.asarray(eval_x, dtype=float)
    pub = _beta_public(public_files)
    fit = fit_beta_constants(public_files, truth=truth, stage=stage)
    if truth is Truth.ENTITY:
        p = fit.get("m_X", fit.get("k"))
        return _smear_entity(x, pub, stage, p)
    return _noentity_shape(x, pub, fit["a2"], fit["a3"], fit["lam"])


# ---------------------------------------------------------------------------
# Orbit
# ---------------------------------------------------------------------------


def _load_t0(files) -> dict:
    """Execute the public T0 model source and return its namespace."""
    ns: dict = {}
    exec(compile(_text(files["t0_model.py"]), "t0_model.py", "exec"), ns)
    return ns


def _orbit_obs(files, ns):
    rows = _csv_rows(_text(files["target_positions.csv"]))[1:]
    name = rows[0][0]
    t_obs = np.array([float(r[1]) for r in rows])
    obs_deg = np.array([float(r[2]) for r in rows])
    t0 = np.asarray(ns["predict_longitudes"](t_obs)[name], dtype=float)
    d = np.radians(obs_deg) - np.radians(t0)
    obs_res = np.arctan2(np.sin(d), np.cos(d)) * ARCSEC_PER_RAD
    return ns["PLANETS"].index(name), t_obs, obs_res


def _accel_correction(ns, X, mu, k, n):
    """Gravity plus the radial force k / r^n about body 0 (same law as the generator)."""
    A = ns["_accel_grav"](X, mu)
    dr = X - X[:, :1, :]
    rr = np.sqrt(np.einsum("bik,bik->bi", dr, dr))
    rr[:, 0] = 1.0
    n = np.asarray(n, dtype=float).reshape(-1, 1, 1)  # scalar or one exponent per batch row
    ext = -k[:, None, None] * dr * rr[..., None] ** (-(n + 1.0))
    ext[:, 0] = 0.0
    A = A + ext
    A[:, 0, :] -= np.einsum("bi,bik->bk", mu[:, 1:], ext[:, 1:]) / mu[:, :1]
    return A


def _residual_rows(ns, mu, elem, k, n, t_eval, tgt) -> np.ndarray:
    """Target residual (arcsec, wrapped) of rows 1.. relative to row 0 (the T0 reference).

    mu (B, N), elem (B, N-1, 4), k (B,). Returns (B-1, len(t_eval)).
    """
    DT = ns["DT"]
    n_steps = max(1, int(math.ceil(float(np.max(t_eval)) / DT)))
    B, N = mu.shape
    x0 = np.empty((B, N, 2))
    v0 = np.empty((B, N, 2))
    for b in range(B):
        x0[b], v0[b] = ns["_initial_state"](mu[b], elem[b])
    if n is None:
        accel = lambda X: ns["_accel_grav"](X, mu)  # noqa: E731
    else:
        accel = lambda X: _accel_correction(ns, X, mu, k, n)  # noqa: E731
    X, _ = ns["_integrate"](accel, x0, v0, DT, n_steps)
    lam = np.unwrap(ns["_longitudes"](X), axis=0)[..., :4]  # (S, B, 4) planets only
    d = lam[..., tgt] - lam[:, :1, tgt]
    R = np.arctan2(np.sin(d), np.cos(d)) * ARCSEC_PER_RAD  # (S, B)
    grid = np.arange(n_steps + 1) * DT
    return CubicSpline(grid, R, axis=0)(np.asarray(t_eval, dtype=float)).T[1:]


def _fit_lm(sim, x0: np.ndarray, t_obs: np.ndarray, obs_res: np.ndarray, bounds=None) -> np.ndarray:
    """Least squares with a batched finite-difference Jacobian (one integration per step).

    Levenberg-Marquardt without bounds, trust-region reflective with bounds."""
    p = len(x0)
    h = 1e-4
    cache: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}

    def batch(x):
        key = tuple(float(v) for v in x)
        if key not in cache:
            X = np.vstack([x] + [x + h * np.eye(p)[i] for i in range(p)])
            R = sim(X, t_obs) - obs_res  # (p+1, m)
            J = ((R[1:] - R[0]) / h).T
            cache[key] = (R[0], J)
        return cache[key]

    kw = {"method": "lm"} if bounds is None else {"method": "trf", "bounds": bounds}
    sol = least_squares(lambda x: batch(x)[0], x0, jac=lambda x: batch(x)[1],
                        xtol=1e-7, ftol=1e-7, gtol=1e-7, max_nfev=FIT_MAX_NFEV, **kw)
    return sol.x


def _entity_sim(ns, tgt, X, t_eval):
    """Outer-body model: X rows are (log q, log a, L0); q = GM_body / GM_star, e = 0, coplanar."""
    gms = float(ns["GM_STAR"])
    gm4 = np.array(ns["GM_PLANETS"], dtype=float)
    elem4 = np.array(ns["ELEMENTS"], dtype=float)
    B = X.shape[0]
    q = np.concatenate([[0.0], np.exp(X[:, 0])])
    a = np.concatenate([[elem4[tgt, 0]], np.exp(X[:, 1])])
    L0 = np.concatenate([[0.0], X[:, 2]])
    mu = np.zeros((B + 1, 6))
    mu[:, 0] = gms
    mu[:, 1:5] = gm4
    mu[:, 5] = q * gms
    elem = np.zeros((B + 1, 5, 4))
    elem[:, :4] = elem4
    elem[:, 4, 0] = a
    elem[:, 4, 3] = L0
    return _residual_rows(ns, mu, elem, np.zeros(B + 1), None, t_eval, tgt)


def _noentity_sim(ns, tgt, X, t_eval):
    """Correction-force model: X rows are (log A, n); the force is A (r / a_t)^-n about the star.

    A is the force at the target's semi-major axis a_t, so A and n are nearly decorrelated."""
    gms = float(ns["GM_STAR"])
    gm4 = np.array(ns["GM_PLANETS"], dtype=float)
    elem4 = np.array(ns["ELEMENTS"], dtype=float)
    a_t = float(elem4[tgt, 0])
    B = X.shape[0]
    mu = np.tile(np.concatenate([[gms], gm4]), (B + 1, 1))
    elem = np.tile(elem4, (B + 1, 1, 1))
    n = np.concatenate([[3.0], X[:, 1]])
    k = np.concatenate([[0.0], np.exp(X[:, 0]) * a_t ** X[:, 1]])
    return _residual_rows(ns, mu, elem, k, n, t_eval, tgt)


def fit_orbit_noentity(public_files) -> dict[str, float]:
    """Fit the correction amplitude A (at a_t) and the exponent n from the public data only."""
    ns = _load_t0(public_files)
    tgt, t_obs, obs_res = _orbit_obs(public_files, ns)
    return _fit_noentity(ns, tgt, t_obs, obs_res)[1]


def _fit_noentity(ns, tgt, t_obs, obs_res):
    sim = partial(_noentity_sim, ns, tgt)
    lo = np.array([-30.0, N_BOUNDS[0]])
    hi = np.array([30.0, N_BOUNDS[1]])
    # Coarse grid over log A (amplitude is almost linear in the residual) at each starting exponent.
    logA = np.linspace(-9.0, 4.0, 14) * math.log(10.0) / 3.0
    best = None
    for n0 in N_STARTS:
        grid = np.stack([logA, np.full_like(logA, n0)], axis=1)
        R = sim(grid, t_obs)
        sse = ((R - obs_res) ** 2).sum(axis=1)
        i = int(np.argmin(sse))
        x_fit = _fit_lm(sim, grid[i], t_obs, obs_res, bounds=(lo, hi))
        cost = float(((sim(x_fit[None], t_obs)[0] - obs_res) ** 2).sum())
        if best is None or cost < best[0]:
            best = (cost, x_fit)
    x = best[1]
    return sim, {"A": float(math.exp(x[0])), "n": float(x[1]), "x": x}


def orbit_oracle(public_files, eval_x, *, truth: Truth) -> np.ndarray:
    """Oracle prediction of the target residual (arcsec) at eval_x (public time units).

    No stage-specific constant is passed in: the no-entity oracle fits the exponent too."""
    ns = _load_t0(public_files)
    tgt, t_obs, obs_res = _orbit_obs(public_files, ns)
    x_eval = np.asarray(eval_x, dtype=float)
    if truth is Truth.ENTITY:
        a_t = float(ns["ELEMENTS"][tgt][0])
        sim = partial(_entity_sim, ns, tgt)
        # Batched coarse grid over (a, L0) at a reference mass; the mass enters the
        # residual almost linearly at this scale, so its best value is a closed-form scale.
        A = a_t * np.geomspace(1.05, 5.0, 6)
        P = np.linspace(0.0, 2.0 * math.pi, 4, endpoint=False)
        GA, GP = np.meshgrid(A, P, indexing="ij")
        q0 = 1e-4
        xg = np.stack([np.full(GA.size, math.log(q0)), np.log(GA.ravel()), GP.ravel()], axis=1)
        R = sim(xg, t_obs)  # (G, m)
        c = (R @ obs_res) / np.maximum((R * R).sum(axis=1), 1e-30)
        sse = np.where(c > 0, ((c[:, None] * R - obs_res) ** 2).sum(axis=1), np.inf)
        best = int(np.argmin(sse))
        x0 = np.array([math.log(q0 * c[best]), math.log(GA.ravel()[best]), GP.ravel()[best]])
        x_fit = _fit_lm(sim, x0, t_obs, obs_res)
        return sim(x_fit[None], x_eval)[0]

    sim, fit = _fit_noentity(ns, tgt, t_obs, obs_res)
    return sim(fit["x"][None], x_eval)[0]
