"""Physics and measurement process of the decay world (internal energy unit: Q = 1).

Hidden physics and measurement are separate layers:

1. Decay (``decay_*``): a complete event in the parent rest frame. Energy and momentum are
   conserved exactly. Final states are populated uniformly in Lorentz-invariant phase space
   (constant matrix element; for three bodies: uniform over the Dalitz plot).
   - two-body: parent -> daughter + light particle (the T0 decay);
   - carrier: parent -> daughter + light particle + unobserved neutral carrier of rest energy m_x.
2. Transport (``transport_loss``): the light particle crosses source material of relative
   thickness t and loses L = a*t + Gamma(shape=b*t, scale=c). Particles with no kinetic energy
   left stop in the source. The same law holds in every world; only the material constants
   (a, b, c) differ.
3. Instruments, applied to the event *after* the decay and transport:
   - spectrometer: kinetic energy left after transport, Gaussian resolution, recording window;
   - calorimeter (source inside it): absorbs the light particle and the daughter completely, so it
     measures their full kinetic energies at emission, Gaussian resolution;
   - recoil detector (hidden check only): daughter momentum magnitude, relative resolution.

Everything here is a pure function of explicit parameters; the hidden truth is chosen in
``world.py``. The reference solver uses the same families with fitted parameters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import special, stats

# Instrument constants, in units of Q (relative resolution for the recoil detector).
SIGMA_SPEC = 0.02
SIGMA_CAL = 0.03
RECOIL_REL_RES = 0.02
WINDOW = (0.10, 1.30)  # spectrometer recording window, units of Q
THICKNESS_RANGE = (0.25, 3.0)  # source thicknesses the experimenter may choose (relative)
CHECK_THICKNESS = 0.05  # hidden-check source: thinner than anything in the measurement menu


@dataclass(frozen=True)
class Kinematics:
    """Public masses in units of Q. Q = M_parent - M_daughter - m_light = 1."""

    m_light: float
    m_daughter: float

    @property
    def m_parent(self) -> float:
        return self.m_daughter + self.m_light + 1.0

    def p_light(self, T):
        T = np.asarray(T, dtype=float)
        return np.sqrt(np.maximum(T * (T + 2.0 * self.m_light), 0.0))

    def two_body(self) -> tuple[float, float]:
        """(kinetic energy of the light particle, momentum) in a two-body decay."""
        M, m1, m3 = self.m_parent, self.m_light, self.m_daughter
        # E1 = (M^2 + m1^2 - m3^2) / 2M with M^2 - m3^2 = (M - m3)(M + m3) (no cancellation).
        E1 = ((M - m3) * (M + m3) + m1 * m1) / (2.0 * M)
        T1 = E1 - m1
        return float(T1), float(math.sqrt(T1 * (T1 + 2.0 * m1)))

    @property
    def p_ref(self) -> float:
        """Light-particle momentum at kinetic energy Q: the public momentum scale."""
        return float(self.p_light(1.0))


# ---------------------------------------------------------------------------
# Decay layer
# ---------------------------------------------------------------------------


def _carrier_axes(kin: Kinematics, m_x: float, E1: np.ndarray):
    """Quantities in the (carrier + daughter) rest frame for light-particle energies E1."""
    M, m1, m2, m3 = kin.m_parent, kin.m_light, m_x, kin.m_daughter
    m23_sq = M * M + m1 * m1 - 2.0 * M * E1
    m23 = np.sqrt(np.maximum(m23_sq, (m2 + m3) ** 2))
    e1s = (M * E1 - m1 * m1) / m23
    # m23^2 - m3^2 = (m23 - m3)(m23 + m3), written to avoid cancellation.
    e2s = ((m23 - m3) * (m23 + m3) + m2 * m2) / (2.0 * m23)
    p1s = np.sqrt(np.maximum(e1s * e1s - m1 * m1, 0.0))
    p2s = np.sqrt(np.maximum(e2s * e2s - m2 * m2, 0.0))
    return e1s, e2s, p1s, p2s


def carrier_T_max(kin: Kinematics, m_x: float) -> float:
    """Largest light-particle kinetic energy in the three-body decay."""
    M, m1, m3 = kin.m_parent, kin.m_light, kin.m_daughter
    s = m3 + m_x
    E1 = ((M - s) * (M + s) + m1 * m1) / (2.0 * M)
    return float(E1 - m1)


def carrier_T_pdf(kin: Kinematics, m_x: float, T: np.ndarray) -> np.ndarray:
    """Exact marginal density (unnormalised) of the light-particle kinetic energy at emission.

    Uniform Dalitz density => dN/dE1 is proportional to p1* p2* (momenta in the 23 rest frame).
    """
    T = np.asarray(T, dtype=float)
    tmax = carrier_T_max(kin, m_x)
    inside = (T > 0.0) & (T < tmax)
    _, _, p1s, p2s = _carrier_axes(kin, m_x, np.where(inside, T, 0.5 * tmax) + kin.m_light)
    return np.where(inside, p1s * p2s, 0.0)


def decay_carrier(kin: Kinematics, m_x: float, n: int, rng: np.random.Generator):
    """Three-body events: (light kinetic energy, daughter momentum, daughter kinetic energy)."""
    tmax = carrier_T_max(kin, m_x)
    grid = np.linspace(0.0, tmax, 40001)
    pdf = carrier_T_pdf(kin, m_x, grid)
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (pdf[1:] + pdf[:-1]) * np.diff(grid))])
    cdf /= cdf[-1]
    T1 = np.interp(rng.random(n), cdf, grid)
    E1 = T1 + kin.m_light
    e1s, e2s, p1s, p2s = _carrier_axes(kin, m_x, E1)
    # m12^2 uniform in [(e1s + e2s)^2 - (p1s + p2s)^2, (e1s + e2s)^2 - (p1s - p2s)^2].
    lo = (e1s + e2s) ** 2 - (p1s + p2s) ** 2
    hi = (e1s + e2s) ** 2 - (p1s - p2s) ** 2
    m12_sq = lo + (hi - lo) * rng.random(n)
    M, m3 = kin.m_parent, kin.m_daughter
    T3 = ((M - m3) ** 2 - m12_sq) / (2.0 * M)  # daughter kinetic energy, cancellation-free
    T3 = np.maximum(T3, 0.0)
    p3 = np.sqrt(T3 * (T3 + 2.0 * m3))
    return T1, p3, T3


def decay_two_body(kin: Kinematics, n: int):
    T1, p1 = kin.two_body()
    T3 = 1.0 - T1  # total kinetic release is Q = 1
    return np.full(n, T1), np.full(n, p1), np.full(n, T3)


# ---------------------------------------------------------------------------
# Transport layer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Material:
    """Energy-loss constants of the source material: L = a*t + Gamma(b*t, c), units of Q."""

    a: float
    b: float
    c: float

    def check(self) -> None:
        if not (self.a >= 0.0 and self.b > 0.0 and self.c > 0.0) or not all(
            math.isfinite(v) for v in (self.a, self.b, self.c)
        ):
            raise ValueError(f"invalid material constants {self}")


def transport_loss(mat: Material, t: float, n: int, rng: np.random.Generator) -> np.ndarray:
    if not t > 0.0:
        raise ValueError("thickness must be positive")
    return mat.a * t + rng.gamma(mat.b * t, mat.c, size=n)


# ---------------------------------------------------------------------------
# Full event generation for one hypothesis (decay + transport + instruments)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hypothesis:
    """A fully specified generative hypothesis: decay kind and material."""

    decay: str  # "two_body" or "carrier"
    m_x: float  # carrier rest energy (ignored for two_body)
    material: Material

    def check(self, kin: Kinematics) -> None:
        if self.decay not in ("two_body", "carrier"):
            raise ValueError(f"unknown decay kind {self.decay!r}")
        if self.decay == "carrier" and not (0.0 <= self.m_x < 1.0 and math.isfinite(self.m_x)):
            raise ValueError("carrier rest energy must lie in [0, Q)")
        self.material.check()


def _emit(h: Hypothesis, kin: Kinematics, n: int, rng):
    if h.decay == "carrier":
        return decay_carrier(kin, h.m_x, n, rng)
    return decay_two_body(kin, n)


MAX_DECAYS = 4_000_000  # exposure cap of one measurement


def sample_query(h: Hypothesis, kin: Kinematics, query: dict, n: int, rng: np.random.Generator,
                 max_decays: int = MAX_DECAYS) -> dict:
    """Simulate ``n`` recorded observations of ``query`` under hypothesis ``h`` (units of Q).

    Spectrometer queries stop at ``max_decays`` decays; then fewer than ``n`` events are returned
    (a measurement where almost every particle stops in the source records little).

    Query types:
    - {"type": "spectrum", "thickness": t}: kinetic energies recorded by the spectrometer;
    - {"type": "calorimeter"}: total deposited energy per decay;
    - {"type": "recoil_coincidence", "thickness": t}: spectrometer energy and daughter momentum.
    """
    qt = query["type"]
    if qt == "calorimeter":
        T1, _p3, T3 = _emit(h, kin, n, rng)
        return {"deposited_energy": T1 + T3 + rng.normal(0.0, SIGMA_CAL, n)}
    if qt not in ("spectrum", "recoil_coincidence"):
        raise ValueError(f"unknown query type {qt!r}")
    t = float(query["thickness"])
    lo, hi = WINDOW
    kept_T, kept_p = [], []
    got, decays = 0, 0
    m = max(2 * n, 256)
    while got < n and decays < max_decays:
        m = min(m, max_decays - decays)
        decays += m
        T1, p3, _T3 = _emit(h, kin, m, rng)
        T_after = T1 - transport_loss(h.material, t, m, rng)
        alive = T_after > 0.0  # particles with no energy left stop in the source
        T_obs = T_after + rng.normal(0.0, SIGMA_SPEC, m)
        ok = alive & (T_obs >= lo) & (T_obs <= hi)
        kept_T.append(T_obs[ok])
        kept_p.append(p3[ok])
        got += int(ok.sum())
        m *= 4  # grow the batch when the recording efficiency is low
    # Exposure cap: if almost every particle stops in the source, fewer than n events are recorded.
    T_obs = np.concatenate(kept_T)[:n]
    if qt == "spectrum":
        return {"kinetic_energy": T_obs}
    p3 = np.concatenate(kept_p)[:n]
    p_obs = p3 * (1.0 + RECOIL_REL_RES * rng.normal(size=p3.size))
    return {"kinetic_energy": T_obs, "recoil_momentum": p_obs}


# ---------------------------------------------------------------------------
# Binned densities for the reference likelihoods (units of Q)
# ---------------------------------------------------------------------------

BIN = 0.0025
EDGES = np.arange(-0.4, 1.7 + BIN / 2, BIN)
CENTERS = 0.5 * (EDGES[1:] + EDGES[:-1])


def _smear(prob: np.ndarray, sigma: float) -> np.ndarray:
    half = int(math.ceil(6 * sigma / BIN))
    x = np.arange(-half, half + 1) * BIN
    k = np.diff(stats.norm.cdf(np.concatenate([x - BIN / 2, [x[-1] + BIN / 2]]), scale=sigma))
    return np.convolve(prob, k, mode="same")


def _emission_points(h: Hypothesis, kin: Kinematics) -> tuple[np.ndarray, np.ndarray]:
    """Light-particle kinetic energy at emission as (values, weights): exact for a two-body line."""
    if h.decay == "two_body":
        T1, _ = kin.two_body()
        return np.array([T1]), np.array([1.0])
    fine = np.linspace(0.0, carrier_T_max(kin, h.m_x), 20001)
    pdf = carrier_T_pdf(kin, h.m_x, fine)
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (pdf[1:] + pdf[:-1]) * np.diff(fine))])
    cdf /= cdf[-1]
    w = np.diff(np.interp(EDGES, fine, cdf, left=0.0, right=1.0))
    keep = w > 1e-12
    return CENTERS[keep], w[keep]


def _window(obs: np.ndarray) -> np.ndarray:
    obs = np.where((CENTERS >= WINDOW[0]) & (CENTERS <= WINDOW[1]), np.maximum(obs, 0.0), 0.0)
    s = obs.sum()
    return obs / s if s > 0 else obs


def spectrum_probs(h: Hypothesis, kin: Kinematics, t: float) -> np.ndarray:
    """Recorded-spectrum bin probabilities at thickness t (normalised over the window)."""
    vals, wts = _emission_points(h, kin)
    m = h.material
    shift = m.a * t
    if shift + m.b * t * m.c < 0.05 * BIN:
        # Negligible loss (well below one bin): smear the emission directly.
        if vals.size == 1:
            return _window(np.diff(stats.norm.cdf(EDGES, loc=vals[0], scale=SIGMA_SPEC)))
        emit = np.zeros(CENTERS.size)
        emit[np.searchsorted(EDGES, vals) - 1] = wts
        return _window(_smear(np.where(CENTERS > 0.0, emit, 0.0), SIGMA_SPEC))
    # Distribution of T_after = T_emit - L on the grid: for each emission value, gamma CDF differences.
    after = np.zeros(CENTERS.size)
    for T0, wi in zip(vals, wts):
        # P(T_after in bin j) = P(L - a t in [T0 - a t - e_{j+1}, T0 - a t - e_j])
        upper = np.clip(T0 - shift - EDGES[:-1], 0.0, None)
        lower = np.clip(T0 - shift - EDGES[1:], 0.0, None)
        after += wi * (special.gammainc(m.b * t, upper / m.c) - special.gammainc(m.b * t, lower / m.c))
    after = np.where(CENTERS > 0.0, after, 0.0)  # stopped particles are not recorded
    return _window(_smear(after, SIGMA_SPEC))


def calorimeter_probs(h: Hypothesis, kin: Kinematics) -> np.ndarray:
    """Deposited-energy bin probabilities. The daughter recoil (about 1e-3 Q) is neglected for the carrier."""
    if h.decay == "two_body":
        return np.diff(stats.norm.cdf(EDGES, loc=1.0, scale=SIGMA_CAL))  # light + daughter kinetic = Q
    vals, wts = _emission_points(h, kin)
    emit = np.zeros(CENTERS.size)
    emit[np.searchsorted(EDGES, vals) - 1] = wts
    obs = np.maximum(_smear(emit, SIGMA_CAL), 0.0)
    return obs / obs.sum()


def query_probs(h: Hypothesis, kin: Kinematics, query: dict) -> tuple[np.ndarray, str]:
    if query["type"] == "spectrum":
        return spectrum_probs(h, kin, float(query["thickness"])), "kinetic_energy"
    if query["type"] == "calorimeter":
        return calorimeter_probs(h, kin), "deposited_energy"
    raise ValueError(f"no binned density for query type {query['type']!r}")


def loglik_binned(probs: np.ndarray, x: np.ndarray, floor: float = 1e-9) -> float:
    """Log-likelihood (bin-density, units of Q) of observations x under bin probabilities."""
    idx = np.clip(np.searchsorted(EDGES, np.asarray(x, dtype=float)) - 1, 0, CENTERS.size - 1)
    return float(np.sum(np.log(np.maximum(probs[idx], floor) / BIN)))
