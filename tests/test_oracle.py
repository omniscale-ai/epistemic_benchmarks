import dataclasses
import functools
import math

import numpy as np
import pytest

from abductbench.config import Family, Stage, Truth, VariantConfig, all_variants
from abductbench.evaluate import oracle as oracle_mod
from abductbench.evaluate.law_eval import LawResult, score_predictions
from abductbench.evaluate.oracle import NOISE_FLOOR, NormalizedScores, OracleScores, normalize, oracle_scores
from abductbench.tasks import build_task
from abductbench.tasks import beta as beta_gen

BETA, ORBIT = Family.BETA, Family.ORBIT
ENT, NOENT = Truth.ENTITY, Truth.NO_ENTITY


def vcfg(family, truth, stage, seed=0, mode=1):
    return VariantConfig(family=family, truth=truth, stage=stage, seed=seed, mode=mode)


@functools.lru_cache(maxsize=None)
def cached_scores(cfg: VariantConfig) -> OracleScores:
    return oracle_scores(cfg)


def other_truth(truth: Truth) -> Truth:
    return NOENT if truth is ENT else ENT


def wrong_family_nrmse(cfg: VariantConfig) -> tuple[float, float]:
    """Score the opposite truth's law as if it were a prediction for cfg's bundle."""
    bundle = build_task(cfg)
    wrong = build_task(dataclasses.replace(cfg, truth=other_truth(cfg.truth)))
    ep = bundle.eval_points()
    return score_predictions(bundle, wrong.truth_law(ep.in_range), wrong.truth_law(ep.extrapolation))


@pytest.mark.parametrize(
    "cfg",
    [
        vcfg(BETA, ENT, Stage.HISTORICAL),
        vcfg(ORBIT, ENT, Stage.HISTORICAL),
        vcfg(ORBIT, NOENT, Stage.HISTORICAL),
    ],
    ids=["beta-entity-a", "orbit-entity-a", "orbit-no_entity-a"],
)
def test_oracle_recovers_constants(cfg):
    # Observed at seed 0 mode 1: oracle nrmse_in 1.6e-9 (beta a), 1.2e-3 (orbit entity a),
    # 4e-5 (orbit no_entity a); opposite-truth law 1.21, 3.15, 0.27. Thresholds keep a wide margin.
    s = cached_scores(cfg)
    wrong_in, _ = wrong_family_nrmse(cfg)
    assert s.nrmse_in < 0.1
    assert wrong_in > 0.1


@pytest.mark.parametrize("stage", [Stage.COUNTERFACTUAL, Stage.SYNTHETIC])
def test_beta_entity_constants_match_truth(stage):
    cfg = vcfg(BETA, ENT, stage)
    fit = oracle_mod.fit_beta_constants(build_task(cfg).public_files, truth=ENT, stage=stage)
    setup = beta_gen._setup(cfg)  # test-side check only; the oracle never sees this
    # Observed: m_X off by -1.9 %, k off by +0.04 (seed 0 mode 1).
    if stage is Stage.COUNTERFACTUAL:
        assert fit["m_X"] == pytest.approx(setup.m_X, rel=0.05)
    else:
        assert fit["k"] == pytest.approx(setup.k, abs=0.1)


def test_oracle_beats_wrong_family():
    # Beta counterfactual entity: the no-entity line-shape family must fit worse.
    # (The stage-a Fermi family is not an option here: stages c and d publish no Z.)
    cfg = vcfg(BETA, ENT, Stage.COUNTERFACTUAL)
    right = cached_scores(cfg).nrmse_in
    wrong_in, _ = _wrong_stage_scores(cfg, lambda files, x: oracle_mod.beta_oracle(
        files, x, truth=NOENT, stage=Stage.COUNTERFACTUAL))
    assert right < wrong_in

    # Orbit entity: a no-entity correction-force family must fit worse.
    ocfg = vcfg(ORBIT, ENT, Stage.HISTORICAL)
    right_o = cached_scores(ocfg).nrmse_in
    wrong_o_in, _ = _wrong_stage_scores(ocfg, lambda files, x: oracle_mod.orbit_oracle(
        files, x, truth=NOENT, n_corr=3.0))
    assert right_o < wrong_o_in


def _wrong_stage_scores(cfg, family_fn):
    """Run an alternative (wrong) family on cfg's public files and score it on cfg's bundle."""
    bundle = build_task(cfg)
    ep = bundle.eval_points()
    x = np.concatenate([ep.in_range, ep.extrapolation])
    pred = family_fn(bundle.public_files, x)
    n_in = len(ep.in_range)
    return score_predictions(bundle, pred[:n_in], pred[n_in:])


def test_oracle_ignores_truth_law():
    cfg = vcfg(BETA, ENT, Stage.SYNTHETIC)
    bundle = build_task(cfg)
    x = bundle.eval_points().in_range

    def poisoned(_):
        raise AssertionError("oracle must not call truth_law")

    poisoned_bundle = dataclasses.replace(bundle, truth_law=poisoned)
    a = bundle.oracle_family(bundle.public_files, x)
    b = poisoned_bundle.oracle_family(poisoned_bundle.public_files, x)
    assert np.array_equal(a, b)


def test_oracle_deterministic():
    beta_cfg = vcfg(BETA, ENT, Stage.SYNTHETIC)
    assert oracle_scores(beta_cfg) == oracle_scores(beta_cfg)
    # Fresh fit versus the (earlier) cached fit of the same orbit configuration.
    orbit_cfg = vcfg(ORBIT, NOENT, Stage.HISTORICAL)
    assert oracle_scores(orbit_cfg) == cached_scores(orbit_cfg)


def test_oracle_smoke_all_16_combos():
    variants = all_variants(seeds=[0], modes=(1,))
    assert len(variants) == 16
    for cfg in variants:
        s = cached_scores(cfg)
        assert math.isfinite(s.nrmse_in) and math.isfinite(s.nrmse_extrap), cfg.variant_id
        assert s.nrmse_in >= 0 and s.nrmse_extrap >= 0, cfg.variant_id


def test_normalize_floor():
    oracle = OracleScores(nrmse_in=0.05, nrmse_extrap=0.2)
    same = normalize(LawResult(status="ok", nrmse_in=0.05, nrmse_extrap=0.2), oracle)
    assert isinstance(same, NormalizedScores)
    assert same.rel_in == pytest.approx(1.0)
    assert same.rel_extrap == pytest.approx(1.0)

    # Oracle at (almost) zero: the denominator is the noise floor, not the oracle value.
    tiny = OracleScores(nrmse_in=1e-7, nrmse_extrap=2e-3)
    assert NOISE_FLOOR == pytest.approx(1e-3)
    n = normalize(LawResult(status="ok", nrmse_in=1e-3, nrmse_extrap=4e-3), tiny)
    assert n.rel_in == pytest.approx(1.0)  # 1e-3 / max(1e-7, 1e-3)
    assert n.rel_extrap == pytest.approx(2.0)  # 4e-3 / max(2e-3, 1e-3)


@pytest.mark.parametrize("status", ["crash", "timeout", "bad_shape", "nonfinite", "missing"])
def test_normalize_none_when_failed(status):
    oracle = OracleScores(nrmse_in=0.05, nrmse_extrap=0.2)
    n = normalize(LawResult(status=status, detail="x"), oracle)
    assert n.rel_in is None and n.rel_extrap is None
