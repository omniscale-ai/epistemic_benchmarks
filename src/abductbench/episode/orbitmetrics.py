"""Orbit episode metrics (separate components, no aggregate; distances in units of the noise SIGMA).

Behavioural class of a model (independent of what it declares):
- ``body``: the model predicts that a sky search finds something beyond false detections (summed over 36
  windows covering the sky at t = 1, expected excess >= 0.4);
- ``force``: no predicted object, but the model explains the target's anomaly (rms of its predicted target
  residual over the initial window >= 2 arcsec);
- ``other``: anything else (e.g. T0 itself).
"""

from __future__ import annotations

import math

import numpy as np

from abductbench.episode import orbitfamily as of
from abductbench.episode import orbitworld as ow
from abductbench.episode.metrics import STRONG_EVIDENCE, _current, _role_mismatch, ed1
from abductbench.episode.protocol import Session, Step
from abductbench.episode.world import EpisodeConfig

N_EVAL = 200
VAR_FLOOR = (0.5 * ow.SIGMA) ** 2
SWEEP = [{"type": "search", "time": 1.0, "lon_min": float(a), "lon_max": float(a + 10)} for a in range(0, 360, 10)]


def _gauss(sample):
    r = np.asarray(sample, float)
    return r.mean(0), np.maximum(r.var(0), VAR_FLOOR)


def _loglik(obs, mu, var) -> float:
    return float(np.sum(-0.5 * (obs - mu) ** 2 / var - 0.5 * np.log(2 * math.pi * var)))


def _count_probs(c, kmax: int = 6):
    h = np.bincount(np.minimum(np.asarray(c, int), kmax), minlength=kmax + 1).astype(float) + 0.5
    return h / h.sum()


def own_info(fa: dict, fb: dict) -> float:
    if "count" in fa:
        p, q = _count_probs(fa["count"]), _count_probs(fb["count"])
        return float(0.5 * (np.sum(p * np.log(p / q)) + np.sum(q * np.log(q / p))))
    return of.gauss_info(*_gauss(fa["residual_arcsec"]), *_gauss(fb["residual_arcsec"]))


def realised_logbf(obs: dict, f_alt: dict, f_cur: dict, n_boot: int = 40) -> tuple[float, float]:
    rng = np.random.default_rng(0)
    if "count" in f_alt:
        c = int(np.asarray(obs["count"]).ravel()[0])
        k = min(c, 6)
        val = math.log(_count_probs(f_alt["count"])[k]) - math.log(_count_probs(f_cur["count"])[k])
        return val, 0.0
    y = np.asarray(obs["residual_arcsec"], float)
    A, C = np.asarray(f_alt["residual_arcsec"]), np.asarray(f_cur["residual_arcsec"])
    val = _loglik(y, *_gauss(A)) - _loglik(y, *_gauss(C))
    boots = [_loglik(y, *_gauss(A[rng.integers(0, len(A), len(A))])) - _loglik(y, *_gauss(C[rng.integers(0, len(C), len(C))]))
             for _ in range(n_boot)]
    return val, float(np.std(boots))


def probe(model, seed: int) -> dict:
    out: dict = {"errors": {}}
    try:
        counts = []
        for k in range(0, len(SWEEP), 6):  # chunks: each call to an agent model has its own CPU limit
            counts += model.simulate_many([dict(q) for q in SWEEP[k:k + 6]], 100, 5151 + k)
        excess = float(sum(np.mean(c["count"]) for c in counts) - ow.FALSE_RATE * len(SWEEP))
        lon_pred = [q["lon_min"] + 5 for q, c in zip(SWEEP, counts) if np.mean(c["count"]) > ow.FALSE_RATE + 0.2]
        out.update({"search_excess": excess, "predicted_object_windows": lon_pred[:6]})
    except Exception as e:
        out["errors"]["search"] = f"{type(e).__name__}: {e}"[:300]
        excess = 0.0
    try:
        r = model.simulate_many([dict(of.INITIAL_QUERY)], 100, 6161)[0]["residual_arcsec"]
        out["target_rms"] = float(np.sqrt(np.mean(np.mean(r, 0) ** 2)))
    except Exception as e:
        out["errors"]["residuals"] = f"{type(e).__name__}: {e}"[:300]
        out["target_rms"] = 0.0
    out["class"] = "body" if excess >= 0.4 else ("force" if out["target_rms"] >= 2.0 else "other")
    return out


