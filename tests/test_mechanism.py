import numpy as np
import pytest

from abductbench.evaluate.mechanism import score_mechanism

HB = {"kind": "hidden_body", "a": 10.0, "mass": 1e-3, "tolerance": {"q_rel": 0.5}}  # q_true = 1e-5
FL = {"kind": "force_law", "n": 3.0, "k": 2.0, "tolerance": {"n_abs": 0.25, "k_rel": 0.3}}
HC = {"kind": "hidden_carriers", "n_carriers": 2, "mass": 0.3, "tolerance": {"mass_abs": 0.1}}
DR = {"kind": "detector_response"}


def test_missing():
    r = score_mechanism(HB, None)
    assert (r.status, r.kind_ok, r.params_ok, r.declared_kind) == ("missing", False, None, None)


@pytest.mark.parametrize(
    "declared",
    [
        "hidden_body",
        {"a": 1, "mass": 1},
        {"kind": 3},
        {"kind": "hidden_body", "a": 10.0},
        {"kind": "hidden_body", "a": "10", "mass": 1.0},
        {"kind": "hidden_body", "a": True, "mass": 1.0},
        {"kind": "hidden_body", "a": float("nan"), "mass": 1.0},
        {"kind": "hidden_body", "a": -5.0, "mass": 1.0},
    ],
)
def test_bad(declared):
    r = score_mechanism(HB, declared)
    assert r.status == "bad" and r.kind_ok is False and r.params_ok is None


def test_wrong_truth_kind_is_kind_mismatch_not_bad():
    # keys of a declared kind that differs from the truth's are not checked at all
    r = score_mechanism(FL, {"kind": "hidden_body", "a": 1.0})
    assert (r.status, r.kind_ok, r.params_ok) == ("ok", False, None)
    r = score_mechanism(FL, {"kind": "hidden_body", "a": -1.0, "mass": -1.0})
    assert (r.status, r.kind_ok, r.params_ok) == ("ok", False, None)


def test_unscored_extra_keys_are_ignored():
    d = {"kind": "hidden_body", "a": 10.0, "mass": 1e-3, "phase": None, "extra": float("nan"), "n": "x"}
    r = score_mechanism(HB, d)
    assert r.status == "ok" and r.params_ok is True
    assert score_mechanism(DR, {"kind": "detector_response", "a": float("nan")}).kind_ok is True
    assert score_mechanism(FL, {"kind": "force_law", "n": 3.0, "k": 2.0, "mass": None}).params_ok is True


def test_hidden_body_needs_both_a_and_mass():
    assert score_mechanism(HB, {"kind": "hidden_body", "mass": 1e-3}).status == "bad"
    assert score_mechanism(HB, {"kind": "hidden_body", "a": 10.0, "mass": 0.0}).status == "bad"


def test_wrong_kind():
    r = score_mechanism(HB, {"kind": "force_law", "n": 3.0, "k": 2.0})
    assert (r.status, r.kind_ok, r.params_ok, r.declared_kind) == ("ok", False, None, "force_law")
    r = score_mechanism(DR, {"kind": "hidden_carriers", "n_carriers": 1, "mass": 0.0})
    assert r.kind_ok is False and r.params_ok is None


def test_unknown_kind_is_wrong_not_bad():
    r = score_mechanism(HB, {"kind": "aliens"})
    assert (r.status, r.kind_ok, r.params_ok) == ("ok", False, None)


def test_other_is_never_ok():
    for truth in (HB, FL, HC, DR):
        r = score_mechanism(truth, {"kind": "other", "description": "x"})
        assert (r.status, r.kind_ok, r.params_ok) == ("ok", False, None)


def test_hidden_body_scores_pull_q_not_a():
    # q = mass / a^2; q_true = 1e-5
    same_q = score_mechanism(HB, {"kind": "hidden_body", "a": 20.0, "mass": 4e-3})  # a is 2x off
    assert same_q.kind_ok and same_q.params_ok is True and same_q.param_errors == {"q_rel": pytest.approx(0.0, abs=1e-9)}
    assert score_mechanism(HB, {"kind": "hidden_body", "a": 10.0, "mass": 1.49e-3}).params_ok is True
    r = score_mechanism(HB, {"kind": "hidden_body", "a": 10.0, "mass": 1.6e-3})
    assert r.params_ok is False and r.param_errors["q_rel"] == pytest.approx(0.6)
    low = score_mechanism(HB, {"kind": "hidden_body", "a": 10.0, "mass": 0.4e-3})
    assert low.params_ok is False and low.param_errors["q_rel"] == pytest.approx(0.6)
    assert set(same_q.param_errors) == {"q_rel"}


def test_force_law_params():
    assert score_mechanism(FL, {"kind": "force_law", "n": 3.2, "k": 2.5}).params_ok is True
    r = score_mechanism(FL, {"kind": "force_law", "n": 3.3, "k": 2.0})
    assert r.params_ok is False and r.param_errors["n"] == pytest.approx(0.3)
    r = score_mechanism(FL, {"kind": "force_law", "n": 3.0, "k": 3.0})
    assert r.params_ok is False and r.param_errors["k"] == pytest.approx(0.5)
    assert score_mechanism(FL, {"kind": "force_law", "n": 3.0, "k": 1.5}).params_ok is True
    assert score_mechanism(FL, {"kind": "force_law", "n": 3.0, "k": -2.0}).params_ok is False


def test_hidden_carriers_params():
    assert score_mechanism(HC, {"kind": "hidden_carriers", "n_carriers": 2.0, "mass": 0.35}).params_ok is True
    r = score_mechanism(HC, {"kind": "hidden_carriers", "n_carriers": 3, "mass": 0.3})
    assert r.kind_ok and r.params_ok is False and r.param_errors["n_carriers"] == 1.0
    assert score_mechanism(HC, {"kind": "hidden_carriers", "n_carriers": 2, "mass": 0.45}).params_ok is False
    assert score_mechanism(HC, {"kind": "hidden_carriers", "n_carriers": 2.5, "mass": 0.3}).params_ok is False


def test_detector_response():
    r = score_mechanism(DR, {"kind": "detector_response", "foo": "bar"})
    assert (r.status, r.kind_ok, r.params_ok, r.param_errors) == ("ok", True, None, {})


def test_default_tolerances_when_truth_has_none():
    t = {"kind": "hidden_body", "a": 10.0, "mass": 1.0}
    assert score_mechanism(t, {"kind": "hidden_body", "a": 10.0, "mass": 1.7}).params_ok is True  # default 0.75
    assert score_mechanism(t, {"kind": "hidden_body", "a": 10.0, "mass": 1.8}).params_ok is False
    r = score_mechanism({"kind": "force_law", "n": 3.0, "k": 2.0}, {"kind": "force_law", "n": 3.2, "k": 2.5})
    assert r.params_ok is True


def test_numpy_numbers_accepted_bool_rejected():
    r = score_mechanism(HB, {"kind": "hidden_body", "a": np.float64(10.5), "mass": np.float32(1.1e-3)})
    assert r.params_ok is True
    r = score_mechanism(HC, {"kind": "hidden_carriers", "n_carriers": np.int64(2), "mass": np.float64(0.3)})
    assert r.params_ok is True
    assert score_mechanism(HC, {"kind": "hidden_carriers", "n_carriers": True, "mass": 0.3}).status == "bad"
