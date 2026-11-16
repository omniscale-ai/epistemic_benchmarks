"""Local baselines and fake agents. All of them go through the same Session protocol as an agent.

Names say what each one knows. ``truth_fed`` receives the hidden truth: it is a protocol sanity
check and the noise floor of the metrics, NOT a solver. ``reference_*`` know the two candidate
families of the world rules and see only the agent's data (family-conditional solvers).
"""

from __future__ import annotations

import json
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from abductbench.episode import physics as ph
from abductbench.episode import reference as ref
from abductbench.episode.metrics import evaluate_session
from abductbench.episode.modelrun import Model, hypothesis_fn, mixture_fn
from abductbench.episode.protocol import Session
from abductbench.episode.world import MAX_N, EpisodeConfig, World

PRIOR_M = 0.15  # prior-typical carrier rest energy (units of Q)
PRIOR_MATERIAL = ph.Material(0.1, 2.1, 0.43)  # prior-typical loss-world material


def _internal(s: Session):
    return [(q, s.world.to_internal(o)) for q, o in s.data_public()]


def _fam_model(name: str, h: ph.Hypothesis, s: Session) -> Model:
    Q = s.world.Q
    if h.decay == "carrier":
        mech = {"kind": "carrier", "mass": h.m_x * Q}
    else:
        mech = {"kind": "loss"}
    return Model(name, fn=hypothesis_fn(h, s.world.kin, Q), mechanism=mech)


def _mixture(name: str, parts: list[tuple[float, Model]]) -> Model:
    parts = [(w, m) for w, m in parts if w > 1e-4]
    if len(parts) == 1:
        return parts[0][1]
    return Model(name, fn=mixture_fn([(w, m.fn) for w, m in parts]), mechanism={"kind": "other", "description": "mixture"})


def _choose(plan: str, fits, kin, rng) -> dict:
    if plan == "adaptive":
        return max(ref.menu_info(fits, kin, MAX_N), key=lambda x: x[1])[0]
    if plan == "repeat":
        return {"type": "spectrum", "thickness": 1.0, "n": MAX_N}
    if plan == "random":
        if rng.random() < 0.5:
            return {"type": "calorimeter", "n": MAX_N}
        return {"type": "spectrum", "thickness": float(rng.uniform(*ph.THICKNESS_RANGE)), "n": MAX_N}
    raise ValueError(plan)


def _hyp(hid, role, model_key, statement, credence):
    return {"id": hid, "role": role, "model": model_key, "statement": statement, "credence": credence}


def reference_solver(s: Session, plan: str = "adaptive", fixed: str | None = None, seed: int = 0) -> None:
    """Family-conditional reference: fit both families, choose a measurement, update, predict.

    ``fixed`` ('carrier' or 'loss') makes a stubborn fake agent that always keeps that class with
    credence 0.9 (it still fits parameters to the data).
    """
    kin = s.world.kin
    rng = np.random.default_rng([seed, 31337])
    while s.budget_left > 0:
        data = _internal(s)
        fits = ref.fit_both(kin, data) if data else {"carrier": ref.Fit("carrier", ref.carrier_h(PRIOR_M), 0, 1),
                                                       "loss": ref.Fit("loss", ph.Hypothesis("two_body", 0, PRIOR_MATERIAL), 0, 3)}
        post = ref.posterior(fits if data else None)
        cur = fixed or max(post, key=post.get)
        alt = "loss" if cur == "carrier" else "carrier"
        cred = {cur: 0.9, alt: 0.1} if fixed else post
        models = {"cur": _fam_model("cur", fits[cur].h, s), "alt": _fam_model("alt", fits[alt].h, s)}
        prereg = {
            "hypotheses": [_hyp("H1", "current", "cur", cur, cred[cur]), _hyp("H2", "alternative", "alt", alt, cred[alt])],
            "undetermined": "family and parameters",
            "measurement": _choose(plan, fits, kin, rng),
            "expected": {"H1": "model forecast", "H2": "model forecast"},
        }
        s.register(prereg, models)
        s.measure()
    data = _internal(s)
    if data:
        fits = ref.fit_both(kin, data)
        post = ref.posterior(fits)
        hc, hl = fits["carrier"].h, fits["loss"].h
    else:
        post = {"carrier": 0.5, "loss": 0.5}
        hc, hl = ref.carrier_h(PRIOR_M), ph.Hypothesis("two_body", 0.0, PRIOR_MATERIAL)
    mc, ml = _fam_model("c", hc, s), _fam_model("l", hl, s)
    if fixed:
        cred = {fixed: 0.9, ("loss" if fixed == "carrier" else "carrier"): 0.1}
        pred = mc if fixed == "carrier" else ml
    else:
        cred = post
        pred = _mixture("mix", [(post["carrier"], mc), (post["loss"], ml)])
    cur = max(cred, key=cred.get)
    s.final({"hypotheses": [_hyp("C", "current" if cur == "carrier" else "alternative", "c", "carrier", cred["carrier"]),
                            _hyp("L", "current" if cur == "loss" else "alternative", "l", "loss", cred["loss"])],
             "undetermined": "-", "predictive_model": "pred"}, {"c": mc, "l": ml, "pred": pred})