class _Ctx:
    def __init__(self, s: Session):
        self.s, self.seed = s, s.cfg.world_seed
        self._fits, self._probes = {}, {}

    def fits(self, data):
        if not data:
            return None
        k = len(data)
        if k not in self._fits:
            self._fits[k] = of.fit_both(self.seed, data)
        return self._fits[k]

    def probe(self, model):
        if id(model) not in self._probes:
            self._probes[id(model)] = probe(model, self.seed)
        return self._probes[id(model)]

    def cls(self, h) -> str:
        if self.s.cfg.menu and h.mechanism and h.mechanism.get("kind") in ("body", "force"):
            return h.mechanism["kind"]
        return self.probe(h.model)["class"]


def _uncertainty(ctx: _Ctx, step: Step, fits) -> dict:
    by = {"body": 0.0, "force": 0.0, "other": 0.0}
    for h in step.hyps:
        by[ctx.cls(h)] += h.credence
    post = of.posterior(fits)
    d = of.dll(fits)
    amb = d is None or abs(d) < 3.0
    return {"agent_P_body": by["body"], "agent_P_force": by["force"], "ref_P_body": post["body"],
            "ref_dll_body_minus_force": d, "ref_ambiguous": bool(amb),
            "overconfident": bool(amb and max(by["body"], by["force"]) >= 0.9)}


def _check(model, s: Session, n: int) -> dict:
    """Mean per-point 1-D energy distance (sigma units) per check block; and the block means."""
    w = s.world
    preds = model.simulate_many([dict(q) for q in of.CHECK_QUERIES], n, 9090)
    blocks = {}
    for i, (q, p) in enumerate(zip(of.CHECK_QUERIES, preds)):
        tr = w.truth_sample(q, n, seed=100 + i)["residual_arcsec"] / ow.SIGMA
        pr = np.asarray(p["residual_arcsec"], float) / ow.SIGMA
        blocks[q["planet"] + ("_dense" if q["planet"] == of.TARGET else "")] = float(np.mean([ed1(pr[:, t], tr[:, t]) for t in range(tr.shape[1])]))
    return {"check_ed": float(np.mean(list(blocks.values()))), "check_blocks": blocks}


class _TruthModel:
    def __init__(self, cfg: EpisodeConfig, seed_off: int):
        self.w = of.OrbitWorld(cfg)
        self.off = seed_off

    def simulate_many(self, qs, n, seed):
        return [self.w.truth_sample(q, n, seed=self.off + i) for i, q in enumerate(qs)]


