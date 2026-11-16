"""Orbit episode: world consistency, pairing, protocol, measurement validation, metrics sanity.

Uses world seed 0 (the reference basis is cached under results/episode/orbit_cache after the first run)."""

import numpy as np
import pytest

from abductbench.episode import orbitfamily as of
from abductbench.episode import orbitworld as ow
from abductbench.episode.orbitworkspace import t0_example, t0_source, task_md
from abductbench.episode.protocol import ProtocolError, Session
from abductbench.episode.world import EpisodeConfig


def cfg(mech, **kw):
    return EpisodeConfig(0, mech, family="orbit", **kw)


def test_pair_shares_everything_public():
    a, b = Session(cfg("body")), Session(cfg("force"))
    assert a.meta == b.meta and task_md(a) == task_md(b) and t0_source(a) == t0_source(b) and t0_example(a) == t0_example(b)
    assert not np.array_equal(a.initial[0][1]["residual_arcsec"], b.initial[0][1]["residual_arcsec"])


def test_body_world_conserves_energy_and_is_absent_from_t0():
    sysm = ow.system(0)
    a_b, ph, m, _ = ow.body_params(0)
    gm, X, V = ow._initial(sysm, m, a_b, ph)
    assert abs(gm.sum() - ow.GM_C - sysm.gm_planets.sum()) < 1e-12  # central GM is the published one
    assert np.allclose((gm[:, None] * V).sum(0), 0.0, atol=1e-12)
    assert np.allclose(ow.t0_lon(0)[0], ow.integrate(sysm, [{}])[0][0, 0])


def test_matched_pair_is_close_on_initial_window_and_differs_later():
    rb, rf = ow.body_truth(0)[0], ow.force_truth(0)
    yb, yf = ow.at(rb[:, 0], ow.T_INITIAL), ow.at(rf[:, 0], ow.T_INITIAL)
    assert np.sqrt(np.mean((yb - yf) ** 2)) < 0.5 * ow.SIGMA
    assert np.max(np.abs(ow.at(rb[:, 1], ow.T_INITIAL) - ow.at(rf[:, 1], ow.T_INITIAL))) > 2 * ow.SIGMA


@pytest.mark.parametrize("bad", [
    {"type": "planet", "planet": "Ithe"}, {"type": "dense", "start": 13.0},
    {"type": "search", "time": 1.0, "lon_min": 0, "lon_max": 30}, {"type": "residuals", "planet": "Moru", "times": [1.0]},
    {"type": "extend", "n": 3},
])
def test_menu_rejects(bad):
    with pytest.raises(ValueError):
        of.validate_measurement(bad)


def test_search_finds_body_only_in_body_world():
    lon = of.body_lon_deg  # noqa: F841 (analytic helper exists)
    _, lb = ow.body_truth(0)
    t = 3.0
    true_lon = float(np.degrees(np.interp(t, ow.grid(), lb)) % 360)
    q = {"type": "search", "time": t, "lon_min": (true_lon - 2) % 360, "lon_max": (true_lon + 2) % 360}
    cb = of.OrbitWorld(cfg("body")).sample(q, 2000, np.random.default_rng(0))["count"]
    cf = of.OrbitWorld(cfg("force")).sample(q, 2000, np.random.default_rng(0))["count"]
    assert cb.mean() > cf.mean() + 0.6


def test_protocol_with_reference_models():
    s = Session(cfg("body"))
    fits = of.fit_both(0, s.initial)
    models = {k: __import__("abductbench.episode.orbitbaselines", fromlist=["x"])._model(k, 0, f) for k, f in fits.items()}
    pre = {"hypotheses": [{"id": "B", "role": "current", "model": "body", "statement": "b", "credence": 0.5},
                          {"id": "F", "role": "alternative", "model": "force", "statement": "f", "credence": 0.5}],
           "undetermined": "-", "measurement": {"type": "planet", "planet": "Moru"}, "expected": {"B": "-", "F": "-"}}
    s.register(pre, models)
    assert s.steps[0].hyps[0].forecast["residual_arcsec"].shape == (200, 40)
    q, obs = s.measure()
    assert obs["residual_arcsec"].shape == (40,)
    with pytest.raises(ProtocolError):
        s.measure()


def test_reference_policies_land_where_expected():
    from abductbench.episode import orbitbaselines as ob

    for mech in ("body", "force"):
        tf = ob.run_one(("truth_fed", cfg(mech).to_dict()))["final"]
        assert tf["check_ed"] < 2 * tf["check_ed_floor_truth"] + 0.01 < tf["check_ed_opposite_mechanism"]
        nd = ob.run_one(("no_data", cfg(mech).to_dict()))["final"]
        assert not nd["uncertainty"]["overconfident"]


def test_hypothesis_tools_reproduce_the_world(tmp_path):
    """The shipped tools must reproduce the hidden worlds exactly (same conventions), for both kinds."""
    import importlib
    import sys

    from abductbench.episode.orbitworkspace import TOOLS

    s = Session(cfg("body", tools=True))
    (tmp_path / "t0_model.py").write_text(t0_source(s))
    (tmp_path / "hyp_tools.py").write_text(TOOLS)
    sys.path.insert(0, str(tmp_path))
    try:
        H = importlib.import_module("hyp_tools")
        a_b, ph, m, _ = ow.body_params(0)
        t = np.array([2.0, 6.0, 10.0])
        rb = H.residuals_body(a_b, m, ph, "Moru", t)
        assert np.allclose(rb, ow.at(ow.body_truth(0)[0][:, 1], t), atol=0.05)
        n, k, _ = ow.force_params(0)
        rf = H.residuals_force(n, k, "Ithe", t)
        assert np.allclose(rf, ow.at(ow.force_truth(0)[:, 0], t), atol=0.05)
    finally:
        sys.path.remove(str(tmp_path))
        for mod in ("hyp_tools", "t0_model"):
            sys.modules.pop(mod, None)
    assert task_md(s) == task_md(Session(cfg("force", tools=True)))
    with pytest.raises(ValueError):
        EpisodeConfig(0, "body", family="orbit", tools=True, menu=False)
