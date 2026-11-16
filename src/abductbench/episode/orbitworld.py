"""Orbit world for the episode protocol: hidden inner body vs extra central force, same target.

Units: time "cycle", distance "unit D", GM in unit D^3/cycle^2, angles in arcseconds.

World rules (told to the agent, identical in both worlds):
- Newtonian gravity between all bodies. The known planets move on orbits about the centre of mass C of
  everything inside the innermost planet's orbit; their published elements at epoch are about C, computed
  with the published central GM (GM_C). T0 assumes a single central mass GM_C (the star) fixed at C.
- Observations are heliocentric longitudes (measured from the star), Gaussian noise SIGMA per observation.

Hidden physics (one of):
- ``body``: an unobserved body on a circular coplanar orbit inside the target's orbit
  (a_body / a_target ~ U(R_BODY)). Star (GM_C - m) and body (m) orbit C. Its mass is set so that the
  target's residual reaches |R(10)| ~ U(AMP) arcsec.
- ``force``: the star (GM_C) sits at C and every planet feels an extra radial acceleration -k r^(-n)
  towards the star. (n, k) are matched per world to the body world's target residuals on the initial
  window (deliberate matched pair, as in the decay world; ambiguity is verified numerically, not assumed).

Physics consequence that makes the pair ambiguous at first: averaged over its fast orbit an inner body
acts on the target like a central force ~ 1/r^4 (quadrupole). What separates the two is non-axisymmetric
and time-variable: short-period perturbations (dense observing series) and the body itself (search).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from abductbench.tasks import orbit as om

ARCSEC = om.ARCSEC_PER_RAD
DT = 0.0005  # cycles; >= 40 steps per orbit of the closest allowed hidden body
HORIZON = 15.5
SIGMA = 1.0  # arcsec per observation
T_INITIAL = np.linspace(0.25, 10.0, 40)
T_EXTEND = np.linspace(10.25, 15.0, 20)
DENSE_SPAN, DENSE_N = 0.5, 200  # dense series: 200 observations over half a cycle
DENSE_START = (0.0, 12.0)
CHECK_START = 15.0  # hidden check: a dense series at a new epoch (not offered by the menu)
SEARCH_MAX_WIDTH = 10.0  # degrees
SEARCH_TIME = (0.0, 15.0)
P_DETECT = 0.8
FALSE_RATE = 0.3  # expected false detections per search window
R_BODY = (0.2, 0.3)
AMP = (20.0, 60.0)
N_GRID = np.round(np.arange(3.0, 5.501, 0.25), 3)
PLANETS = ("Ithe", "Moru", "Saska", "Delan")
STAR = "Aru"
PERT = 5  # state index of the hidden body
GM_C = 4 * math.pi**2


def dense_times(start: float) -> np.ndarray:
    return start + np.linspace(0.0, DENSE_SPAN, DENSE_N)


T_CHECK = dense_times(CHECK_START)


@dataclass(frozen=True)
class System:
    gm_planets: np.ndarray  # (4,)
    elements: np.ndarray  # (4, 4): a, e, varpi, L0 about C


@lru_cache(maxsize=64)
def system(world_seed: int) -> System:
    rng = np.random.default_rng([world_seed, 4242])
    a = np.array([rng.uniform(0.36, 0.44), rng.uniform(0.65, 0.8), rng.uniform(0.95, 1.1), rng.uniform(1.4, 1.7)])
    e = np.array([rng.uniform(0.15, 0.22), rng.uniform(0.0, 0.02), rng.uniform(0.0, 0.02), rng.uniform(0.05, 0.1)])
    q = np.array([1.7e-7, 2.4e-6, 3.0e-6, 3.2e-7]) * rng.uniform(0.7, 1.4, 4)
    ang = rng.uniform(0, 2 * math.pi, (4, 2))
    return System(GM_C * q, np.column_stack([a, e, ang[:, 0], ang[:, 1]]))


def _initial(sysm: System, m_body: float, a_body: float, phase: float):
    """Positions/velocities (6, 2): star, 4 planets, body. Planets about C; star and body about C."""
    gm = np.concatenate([[GM_C - m_body], sysm.gm_planets, [m_body]])
    X = np.zeros((6, 2))
    V = np.zeros((6, 2))
    r, v = om._state_from_elements(GM_C, a_body, 0.0, 0.0, phase)  # body relative to star, total GM_C
    f = m_body / GM_C
    X[0], V[0] = -f * r, -f * v
    X[PERT], V[PERT] = (1 - f) * r, (1 - f) * v
    for i in range(4):
        X[1 + i], V[1 + i] = om._state_from_elements(GM_C + sysm.gm_planets[i], *sysm.elements[i])
    M = gm.sum()
    X -= (gm[:, None] * X).sum(0) / M
    V -= (gm[:, None] * V).sum(0) / M
    return gm, X, V


def integrate(sysm: System, rows: list[dict], horizon: float = HORIZON):
    """Batch integration. Row keys: m_body, a_body, phase, k, n (one n per batch).

    Returns (longitudes (S, B, 4) unwrapped, heliocentric longitude of the body (S, B))."""
    ns = {float(r.get("n", 4.0)) for r in rows}
    if len(ns) != 1:
        raise ValueError("one exponent per batch")
    n = ns.pop()
    G, X0, V0, K = [], [], [], []
    for r in rows:
        gm, X, V = _initial(sysm, r.get("m_body", 0.0), r.get("a_body", 0.25 * sysm.elements[0, 0]), r.get("phase", 0.0))
        G.append(gm), X0.append(X), V0.append(V), K.append(r.get("k", 0.0))
    steps = int(round(horizon / DT))
    X, _ = om._run(np.array(G), np.stack(X0), np.stack(V0), np.array(K, float), n, DT, steps)
    lon = np.unwrap(om._longitudes(X), axis=0)  # bodies 1..5 relative to the star
    return lon[..., :4], lon[..., 4]


def grid() -> np.ndarray:
    return np.arange(int(round(HORIZON / DT)) + 1) * DT


def at(series: np.ndarray, times) -> np.ndarray:
    g = grid()
    t = np.asarray(times, float)
    flat = series.reshape(series.shape[0], -1)
    out = np.stack([np.interp(t, g, flat[:, j]) for j in range(flat.shape[1])], axis=-1)
    return out.reshape((len(t),) + series.shape[1:])


@lru_cache(maxsize=64)
def t0_lon(world_seed: int) -> np.ndarray:
    lam, _ = integrate(system(world_seed), [{}])
    return lam[:, 0, :]


def residuals(world_seed: int, lam: np.ndarray) -> np.ndarray:
    return (lam - t0_lon(world_seed)[:, None, :]) * ARCSEC


@lru_cache(maxsize=64)
def body_params(world_seed: int) -> tuple[float, float, float, float]:
    """(a_body, phase, m_body, amplitude) of the world seed; mass calibrated to the target amplitude at 10."""
    sysm = system(world_seed)
    rng = np.random.default_rng([world_seed, 777])
    a_b = rng.uniform(*R_BODY) * sysm.elements[0, 0]
    ph = rng.uniform(0, 2 * math.pi)
    amp = rng.uniform(*AMP)
    m0 = GM_C * 1e-6
    lam, _ = integrate(sysm, [{"m_body": m0, "a_body": a_b, "phase": ph}], horizon=10.5)
    t0 = t0_lon(world_seed)[: lam.shape[0]]
    g = grid()[: lam.shape[0]]
    r10 = np.interp(10.0, g, (lam[:, 0, 0] - t0[:, 0]) * ARCSEC)
    return float(a_b), float(ph), float(m0 * amp / abs(r10)), float(amp)


@lru_cache(maxsize=64)
def body_truth(world_seed: int) -> tuple[np.ndarray, np.ndarray]:
    a_b, ph, m, _ = body_params(world_seed)
    lam, lb = integrate(system(world_seed), [{"m_body": m, "a_body": a_b, "phase": ph}])
    return residuals(world_seed, lam)[:, 0, :], lb[:, 0]


@lru_cache(maxsize=64)
def force_basis(world_seed: int) -> np.ndarray:
    """Residual response per unit k for each n in N_GRID: (len(N_GRID), S, 4); linear in small k."""
    sysm = system(world_seed)
    k0 = 1e-9
    return np.stack([residuals(world_seed, integrate(sysm, [{"k": k0, "n": float(n)}])[0])[:, 0, :] / k0
                     for n in N_GRID])


@lru_cache(maxsize=64)
def force_params(world_seed: int) -> tuple[float, float, float]:
    """Matched force world: least-squares fit (grid in n, linear in k) to the noise-free body-world target
    residuals at the initial observation times. Returns (n, k, rms misfit in arcsec)."""
    y = at(body_truth(world_seed)[0][:, 0], T_INITIAL)
    B = force_basis(world_seed)
    R = np.stack([at(B[i][:, 0], T_INITIAL) for i in range(len(N_GRID))])
    c = (R @ y) / np.einsum("ij,ij->i", R, R)
    sse = ((c[:, None] * R - y) ** 2).sum(1)
    i = int(np.argmin(sse))
    return float(N_GRID[i]), float(c[i]), float(math.sqrt(sse[i] / len(y)))


@lru_cache(maxsize=64)
def force_truth(world_seed: int) -> np.ndarray:
    n, k, _ = force_params(world_seed)
    lam, _ = integrate(system(world_seed), [{"k": k, "n": n}])
    return residuals(world_seed, lam)[:, 0, :]


def in_window(lon: float, lo: float, hi: float) -> bool:
    lo, hi = lo % 360.0, hi % 360.0
    return lo <= lon <= hi if lo <= hi else (lon >= lo or lon <= hi)


def window_width(lo: float, hi: float) -> float:
    w = hi - lo
    return w % 360.0 if w < 0 else w


def short_period_rms(series: np.ndarray, times: np.ndarray, deg: int = 3) -> float:
    """RMS of a series about a low-order polynomial over a short span (the short-period content)."""
    y = np.asarray(series, float)
    t = np.asarray(times, float)
    p = np.polyfit(t - t.mean(), y, deg)
    return float(np.std(y - np.polyval(p, t - t.mean())))
