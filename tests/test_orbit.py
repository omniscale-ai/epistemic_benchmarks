import csv
import functools
import io

import numpy as np
import pytest

from abductbench.config import Family, Stage, Truth, VariantConfig
from abductbench.tasks import build_task
from abductbench.tasks.orbit import (
    DT_YR,
    EXT_YR,
    _SPECS,
    _accel,
    _energy,
    _initial_state,
    _longitudes,
    _residuals,
    _run,
    _universe,
    build_orbit,
)

FORBIDDEN = ["entity", "no_entity", "neutrino", "truth", "neptune", "vulcan", "perturber", "hidden planet"]
PUBLIC = {"task.md", "target_positions.csv", "other_residuals.csv", "known_bodies.csv", "t0_model.py"}
NOISE = 0.05  # arcsec, default cfg.noise


def cfg(truth, stage=Stage.HISTORICAL, seed=0, mode=1):
    return VariantConfig(family=Family.ORBIT, truth=truth, stage=stage, seed=seed, mode=mode)


@functools.lru_cache(maxsize=None)
def _bundle(truth, stage=Stage.HISTORICAL, seed=0, mode=1):
    return build_orbit(cfg(truth, stage, seed, mode))


def _rows(bundle, name):
    return list(csv.DictReader(io.StringIO(bundle.public_files[name])))


def _target_name(bundle):
    return _rows(bundle, "target_positions.csv")[0]["body"]


def _target_data(bundle):
    rows = _rows(bundle, "target_positions.csv")
    return np.array([float(r["time"]) for r in rows]), np.array([float(r["longitude_deg"]) for r in rows])


def _t0_predict(bundle):
    ns = {}
    exec(bundle.public_files["t0_model.py"], ns)
    return ns["predict_longitudes"]


def test_public_files_and_answer_free_text():
    for truth in Truth:
        for stage in Stage:
            b = _bundle(truth, stage)
            assert set(b.public_files) == PUBLIC
            text = "\n".join(
                v if isinstance(v, str) else v.decode() for v in b.public_files.values()
            ).lower()
            for word in FORBIDDEN:
                assert word not in text, (truth, stage, word)


def test_task_md_states_signature_and_domain_keys():
    b = _bundle(Truth.ENTITY)
    md = b.public_files["task.md"]
    assert "law(t: np.ndarray) -> np.ndarray" in md
    assert "DOMAIN" in md and "time_range" in md and "radius_range" in md
    assert set(b.true_domain) == {"time_range", "radius_range"}
    assert b.rubric_id == "orbit-entity-a"
    assert b.discriminating_queries == frozenset({"search_region", "other_body_residuals"})
    assert _bundle(Truth.NO_ENTITY, Stage.SYNTHETIC).rubric_id == "orbit-no_entity-d"


KINDS = ['"hidden_body"', '"force_law"', '"other"']


def _mech_section(md):
    i = md.index("`MECHANISM`")
    return md[i:]


def test_task_md_mechanism_section_identical_kinds():
    for stage in Stage:
        e = _bundle(Truth.ENTITY, stage).public_files["task.md"]
        n = _bundle(Truth.NO_ENTITY, stage).public_files["task.md"]
        assert _mech_section(e) == _mech_section(n)
        sec = _mech_section(e)
        for kind in KINDS:
            assert kind in sec
        assert "k / r^n" in sec and "checked automatically" in sec and "GM column" in sec


def test_eval_points_extent_40_years():
    assert EXT_YR == 40.0
    for stage in Stage:
        for truth in Truth:
            b = _bundle(truth, stage)
            ep = b.eval_points()
            tick = _SPECS[stage].tick_yr
            assert ep.in_range[-1] * tick == pytest.approx(10.0)
            assert ep.extrapolation[0] * tick > 10.0
            assert ep.extrapolation[-1] * tick == pytest.approx(40.0)
            assert np.all(np.isfinite(b.truth_law(ep.extrapolation)))


