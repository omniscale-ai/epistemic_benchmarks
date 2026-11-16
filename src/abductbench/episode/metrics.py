"""Episode metrics. Separate components, no aggregate score.

All distances are dimensionless: energies are divided by Q and momenta by p_Q (light-particle
momentum at kinetic energy Q); both are public. Energy distances (ED) are proper-score based:
a hedged mixture is not penalised relative to a confident guess when the data do not decide.

Behavioural class of a model (from probes, independent of what it declares):
- ``loss``: calorimeter median >= 0.95 Q and the spectrum mean drops by > 0.03 Q from t=0.5 to t=2;
- ``carrier``: calorimeter median <= 0.92 Q and the spectrum mean is insensitive to thickness;
- ``other``: anything else (mixtures, nonstandard models).
"""

from __future__ import annotations

import math

import numpy as np

from abductbench.episode import physics as ph
from abductbench.episode import reference as ref
from abductbench.episode.protocol import Session, Step
from abductbench.episode.world import HIDDEN_CHECK, World

N_EVAL = 2000
STRONG_EVIDENCE = 3.0  # nats; |realised log BF| below max(this, 2 x forecast-noise sd) is weak evidence
PROBES = (
    {"type": "calorimeter"},
    {"type": "spectrum", "thickness": 0.5},
    {"type": "spectrum", "thickness": 2.0},
    {"type": "recoil_coincidence", "thickness": ph.CHECK_THICKNESS},
)


# ---------------------------------------------------------------------------
# Distances
# ---------------------------------------------------------------------------


def ed1(x: np.ndarray, y: np.ndarray) -> float:
    """1-D energy distance 2 * integral (F - G)^2, exact for empirical CDFs."""
    x, y = np.sort(np.asarray(x, float)), np.sort(np.asarray(y, float))
    z = np.concatenate([x, y])
    z.sort()
    F = np.searchsorted(x, z[:-1], side="right") / x.size
    G = np.searchsorted(y, z[:-1], side="right") / y.size
    return float(2.0 * np.sum((F - G) ** 2 * np.diff(z)))


def _mean_pdist(a: np.ndarray, b: np.ndarray) -> float:
    tot = 0.0
    for i in range(0, a.shape[0], 500):
        d = a[i : i + 500, None, :] - b[None, :, :]
        tot += float(np.sqrt((d * d).sum(-1)).sum())
    return tot / (a.shape[0] * b.shape[0])


def ed2(X: np.ndarray, Y: np.ndarray) -> float:
    """Multivariate energy distance 2E|X-Y| - E|X-X'| - E|Y-Y'|."""
    return 2 * _mean_pdist(X, Y) - _mean_pdist(X, X) - _mean_pdist(Y, Y)


def _check_coords(sample: dict, Q: float, p_ref: float) -> np.ndarray:
    return np.column_stack([np.asarray(sample["kinetic_energy"]) / Q, np.asarray(sample["recoil_momentum"]) / p_ref])


KEY = {"spectrum": "kinetic_energy", "calorimeter": "deposited_energy"}


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------


def probe(model, world: World, n: int = N_EVAL) -> dict:
    """Behavioural probes. Each probe runs separately: a model that cannot answer one query (e.g. an
    alternative hypothesis written only for the calorimeter) still gets a class from the others."""
    Q, kin = world.Q, world.kin
    out: dict = {"errors": {}}
    got = {}
    for name, q in zip(("cal", "s05", "s2", "rc"), PROBES):
        try:
            got[name] = model.simulate_many([dict(q)], n, 424242)[0]
            if name == "cal":
                got[name]["deposited_energy"]
            elif name == "rc":
                got[name]["recoil_momentum"], got[name]["kinetic_energy"]
            else:
                got[name]["kinetic_energy"]
        except Exception as e:
            out["errors"][name] = f"{type(e).__name__}: {e}"[:300]
            got.pop(name, None)
    if "cal" not in got:
        return {"error": "calorimeter probe failed", **out}
    cal_ratio = float(np.median(got["cal"]["deposited_energy"]) / Q)
    shift = None
    if "s05" in got and "s2" in got:
        shift = float((np.mean(got["s05"]["kinetic_energy"]) - np.mean(got["s2"]["kinetic_energy"])) / Q)
    if shift is None:
        cls = "other"
    elif cal_ratio >= 0.95 and shift > 0.03:
        cls = "loss"
    elif cal_ratio <= 0.92 and abs(shift) <= 0.03:
        cls = "carrier"
    else:
        cls = "other"
    out.update({"cal_ratio": cal_ratio, "thickness_shift": shift, "class": cls})
    if "s05" in got:
        out["_s05"] = np.asarray(got["s05"]["kinetic_energy"]) / Q
    if "rc" in got:
        T = np.asarray(got["rc"]["kinetic_energy"]) / Q
        pR = np.asarray(got["rc"]["recoil_momentum"]) / Q
        out.update({"recoil_median_over_pQ": float(np.median(pR) / kin.p_ref),
                    "recoil_iqr_over_pQ": float(np.subtract(*np.percentile(pR, [75, 25])) / kin.p_ref),
                    "_T": T, "_pR": pR})
    return out


