"""Decay-world generator: consistency, pairing, seeds, units, ambiguity and discriminability."""

import numpy as np
import pytest

from abductbench.episode import physics as ph
from abductbench.episode import reference as ref
from abductbench.episode.protocol import Session
from abductbench.episode.workspace import t0_model, task_md
from abductbench.episode.world import EpisodeConfig, World, validate_measurement


def test_three_body_events_conserve_energy_and_momentum():
    w = World(EpisodeConfig(1, "carrier"))
    kin, m = w.kin, w.sh.m_x
    T1, p3, T3 = ph.decay_carrier(kin, m, 50000, np.random.default_rng(0))
    E2 = 1.0 - T1 - T3  # carrier energy from total energy (Q = 1)
    assert np.all(E2 >= m - 1e-12)
    p1 = kin.p_light(T1)
    p2 = np.sqrt(np.maximum(E2**2 - m**2, 0))
    # momentum balance: |p3| must close the triangle with |p1| and |p2|
    assert np.all(p3 <= p1 + p2 + 1e-7) and np.all(p3 >= np.abs(p1 - p2) - 1e-7)


def test_loss_world_recoil_is_set_at_decay_not_by_measured_energy():
    w = World(EpisodeConfig(2, "loss"))
    s = ph.sample_query(w.truth, w.kin, {"type": "recoil_coincidence", "thickness": 1.0}, 5000, np.random.default_rng(1))
    _, p2 = w.kin.two_body()
    # recorded energies spread widely (energy loss), recoil stays at the two-body value (2% resolution)
    assert np.std(s["kinetic_energy"]) > 0.1
    assert abs(np.median(s["recoil_momentum"]) / p2 - 1) < 0.01
    assert np.corrcoef(s["kinetic_energy"], s["recoil_momentum"])[0, 1] ** 2 < 0.01


@pytest.mark.parametrize("mech", ["carrier", "loss"])
def test_sampler_matches_binned_density(mech):
    w = World(EpisodeConfig(4, mech))
    for q in ({"type": "spectrum", "thickness": 1.0}, {"type": "spectrum", "thickness": 2.0}, {"type": "calorimeter"}):
        probs, key = ph.query_probs(w.truth, w.kin, q)
        x = ph.sample_query(w.truth, w.kin, q, 100000, np.random.default_rng(2))[key]
        h, _ = np.histogram(x, ph.EDGES)
        assert np.max(np.abs(np.cumsum(h) / h.sum() - np.cumsum(probs))) < 0.01


def test_pair_shares_everything_public():
    a, b = Session(EpisodeConfig(5, "carrier")), Session(EpisodeConfig(5, "loss"))
    assert a.meta == b.meta
    assert task_md(a) == task_md(b)
    assert t0_model(a) == t0_model(b)
    assert not np.array_equal(a.initial[0][1]["kinetic_energy"], b.initial[0][1]["kinetic_energy"])


def test_seeds_are_separate():
    base = World(EpisodeConfig(3, "carrier", obs_seed=0))
    other_obs = World(EpisodeConfig(3, "carrier", obs_seed=1))
    other_menu = World(EpisodeConfig(3, "carrier", obs_seed=0, menu=False, agent_rep=4))
    assert base.public_metadata() == other_obs.public_metadata()
    d0 = base.observe_initial()[0][1]["kinetic_energy"]
    assert not np.array_equal(d0, other_obs.observe_initial()[0][1]["kinetic_energy"])
    assert np.array_equal(d0, other_menu.observe_initial()[0][1]["kinetic_energy"])  # menu/rep never enter data


def test_unit_scale_only_rescales_public_values():
    a = World(EpisodeConfig(6, "loss"))
    b = World(EpisodeConfig(6, "loss", unit_scale=7.3))
    assert b.Q == pytest.approx(7.3 * a.Q)
    np.testing.assert_allclose(b.observe_initial()[0][1]["kinetic_energy"], 7.3 * a.observe_initial()[0][1]["kinetic_energy"])


@pytest.mark.parametrize("bad", [
    {"type": "recoil_coincidence", "thickness": 0.05, "n": 10},
    {"type": "spectrum", "thickness": 0.05, "n": 10},
    {"type": "spectrum", "thickness": 1.0, "n": 401},
    {"type": "spectrum", "thickness": float("nan"), "n": 10},
    {"type": "calorimeter", "n": True},
    {"type": "calorimeter", "n": 10, "thickness": 1.0},
])
def test_measurement_menu_rejects(bad):
    with pytest.raises(ValueError):
        validate_measurement(bad)


def test_initial_ambiguity_and_measurement_discriminability():
    """Numerical identifiability check on 6 world seeds x 2 mechanisms (not a statement in prose)."""
    ambiguous, decided = 0, 0
    for sd in range(6):
        for mech in ("carrier", "loss"):
            w = World(EpisodeConfig(sd, mech))
            data = [(q, w.to_internal(o)) for q, o in w.observe_initial()]
            ambiguous += abs(ref.dll(ref.fit_both(w.kin, data))) < ref.AMBIGUOUS_DLL
            cal = {"type": "calorimeter", "n": 100}
            p = ref.posterior(ref.fit_both(w.kin, data + [(cal, w.to_internal(w.observe(cal, 0)))]))["carrier"]
            decided += (p > 0.99) if mech == "carrier" else (p < 0.01)
    assert ambiguous >= 9  # most instances ambiguous at A; the rest are reported as "lean_*"
    assert decided == 12