def test_truth_law_accurate_over_40_years():
    # compare the spline against a run with half the step on the truth row
    for truth in Truth:
        c = cfg(truth)
        u = _universe(c)
        b = _bundle(truth)
        mu = np.stack([u.mu_base.copy(), u.mu_base.copy()])
        mu[0, 5] = 0.0
        k = np.zeros(2)
        if truth is Truth.NO_ENTITY:
            mu[1, 5] = 0.0
            k[1] = u.k
        x0, v0 = _initial_state(u.mu_base, u.elements)
        X, _ = _run(mu, np.stack([x0, x0]), np.stack([v0, v0]), k, u.n, u.dt / 2, 2 * u.n_steps(EXT_YR))
        res = _residuals(_longitudes(X))[:, 0, u.target_planet]
        t = np.arange(len(res)) * u.dt / 2
        sel = slice(0, None, 37)
        assert np.max(np.abs(res[sel] - b.truth_law(t[sel]))) < 0.01 * max(1.0, np.max(np.abs(res)))


def test_energy_conserved_40_years():
    for truth in Truth:
        u = _universe(cfg(truth))
        mu = u.mu_base.copy()[None, :]
        mu[0, 5] = 0.0
        x0, v0 = _initial_state(u.mu_base, u.elements)
        k = np.array([u.k if truth is Truth.NO_ENTITY else 0.0])
        X, V = _run(mu, x0[None], v0[None], k, u.n, u.dt, u.n_steps(EXT_YR))
        E = _energy(mu, k, u.n, X, V)[:, 0]
        assert np.max(np.abs(E - E[0])) / abs(E[0]) < 1e-6


def test_true_mechanism_per_truth_and_stage():
    for stage in Stage:
        u = _universe(cfg(Truth.ENTITY, stage))
        m = _bundle(Truth.ENTITY, stage).true_mechanism
        assert m == {"kind": "hidden_body", "a": pytest.approx(u.elements[4, 0]), "mass": pytest.approx(u.mu_base[5]),
                     "tolerance": {"a_factor": 1.3}}
        mn = _bundle(Truth.NO_ENTITY, stage).true_mechanism
        assert mn["kind"] == "force_law" and mn["n"] == _SPECS[stage].n_corr and mn["k"] > 0
        assert mn["tolerance"] == {"n_abs": 0.25, "k_rel": 0.3}


def test_force_law_declaration_matches_generator_term():
    for stage in Stage:
        u = _universe(cfg(Truth.NO_ENTITY, stage))
        mech = _bundle(Truth.NO_ENTITY, stage).true_mechanism
        for r in (0.5 * u.elements[0, 0], 2.0 * u.elements[3, 0]):
            # star at the origin, one massless test body on the x axis at distance r
            X = np.array([[[0.0, 0.0], [r, 0.0]]])
            mu = np.array([[1e-30, 0.0]])  # gravity negligible
            ext = _accel(X, mu, np.array([u.k]), u.n)[0, 1, 0]
            assert ext == pytest.approx(-mech["k"] / r ** mech["n"], rel=1e-12)


def test_build_task_dispatches_to_orbit():
    b = build_task(cfg(Truth.NO_ENTITY))
    assert b.rubric_id == "orbit-no_entity-a"
    assert b.entity is False


def test_entity_residuals_nonzero_vs_t0():
    b = _bundle(Truth.ENTITY)
    grid = np.linspace(0.0, b.true_domain["time_range"][1], 400)
    assert np.max(np.abs(b.truth_law(grid))) > 5 * NOISE


def test_no_entity_residuals_nonzero_vs_t0():
    b = _bundle(Truth.NO_ENTITY)
    grid = np.linspace(0.0, b.true_domain["time_range"][1], 400)
    assert np.max(np.abs(b.truth_law(grid))) > 5 * NOISE


def test_public_t0_model_matches_truth_law():
    for truth in Truth:
        b = _bundle(truth)
        t, lon = _target_data(b)
        pred = _t0_predict(b)(t)[_target_name(b)]
        resid = (np.degrees(np.angle(np.exp(1j * np.radians(lon - pred))))) * 3600.0
        assert np.max(np.abs(resid - b.truth_law(t))) < 5 * NOISE


def test_pair_shares_signature_and_grid():
    e = _bundle(Truth.ENTITY)
    n = _bundle(Truth.NO_ENTITY)
    assert set(e.public_files) == set(n.public_files)
    assert e.public_files["t0_model.py"] == n.public_files["t0_model.py"]
    assert e.public_files["known_bodies.csv"] == n.public_files["known_bodies.csv"]
    assert e.true_domain["time_range"] == n.true_domain["time_range"]
    assert np.array_equal(_target_data(e)[0], _target_data(n)[0])
    T = np.linspace(0.0, 12.0, 300).reshape(10, 30)
    assert e.truth_law(T).shape == n.truth_law(T).shape == (10, 30)
    assert np.all(np.isfinite(n.truth_law(T)))


