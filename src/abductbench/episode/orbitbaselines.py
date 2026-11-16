"""Orbit-episode baselines and fake agents, all through the Session protocol (cf. baselines.py).

``truth_fed`` is handed the hidden truth: a sanity check and the metric floor, not a solver.
``reference_*`` know the two families of the world rules and see only the episode's data.
``textbook``: the memorised answer for a Mercury-like anomaly — no hidden body, a relativity-like extra
central force ~ 1/r^4 (k fitted to the target's initial residuals), held with credence 0.95.
"""

from __future__ import annotations

import math
from multiprocessing import Pool

import numpy as np

from abductbench.episode import orbitfamily as of
from abductbench.episode import orbitworld as ow
from abductbench.episode.modelrun import Model, mixture_fn
from abductbench.episode.orbitmetrics import evaluate_orbit_session
from abductbench.episode.protocol import Session
from abductbench.episode.world import EpisodeConfig


def _model(name: str, seed: int, fit: of.OFit) -> Model:
    if fit.family == "body":
        aT = ow.system(seed).elements[0, 0]
        mech = {"kind": "body", "a": fit.params["a_ratio"] * aT, "gm": max(fit.params["m"], 1e-12)}
    else:
        mech = {"kind": "force", "n": fit.params["n"], "k": fit.params["k"]}
    return Model(name, fn=of.fit_fn(seed, fit), mechanism=mech)


def _hyp(hid, role, key, statement, cred):
    return {"id": hid, "role": role, "model": key, "statement": statement, "credence": cred}


def _choose(plan: str, seed: int, fits, rng) -> dict:
    if plan == "adaptive":
        return max(of.menu_info(seed, fits), key=lambda x: x[1])[0]
    if plan == "repeat":
        return {"type": "extend"}
    if plan == "random":
        k = rng.integers(4)
        if k == 0:
            return {"type": "planet", "planet": str(rng.choice(ow.PLANETS[1:]))}
        if k == 1:
            return {"type": "extend"}
        if k == 2:
            return {"type": "dense", "start": float(rng.uniform(*ow.DENSE_START))}
        lo = float(rng.uniform(0, 360))
        return {"type": "search", "time": float(rng.uniform(*ow.SEARCH_TIME)), "lon_min": lo, "lon_max": (lo + 10) % 360}
    raise ValueError(plan)


def _prior_fits(seed: int) -> dict:
    """Prior-typical members of both families (no data): unit-amplitude scaled to 40 arcsec at t = 10."""
    out = {}
    fb = of.OFit("body", {"a_ratio": 0.26, "phase": 0.0, "m": 1.0}, 0.0, 3)
    r10 = of.predict_mean(seed, fb, 0, [10.0])[0]
    fb.params["m"] = 40.0 / abs(r10)
    out["body"] = fb
    ff = of.OFit("force", {"n": 4.25, "k": 1.0}, 0.0, 2)
    r10 = of.predict_mean(seed, ff, 0, [10.0])[0]
    ff.params["k"] = 40.0 / r10
    out["force"] = ff
    return out


def reference_solver(s: Session, plan: str = "adaptive", fixed: str | None = None, seed_rng: int = 0) -> None:
    seed = s.cfg.world_seed
    rng = np.random.default_rng([seed_rng, 99])
    while s.budget_left > 0:
        data = s.data_public()
        fits = of.fit_both(seed, data) if data else _prior_fits(seed)
        post = of.posterior(fits if data else None)
        cur = fixed or max(post, key=post.get)
        alt = "force" if cur == "body" else "body"
        cred = {cur: 0.9, alt: 0.1} if fixed else post
        models = {"cur": _model("cur", seed, fits[cur]), "alt": _model("alt", seed, fits[alt])}
        s.register({"hypotheses": [_hyp("H1", "current", "cur", cur, cred[cur]), _hyp("H2", "alternative", "alt", alt, cred[alt])],
                    "undetermined": "family and parameters", "measurement": _choose(plan, seed, fits, rng),
                    "expected": {"H1": "forecast", "H2": "forecast"}}, models)
        s.measure()
    data = s.data_public()
    fits = of.fit_both(seed, data) if data else _prior_fits(seed)
    post = of.posterior(fits) if data else {"body": 0.5, "force": 0.5}
    mb, mf = _model("b", seed, fits["body"]), _model("f", seed, fits["force"])
    if fixed:
        cred = {fixed: 0.9, ("force" if fixed == "body" else "body"): 0.1}
        pred = mb if fixed == "body" else mf
    else:
        cred = post
        parts = [(w, m) for w, m in ((post["body"], mb), (post["force"], mf)) if w > 1e-4]
        pred = parts[0][1] if len(parts) == 1 else Model("mix", fn=mixture_fn([(w, m.fn) for w, m in parts]),
                                                         mechanism={"kind": "other", "description": "mixture"})
    cur = max(cred, key=cred.get)
    s.final({"hypotheses": [_hyp("B", "current" if cur == "body" else "alternative", "b", "body", cred["body"]),
                            _hyp("F", "current" if cur == "force" else "alternative", "f", "force", cred["force"])],
             "undetermined": "-", "predictive_model": "pred"}, {"b": mb, "f": mf, "pred": pred})


