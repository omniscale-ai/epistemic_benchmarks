"""Reference families, fits, posterior and measurement informativeness (units of Q).

The reference is *family-conditional*: it knows the two candidate families that the world rules
make available (carrier(m) and two-body + loss(a, b, c)) and sees exactly the data the agent saw.
It never reads the hidden truth. It is used for (1) the reference posterior that calibrates the
agent's stated uncertainty, (2) the reference informativeness of a chosen measurement, (3) the
local reference solver that demonstrates solvability.

Posterior: Akaike weights with equal prior mass on the two families (carrier: 1 parameter,
loss: 3). This is an approximation stated in docs/episode-design.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import optimize

from abductbench.episode import physics as ph

NEGLIGIBLE = ph.Material(a=0.0, b=1.0, c=1e-7)
M_MAX = 0.6
Data = list[tuple[dict, dict]]  # (query, observation dict in units of Q)


def carrier_h(m: float) -> ph.Hypothesis:
    return ph.Hypothesis("carrier", float(m), NEGLIGIBLE)


def loss_h(a: float, b: float, c: float) -> ph.Hypothesis:
    return ph.Hypothesis("two_body", 0.0, ph.Material(float(a), float(b), float(c)))


def loglik(h: ph.Hypothesis, kin: ph.Kinematics, data: Data) -> float:
    total = 0.0
    for q, obs in data:
        probs, key = ph.query_probs(h, kin, q)
        total += ph.loglik_binned(probs, obs[key])
    return total


@dataclass
class Fit:
    family: str
    h: ph.Hypothesis
    ll: float
    k: int  # number of fitted parameters

    @property
    def aic_half(self) -> float:
        return self.ll - self.k


def fit_carrier(kin: ph.Kinematics, data: Data) -> Fit:
    grid = np.linspace(0.0, M_MAX, 31)
    lls = [loglik(carrier_h(m), kin, data) for m in grid]
    i = int(np.argmax(lls))
    lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    r = optimize.minimize_scalar(lambda m: -loglik(carrier_h(m), kin, data), bounds=(lo, hi), method="bounded",
                                 options={"xatol": 1e-4})
    m, ll = (float(r.x), float(-r.fun)) if -r.fun > lls[i] else (float(grid[i]), float(lls[i]))
    return Fit("carrier", carrier_h(m), ll, 1)


def fit_loss(kin: ph.Kinematics, data: Data) -> Fit:
    def nll(x):
        a, lb, lc = x
        if not (0.0 <= a <= 1.0 and -2.0 <= lb <= 3.5 and -8.0 <= lc <= 1.0):
            return 1e12
        return -loglik(loss_h(a, math.exp(lb), math.exp(lc)), kin, data)

    best = None
    for a0, b0, c0 in ((0.0, 2.0, 0.4), (0.1, 2.0, 0.4), (0.2, 3.0, 0.2), (0.0, 1.0, 0.05)):
        r = optimize.minimize(nll, [a0, math.log(b0), math.log(c0)], method="Nelder-Mead",
                              options={"maxiter": 600, "xatol": 1e-4, "fatol": 1e-4})
        if best is None or r.fun < best.fun:
            best = r
    a, lb, lc = best.x
    return Fit("loss", loss_h(a, math.exp(lb), math.exp(lc)), float(-best.fun), 3)


def fit_both(kin: ph.Kinematics, data: Data) -> dict[str, Fit]:
    return {"carrier": fit_carrier(kin, data), "loss": fit_loss(kin, data)}


def posterior(fits: dict[str, Fit] | None) -> dict[str, float]:
    """Akaike-weight posterior over the two families; 0.5/0.5 without data."""
    if not fits:
        return {"carrier": 0.5, "loss": 0.5}
    s = {k: f.aic_half for k, f in fits.items()}
    mx = max(s.values())
    w = {k: math.exp(v - mx) for k, v in s.items()}
    z = sum(w.values())
    return {k: v / z for k, v in w.items()}


AMBIGUOUS_DLL = 3.0  # nats: max log-likelihood ratio below which the data do not pick a family


def dll(fits: dict[str, Fit] | None) -> float | None:
    """Maximised log-likelihood ratio carrier - loss (no parameter penalty); None without data."""
    if not fits:
        return None
    return fits["carrier"].ll - fits["loss"].ll


def expected_info(h1: ph.Hypothesis, h2: ph.Hypothesis, kin: ph.Kinematics, query: dict) -> float:
    """Expected |log Bayes factor| (nats) of ``query['n']`` events: n * symmetric KL of the binned laws."""
    p1, _ = ph.query_probs(h1, kin, query)
    p2, _ = ph.query_probs(h2, kin, query)
    eps = 1e-12
    p1 = np.maximum(p1, eps)
    p2 = np.maximum(p2, eps)
    p1, p2 = p1 / p1.sum(), p2 / p2.sum()
    skl = 0.5 * (np.sum(p1 * np.log(p1 / p2)) + np.sum(p2 * np.log(p2 / p1)))
    return float(query.get("n", 1) * skl)


MENU_CANDIDATES = (
    {"type": "spectrum", "thickness": 0.25},
    {"type": "spectrum", "thickness": 0.5},
    {"type": "spectrum", "thickness": 1.0},
    {"type": "spectrum", "thickness": 2.0},
    {"type": "spectrum", "thickness": 3.0},
    {"type": "calorimeter"},
)


def menu_info(fits: dict[str, Fit], kin: ph.Kinematics, n: int) -> list[tuple[dict, float]]:
    out = []
    for q in MENU_CANDIDATES:
        qq = {**q, "n": n}
        out.append((qq, expected_info(fits["carrier"].h, fits["loss"].h, kin, qq)))
    return out


# ---------------------------------------------------------------------------
# Sample-based informativeness, for models known only through samples (agent models)
# ---------------------------------------------------------------------------


def _hist_density(x: np.ndarray, edges: np.ndarray, pseudo: float = 0.5) -> np.ndarray:
    h, _ = np.histogram(x, edges)
    h = h.astype(float) + pseudo
    return h / h.sum()


def common_edges(*samples: np.ndarray, nbins: int = 30) -> np.ndarray:
    allx = np.concatenate([np.asarray(s, dtype=float).ravel() for s in samples])
    lo, hi = np.percentile(allx, [0.5, 99.5])
    if not hi > lo:
        hi = lo + 1e-3
    pad = 0.05 * (hi - lo)
    return np.linspace(lo - pad, hi + pad, nbins + 1)


def sample_info(x1: np.ndarray, x2: np.ndarray, n: int, nbins: int = 30) -> float:
    """n * symmetric KL between histogram estimates of two predicted samples, bias-corrected.

    Two finite samples of the same law have E[symmetric KL] ~ (B - 1)(1/N1 + 1/N2) / 2 (B occupied
    bins); that bias is subtracted and the result clipped at 0. Scale-free.
    """
    x1, x2 = np.asarray(x1, float), np.asarray(x2, float)
    edges = common_edges(x1, x2, nbins=nbins)
    p1, p2 = _hist_density(x1, edges), _hist_density(x2, edges)
    skl = 0.5 * (np.sum(p1 * np.log(p1 / p2)) + np.sum(p2 * np.log(p2 / p1)))
    h1, _ = np.histogram(x1, edges)
    h2, _ = np.histogram(x2, edges)
    occupied = int(np.sum((h1 + h2) > 0))
    bias = max(occupied - 1, 0) * (1.0 / x1.size + 1.0 / x2.size) / 2.0
    return float(max(n * (skl - bias), 0.0))


def _lbf(obs, pa_s, pc_s, edges) -> float:
    pa, pc = _hist_density(pa_s, edges), _hist_density(pc_s, edges)
    idx = np.clip(np.searchsorted(edges, obs) - 1, 0, len(edges) - 2)
    return float(np.sum(np.log(pa[idx])) - np.sum(np.log(pc[idx])))


def sample_logbf(obs: np.ndarray, pred_alt: np.ndarray, pred_cur: np.ndarray, nbins: int = 30,
                 n_boot: int = 40, seed: int = 0) -> tuple[float, float]:
    """Realised log Bayes factor log p(obs | alt) - log p(obs | cur) and its Monte Carlo noise.

    Densities are histograms of the registered forecast samples. Observations outside the predicted
    range fall into the outer bins (clipped), so a model that puts no mass where data fall is
    penalised through the pseudo-count, not with -inf. The second value is the bootstrap standard
    deviation over resampled forecasts (finite-sample noise of the forecast, not of the data).
    """
    obs = np.asarray(obs, float)
    pred_alt, pred_cur = np.asarray(pred_alt, float), np.asarray(pred_cur, float)
    edges = common_edges(pred_alt, pred_cur, obs, nbins=nbins)
    val = _lbf(obs, pred_alt, pred_cur, edges)
    rng = np.random.default_rng(seed)
    boots = [_lbf(obs, rng.choice(pred_alt, pred_alt.size), rng.choice(pred_cur, pred_cur.size), edges)
             for _ in range(n_boot)]
    return val, float(np.std(boots))
