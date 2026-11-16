"""Orbit episode: public view, measurements, model queries, reference families and fits.

Everything the agent sees or can request is defined here; the hidden truth comes from ``orbitworld``.
Measurement menu (budget 2 by default):
- {"type": "planet", "planet": <name other than the target>}  residuals at the initial 40 times;
- {"type": "extend"}                                            target residuals at T_EXTEND (20 times);
- {"type": "dense", "start": t in [0, 12]}                      target residuals, 200 times over 0.5 cycle;
- {"type": "search", "time": t in [0, 15], "lon_min", "lon_max"} a <= 10 degree sky window: detections.
Model queries (what an agent's ``simulate`` must answer):
- {"type": "residuals", "planet": name, "times": [...]} -> {"residual_arcsec": (n, T)}
- {"type": "search", "time", "lon_min", "lon_max"}       -> {"count": (n,)}

The reference (family-conditional) knows both families of the world rules and sees only the agent's data:
- body(a_ratio, phase, m): grid in a_ratio x phase, linear in m (small perturbation);
- force(n, k): grid in n, linear in k.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from abductbench.episode import orbitworld as ow

A_RATIOS = np.round(np.arange(0.18, 0.321, 0.02), 3)
PHASES = np.linspace(0.0, 2 * math.pi, 24, endpoint=False)
CACHE = Path(__file__).resolve().parents[3] / "results" / "episode" / "orbit_cache"
MAX_N = 200
_STREAM_INITIAL, _STREAM_MEASURE, _STREAM_CHECK = 11, 12, 13
TARGET = ow.PLANETS[0]


# ---------------------------------------------------------------------------
# Measurements and model queries
# ---------------------------------------------------------------------------


def validate_measurement(q: dict) -> dict:
    if not isinstance(q, dict):
        raise ValueError("measurement must be a JSON object")
    t = q.get("type")

    def num(key, lo, hi):
        v = q.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
            raise ValueError(f"{key} must be a number in [{lo}, {hi}]")
        return float(v)

    def only(keys):
        extra = set(q) - set(keys) - {"type"}
        if extra:
            raise ValueError(f"unexpected keys: {sorted(extra)}")

    if t == "planet":
        only({"planet"})
        if q.get("planet") not in ow.PLANETS[1:]:
            raise ValueError(f"planet must be one of {list(ow.PLANETS[1:])}")
        return {"type": "planet", "planet": q["planet"]}
    if t == "extend":
        only(set())
        return {"type": "extend"}
    if t == "dense":
        only({"start"})
        return {"type": "dense", "start": num("start", *ow.DENSE_START)}
    if t == "search":
        only({"time", "lon_min", "lon_max"})
        tt = num("time", *ow.SEARCH_TIME)
        lo, hi = num("lon_min", -360, 720), num("lon_max", -360, 720)
        if ow.window_width(lo, hi) > ow.SEARCH_MAX_WIDTH:
            raise ValueError(f"search window must be at most {ow.SEARCH_MAX_WIDTH:g} degrees wide")
        return {"type": "search", "time": tt, "lon_min": lo, "lon_max": hi}
    raise ValueError("measurement type must be one of: planet, extend, dense, search")


def model_query(meas: dict) -> dict:
    """The model query whose answer is the forecast of a measurement."""
    t = meas["type"]
    if t == "planet":
        return {"type": "residuals", "planet": meas["planet"], "times": ow.T_INITIAL.tolist()}
    if t == "extend":
        return {"type": "residuals", "planet": TARGET, "times": ow.T_EXTEND.tolist()}
    if t == "dense":
        return {"type": "residuals", "planet": TARGET, "times": ow.dense_times(meas["start"]).tolist()}
    return {k: meas[k] for k in ("type", "time", "lon_min", "lon_max")}


INITIAL_QUERY = {"type": "residuals", "planet": TARGET, "times": ow.T_INITIAL.tolist()}
CHECK_QUERIES = (
    {"type": "residuals", "planet": TARGET, "times": ow.T_CHECK.tolist()},
    *({"type": "residuals", "planet": p, "times": np.linspace(12.0, 15.0, 20).tolist()} for p in ow.PLANETS[1:]),
)
VALIDATION_QUERIES = (
    {"type": "residuals", "planet": ow.PLANETS[2], "times": [1.0, 2.0, 3.0]},
    {"type": "search", "time": 1.0, "lon_min": 0.0, "lon_max": 10.0},
)


def validate_sample(query: dict, sample: dict, n: int) -> dict:
    from abductbench.episode.modelrun import ModelError

    if query["type"] == "search":
        if "count" not in sample:
            raise ModelError("simulate(search) must return key 'count'")
        c = np.asarray(sample["count"], dtype=float)
        if c.shape != (n,) or not np.all(np.isfinite(c)) or np.any(c < 0) or np.any(c != np.round(c)):
            raise ModelError(f"simulate(search)['count'] must be {n} non-negative integers")
        return {"count": c}
    if "residual_arcsec" not in sample:
        raise ModelError("simulate(residuals) must return key 'residual_arcsec'")
    r = np.asarray(sample["residual_arcsec"], dtype=float)
    T = len(query["times"])
    if r.shape != (n, T):
        raise ModelError(f"simulate(residuals)['residual_arcsec'] must have shape ({n}, {T}), got {r.shape}")
    if not np.all(np.isfinite(r)) or np.max(np.abs(r)) > 1e7:
        raise ModelError("residuals must be finite and below 1e7 arcsec")
    return {"residual_arcsec": r}


def validate_mechanism(mech, menu: bool):
    from abductbench.episode.modelrun import ModelError

    if not menu:
        return None if mech is None else {"description": str(mech.get("description", ""))[:2000]}
    if not isinstance(mech, dict) or mech.get("kind") not in ("body", "force", "other"):
        raise ModelError('MECHANISM must be a dict with kind "body", "force" or "other"')

    def pos(key):
        v = mech.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ModelError(f"MECHANISM needs a positive number '{key}'")
        return float(v)

    if mech["kind"] == "body":
        a = pos("a")
        gm = pos("gm")
        if gm >= ow.GM_C:
            raise ModelError("body gm must be smaller than the central GM")
        return {"kind": "body", "a": a, "gm": gm}
    if mech["kind"] == "force":
        return {"kind": "force", "n": pos("n"), "k": float(mech.get("k", 0.0)) if isinstance(mech.get("k"), (int, float)) else 0.0}
    return {"kind": "other", "description": str(mech.get("description", ""))[:2000]}


# ---------------------------------------------------------------------------
# World (truth + observations)
# ---------------------------------------------------------------------------


@dataclass
class OrbitWorld:
    cfg: object
    seed: int = field(init=False)

    def __post_init__(self):
        self.seed = self.cfg.world_seed
        self.mechanism = self.cfg.mechanism
        self.Q = 1.0  # no energy scale: kept for interface compatibility

    def public_metadata(self) -> dict:
        s = ow.system(self.seed)
        return {
            "time_unit": "cycle", "distance_unit": "unit D", "angle_unit": "arcsec",
            "star": ow.STAR, "gm_central": ow.GM_C, "target": TARGET,
            "planets": [{"name": p, "gm": float(s.gm_planets[i]), "a": float(s.elements[i, 0]),
                         "e": float(s.elements[i, 1]), "longitude_of_pericentre_deg": float(np.degrees(s.elements[i, 2]) % 360),
                         "mean_longitude_epoch_deg": float(np.degrees(s.elements[i, 3]) % 360)} for i, p in enumerate(ow.PLANETS)],
            "sigma_arcsec": ow.SIGMA, "initial_times": ow.T_INITIAL.tolist(), "extend_times": ow.T_EXTEND.tolist(),
            "dense": {"span": ow.DENSE_SPAN, "n": ow.DENSE_N, "start_range": list(ow.DENSE_START)},
            "search": {"max_width_deg": ow.SEARCH_MAX_WIDTH, "time_range": list(ow.SEARCH_TIME),
                       "detection_probability": ow.P_DETECT, "false_detections_per_window": ow.FALSE_RATE},
        }

    def _truth_res(self) -> np.ndarray:
        return ow.body_truth(self.seed)[0] if self.mechanism == "body" else ow.force_truth(self.seed)

    def _rng(self, stream: int, idx: int):
        return np.random.default_rng([self.seed, self.cfg.obs_seed, stream, idx])

    def initial_plan(self) -> list[dict]:
        return [] if self.cfg.condition == "no_data" else [dict(INITIAL_QUERY)]

    def observe_initial(self) -> list[tuple[dict, dict]]:
        out = []
        for i, q in enumerate(self.initial_plan()):
            out.append((q, self.sample(q, 1, self._rng(_STREAM_INITIAL, i), flat=True)))
        return out

    def observe(self, meas: dict, idx: int) -> dict:
        q = model_query(validate_measurement(meas))
        return self.sample(q, 1, self._rng(_STREAM_MEASURE, idx), flat=True)

    def sample(self, q: dict, n: int, rng, flat: bool = False) -> dict:
        """n realisations of the query under the truth (noise included)."""
        if q["type"] == "search":
            hit = False
            if self.mechanism == "body":
                _, lb = ow.body_truth(self.seed)
                lon = float(np.degrees(np.interp(q["time"], ow.grid(), lb)) % 360.0)
                hit = ow.in_window(lon, q["lon_min"], q["lon_max"])
            det = (rng.random(n) < ow.P_DETECT) if hit else np.zeros(n, bool)
            cnt = det.astype(float) + rng.poisson(ow.FALSE_RATE, n)
            if flat:
                lo = q["lon_min"]
                w = ow.window_width(q["lon_min"], q["lon_max"])
                lons = [float((lo + rng.uniform(0, w)) % 360) for _ in range(int(cnt[0]) - int(det[0]))]
                if det[0]:
                    lons.append(float(lon))
                return {"count": cnt[:1], "longitudes_deg": np.array(sorted(lons))}
            return {"count": cnt}
        j = ow.PLANETS.index(q["planet"])
        mean = ow.at(self._truth_res()[:, j], q["times"])
        r = mean[None, :] + rng.normal(0, ow.SIGMA, (n, len(q["times"])))
        if flat:
            return {"time": np.asarray(q["times"], float), "residual_arcsec": r[0]}
        return {"residual_arcsec": r}

    def truth_sample(self, q: dict, n: int, seed: int = 0) -> dict:
        mech = ("body", "force").index(self.mechanism)
        return self.sample(q, n, np.random.default_rng([self.seed, mech, _STREAM_CHECK, seed]))


# ---------------------------------------------------------------------------
# Reference families
# ---------------------------------------------------------------------------


@lru_cache(maxsize=16)
def body_basis(seed: int) -> np.ndarray:
    """Residual response per unit body GM: (len(A_RATIOS), len(PHASES), S', 4) on a 4x coarser grid."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"body_{ow.__name__}_{seed}_{len(A_RATIOS)}x{len(PHASES)}_dt{ow.DT}_h{ow.HORIZON}.npy"
    if f.exists():
        return np.load(f)
    sysm = ow.system(seed)
    m0 = ow.GM_C * 1e-6
    aT = sysm.elements[0, 0]
    out = np.empty((len(A_RATIOS), len(PHASES), len(ow.grid()[::4]), 4), dtype=np.float32)
    for i, ar in enumerate(A_RATIOS):
        rows = [{"m_body": m0, "a_body": ar * aT, "phase": float(p)} for p in PHASES]
        lam, _ = ow.integrate(sysm, rows)
        out[i] = (ow.residuals(seed, lam) / m0)[::4].transpose(1, 0, 2)
    np.save(f, out)
    return out


def _coarse_at(series: np.ndarray, times) -> np.ndarray:
    g = ow.grid()[::4]
    return np.interp(np.asarray(times, float), g, series)


@dataclass
class OFit:
    family: str
    params: dict
    ll: float
    k: int

    @property
    def aic_half(self) -> float:
        return self.ll - self.k


def _gauss_ll(r: np.ndarray) -> float:
    return float(-0.5 * np.sum((r / ow.SIGMA) ** 2) - r.size * math.log(ow.SIGMA * math.sqrt(2 * math.pi)))


def _residual_data(data: list[tuple[dict, dict]]):
    """Stack residual observations: list of (planet index, times, values); search records separately."""
    res, srch = [], []
    for q, o in data:
        mq = model_query(q) if q["type"] in ("planet", "extend", "dense") else q
        if mq["type"] == "residuals":
            res.append((ow.PLANETS.index(mq["planet"]), np.asarray(o["time"] if "time" in o else mq["times"], float),
                        np.asarray(o["residual_arcsec"], float)))
        else:
            srch.append((q, float(np.asarray(o["count"]).ravel()[0])))
    return res, srch


def _search_ll(lon_body: float | None, q: dict, count: float) -> float:
    lam = ow.FALSE_RATE
    p_hit = ow.P_DETECT if (lon_body is not None and ow.in_window(lon_body, q["lon_min"], q["lon_max"])) else 0.0
    c = int(count)
    from math import exp, factorial
    pois = lambda k: exp(-lam) * lam**k / factorial(k) if k >= 0 else 0.0  # noqa: E731
    return math.log(max((1 - p_hit) * pois(c) + p_hit * pois(c - 1), 1e-300))


def body_lon_deg(seed: int, a_ratio: float, phase: float, t: float) -> float:
    a = a_ratio * ow.system(seed).elements[0, 0]
    return float(np.degrees(phase + math.sqrt(ow.GM_C / a**3) * t) % 360.0)


def _coarse_interp(B: np.ndarray, planet: int, times) -> np.ndarray:
    """Vectorised linear interpolation of the body basis (A, P, S', 4) at times: (A, P, T)."""
    g = ow.grid()[::4]
    t = np.clip(np.asarray(times, float), g[0], g[-1])
    i1 = np.clip(np.searchsorted(g, t), 1, len(g) - 1)
    w = (t - g[i1 - 1]) / (g[i1] - g[i1 - 1])
    return B[:, :, i1 - 1, planet] * (1 - w) + B[:, :, i1, planet] * w


def synodic_period(seed: int, a_ratio: float) -> float:
    aT = ow.system(seed).elements[0, 0]
    nb = math.sqrt(ow.GM_C / (a_ratio * aT) ** 3)
    nt = math.sqrt(ow.GM_C / aT**3)
    return 2 * math.pi / (nb - nt)


@lru_cache(maxsize=16)
def body_split(seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Body basis split into a slow part and the phase-averaged variance of the fast part.

    Slow part: boxcar average over one synodic period of the body with the target (removes the body's
    short-period terms exactly, keeps the target's own orbital-period signal); it depends on the phase
    through the osculating-epoch elements. Returns slow (A, P, S', 4) and fast variance (A, S', 4)."""
    from scipy.ndimage import uniform_filter1d

    B = body_basis(seed).astype(float)
    S = np.empty_like(B)
    for i, ar in enumerate(A_RATIOS):
        width = max(3, int(round(synodic_period(seed, float(ar)) / (4 * ow.DT))) | 1)
        S[i] = uniform_filter1d(B[i], size=width, axis=1, mode="nearest")
    return S, ((B - S) ** 2).mean(1)


UPS_A, UPS_P = 4, 4  # refinement factors in a_ratio and phase


def _refined(S: np.ndarray, V: np.ndarray, planet_times: list) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Slow part and fast variance at the observation times on a refined (a, phase) grid:
    cubic spline in a_ratio, Fourier (band-limited) interpolation in phase. Returns R (A', P', T), V (A', T),
    and the refined a_ratio and phase axes."""
    from scipy.interpolate import CubicSpline

    R = np.concatenate([_coarse_interp(S, p, t) for p, t in planet_times], axis=-1)  # (A, P, T)
    Vt = np.concatenate([_stat_at(V, p, t) for p, t in planet_times], axis=-1)  # (A, T)
    a_f = np.linspace(A_RATIOS[0], A_RATIOS[-1], (len(A_RATIOS) - 1) * UPS_A + 1)
    R = CubicSpline(A_RATIOS, R, axis=0)(a_f)
    Vt = np.maximum(CubicSpline(A_RATIOS, Vt, axis=0)(a_f), 0.0)
    P = len(PHASES)
    F = np.fft.rfft(R, axis=1)
    R = np.fft.irfft(F, n=P * UPS_P, axis=1) * UPS_P
    p_f = np.linspace(0.0, 2 * math.pi, P * UPS_P, endpoint=False)
    return R, Vt, a_f, p_f


def _body_ll(seed: int, res):
    """Gaussian log-likelihood on the refined (a_ratio, phase) grid, maximised over the mass.

    Mean = m * slow part at that phase; variance = SIGMA^2 + m^2 * phase-averaged fast-part variance
    (the short-period pattern is treated as unknown). Returns ll (A', P'), m (A', P'), a axis, phase axis."""
    S, Vf = body_split(seed)
    R, V, a_f, p_f = _refined(S, Vf, [(p, t) for p, t, _ in res])
    V = V[:, None, :]
    y = np.concatenate([v for _, _, v in res])
    m0 = np.maximum(np.einsum("apt,t->ap", R, y) / np.maximum(np.einsum("apt,apt->ap", R, R), 1e-30), 0.0)
    best_ll = np.full(m0.shape, -np.inf)
    best_m = m0.copy()
    for f in np.geomspace(0.8, 1.25, 11):
        m = m0 * f
        var = ow.SIGMA**2 + (m[..., None] ** 2) * V
        ll = (-0.5 * (y - m[..., None] * R) ** 2 / var - 0.5 * np.log(2 * math.pi * var)).sum(-1)
        better = ll > best_ll
        best_ll = np.where(better, ll, best_ll)
        best_m = np.where(better, m, best_m)
    return best_ll, best_m, a_f, p_f


def _stat_at(M: np.ndarray, planet: int, times) -> np.ndarray:
    """(A, S', 4) -> (A, T) at times."""
    return _coarse_interp(M[:, None], planet, times)[:, 0]


def fit_body(seed: int, data) -> OFit:
    res, srch = _residual_data(data)
    if res:
        ll, m, a_f, p_f = _body_ll(seed, res)
    else:
        a_f, p_f = A_RATIOS, PHASES
        ll, m = np.zeros((len(a_f), len(p_f))), np.zeros((len(a_f), len(p_f)))
    for q, c in srch:  # the fast phase is not estimated: a body is in the window for a fraction w/360 of phases
        w = ow.window_width(q["lon_min"], q["lon_max"]) / 360.0
        lam = ow.FALSE_RATE
        k = int(c)
        p0 = lambda j: math.exp(-lam) * lam**j / math.factorial(j) if j >= 0 else 0.0  # noqa: E731
        ll = ll + math.log(max((1 - ow.P_DETECT * w) * p0(k) + ow.P_DETECT * w * p0(k - 1), 1e-300))
    i, j = np.unravel_index(int(np.argmax(ll)), ll.shape)
    return OFit("body", {"a_ratio": float(a_f[i]), "phase": float(p_f[j]), "m": float(m[i, j])}, float(ll[i, j]), 3)


def fit_force(seed: int, data) -> OFit:
    res, srch = _residual_data(data)
    B = ow.force_basis(seed)
    g = ow.grid()
    best = None
    for i, n in enumerate(ow.N_GRID):
        R = np.concatenate([np.interp(t, g, B[i][:, p]) for p, t, _ in res])
        y = np.concatenate([v for _, _, v in res])
        k = (R @ y) / max(R @ R, 1e-30)
        ll = _gauss_ll(y - k * R) + sum(_search_ll(None, q, c) for q, c in srch)
        if best is None or ll > best.ll:
            best = OFit("force", {"n": float(n), "k": float(k)}, ll, 2)
    return best


def fit_both(seed: int, data) -> dict[str, OFit]:
    return {"body": fit_body(seed, data), "force": fit_force(seed, data)}


def posterior(fits) -> dict[str, float]:
    if not fits:
        return {"body": 0.5, "force": 0.5}
    s = {k: f.aic_half for k, f in fits.items()}
    mx = max(s.values())
    w = {k: math.exp(v - mx) for k, v in s.items()}
    z = sum(w.values())
    return {k: v / z for k, v in w.items()}


def dll(fits) -> float | None:
    return None if not fits else fits["body"].ll - fits["force"].ll


def _ij(fit: OFit) -> tuple[int, int]:
    return (int(np.argmin(np.abs(A_RATIOS - fit.params["a_ratio"]))),
            int(np.argmin(np.abs(PHASES - fit.params.get("phase", 0.0)))))


def _slow_at(seed: int, a_ratio: float, phase: float, planet: int, times) -> tuple[np.ndarray, np.ndarray]:
    """Slow part and fast variance (per unit GM) at a continuous (a_ratio, phase)."""
    from scipy.interpolate import CubicSpline

    S, V = body_split(seed)
    R = _coarse_interp(S, planet, times)  # (A, P, T)
    Vt = _stat_at(V, planet, times)  # (A, T)
    Ra = CubicSpline(A_RATIOS, R, axis=0)(a_ratio)  # (P, T)
    Va = np.maximum(CubicSpline(A_RATIOS, Vt, axis=0)(a_ratio), 0.0)
    F = np.fft.rfft(Ra, axis=0)
    k = np.arange(F.shape[0])
    P = len(PHASES)
    w = np.where((k == 0) | ((P % 2 == 0) & (k == P // 2)), 1.0, 2.0)
    slow = (w[:, None] * (F * np.exp(1j * k[:, None] * phase)).real).sum(0) / P
    return slow, Va


def predict_mean(seed: int, fit: OFit, planet: int, times) -> np.ndarray:
    if fit.family == "body":
        return fit.params["m"] * _slow_at(seed, fit.params["a_ratio"], fit.params.get("phase", 0.0), planet, times)[0]
    i = int(np.argmin(np.abs(ow.N_GRID - fit.params["n"])))
    return fit.params["k"] * np.interp(np.asarray(times, float), ow.grid(), ow.force_basis(seed)[i][:, planet])


def predict_var(seed: int, fit: OFit, planet: int, times) -> np.ndarray:
    v = np.full(len(times), ow.SIGMA**2)
    if fit.family == "body":
        v = v + fit.params["m"] ** 2 * _slow_at(seed, fit.params["a_ratio"], fit.params.get("phase", 0.0), planet, times)[1]
    return v


def fit_fn(seed: int, fit: OFit):
    """In-process model of a fitted reference hypothesis: n noisy realisations. For a body the slow part
    follows the fitted phase; the fast (short-period) part of each realisation comes from a random phase,
    because the reference does not estimate the body's position along its fast orbit."""

    def fn(query: dict, n: int, s: int) -> dict:
        rng = np.random.default_rng(s)
        if fit.family == "body":
            i, j0 = _ij(fit)
            phases = rng.integers(0, len(PHASES), n)
        if query["type"] == "search":
            det = np.zeros(n, bool)
            if fit.family == "body":
                hits = np.array([ow.in_window(body_lon_deg(seed, A_RATIOS[i], PHASES[j], query["time"]),
                                              query["lon_min"], query["lon_max"]) for j in range(len(PHASES))])
                det = hits[phases] & (rng.random(n) < ow.P_DETECT)
            return {"count": det.astype(float) + rng.poisson(ow.FALSE_RATE, n)}
        p = ow.PLANETS.index(query["planet"])
        t = query["times"]
        if fit.family == "body":
            S, _ = body_split(seed)
            B = body_basis(seed)[i:i + 1].astype(float)
            slow = _slow_at(seed, fit.params["a_ratio"], fit.params.get("phase", 0.0), p, t)[0]
            fast = (_coarse_interp(B, p, t) - _coarse_interp(S[i:i + 1], p, t))[0]  # (P, T) nearest a-row
            mu = fit.params["m"] * (slow[None, :] + fast[phases])
        else:
            mu = np.broadcast_to(predict_mean(seed, fit, p, t), (n, len(t)))
        return {"residual_arcsec": mu + rng.normal(0, ow.SIGMA, (n, len(t)))}

    return fn


MENU_CANDIDATES = (
    *({"type": "planet", "planet": p} for p in ow.PLANETS[1:]),
    {"type": "extend"},
    *({"type": "dense", "start": s} for s in (0.0, 6.0, 12.0)),
)


def gauss_info(mu1, v1, mu2, v2) -> float:
    """Symmetric KL (nats) between two independent-Gaussian forecasts, summed over points."""
    mu1, v1, mu2, v2 = map(lambda a: np.asarray(a, float), (mu1, v1, mu2, v2))
    kl12 = 0.5 * (v1 / v2 + (mu1 - mu2) ** 2 / v2 - 1 + np.log(v2 / v1))
    kl21 = 0.5 * (v2 / v1 + (mu1 - mu2) ** 2 / v1 - 1 + np.log(v1 / v2))
    return float(0.5 * np.sum(kl12 + kl21))


def expected_info(seed: int, f1: OFit, f2: OFit, meas: dict) -> float:
    mq = model_query(meas)
    if mq["type"] == "search":
        # The reference cannot aim a search (it does not estimate the body's phase): a body is in a window
        # of width w for a fraction w/360 of phases.
        w = ow.window_width(mq["lon_min"], mq["lon_max"]) / 360.0
        p = [ow.P_DETECT * w if f.family == "body" else 0.0 for f in (f1, f2)]
        a, b = (min(max(x, 1e-6), 1 - 1e-6) for x in p)
        return float(0.5 * (a * math.log(a / b) + (1 - a) * math.log((1 - a) / (1 - b))
                            + b * math.log(b / a) + (1 - b) * math.log((1 - b) / (1 - a))))
    j = ow.PLANETS.index(mq["planet"])
    t = mq["times"]
    return gauss_info(predict_mean(seed, f1, j, t), predict_var(seed, f1, j, t),
                      predict_mean(seed, f2, j, t), predict_var(seed, f2, j, t))


def menu_info(seed: int, fits) -> list[tuple[dict, float]]:
    """Expected information of the menu options for the reference. Searches are excluded: without a phase
    estimate a 10-degree search is nearly uninformative for the reference (an agent may still aim one)."""
    return [(dict(q), expected_info(seed, fits["body"], fits["force"], q)) for q in MENU_CANDIDATES]