def evaluate_orbit_session(s: Session, n: int = N_EVAL) -> dict:
    ctx = _Ctx(s)
    seed = ctx.seed
    res: dict = {"config": s.cfg.to_dict(), "truth_mechanism": s.cfg.mechanism, "family": "orbit"}
    fA = ctx.fits(s.initial)
    dA = of.dll(fA)
    cat = "no_data" if dA is None else ("ambiguous" if abs(dA) < 3.0 else ("lean_body" if dA > 0 else "lean_force"))
    res["instance"] = {"ref_dll_initial": dA, "ref_P_body_initial": of.posterior(fA)["body"], "category": cat,
                       "match_rms_arcsec": ow.force_params(seed)[2]}
    regs = [st for st in s.steps if st.kind == "register"]
    final = next((st for st in s.steps if st.kind == "final"), None)
    seq = regs + ([final] if final else [])
    steps = []
    for i, st in enumerate(regs):
        cur = _current(st)
        alt = max([h for h in st.hyps if h is not cur], key=lambda h: h.credence)
        fits = ctx.fits(s.data_until(st))
        mq = s.fam.model_query(st.measurement)
        if fits is not None:
            ref_info = of.expected_info(seed, fits["body"], fits["force"], st.measurement)
            best = max(v for _, v in of.menu_info(seed, fits))
        else:
            ref_info = best = float("nan")
        rec = {"measurement": st.measurement, "classes": {h.id: ctx.cls(h) for h in st.hyps},
               "alternative_differs_in_class": ctx.cls(cur) != ctx.cls(alt), "role_label_mismatch": _role_mismatch(st),
               "design_info_own": own_info(cur.forecast, alt.forecast), "design_info_ref": ref_info,
               "design_info_ref_frac_of_menu_max": ref_info / best if best and math.isfinite(best) and best > 0 else None,
               "uncertainty_before": _uncertainty(ctx, st, fits)}
        if st.observation is not None:
            lbf, sd = realised_logbf(st.observation, alt.forecast, cur.forecast)
            thr = max(STRONG_EVIDENCE, 2 * sd)
            f = {"logbf_alt_vs_current": lbf, "logbf_forecast_noise_sd": sd, "strong_threshold": thr}
            if "residual_arcsec" in st.observation:
                y = np.asarray(st.observation["residual_arcsec"], float)
                f["rms_current_sigma"] = float(np.sqrt(np.mean((np.mean(cur.forecast["residual_arcsec"], 0) - y) ** 2)) / ow.SIGMA)
                f["rms_alternative_sigma"] = float(np.sqrt(np.mean((np.mean(alt.forecast["residual_arcsec"], 0) - y) ** 2)) / ow.SIGMA)
            rec["forecast"] = f
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            if nxt is not None:
                before, after = ctx.cls(cur), ctx.cls(_current(nxt))
                switched = before != after
                if abs(lbf) < thr:
                    v = "weak_evidence"
                elif lbf >= thr:
                    v = "justified_switch" if switched else "unjustified_keep"
                else:
                    v = "unjustified_switch" if switched else "justified_keep"
                if not rec["alternative_differs_in_class"] and v != "weak_evidence":
                    v += "_same_class_alternative"
                # Second, external verdict: does the agent's class after the observation agree with what the
                # reference prefers on the same data? (The first verdict is relative to the agent's own models.)
                f_after = ctx.fits(s.data_until(nxt))
                p_after = of.posterior(f_after)
                d_after = of.dll(f_after)
                ref_cls = None if d_after is None or abs(d_after) < 3.0 else ("body" if d_after > 0 else "force")
                rec["revision"] = {"class_before": before, "class_after": after, "switched": switched, "verdict": v,
                                   "ref_P_body_after": p_after["body"], "ref_class_after": ref_cls,
                                   "agrees_with_reference": None if ref_cls is None else after == ref_cls}
        steps.append(rec)
    res["steps"] = steps
    if final is None:
        res["final"] = None
        return res
    fits_all = ctx.fits(s.data_public())
    cur = _current(final)
    fin = {"uncertainty": _uncertainty(ctx, final, fits_all), "current_class": ctx.cls(cur),
           "role_label_mismatch": _role_mismatch(final)}
    cons = {}
    for h in final.hyps:
        pr = ctx.probe(h.model)
        decl = h.mechanism
        ok = None
        if s.cfg.menu and decl and decl.get("kind") in ("body", "force"):
            ok = pr["class"] == decl["kind"]
        cons[h.id] = {"declared": decl, "behaviour": pr, "consistent": ok}
    fin["consistency"] = cons
    fin["current_consistent"] = cons[cur.id]["consistent"]
    a_b, ph, m, _ = ow.body_params(seed)
    n_f, k_f, _ = ow.force_params(seed)
    fin["truth_params"] = {"a_ratio": a_b / ow.system(seed).elements[0, 0], "gm": m} if s.cfg.mechanism == "body" else {"n": n_f, "k": k_f}
    if cur.mechanism and cur.mechanism.get("kind") == "body":
        fin["declared_body"] = {"a_ratio": cur.mechanism["a"] / ow.system(seed).elements[0, 0], "gm": cur.mechanism["gm"]}
    if cur.mechanism and cur.mechanism.get("kind") == "force":
        fin["declared_force"] = {"n": cur.mechanism["n"], "k": cur.mechanism.get("k")}
    try:
        fin.update(_check(final.predictive, s, n))
    except Exception as e:
        fin["check_error"] = str(e)[:500]
    fin["check_ed_floor_truth"] = _check(_TruthModel(s.cfg, 500), s, n)["check_ed"]
    opp = _check(_TruthModel(s.cfg.paired(), 700), s, n)
    fin["check_ed_opposite_mechanism"] = opp["check_ed"]
    try:
        r = final.predictive.simulate_many([dict(of.INITIAL_QUERY)], n, 31)[0]["residual_arcsec"]
        t = s.world.truth_sample(of.INITIAL_QUERY, n, seed=32)["residual_arcsec"]
        fin["initial_fit_ed"] = float(np.mean([ed1(r[:, j] / ow.SIGMA, t[:, j] / ow.SIGMA) for j in range(t.shape[1])]))
    except Exception as e:
        fin["initial_fit_error"] = str(e)[:300]
    res["final"] = fin
    return res