def mechanism_consistency(decl: dict | None, pr: dict, world: World) -> dict:
    """Does the executable model behave as its declared mechanism requires? (menu condition)"""
    if "error" in pr:
        return {"consistent": False, "reason": "probe failed"}
    if not decl or decl.get("kind") not in ("carrier", "loss"):
        return {"consistent": None, "reason": "no checkable declaration"}
    if "_pR" not in pr or "_s05" not in pr:
        return {"consistent": None, "reason": "model does not answer every probe: " + ", ".join(pr["errors"])}
    kin = world.kin
    if decl["kind"] == "loss":
        _, p2 = kin.two_body()
        ok_cls = pr["class"] == "loss"
        ok_recoil = abs(pr["recoil_median_over_pQ"] * kin.p_ref / p2 - 1.0) < 0.03 and pr["recoil_iqr_over_pQ"] < 0.1
        return {"consistent": bool(ok_cls and ok_recoil), "class_ok": ok_cls, "two_body_recoil_ok": bool(ok_recoil)}
    m = decl["mass"] / world.Q
    T, pR = pr["_T"], pr["_pR"]
    p1 = kin.p_light(T)
    E2 = 1.0 - T
    p2 = np.sqrt(np.maximum(E2 * E2 - m * m, 0.0))
    tol = 0.05 * kin.p_ref
    viol = float(np.mean((E2 < m - 0.06) | (pR > p1 + p2 + tol) | (pR < np.abs(p1 - p2) - tol)))
    endpoint = float(np.percentile(pr["_s05"], 99))
    ok_end = endpoint <= ph.carrier_T_max(kin, m) + 3 * ph.SIGMA_SPEC
    ok_cls = pr["class"] == "carrier"
    return {"consistent": bool(ok_cls and viol < 0.1 and ok_end), "class_ok": ok_cls,
            "kinematic_violation_frac": viol, "endpoint_ok": bool(ok_end)}


def behavioural_mass(pr: dict, world: World) -> float | None:
    """Carrier rest energy (units of Q) implied by what the model itself predicts.

    The reference carrier family is fitted to the model's own spectrometer energies on the thinnest
    source (t = 0.05, recoil-coincidence probe), where source loss is negligible. Defined only for
    models whose behaviour is carrier-like; it works the same with and without the menu.
    """
    if pr.get("class") != "carrier" or "_T" not in pr:
        return None
    T = pr["_T"]
    T = T[(T >= ph.WINDOW[0]) & (T <= ph.WINDOW[1])]
    if T.size < 100:
        return None
    q = {"type": "spectrum", "thickness": ph.CHECK_THICKNESS}
    return float(ref.fit_carrier(world.kin, [(q, {"kinetic_energy": T})]).h.m_x)


# ---------------------------------------------------------------------------
# Episode evaluation
# ---------------------------------------------------------------------------


class _Ctx:
    def __init__(self, s: Session):
        self.s = s
        self.w = s.world
        self.Q = s.world.Q
        self.kin = s.world.kin
        self._fits: dict[int, dict] = {}
        self._probes: dict[int, dict] = {}

    def internal(self, data):
        return [({k: v for k, v in q.items()}, self.w.to_internal(o)) for q, o in data]

    def fits(self, data) -> dict | None:
        if not data:
            return None
        key = len(data)
        if key not in self._fits:
            self._fits[key] = ref.fit_both(self.kin, self.internal(data))
        return self._fits[key]

    def probe(self, model) -> dict:
        k = id(model)
        if k not in self._probes:
            self._probes[k] = probe(model, self.w)
        return self._probes[k]

    def cls(self, h) -> str:
        """Class used for credence accounting: the declaration (menu) or the probed behaviour."""
        if self.s.cfg.menu and h.mechanism and h.mechanism.get("kind") in ("carrier", "loss"):
            return h.mechanism["kind"]
        return self.probe(h.model).get("class", "other")


