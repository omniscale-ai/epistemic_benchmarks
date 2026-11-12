"""End-to-end smoke test: scripts/smoke.py over all 16 variants (seed 0, mode 1)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import smoke  # noqa: E402

from abductbench.config import all_variants  # noqa: E402
from abductbench.tasks import build_task  # noqa: E402

EXPECTED_IDS = {cfg.variant_id for cfg in all_variants(seeds=[0], modes=(1,))}


@pytest.fixture(scope="module")
def oracle_cache():
    return {}


@pytest.fixture(scope="module")
def oracle_result(tmp_path_factory, oracle_cache):
    root = tmp_path_factory.mktemp("smoke_oracle")
    return smoke.run_smoke(root, seed=0, agent="oracle", oracle_cache=oracle_cache)


def test_smoke_all_16_variants_oracle_agent(oracle_result):
    runs = oracle_result["runs"]
    assert len(runs) == 16
    assert set(runs.variant_id) == EXPECTED_IDS

    assert (runs.law_status == "ok").all(), runs[["variant_id", "law_status", "law_detail"]]
    assert (runs.answer_status == "ok").all()

    assert runs.rel_in.map(lambda v: v is not None and math.isfinite(v)).all()
    assert (runs.nrmse_in < 1e-6).all()
    assert (runs.rel_in <= 1.0).all()

    assert (runs.entity_pred.astype(bool) == runs.entity_truth.astype(bool)).all()
    pairs = oracle_result["pairs"]
    assert len(pairs) == 8
    assert (pairs.pair_entity_rate == 1.0).all()

    assert oracle_result["judge_calls"] == 16
    assert (runs.rubric_pass_rate == 1.0).all()
    assert (runs.domain_score > 0.99).all()

    assert (runs.mech_status == "ok").all()
    assert runs.mech_kind_ok.astype(bool).all()
    for _, row in runs.iterrows():
        if row["mech_declared_kind"] == "detector_response":
            assert row["mech_params_ok"] is None or pd.isna(row["mech_params_ok"]), row["variant_id"]
        else:
            assert row["mech_params_ok"] is True or row["mech_params_ok"] == True, row["variant_id"]  # noqa: E712
    assert (oracle_result["summary"].mechanism_kind_rate == 1.0).all()


def test_smoke_constant_yes_agent_pair_rate_zero(tmp_path, oracle_cache):
    result = smoke.run_smoke(tmp_path, seed=0, agent="constant_yes", oracle_cache=oracle_cache)
    pairs = result["pairs"]
    assert len(pairs) == 8
    assert (pairs.pair_entity_rate == 0.0).all()

    summary = result["summary"]
    assert set(summary.entity_correct_rate) == {0.0, 1.0}
    assert summary.entity_correct_rate.mean() == pytest.approx(0.5)


def test_smoke_curve_fit_agent_scores_on_prediction_not_mechanism(tmp_path, oracle_cache):
    result = smoke.run_smoke(tmp_path, seed=0, agent="curve_fit", oracle_cache=oracle_cache)
    runs = result["runs"]
    assert len(runs) == 16
    assert (runs.mech_status == "missing").all()
    assert not runs.mech_kind_ok.astype(bool).any()
    assert (runs.law_status == "ok").all()
    assert (runs.nrmse_in < 1e-6).all()
    assert (result["summary"].mechanism_kind_rate == 0.0).all()


def test_smoke_wrong_mechanism_agent_kind_not_ok(tmp_path, oracle_cache):
    result = smoke.run_smoke(tmp_path, seed=0, agent="wrong_mechanism", oracle_cache=oracle_cache)
    runs = result["runs"]
    assert len(runs) == 16
    assert (runs.law_status == "ok").all()
    assert (runs.mech_status == "ok").all()
    assert not runs.mech_kind_ok.astype(bool).any()
    assert (result["summary"].mechanism_kind_rate == 0.0).all()


def test_smoke_runner_never_leaks_truth_into_workspace(oracle_result):
    runs = oracle_result["runs"]
    row = runs[runs.variant_id == "beta-entity-a-s0-m1"].iloc[0]
    workspace = Path(row["workspace"])
    listing = {p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()}

    cfg = next(c for c in all_variants(seeds=[0], modes=(1,)) if c.variant_id == row["variant_id"])
    public = set(build_task(cfg).public_files)
    assert listing == public | {"law.py", "answer.md"}


FORBIDDEN_WORDS = ["entity", "neutrino", "neptune", "vulcan", "truth"]


def test_smoke_all_16_workspaces_have_no_truth_words(oracle_result):
    runs = oracle_result["runs"]
    assert len(runs) == 16
    for _, row in runs.iterrows():
        workspace = Path(row["workspace"])
        cfg = next(c for c in all_variants(seeds=[0], modes=(1,)) if c.variant_id == row["variant_id"])
        public = set(build_task(cfg).public_files)
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(workspace).as_posix()
            if rel in public:  # untouched public file: also text-scanned
                text = path.read_bytes().decode("utf-8", errors="ignore").lower()
                for word in FORBIDDEN_WORDS:
                    assert word not in text, (row["variant_id"], rel, word)
            for word in FORBIDDEN_WORDS:
                assert word not in rel.lower(), (row["variant_id"], rel, word)