def no_data(s: Session) -> None:
    """Condition-only control: knows the families and prior-typical parameters, ignores all data."""
    mc = _fam_model("c", ref.carrier_h(PRIOR_M), s)
    ml = _fam_model("l", ph.Hypothesis("two_body", 0.0, PRIOR_MATERIAL), s)
    s.final({"hypotheses": [_hyp("C", "current", "c", "carrier", 0.5), _hyp("L", "alternative", "l", "loss", 0.5)],
             "undetermined": "everything", "predictive_model": "pred"},
            {"c": mc, "l": ml, "pred": _mixture("mix", [(0.5, mc), (0.5, ml)])})


def _pheno_fn(s: Session):
    """Fit-only predictor: resample the observed initial spectrum for every query; T0 recoil balance."""
    Q, kin = s.world.Q, s.world.kin
    T_obs = np.concatenate([o["kinetic_energy"] for q, o in s.initial if q["type"] == "spectrum"])
    lo, hi = s.meta["spectrometer_window"]
    bw = 0.5 * s.meta["spectrometer_sigma"]

    def draw(n, rng):
        x = rng.choice(T_obs, n) + rng.normal(0, bw, n)
        return np.clip(x, lo, hi)

    def fn(query, n, seed):
        rng = np.random.default_rng(seed)
        T = draw(n, rng)
        if query["type"] == "calorimeter":
            return {"deposited_energy": T}
        if query["type"] == "spectrum":
            return {"kinetic_energy": T}
        return {"kinetic_energy": T, "recoil_momentum": kin.p_light(T / Q) * Q}  # T0: daughter balances the particle

    return fn


def phenomenological(s: Session) -> None:
    pm = Model("pheno", fn=_pheno_fn(s), mechanism={"kind": "other", "description": "fitted curve"})
    t0 = _fam_model("t0", ph.Hypothesis("two_body", 0.0, ref.NEGLIGIBLE), s)
    t0.mechanism = {"kind": "other", "description": "T0"}
    models = {"p": pm, "t0": t0}
    while s.budget_left > 0:
        s.register({"hypotheses": [_hyp("P", "current", "p", "curve", 0.9), _hyp("T", "alternative", "t0", "T0", 0.1)],
                    "undetermined": "-", "measurement": {"type": "spectrum", "thickness": 1.0, "n": MAX_N},
                    "expected": {"P": "same curve", "T": "line"}}, models)
        s.measure()
    s.final({"hypotheses": [_hyp("P", "current", "p", "curve", 0.9)], "undetermined": "-", "predictive_model": "p"}, models)


def _textbook_fn(s: Session):
    """Memorised answer: massless carrier, Fermi spectrum p E (Q-T)^2, isotropic carrier direction."""
    Q, kin = s.world.Q, s.world.kin
    grid = np.linspace(0.0, 1.0, 20001)
    E = grid + kin.m_light
    pdf = kin.p_light(grid) * E * (1.0 - grid) ** 2
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (pdf[1:] + pdf[:-1]) * np.diff(grid))])
    cdf /= cdf[-1]

    def emit(n, rng):
        T = np.interp(rng.random(n), cdf, grid)
        pe, pv = kin.p_light(T), 1.0 - T
        c = rng.uniform(-1, 1, n)
        return T, np.sqrt(pe**2 + pv**2 + 2 * pe * pv * c)

    def fn(query, n, seed):
        rng = np.random.default_rng(seed)
        if query["type"] == "calorimeter":
            T, _ = emit(n, rng)
            return {"deposited_energy": (T + rng.normal(0, ph.SIGMA_CAL, n)) * Q}
        Ts, ps = [], []
        while sum(len(x) for x in Ts) < n:
            T, pR = emit(2 * n, rng)
            To = T + rng.normal(0, ph.SIGMA_SPEC, 2 * n)
            ok = (To >= ph.WINDOW[0]) & (To <= ph.WINDOW[1])
            Ts.append(To[ok])
            ps.append(pR[ok])
        T, pR = np.concatenate(Ts)[:n] * Q, np.concatenate(ps)[:n] * Q
        return {"kinetic_energy": T} if query["type"] == "spectrum" else {"kinetic_energy": T, "recoil_momentum": pR}

    return fn


