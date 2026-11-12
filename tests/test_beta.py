import csv
import io

import numpy as np
import pytest

from abductbench.config import Family, Stage, Truth, TaskBundle, VariantConfig
from abductbench.tasks import build_task
from abductbench.tasks.beta import build_beta

FORBIDDEN = ["entity", "no_entity", "neutrino", "truth", "neptune", "vulcan", "hidden", "unseen", "missing"]


def cfg(truth, stage=Stage.HISTORICAL, seed=0, mode=1):
    return VariantConfig(family=Family.BETA, truth=truth, stage=stage, seed=seed, mode=mode)


def q_of(bundle: TaskBundle) -> float:
    """Q from the public mass table: M(parent) - M(daughter) - rest energy of the light particle."""
    rows = list(csv.DictReader(io.StringIO(bundle.public_files["masses.csv"])))
    m_p, m_d, m_e = (float(r["mass"]) for r in rows)
    return m_p - m_d - m_e


def test_entity_spectrum_vanishes_at_endpoint():
    b = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL))
    Q = q_of(b)
    peak = b.truth_law(np.linspace(0.1 * Q, Q, 500)).max()
    at_endpoint = b.truth_law(np.array([Q]))[0]
    assert at_endpoint / peak < 1e-3


def test_no_entity_has_line_at_Q():
    b = build_beta(cfg(Truth.NO_ENTITY, Stage.HISTORICAL))
    Q = q_of(b)
    grid = np.linspace(0.0, 1.1 * Q, 4001)
    peak_T = grid[np.argmax(b.truth_law(grid))]
    assert abs(peak_T - Q) < 2 * 0.05 * Q


def test_pair_shares_signature_and_grid():
    T = np.linspace(0.1, 1.1, 300)
    T2 = T.reshape(10, 30)
    e = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL))
    n = build_beta(cfg(Truth.NO_ENTITY, Stage.HISTORICAL))
    for bundle in (e, n):
        out = bundle.truth_law(T)
        assert out.shape == T.shape
        assert np.all(out >= 0) and np.all(np.isfinite(out))
        assert bundle.truth_law(T2).shape == T2.shape
    assert e.truth_law(T).shape == n.truth_law(T).shape


def test_deterministic_by_seed():
    a = build_beta(cfg(Truth.ENTITY, Stage.COUNTERFACTUAL, seed=3))
    b = build_beta(cfg(Truth.ENTITY, Stage.COUNTERFACTUAL, seed=3))
    c = build_beta(cfg(Truth.ENTITY, Stage.COUNTERFACTUAL, seed=4))
    assert a.public_files == b.public_files
    grid = np.linspace(0.05, 1.5, 200)
    np.testing.assert_array_equal(a.truth_law(grid), b.truth_law(grid))
    assert a.public_files["events.csv"] != c.public_files["events.csv"]


def test_stage_c_differs_from_a():
    a = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL, seed=1))
    c = build_beta(cfg(Truth.ENTITY, Stage.COUNTERFACTUAL, seed=1))
    Q = q_of(a)
    assert Q == pytest.approx(q_of(c))
    x = np.linspace(0.0, 1.0, 2001)[1:-1]
    fa = a.truth_law(x * Q) * Q
    fc = c.truth_law(x * Q) * Q
    rel = np.linalg.norm(fa - fc) / np.linalg.norm(fa)
    assert rel > 0.1


def test_public_files_have_required_content_and_no_answer_words():
    for truth in Truth:
        for stage in Stage:
            b = build_beta(cfg(truth, stage))
            assert set(b.public_files) == {"task.md", "events.csv", "masses.csv", "detector.md"}
            text = "\n".join(
                v if isinstance(v, str) else v.decode() for v in b.public_files.values()
            ).lower()
            for word in FORBIDDEN:
                assert word not in text, (truth, stage, word)
            task = b.public_files["task.md"]
            assert "energy_range" in task
            assert "law(T: np.ndarray) -> np.ndarray" in task
            assert b.rubric_id == f"beta-{truth.value}-{stage.value}"
            assert b.discriminating_queries == frozenset({"recoil_correlation", "target_thickness_scan"})
            assert b.entity == (truth is Truth.ENTITY)


def test_events_table_columns():
    b = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL))
    rows = list(csv.DictReader(io.StringIO(b.public_files["events.csv"])))
    assert len(rows) > 100
    assert set(rows[0]) == {"kinetic_energy", "recoil_energy", "recoil_angle_deg"}


def _median_momentum_mismatch(bundle: TaskBundle) -> float:
    rows = list(csv.DictReader(io.StringIO(bundle.public_files["events.csv"])))
    masses = list(csv.DictReader(io.StringIO(bundle.public_files["masses.csv"])))
    m_d = float(masses[1]["mass"])
    m_e = float(masses[2]["mass"])
    T = np.array([float(r["kinetic_energy"]) for r in rows])
    Er = np.array([float(r["recoil_energy"]) for r in rows])
    p_e = np.sqrt((T + m_e) ** 2 - m_e**2)
    p_r = np.sqrt(Er**2 + 2 * Er * m_d)
    return float(np.median(np.abs(p_r / p_e - 1)))


def test_momentum_balance_holds_only_without_entity():
    n = build_beta(cfg(Truth.NO_ENTITY, Stage.HISTORICAL, seed=2))
    e = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL, seed=2))
    assert _median_momentum_mismatch(n) < 0.05
    assert _median_momentum_mismatch(e) > 0.15


def test_eval_points_lie_in_domain_and_extrapolation_outside():
    for truth in Truth:
        b = build_beta(cfg(truth, Stage.OBFUSCATED))
        ev = b.eval_points()
        lo, hi = b.true_domain["energy_range"]
        assert len(ev.in_range) == 2000
        assert ev.in_range.min() >= lo - 1e-12 and ev.in_range.max() <= hi + 1e-12
        outside = (ev.extrapolation < lo) | (ev.extrapolation > hi)
        assert outside.all()


def test_stage_b_is_rescaled_units():
    a = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL, seed=5))
    b = build_beta(cfg(Truth.ENTITY, Stage.OBFUSCATED, seed=5))
    assert q_of(b) == pytest.approx(2 * q_of(a))
    assert "unit U" in b.public_files["task.md"]


def test_build_task_dispatches_beta():
    b = build_task(cfg(Truth.ENTITY, Stage.HISTORICAL))
    assert isinstance(b, TaskBundle)
    assert b.rubric_id == "beta-entity-a"


def test_build_task_orbit_not_implemented_yet():
    orbit = VariantConfig(family=Family.ORBIT, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1)
    with pytest.raises(NotImplementedError):
        build_task(orbit)