def no_data(s: Session) -> None:
    """Condition-only control: prior-typical members of both families, ignores all data.

    The body is spread over all phases (no data fixes it); the force sign is unknown (+/-)."""
    seed = s.cfg.world_seed
    pf = _prior_fits(seed)
    bodies = [of.OFit("body", {**pf["body"].params, "phase": float(p)}, 0, 3) for p in of.PHASES[::3]]
    forces = [of.OFit("force", {**pf["force"].params, "k": sg * pf["force"].params["k"]}, 0, 2) for sg in (1, -1)]
    mb = Model("b", fn=mixture_fn([(1.0, of.fit_fn(seed, f)) for f in bodies]),
               mechanism={"kind": "body", "a": 0.26 * ow.system(seed).elements[0, 0], "gm": pf["body"].params["m"]})
    mf = Model("f", fn=mixture_fn([(1.0, of.fit_fn(seed, f)) for f in forces]), mechanism={"kind": "force", "n": 4.25, "k": 0.0})
    mix = Model("mix", fn=mixture_fn([(0.5, mb.fn), (0.5, mf.fn)]), mechanism={"kind": "other", "description": "prior mixture"})
    s.final({"hypotheses": [_hyp("B", "current", "b", "body", 0.5), _hyp("F", "alternative", "f", "force", 0.5)],
             "undetermined": "everything", "predictive_model": "mix"}, {"b": mb, "f": mf, "mix": mix})


def _pheno_fn(s: Session):
    """Fit-only: quadratic in time through the target's initial residuals; nothing for other planets."""
    q, o = s.initial[0]
    p = np.polyfit(np.asarray(o["time"]), np.asarray(o["residual_arcsec"]), 2)

    def fn(query, n, seed):
        rng = np.random.default_rng(seed)
        if query["type"] == "search":
            return {"count": rng.poisson(ow.FALSE_RATE, n).astype(float)}
        t = np.asarray(query["times"], float)
        mu = np.polyval(p, t) if query["planet"] == of.TARGET else np.zeros_like(t)
        return {"residual_arcsec": mu[None, :] + rng.normal(0, ow.SIGMA, (n, len(t)))}

    return fn


def phenomenological(s: Session) -> None:
    pm = Model("pheno", fn=_pheno_fn(s), mechanism={"kind": "other", "description": "quadratic fit"})
    t0 = Model("t0", fn=lambda q, n, sd: ({"count": np.random.default_rng(sd).poisson(ow.FALSE_RATE, n).astype(float)}
                                          if q["type"] == "search" else
                                          {"residual_arcsec": np.random.default_rng(sd).normal(0, ow.SIGMA, (n, len(q["times"])))}),
               mechanism={"kind": "other", "description": "T0"})
    models = {"p": pm, "t0": t0}
    while s.budget_left > 0:
        s.register({"hypotheses": [_hyp("P", "current", "p", "curve", 0.9), _hyp("T", "alternative", "t0", "T0", 0.1)],
                    "undetermined": "-", "measurement": {"type": "extend"}, "expected": {"P": "curve", "T": "zero"}}, models)
        s.measure()
    s.final({"hypotheses": [_hyp("P", "current", "p", "curve", 0.9)], "undetermined": "-", "predictive_model": "p"}, models)


def textbook(s: Session) -> None:
    seed = s.cfg.world_seed
    data = s.data_public()
    i = int(np.argmin(np.abs(ow.N_GRID - 4.0)))
    if data:
        res, _ = of._residual_data(data)
        R = np.concatenate([np.interp(t, ow.grid(), ow.force_basis(seed)[i][:, p]) for p, t, _ in res])
        y = np.concatenate([v for _, _, v in res])
        k = float((R @ y) / (R @ R))
    else:
        k = _prior_fits(seed)["force"].params["k"]
    gr = Model("gr", fn=of.fit_fn(seed, of.OFit("force", {"n": 4.0, "k": k}, 0, 2)), mechanism={"kind": "force", "n": 4.0, "k": k})
    fb = _prior_fits(seed)["body"]
    vb = _model("v", seed, fb)
    models = {"gr": gr, "v": vb}
    while s.budget_left > 0:
        s.register({"hypotheses": [_hyp("G", "current", "gr", "relativity-like correction", 0.95),
                                   _hyp("V", "alternative", "v", "inner planet", 0.05)],
                    "undetermined": "-", "measurement": {"type": "extend"}, "expected": {"G": "-", "V": "-"}}, models)
        s.measure()
    s.final({"hypotheses": [_hyp("G", "current", "gr", "relativity-like correction", 0.95)], "undetermined": "-",
             "predictive_model": "gr"}, models)