def _p_carrier(ctx: _Ctx, step: Step) -> dict:
    by = {"carrier": 0.0, "loss": 0.0, "other": 0.0}
    for h in step.hyps:
        by[ctx.cls(h)] += h.credence
    by["unassigned"] = max(0.0, 1.0 - sum(by.values()))
    return by


def _uncertainty(agent: dict, fits) -> dict:
    """Agent credence vs what the data available at that moment support.

    ``ref_ambiguous``: the maximised likelihood ratio of the two reference families is below
    AMBIGUOUS_DLL (or there are no data). ``overconfident``: the agent puts >= 0.9 on one family
    although the data are ambiguous in that sense. The AIC posterior is reported for comparison.
    """
    post = ref.posterior(fits)
    d = ref.dll(fits)
    ambiguous = d is None or abs(d) < ref.AMBIGUOUS_DLL
    overconf = ambiguous and max(agent["carrier"], agent["loss"]) >= 0.9
    return {"agent_P_carrier": agent["carrier"], "agent_P_loss": agent["loss"], "ref_P_carrier": post["carrier"],
            "ref_dll_carrier_minus_loss": d, "abs_gap": abs(agent["carrier"] - post["carrier"]),
            "ref_ambiguous": bool(ambiguous), "overconfident": bool(overconf)}


def _corr(a: np.ndarray, b: np.ndarray) -> float | None:
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _current(step: Step):
    """The agent's operative hypothesis: highest credence; ties go to the one labelled 'current'.

    Agents sometimes move credence without relabelling roles (seen in a real run: 'current' at 0.03,
    'alternative' at 0.92). Credence is the stated belief; the label is bookkeeping.
    """
    return max(step.hyps, key=lambda h: (h.credence, h.role == "current"))


def _role_mismatch(step: Step) -> bool:
    labelled = next(h for h in step.hyps if h.role == "current")
    return _current(step) is not labelled and _current(step).credence > labelled.credence


