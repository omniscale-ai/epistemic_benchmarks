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
    peak = b.truth_law(np.linspace(0.25 * Q, Q, 500)).max()
    at_endpoint = b.truth_law(np.array([Q]))[0]
    # Detector-seen density: the endpoint is smeared by the resolution, so it is about half
    # the (small) value at the edge, not zero; far above Q it vanishes.
    assert at_endpoint / peak < 0.05
    assert b.truth_law(np.array([1.2 * Q]))[0] / peak < 1e-3


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
            text = text.replace("hidden_carriers", "").replace("detector_response", "")
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


def test_eval_points_bands_and_domain():
    from abductbench.tasks.beta import WINDOW

    for truth in Truth:
        b = build_beta(cfg(truth, Stage.OBFUSCATED))
        Q = q_of(b)
        ev = b.eval_points()
        assert len(ev.in_range) == 2000
        np.testing.assert_allclose([ev.in_range.min(), ev.in_range.max()], [WINDOW[0] * Q, WINDOW[1] * Q])
        low = ev.extrapolation[ev.extrapolation < WINDOW[0] * Q]
        high = ev.extrapolation[ev.extrapolation > WINDOW[1] * Q]
        assert len(low) + len(high) == len(ev.extrapolation) and len(low) > 0 and len(high) > 0
        assert low.min() == pytest.approx(0.02 * Q) and low.max() < WINDOW[0] * Q
        assert high.min() > WINDOW[1] * Q and high.max() == pytest.approx(1.5 * Q)
        lo, hi = b.true_domain["energy_range"]
        if truth is Truth.ENTITY:
            assert (lo, hi) == pytest.approx((0.25 * Q, Q))
        # truth law is defined, finite and non-negative over the whole evaluated range
        for pts in (ev.in_range, ev.extrapolation):
            out = b.truth_law(pts)
            assert np.all(np.isfinite(out)) and np.all(out >= 0)
        assert b.truth_law(ev.extrapolation).max() > 0


def test_entity_high_band_is_gaussian_tail_no_entity_is_line_tail():
    e = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL))
    n = build_beta(cfg(Truth.NO_ENTITY, Stage.HISTORICAL))
    Q = q_of(e)
    hi = np.linspace(1.25 * Q, 1.5 * Q, 20)
    assert e.truth_law(hi).max() < 1e-4 * e.truth_law(np.linspace(0.3 * Q, Q, 50)).max()
    assert n.truth_law(hi).max() < 1e-4 * n.truth_law(np.array([Q])).max()


def test_held_out_bands_not_in_events():
    from abductbench.tasks.beta import WINDOW

    for truth in Truth:
        b = build_beta(cfg(truth, Stage.HISTORICAL))
        Q = q_of(b)
        T = np.array([float(r["kinetic_energy"]) for r in csv.DictReader(io.StringIO(b.public_files["events.csv"]))])
        assert T.min() >= WINDOW[0] * Q and T.max() <= WINDOW[1] * Q
        lo, hi = WINDOW[0] * Q, WINDOW[1] * Q
        import re

        m = re.search(r"window: (\S+) to (\S+) ", b.public_files["detector.md"])
        assert (float(m.group(1)), float(m.group(2))) == pytest.approx((lo, hi), rel=1e-6)


@pytest.mark.parametrize("stage", list(Stage))
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_true_mechanism_matches_generator(stage, seed):
    from abductbench.tasks.beta import _setup

    c = cfg(Truth.ENTITY, stage, seed=seed)
    s = _setup(c)
    m = build_beta(c).true_mechanism
    assert m["kind"] == "hidden_carriers"
    if stage is Stage.SYNTHETIC:
        assert m["n_carriers"] == s.k and s.k in (2, 3) and m["mass"] == 0.0
    elif stage is Stage.COUNTERFACTUAL:
        assert m["n_carriers"] == 1 and m["mass"] == pytest.approx(0.3 * q_of(build_beta(c)))
    else:
        assert m["n_carriers"] == 1 and m["mass"] == 0.0
    assert m["tolerance"] == {"mass_abs": pytest.approx(0.1 * q_of(build_beta(c)))}
    assert build_beta(cfg(Truth.NO_ENTITY, stage, seed=seed)).true_mechanism == {"kind": "detector_response"}


def test_mechanism_section_identical_across_truths():
    marker = "- `MECHANISM`"
    for stage in Stage:
        for mode in (1, 2):
            texts = []
            for truth in Truth:
                c = VariantConfig(family=Family.BETA, truth=truth, stage=stage, seed=0, mode=mode)
                t = build_beta(c).public_files["task.md"]
                assert marker in t
                texts.append(t[t.index(marker):])
            assert texts[0] == texts[1]
            for tok in ('"hidden_carriers"', '"detector_response"', '"other"', "n_carriers", "description"):
                assert tok in texts[0]
            assert "outside" in texts[0]


def test_stage_b_is_rescaled_units():
    a = build_beta(cfg(Truth.ENTITY, Stage.HISTORICAL, seed=5))
    b = build_beta(cfg(Truth.ENTITY, Stage.OBFUSCATED, seed=5))
    assert q_of(b) == pytest.approx(2 * q_of(a))
    assert "unit U" in b.public_files["task.md"]


def test_build_task_dispatches_beta():
    b = build_task(cfg(Truth.ENTITY, Stage.HISTORICAL))
    assert isinstance(b, TaskBundle)
    assert b.rubric_id == "beta-entity-a"


def test_build_task_dispatches_orbit():
    orbit = VariantConfig(family=Family.ORBIT, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1)
    assert build_task(orbit).rubric_id == "orbit-entity-a"


@pytest.mark.parametrize("truth", list(Truth))
@pytest.mark.parametrize("mode", [1, 2])
def test_stage_d_uses_fictional_vocabulary(truth, mode):
    from abductbench.tasks import query_help
    from abductbench.workspace import _mode2_files

    c = VariantConfig(family=Family.BETA, truth=truth, stage=Stage.SYNTHETIC, seed=0, mode=mode)
    b = build_beta(c)
    files = dict(b.public_files)
    if mode == 2:
        files = _mode2_files(c, files, 40.0)
        files["help"] = query_help(c)
    text = "\n".join(v if isinstance(v, str) else v.decode() for v in files.values()).lower()
    for word in ["electron", "nucleus", "mev", "neutrino", "beta decay", "beta-decay"]:
        assert word not in text, word
    # distinct from stage b's neutral names
    b_text = build_beta(VariantConfig(family=Family.BETA, truth=truth, stage=Stage.OBFUSCATED, seed=0, mode=mode)).public_files["masses.csv"]
    assert "unit W" in b.public_files["masses.csv"] and "unit W" not in b_text