def test_deterministic_by_seed():
    a = build_orbit(cfg(Truth.NO_ENTITY, Stage.COUNTERFACTUAL, seed=3))
    b = build_orbit(cfg(Truth.NO_ENTITY, Stage.COUNTERFACTUAL, seed=3))
    c = _bundle(Truth.NO_ENTITY, Stage.COUNTERFACTUAL, seed=4)
    assert a.public_files == b.public_files
    grid = np.linspace(0.0, 12.0, 200)
    np.testing.assert_array_equal(a.truth_law(grid), b.truth_law(grid))
    assert a.public_files["target_positions.csv"] != c.public_files["target_positions.csv"]


def test_stage_c_law_differs():
    grid = np.linspace(0.05, 10.0, 400)
    for truth in Truth:
        a = _bundle(truth, Stage.HISTORICAL)
        c = _bundle(truth, Stage.COUNTERFACTUAL)
        fa, fc = a.truth_law(grid), c.truth_law(grid)
        assert np.linalg.norm(fa - fc) / np.linalg.norm(fa) > 0.1


def test_energy_conserved_to_1e6():
    for truth in Truth:
        u = _universe(cfg(truth))
        mu = u.mu_base.copy()[None, :]
        mu[0, 5] = 0.0  # the optional perturber is not part of the energy check here
        x0, v0 = _initial_state(u.mu_base, u.elements)
        k = np.array([u.k if truth is Truth.NO_ENTITY else 0.0])
        X, V = _run(mu, x0[None], v0[None], k, u.n, u.dt, u.n_steps(10.0))
        E = _energy(mu, k, u.n, X, V)[:, 0]
        assert np.max(np.abs(E - E[0])) / abs(E[0]) < 1e-6


def _series(u, mus, ks, n_steps, elements_rows=None):
    """Residuals (S+1, B-1, 4) in arcsec of each batch row vs row 0 (the unperturbed system)."""
    x0s, v0s = [], []
    for mu, el in zip(mus, elements_rows):
        x0, v0 = _initial_state(mu, el)
        x0s.append(x0)
        v0s.append(v0)
    X, _ = _run(np.stack(mus), np.stack(x0s), np.stack(v0s), np.asarray(ks, float), u.n, u.dt, n_steps)
    return _residuals(_longitudes(X))


def test_no_entity_single_perturber_fails_crosscheck():
    b = _bundle(Truth.NO_ENTITY)
    u = _universe(cfg(Truth.NO_ENTITY))
    t_obs, _ = _target_data(b)
    t_idx = np.round(t_obs / DT_YR).astype(int)
    tgt = u.target_planet
    venus = 1
    target_res = b.truth_law(t_obs)
    rows = _rows(b, "other_residuals.csv")
    other_obs = np.array([float(r["residual_arcsec"]) for r in rows if r["body"] == u.names[1 + venus]])
    assert len(other_obs) == len(t_obs)

    # (1) one interior perturber (circular, coplanar, inside the target orbit), fitted to the target alone
    a_grid = np.linspace(0.06, 0.34, 8)
    phi_grid = np.arange(4) * np.pi / 2
    cands = [(a, p) for a in a_grid for p in phi_grid]
    mu_unit = 1e-6
    base = u.mu_base.copy()
    base[5] = 0.0
    mus = [base] + [np.where(np.arange(6) == 5, mu_unit, base) for _ in cands]
    els = [u.elements] + [np.vstack([u.elements[:4], [[a, 0.0, p, p]]]) for a, p in cands]
    res = _series(u, mus, np.zeros(len(mus)), u.n_steps(10.0), els)[t_idx]  # (T, B-1, 4)
    f_t, f_v = res[:, :, tgt], res[:, :, venus]
    scale = (f_t * target_res[:, None]).sum(0) / (f_t * f_t).sum(0)  # best mass per candidate
    fit_rms = np.sqrt(np.mean((scale * f_t - target_res[:, None]) ** 2, axis=0))
    best = int(np.argmin(fit_rms))
    assert fit_rms[best] < 0.1 * np.sqrt(np.mean(target_res**2))  # it does fit the target
    pred_venus = scale[best] * f_v[:, best]
    assert np.sqrt(np.mean((pred_venus - other_obs) ** 2)) > 3 * NOISE  # but misses the other planet

    # (2) the true correction law k/r^n, fitted to the same target data, predicts the other planet
    mus = [base, base.copy()]
    res_k = _series(u, mus, [0.0, u.k], u.n_steps(10.0), [u.elements, u.elements])[t_idx]
    g_t, g_v = res_k[:, 0, tgt], res_k[:, 0, venus]
    fit_k = (g_t * target_res).sum() / (g_t * g_t).sum()
    assert np.sqrt(np.mean((fit_k * g_v - other_obs) ** 2)) < 2 * NOISE
    assert np.sqrt(np.mean((fit_k * g_t - target_res) ** 2)) < 2 * NOISE