def textbook(s: Session) -> None:
    tb = Model("textbook", fn=_textbook_fn(s), mechanism={"kind": "carrier", "mass": 0.0})
    ml = _fam_model("l", ph.Hypothesis("two_body", 0.0, PRIOR_MATERIAL), s)
    models = {"tb": tb, "l": ml}
    while s.budget_left > 0:
        s.register({"hypotheses": [_hyp("N", "current", "tb", "massless carrier", 0.95),
                                   _hyp("L", "alternative", "l", "loss", 0.05)],
                    "undetermined": "-", "measurement": {"type": "calorimeter", "n": MAX_N},
                    "expected": {"N": "deficit", "L": "line at Q"}}, models)
        s.measure()
    s.final({"hypotheses": [_hyp("N", "current", "tb", "massless carrier", 0.95)], "undetermined": "-",
             "predictive_model": "tb"}, models)


def truth_fed(s: Session) -> None:
    """SANITY CHECK ONLY: is handed the hidden truth. Not a solver."""
    w = s.world
    true = Model("truth", fn=hypothesis_fn(w.truth, w.kin, w.Q),
                 mechanism={"kind": "carrier", "mass": w.truth.m_x * w.Q} if w.truth.decay == "carrier" else {"kind": "loss"})
    other = World(s.cfg.paired())
    wrong = Model("wrong", fn=hypothesis_fn(other.truth, w.kin, w.Q),
                  mechanism={"kind": "carrier", "mass": other.truth.m_x * w.Q} if other.truth.decay == "carrier" else {"kind": "loss"})
    models = {"t": true, "w": wrong}
    while s.budget_left > 0:
        s.register({"hypotheses": [_hyp("T", "current", "t", "truth", 1.0), _hyp("W", "alternative", "w", "paired", 0.0)],
                    "undetermined": "-", "measurement": {"type": "calorimeter", "n": MAX_N},
                    "expected": {"T": "-", "W": "-"}}, models)
        s.measure()
    s.final({"hypotheses": [_hyp("T", "current", "t", "truth", 1.0)], "undetermined": "-", "predictive_model": "t"}, models)


POLICIES = {
    "reference_adaptive": lambda s: reference_solver(s, "adaptive"),
    "reference_repeat": lambda s: reference_solver(s, "repeat"),
    "reference_random": lambda s: reference_solver(s, "random", seed=s.cfg.world_seed),
    "stubborn_carrier": lambda s: reference_solver(s, "adaptive", fixed="carrier"),
    "stubborn_loss": lambda s: reference_solver(s, "adaptive", fixed="loss"),
    "no_data": no_data,
    "phenomenological": phenomenological,
    "textbook": textbook,
    "truth_fed": truth_fed,
}


def run_one(args) -> dict:
    policy, cfg_dict = args
    cfg = EpisodeConfig.from_dict(cfg_dict)
    s = Session(cfg)
    POLICIES[policy](s)
    r = evaluate_session(s)
    r["policy"] = policy
    return r


# ---------------------------------------------------------------------------
# Single-feature heuristic and initial identifiability study (no protocol needed)
# ---------------------------------------------------------------------------


def _features(cfg: EpisodeConfig) -> dict:
    w = World(cfg)
    T = w.to_internal(w.observe_initial()[0][1])["kinetic_energy"]
    return {"mean": float(T.mean()), "frac_above_0.8": float(np.mean(T > 0.8)), "std": float(T.std()),
            "q90": float(np.percentile(T, 90))}


