"""Episode metrics: distances, unit invariance, and that controls land where they should."""

import numpy as np
import pytest

from abductbench.episode import baselines as bl
from abductbench.episode.metrics import ed1, ed2
from abductbench.episode.world import EpisodeConfig


def test_ed1_matches_pairwise_definition():
    rng = np.random.default_rng(0)
    x, y = rng.normal(size=300), rng.normal(0.5, 1.2, size=200)
    brute = 2 * np.abs(x[:, None] - y).mean() - np.abs(x[:, None] - x).mean() - np.abs(y[:, None] - y).mean()
    assert ed1(x, y) == pytest.approx(brute, rel=1e-9)
    assert ed2(x[:, None], y[:, None]) == pytest.approx(brute, rel=1e-9)


def _flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flat(v, prefix + k + "."))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            for i, x in enumerate(v):
                out.update(_flat(x, f"{prefix}{k}.{i}."))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[prefix + k] = float(v)
    return out


def test_metrics_are_unit_invariant():
    a = bl.run_one(("reference_adaptive", EpisodeConfig(2, "loss").to_dict()))
    b = bl.run_one(("reference_adaptive", EpisodeConfig(2, "loss", unit_scale=13.0).to_dict()))
    fa, fb = _flat(a), _flat(b)
    skip = ("config.unit_scale", "instance.ref_m_fit_initial")  # the config itself and a public-unit echo
    for k, v in fa.items():
        if k in skip or "mass" in k:
            continue
        assert fb[k] == pytest.approx(v, rel=1e-6, abs=1e-9), k


@pytest.fixture(scope="module")
def rows():
    pols = ["truth_fed", "reference_adaptive", "stubborn_carrier", "textbook", "no_data"]
    return {(p, m): bl.run_one((p, EpisodeConfig(3, m).to_dict())) for p in pols for m in ("carrier", "loss")}


def test_truth_fed_sits_at_the_noise_floor(rows):
    for m in ("carrier", "loss"):
        f = rows[("truth_fed", m)]["final"]
        assert f["check_ed"] < 3 * f["check_ed_floor_truth"] + 1e-3 < f["check_ed_opposite_mechanism"]


def test_reference_solver_resolves_and_keeps_confirmed_hypothesis(rows):
    for m in ("carrier", "loss"):
        r = rows[("reference_adaptive", m)]
        assert r["final"]["current_class"] == m
        assert r["steps"][0]["revision"]["verdict"] in ("justified_keep", "justified_switch")
        assert r["final"]["check_ed"] < 0.05 * r["final"]["check_ed_opposite_mechanism"]


def test_stubborn_agent_is_flagged_only_where_evidence_contradicts_it(rows):
    assert rows[("stubborn_carrier", "carrier")]["steps"][0]["revision"]["verdict"] == "justified_keep"
    assert rows[("stubborn_carrier", "loss")]["steps"][0]["revision"]["verdict"] == "unjustified_keep"


def test_confident_memorised_answer_is_overconfident_when_data_are_ambiguous(rows):
    r = rows[("textbook", "loss")]
    assert r["instance"]["category"] == "ambiguous"
    assert r["steps"][0]["uncertainty_before"]["overconfident"]
    assert r["final"]["check_ed"] > 0.5 * r["final"]["check_ed_opposite_mechanism"]


def test_no_data_control_is_not_called_overconfident_and_hedges(rows):
    for m in ("carrier", "loss"):
        f = rows[("no_data", m)]["final"]
        assert not f["uncertainty"]["overconfident"]
        assert f["check_ed_floor_truth"] < f["check_ed"] < f["check_ed_opposite_mechanism"]


def test_operative_hypothesis_follows_credence_not_label():
    from abductbench.episode.metrics import _current, _role_mismatch
    from abductbench.episode.protocol import HypRecord, Step

    hs = [HypRecord("H1", "current", "loss", 0.03, {"kind": "loss"}, None),
          HypRecord("H2", "alternative", "carrier", 0.92, {"kind": "carrier", "mass": 0.2}, None)]
    st = Step("final", 2, hs, "-")
    assert _current(st).id == "H2" and _role_mismatch(st)
    hs[1].credence = 0.03
    assert _current(st).id == "H1" and not _role_mismatch(st)