def test_public_t0_model_is_gravity_only():
    """The shipped T0 must not expose the correction law (no k, n, or r^n text)."""
    for stage in Stage:
        src = _bundle(Truth.NO_ENTITY, stage).public_files["t0_model.py"]
        lowered = src.lower()
        for token in ["k / r", "r^n", "r**n", "correction", "power", "exponent", " k,", "n=3", "n = 3"]:
            assert token not in lowered, (stage, token)
        assert "k / r^n" not in src and "correction" not in lowered


def _outer_family(u, t_idx, target_res):
    """Single circular outer perturber, mass linear, on a coarse (distance, phase) grid.

    Returns residuals (T, B, 4), the least-squares mass scale per candidate, and the
    target misfit per candidate, where B is the number of candidates.
    """
    base = u.mu_base.copy()
    base[5] = 0.0
    a_t = u.elements[u.target_planet, 0]
    cands = [(a, p) for a in a_t * np.geomspace(1.1, 3.0, 7) for p in np.arange(8) * np.pi / 4]
    mus = [base] + [np.where(np.arange(6) == 5, 1e-6, base) for _ in cands]
    els = [u.elements] + [np.vstack([u.elements[:4], [[a, 0.0, p, p]]]) for a, p in cands]
    res = _series(u, mus, np.zeros(len(mus)), u.n_steps(10.0), els)[t_idx]
    f_t = res[:, :, u.target_planet]
    scale = (f_t * target_res[:, None]).sum(0) / (f_t * f_t).sum(0)
    misfit = _misfit(res, u.target_planet, target_res)
    return res, scale, misfit


def _misfit(res, tgt, target_res):
    """RMS misfit of the best linear mass scale per candidate, res shape (T, B, 4)."""
    f_t = res[:, :, tgt]
    scale = (f_t * target_res[:, None]).sum(0) / (f_t * f_t).sum(0)
    return np.sqrt(np.mean((scale * f_t - target_res[:, None]) ** 2, axis=0))


@pytest.mark.parametrize("stage", list(Stage))
def test_entity_other_residuals_significant_and_consistent(stage):
    b = _bundle(Truth.ENTITY, stage)
    u = _universe(cfg(Truth.ENTITY, stage))
    t_obs, _ = _target_data(b)
    t_idx = np.round(t_obs / u.dt).astype(int)
    target_res = b.truth_law(t_obs)
    rows = _rows(b, "other_residuals.csv")
    others = [j for j in range(4) if j != u.target_planet]
    obs = {j: np.array([float(r["residual_arcsec"]) for r in rows if r["body"] == u.names[1 + j]]) for j in others}
    # (a) significant: the nearest other body (in semi-major axis to the target) is well above noise
    near = min(others, key=lambda j: abs(u.elements[j, 0] - u.elements[u.target_planet, 0]))
    assert np.sqrt(np.mean(obs[near] ** 2)) > 5 * NOISE
    # (b) consistent: single outer perturbers that fit the target within 3 sigma include one
    # that also predicts every other body within 3 sigma. The target-only family is broad in
    # distance (the target series alone does not fix it), so the check is over the family.
    assert np.sqrt(np.mean(target_res**2)) > 5 * NOISE
    res, scale, misfit = _outer_family(u, t_idx, target_res)
    ok = np.flatnonzero(misfit <= 3 * NOISE)
    assert len(ok) > 0, (stage, "no single perturber fits the target")
    consistent = [
        c for c in ok if all(np.sqrt(np.mean((scale[c] * res[:, c, j] - obs[j]) ** 2)) < 3 * NOISE for j in others)
    ]
    assert consistent, (stage, "no fitting single perturber predicts the other bodies")