def _auc(pos: np.ndarray, neg: np.ndarray) -> float:
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1
    return float((r[: pos.size].sum() - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def heuristic_study(train=range(100, 300), test=range(0, 100), processes: int = 8) -> dict:
    """Best single spectral feature at A: threshold fitted on train seeds, accuracy/AUC on test seeds."""
    cfgs = [EpisodeConfig(sd, m) for sd in list(train) + list(test) for m in ("carrier", "loss")]
    with Pool(processes) as p:
        feats = p.map(_features, cfgs)
    rows = [(c.world_seed, c.mechanism, f) for c, f in zip(cfgs, feats)]
    out = {}
    tr = [r for r in rows if r[0] in set(train)]
    te = [r for r in rows if r[0] in set(test)]
    for name in rows[0][2]:
        xs = np.array([r[2][name] for r in tr])
        ys = np.array([r[1] == "carrier" for r in tr])
        best = (0.0, 0.0, 1)
        for thr in np.unique(xs):
            for sign in (1, -1):
                acc = float(np.mean((sign * (xs - thr) > 0) == ys))
                if acc > best[0]:
                    best = (acc, float(thr), sign)
        xt = np.array([r[2][name] for r in te])
        yt = np.array([r[1] == "carrier" for r in te])
        acc_t = float(np.mean((best[2] * (xt - best[1]) > 0) == yt))
        out[name] = {"train_acc": best[0], "test_acc": acc_t,
                     "test_auc": _auc(best[2] * xt[yt], best[2] * xt[~yt])}
    return out


def posterior_study(seeds=range(0, 40), processes: int = 8) -> list[dict]:
    with Pool(processes) as p:
        return p.map(_post_one, [(sd, m) for sd in seeds for m in ("carrier", "loss")])


def _post_one(args) -> dict:
    sd, m = args
    w = World(EpisodeConfig(sd, m))
    data = [(q, w.to_internal(o)) for q, o in w.observe_initial()]
    fits = ref.fit_both(w.kin, data)
    return {"world_seed": sd, "mechanism": m, "ref_P_carrier": ref.posterior(fits)["carrier"],
            "ref_dll": ref.dll(fits), "match_kl": w.match_kl}


def run_table(policies, seeds, conditions=("ambiguous",), processes: int = 8) -> list[dict]:
    jobs = [(p, EpisodeConfig(sd, m, condition=c).to_dict()) for p in policies for c in conditions
            for sd in seeds for m in ("carrier", "loss")]
    with Pool(processes) as pool:
        return pool.map(run_one, jobs)


def summarise(rows: list[dict]) -> list[dict]:
    """Per (policy, condition, mechanism): means of the separate components (no aggregate)."""
    groups: dict = {}
    for r in rows:
        k = (r["policy"], r["config"]["condition"], r["truth_mechanism"])
        groups.setdefault(k, []).append(r)
    out = []

    def mean(xs):
        xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
        return float(np.mean(xs)) if xs else None

    for (pol, cond, mech), rs in sorted(groups.items()):
        fin = [r["final"] or {} for r in rs]
        st0 = [r["steps"][0] if r["steps"] else {} for r in rs]
        rev = [s.get("revision", {}).get("verdict") for s in st0]
        out.append({
            "policy": pol, "condition": cond, "mechanism": mech, "n": len(rs),
            "final_class_correct": mean([float(f.get("current_class") == mech) for f in fin]),
            "final_P_true": mean([f.get("uncertainty", {}).get(f"agent_P_{mech}") for f in fin]),
            "final_ref_P_true": mean([(f.get("uncertainty", {}).get("ref_P_carrier") if mech == "carrier"
                                       else 1 - f.get("uncertainty", {}).get("ref_P_carrier", float("nan"))) for f in fin]),
            "overconfident_final": mean([float(f.get("uncertainty", {}).get("overconfident", False)) for f in fin]),
            "initial_fit_ed": mean([f.get("initial_fit_ed") for f in fin]),
            "check_ed": mean([f.get("check_ed") for f in fin]),
            "check_floor": mean([f.get("check_ed_floor_truth") for f in fin]),
            "check_opposite": mean([f.get("check_ed_opposite_mechanism") for f in fin]),
            "design_info_ref_step1": mean([s.get("design_info_ref") for s in st0]),
            "design_frac_menu_max_step1": mean([s.get("design_info_ref_frac_of_menu_max") for s in st0]),
            "forecast_ed_current_step1": mean([s.get("forecast", {}).get("ed_current") for s in st0]),
            "revision_step1": {v: rev.count(v) for v in sorted(set(x for x in rev if x))},
            "consistent_current": mean([None if f.get("current_consistent") is None else float(f["current_consistent"])
                                        for f in fin]),
            "categories": {c: [r["instance"]["category"] for r in rs].count(c)
                           for c in sorted(set(r["instance"]["category"] for r in rs))},
        })
    return out


def save(rows, summary, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