def evaluate_session(s: Session, n: int = N_EVAL) -> dict:
    ctx = _Ctx(s)
    w, Q, kin = ctx.w, ctx.Q, ctx.kin
    res: dict = {"config": s.cfg.to_dict(), "truth_mechanism": s.cfg.mechanism}

    # Instance category from the reference posterior on the initial data (not from the truth).
    fA = ctx.fits(s.initial)
    pA = ref.posterior(fA)
    dA = ref.dll(fA)
    if dA is None:
        cat = "no_data"
    elif abs(dA) < ref.AMBIGUOUS_DLL:
        cat = "ambiguous"
    else:
        cat = "lean_carrier" if dA > 0 else "lean_loss"
    res["instance"] = {"ref_P_carrier_initial": pA["carrier"], "ref_dll_initial": dA, "category": cat,
                       "ref_m_fit_initial": None if fA is None else fA["carrier"].h.m_x * Q}

    regs = [st for st in s.steps if st.kind == "register"]
    final = next((st for st in s.steps if st.kind == "final"), None)
    seq = regs + ([final] if final else [])

    steps_out = []
    for i, st in enumerate(regs):
        cur = _current(st)
        alts = [h for h in st.hyps if h is not cur]
        alt = max(alts, key=lambda h: h.credence)
        key = KEY[st.measurement["type"]]
        nq = st.measurement["n"]
        data = s.data_until(st)
        fits = ctx.fits(data)
        mq = {k: v for k, v in st.measurement.items()}
        if fits is not None:
            ref_info = ref.expected_info(fits["carrier"].h, fits["loss"].h, kin, mq)
            best = max(v for _, v in ref.menu_info(fits, kin, nq))
        else:
            ref_info = best = float("nan")
        own_info = ref.sample_info(cur.forecast[key] / Q, alt.forecast[key] / Q, nq)
        rec = {
            "measurement": st.measurement,
            "classes": {h.id: ctx.cls(h) for h in st.hyps},
            "alternative_differs_in_class": ctx.cls(cur) != ctx.cls(alt),
            "role_label_mismatch": _role_mismatch(st),
            "design_info_own": own_info,
            "design_info_ref": ref_info,
            "design_info_ref_frac_of_menu_max": ref_info / best if best and math.isfinite(best) else None,
            "uncertainty_before": _uncertainty(_p_carrier(ctx, st), fits),
        }
        if st.observation is not None:
            obs = st.observation[key] / Q
            lbf, lbf_sd = ref.sample_logbf(obs, alt.forecast[key] / Q, cur.forecast[key] / Q)
            threshold = max(STRONG_EVIDENCE, 2.0 * lbf_sd)
            rec["forecast"] = {
                "ed_current": ed1(cur.forecast[key] / Q, obs),
                "ed_alternative": ed1(alt.forecast[key] / Q, obs),
                "logbf_alt_vs_current": lbf,
                "logbf_forecast_noise_sd": lbf_sd,
                "strong_threshold": threshold,
            }
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            if nxt is not None:
                before, after = ctx.cls(cur), ctx.cls(_current(nxt))
                switched = after != before
                if abs(lbf) < threshold:
                    verdict = "weak_evidence"
                elif lbf >= threshold:
                    verdict = "justified_switch" if switched else "unjustified_keep"
                else:
                    verdict = "unjustified_switch" if switched else "justified_keep"
                if not rec["alternative_differs_in_class"] and verdict != "weak_evidence":
                    verdict += "_same_class_alternative"
                f_after = ctx.fits(s.data_until(nxt))
                d_after = ref.dll(f_after)
                ref_cls = None if d_after is None or abs(d_after) < ref.AMBIGUOUS_DLL else ("carrier" if d_after > 0 else "loss")
                rec["revision"] = {"class_before": before, "class_after": after, "switched": switched,
                                   "verdict": verdict, "ref_class_after": ref_cls,
                                   "agrees_with_reference": None if ref_cls is None else after == ref_cls}
        steps_out.append(rec)
    res["steps"] = steps_out

    if final is None:
        res["final"] = None
        return res

    # Final: uncertainty, consistency, initial fit, hidden check.
    fits_all = ctx.fits(s.data_public())
    fin = {"uncertainty": _uncertainty(_p_carrier(ctx, final), fits_all),
           "current_class": ctx.cls(_current(final))}
    cons = {}
    for h in final.hyps:
        pr = ctx.probe(h.model)
        cons[h.id] = {"declared": h.mechanism, "behaviour": {k: v for k, v in pr.items() if not k.startswith("_")},
                      **mechanism_consistency(h.mechanism, pr, w)}
    fin["consistency"] = cons
    cur = _current(final)
    fin["current_consistent"] = cons[cur.id].get("consistent")
    fin["role_label_mismatch"] = _role_mismatch(final)
    fin["current_behavioural_mass_over_Q"] = behavioural_mass(ctx.probe(cur.model), w)
    if cur.mechanism and cur.mechanism.get("kind") == "carrier" and s.cfg.mechanism == "carrier":
        fin["carrier_mass_error_over_Q"] = abs(cur.mechanism["mass"] / Q - w.sh.m_x)

    pred = final.predictive
    try:
        init_q = {"type": "spectrum", "thickness": 1.0}
        pi, pc = pred.simulate_many([init_q, dict(HIDDEN_CHECK)], n, 777)
    except Exception as e:
        fin["predictive_error"] = str(e)[:500]
        res["final"] = fin
        return res
    truth_init = w.truth_sample(init_q, n, seed=1)["kinetic_energy"]
    fin["initial_fit_ed"] = ed1(pi["kinetic_energy"] / Q, truth_init)
    if fits_all is not None:
        for fam, f in fits_all.items():
            refs = ph.sample_query(f.h, kin, init_q, n, np.random.default_rng(5))["kinetic_energy"]
            fin[f"initial_fit_ed_ref_{fam}"] = ed1(refs, truth_init)
    t1 = w.truth_sample(HIDDEN_CHECK, n, seed=2)
    T1 = np.column_stack([t1["kinetic_energy"], t1["recoil_momentum"] / kin.p_ref])
    try:
        P = _check_coords(pc, Q, Q * kin.p_ref)
        fin["check_ed"] = ed2(P, T1)
        # Decomposition: which part of the new consequence is wrong (energy marginal, recoil marginal,
        # or the energy-recoil relation). Diagnostic only; check_ed remains the score.
        fin["check_parts"] = {
            "ed_energy": ed1(P[:, 0], T1[:, 0]),
            "ed_recoil": ed1(P[:, 1], T1[:, 1]),
            "corr_agent": _corr(P[:, 0], P[:, 1]),
            "corr_truth": _corr(T1[:, 0], T1[:, 1]),
        }
    except Exception as e:
        fin["check_error"] = str(e)[:500]
    t2 = w.truth_sample(HIDDEN_CHECK, n, seed=3)
    fin["check_ed_floor_truth"] = ed2(np.column_stack([t2["kinetic_energy"], t2["recoil_momentum"] / kin.p_ref]), T1)
    wp = World(s.cfg.paired())
    op = wp.truth_sample(HIDDEN_CHECK, n, seed=4)
    fin["check_ed_opposite_mechanism"] = ed2(np.column_stack([op["kinetic_energy"], op["recoil_momentum"] / kin.p_ref]), T1)
    res["final"] = fin
    return res