def truth_fed(s: Session) -> None:
    """SANITY CHECK ONLY: handed the hidden truth."""
    w = s.world
    mech = s.cfg.mechanism

    def fn(q, n, sd):
        return w.sample(q, n, np.random.default_rng(sd))

    a_b, _, m, _ = ow.body_params(s.cfg.world_seed)
    nf, kf, _ = ow.force_params(s.cfg.world_seed)
    decl = {"kind": "body", "a": a_b, "gm": m} if mech == "body" else {"kind": "force", "n": nf, "k": kf}
    t = Model("t", fn=fn, mechanism=decl)
    other = of.OrbitWorld(s.cfg.paired())
    o = Model("o", fn=lambda q, n, sd: other.sample(q, n, np.random.default_rng(sd)),
              mechanism={"kind": "force", "n": nf, "k": kf} if mech == "body" else {"kind": "body", "a": a_b, "gm": m})
    models = {"t": t, "o": o}
    while s.budget_left > 0:
        s.register({"hypotheses": [_hyp("T", "current", "t", "truth", 1.0), _hyp("O", "alternative", "o", "paired", 0.0)],
                    "undetermined": "-", "measurement": {"type": "planet", "planet": ow.PLANETS[1]},
                    "expected": {"T": "-", "O": "-"}}, models)
        s.measure()
    s.final({"hypotheses": [_hyp("T", "current", "t", "truth", 1.0)], "undetermined": "-", "predictive_model": "t"}, models)


POLICIES = {
    "reference_adaptive": lambda s: reference_solver(s, "adaptive"),
    "reference_repeat": lambda s: reference_solver(s, "repeat"),
    "reference_random": lambda s: reference_solver(s, "random", seed_rng=s.cfg.world_seed),
    "stubborn_body": lambda s: reference_solver(s, "adaptive", fixed="body"),
    "stubborn_force": lambda s: reference_solver(s, "adaptive", fixed="force"),
    "no_data": no_data,
    "phenomenological": phenomenological,
    "textbook": textbook,
    "truth_fed": truth_fed,
}


def run_one(args) -> dict:
    policy, cfg_dict = args
    s = Session(EpisodeConfig.from_dict(cfg_dict))
    POLICIES[policy](s)
    r = evaluate_orbit_session(s)
    r["policy"] = policy
    return r


def run_table(policies, seeds, conditions=("ambiguous",), processes: int = 6) -> list[dict]:
    jobs = [(p, EpisodeConfig(sd, m, condition=c, family="orbit").to_dict()) for p in policies for c in conditions
            for sd in seeds for m in ("body", "force")]
    with Pool(processes) as pool:
        return pool.map(run_one, jobs)


def summarise(rows: list[dict]) -> list[dict]:
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["policy"], r["config"]["condition"], r["truth_mechanism"]), []).append(r)

    def mean(xs):
        xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
        return float(np.mean(xs)) if xs else None

    out = []
    for (pol, cond, mech), rs in sorted(groups.items()):
        fin = [r["final"] or {} for r in rs]
        st0 = [r["steps"][0] if r["steps"] else {} for r in rs]
        rev = [x.get("revision", {}).get("verdict") for x in st0]
        out.append({
            "policy": pol, "condition": cond, "mechanism": mech, "n": len(rs),
            "categories": {c: [r["instance"]["category"] for r in rs].count(c) for c in sorted({r["instance"]["category"] for r in rs})},
            "final_class_correct": mean([float(f.get("current_class") == mech) for f in fin]),
            "final_P_true": mean([(f.get("uncertainty") or {}).get(f"agent_P_{mech}") for f in fin]),
            "overconfident_final": mean([float((f.get("uncertainty") or {}).get("overconfident", False)) for f in fin]),
            "check_ed": mean([f.get("check_ed") for f in fin]), "check_floor": mean([f.get("check_ed_floor_truth") for f in fin]),
            "check_opposite": mean([f.get("check_ed_opposite_mechanism") for f in fin]),
            "design_info_ref_step1": mean([x.get("design_info_ref") for x in st0]),
            "design_frac_menu_max_step1": mean([x.get("design_info_ref_frac_of_menu_max") for x in st0]),
            "revision_step1": {v: rev.count(v) for v in sorted({x for x in rev if x})},
        })
    return out
