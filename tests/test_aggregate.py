import dataclasses
import json
import math
import re
import shutil
import subprocess
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from abductbench.config import Family, Stage, Truth, VariantConfig, all_variants
from abductbench.config import cfg_from_variant_id
from abductbench.evaluate.aggregate import (
    RUN_COLUMNS,
    RunScores,
    aggregate,
    evaluate_run,
    pair_table,
    stage_gap_table,
    write_results,
)
from abductbench.evaluate.oracle import OracleScores
from abductbench.runner import RunRecord

REPORT = Path(__file__).resolve().parents[1] / "report" / "report.qmd"


def vcfg(family="beta", truth="entity", stage="a", seed=0, mode=1, n_points=400):
    return VariantConfig(
        family=Family(family), truth=Truth(truth), stage=Stage(stage), seed=seed, mode=mode, n_points=n_points
    )


def score(family="beta", truth="entity", stage="a", seed=0, mode=1, **over) -> RunScores:
    cfg = vcfg(family, truth, stage, seed, mode)
    base = dict(
        variant_id=cfg.variant_id,
        family=family,
        truth=truth,
        stage=stage,
        seed=seed,
        mode=mode,
        law_status="ok",
        law_detail="ok",
        nrmse_in=0.5,
        nrmse_extrap=0.5,
        rel_in=1.0,
        rel_extrap=1.0,
        n_params_proxy=10,
        domain_score=1.0,
        answer_status="ok",
        entity_pred=(truth == "entity"),
        entity_truth=(truth == "entity"),
        rubric_pass_rate=0.5,
        judge_status="ok",
        judge_items=None,
        discriminating_fraction=None,
        timed_out=False,
        returncode=0,
    )
    base.update(over)
    return RunScores(**base)


def write_law(path: Path, source: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    law = path / "law.py"
    law.write_text(source, encoding="utf-8")
    return law


def perfect_source(bundle) -> str:
    """law.py that reproduces the truth by interpolating values embedded at the eval points."""
    ep = bundle.eval_points()
    x = np.unique(np.concatenate([ep.in_range, ep.extrapolation]).astype(float))
    y = np.asarray(bundle.truth_law(x), dtype=float)
    return (
        "import numpy as np\n"
        f"DOMAIN = {json.dumps({k: list(map(float, v)) for k, v in bundle.true_domain.items()})}\n"
        f"_X = np.array({json.dumps(x.tolist())})\n"
        f"_Y = np.array({json.dumps(y.tolist())})\n"
        "def law(t):\n"
        "    return np.interp(np.asarray(t, dtype=float), _X, _Y)\n"
    )


CONSTANT_SOURCE = (
    "import numpy as np\n"
    "def law(t):\n"
    "    return np.full_like(np.asarray(t, dtype=float), 7.0)\n"
)

VALID_ANSWER = (
    "## Law\nSee law.py.\n\n"
    "## Limits\nApplies in the window.\n\n"
    "## Explanation\nA hidden light particle carries the missing energy.\n\n"
    "ENTITY: yes\n"
)


def all_pass_runner(prompt: str) -> str:
    ids = re.findall(r"^- id: (\S+)$", prompt, flags=re.MULTILINE)
    return json.dumps({"items": {i: {"pass": True, "quote": "x"} for i in ids}})


def record_for(cfg, law_path=None, answer_path=None, transcript=None) -> RunRecord:
    return RunRecord(
        variant_id=cfg.variant_id,
        workspace=Path("/nonexistent/ws"),
        law_path=law_path,
        answer_path=answer_path,
        transcript_path=transcript,
        returncode=0,
        timed_out=False,
    )


def test_cfg_from_variant_id_roundtrip():
    for cfg in all_variants(seeds=range(5)):
        assert cfg_from_variant_id(cfg.variant_id) == cfg
    cfg = cfg_from_variant_id("beta-no_entity-c-s3-m2")
    assert (cfg.family, cfg.truth, cfg.stage, cfg.seed, cfg.mode) == (
        Family.BETA, Truth.NO_ENTITY, Stage.COUNTERFACTUAL, 3, 2,
    )
    for bad in ["", "beta-entity-e-s0-m1", "gamma-entity-a-s0-m1", "beta-entity-a-s0-m3", "beta-entity-a-s0"]:
        with pytest.raises(ValueError):
            cfg_from_variant_id(bad)


def test_evaluate_run_missing_law_and_answer(tmp_path):
    cfg = vcfg()
    calls = []

    def stub(prompt):
        calls.append(prompt)
        return "{}"

    rec = record_for(cfg, law_path=None, answer_path=None)
    s = evaluate_run(cfg, rec, judge_runner=stub, oracle_cache={})
    assert s.law_status == "missing"
    assert s.answer_status == "missing"
    assert s.rel_in is None and s.rel_extrap is None
    assert s.entity_pred is None
    assert s.judge_status == "skipped"
    assert s.rubric_pass_rate is None
    assert calls == []
    # Paths that exist but are not a law/answer file must not raise either.
    rec2 = record_for(cfg, law_path=tmp_path, answer_path=tmp_path)
    s2 = evaluate_run(cfg, rec2, judge_runner=stub, oracle_cache={})
    assert s2.law_status == "missing" and s2.answer_status == "missing"
    json.dumps(dataclasses.asdict(s2))


def test_evaluate_run_perfect_law(tmp_path):
    cfg = vcfg()
    from abductbench.tasks import build_task

    bundle = build_task(cfg)
    law = write_law(tmp_path / "ws", perfect_source(bundle))
    ans = tmp_path / "ws" / "answer.md"
    ans.write_text(VALID_ANSWER, encoding="utf-8")
    s = evaluate_run(cfg, record_for(cfg, law_path=law, answer_path=ans), judge_runner=all_pass_runner)
    assert s.law_status == "ok"
    assert s.answer_status == "ok"
    assert s.entity_pred is True and s.entity_truth is True
    assert s.judge_status == "ok"
    assert s.rubric_pass_rate == pytest.approx(1.0)
    assert s.rel_in is not None and s.rel_in < 1e-6
    assert s.rel_extrap is not None and s.rel_extrap < 1e-6
    assert s.domain_score == pytest.approx(1.0)
    assert isinstance(s.judge_items, dict) and all(v["pass"] for v in s.judge_items.values())
    json.dumps(dataclasses.asdict(s))


def test_judge_error_not_counted_as_pass(tmp_path):
    cfg = vcfg()
    ans = tmp_path / "answer.md"
    ans.write_text(VALID_ANSWER, encoding="utf-8")
    bad = lambda prompt: "no json here"  # noqa: E731
    s = evaluate_run(cfg, record_for(cfg, answer_path=ans), judge_runner=bad)
    assert s.judge_status == "judge_error"
    assert s.rubric_pass_rate is None
    assert s.judge_items is None
    # Aggregation excludes the judge_error run from the rubric mean and counts it.
    ok = score(rubric_pass_rate=1.0)
    err = score(seed=1, judge_status="judge_error", rubric_pass_rate=None, judge_items=None)
    row = aggregate([ok, err]).iloc[0]
    assert row["rubric_pass_rate_mean"] == pytest.approx(1.0)
    assert row["judge_error_count"] == 1
    assert row["n_runs"] == 2


def test_judge_skipped_when_answer_not_ok(tmp_path):
    cfg = vcfg()
    ans = tmp_path / "answer.md"
    ans.write_text("## Law\nx\n\nENTITY: yes\n", encoding="utf-8")  # sections missing
    calls = []

    def stub(prompt):
        calls.append(prompt)
        return all_pass_runner(prompt)

    s = evaluate_run(cfg, record_for(cfg, answer_path=ans), judge_runner=stub)
    assert s.answer_status == "missing_sections"
    assert s.entity_pred is True
    assert s.judge_status == "skipped"
    assert s.rubric_pass_rate is None
    assert calls == []


def test_evaluate_run_uses_oracle_for_normalization(tmp_path, monkeypatch):
    import abductbench.evaluate.aggregate as agg

    cfg = vcfg()
    from abductbench.tasks import build_task

    bundle = build_task(cfg)
    law = write_law(tmp_path / "ws", CONSTANT_SOURCE)
    seen = []

    def fake_oracle(c):
        seen.append(c)
        return OracleScores(nrmse_in=0.25, nrmse_extrap=0.5)

    monkeypatch.setattr(agg, "oracle_scores", fake_oracle)
    s = evaluate_run(cfg, record_for(cfg, law_path=law), judge_runner=all_pass_runner, oracle_cache={}, use_judge=False)
    assert s.law_status == "ok"
    assert s.rel_in == pytest.approx(s.nrmse_in / 0.25)
    assert s.rel_extrap == pytest.approx(s.nrmse_extrap / 0.5)
    assert s.judge_status == "skipped"
    assert len(seen) == 1
    assert bundle.entity is True


def test_aggregate_groups_by_stage():
    scores = [
        score(stage="a", seed=0, rel_in=1.0),
        score(stage="a", seed=1, rel_in=3.0),
        score(stage="c", seed=0, rel_in=2.0),
        score(stage="a", truth="no_entity", seed=0, rel_in=5.0, entity_pred=False),
        score(stage="a", seed=0, mode=2, rel_in=4.0, discriminating_fraction=0.25),
        score(stage="a", seed=1, mode=2, rel_in=6.0, discriminating_fraction=0.75),
    ]
    df = aggregate(scores)
    assert list(df.columns)[:4] == ["family", "truth", "stage", "mode"]
    assert len(df) == 4  # (entity,a,m1), (entity,c,m1), (no_entity,a,m1), (entity,a,m2)
    a1 = df[(df.truth == "entity") & (df.stage == "a") & (df["mode"] == 1)].iloc[0]
    assert a1["n_runs"] == 2
    assert a1["median_rel_in"] == pytest.approx(2.0)
    assert a1["law_ok_rate"] == pytest.approx(1.0)
    assert a1["entity_correct_rate"] == pytest.approx(1.0)
    assert math.isnan(a1["median_discriminating_fraction"])
    c1 = df[(df.truth == "entity") & (df.stage == "c") & (df["mode"] == 1)].iloc[0]
    assert c1["n_runs"] == 1 and c1["median_rel_in"] == pytest.approx(2.0)
    a2 = df[(df.truth == "entity") & (df.stage == "a") & (df["mode"] == 2)].iloc[0]
    assert a2["median_discriminating_fraction"] == pytest.approx(0.5)
    assert a2["median_rel_in"] == pytest.approx(5.0)
    na = df[(df.truth == "no_entity") & (df.stage == "a") & (df["mode"] == 1)].iloc[0]
    assert na["entity_correct_rate"] == pytest.approx(1.0)


def test_pair_rate_uses_pair_level_scores():
    # Pair s0: entity correct, no_entity wrong -> pair False.
    # Pair s1: both correct -> True. Pair s2: only the entity member present -> excluded.
    scores = [
        score(truth="entity", seed=0, entity_pred=True, entity_truth=True),
        score(truth="no_entity", seed=0, entity_pred=True, entity_truth=False),
        score(truth="entity", seed=1, entity_pred=True, entity_truth=True),
        score(truth="no_entity", seed=1, entity_pred=False, entity_truth=False),
        score(truth="entity", seed=2, entity_pred=True, entity_truth=True),
    ]
    pt = pair_table(scores)
    row = pt[(pt.family == "beta") & (pt.stage == "a") & (pt["mode"] == 1)].iloc[0]
    assert row["n_pairs"] == 2
    assert row["n_incomplete_pairs"] == 1
    assert row["pair_entity_rate"] == pytest.approx(0.5)
    # Variant-level rate over the same runs counts each member separately.
    agg = aggregate(scores)
    v = agg[(agg.truth == "no_entity") & (agg.stage == "a")].iloc[0]
    assert v["entity_correct_rate"] == pytest.approx(0.5)


def test_stage_gap_table():
    scores = [
        score(stage="a", seed=0, rel_in=1.0, rubric_pass_rate=0.8),
        score(stage="a", seed=1, rel_in=1.0, rubric_pass_rate=0.8),
        score(stage="c", seed=0, rel_in=2.0, rubric_pass_rate=0.6),
        score(stage="d", seed=0, rel_in=4.0, rubric_pass_rate=0.4),
        # Only stage a and d for orbit: stage c gap must be NaN.
        score(family="orbit", stage="a", seed=0, rel_in=1.0, rubric_pass_rate=0.9),
        score(family="orbit", stage="d", seed=0, rel_in=3.0, rubric_pass_rate=0.5),
    ]
    gt = stage_gap_table(scores)
    beta = gt[(gt.family == "beta") & (gt.truth == "entity") & (gt["mode"] == 1)].iloc[0]
    assert beta["rel_in_c_minus_a"] == pytest.approx(1.0)
    assert beta["rel_in_d_minus_a"] == pytest.approx(3.0)
    assert beta["rubric_c_minus_a"] == pytest.approx(-0.2)
    assert beta["rubric_d_minus_a"] == pytest.approx(-0.4)
    orbit = gt[(gt.family == "orbit") & (gt.truth == "entity") & (gt["mode"] == 1)].iloc[0]
    assert math.isnan(orbit["rel_in_c_minus_a"])
    assert orbit["rel_in_d_minus_a"] == pytest.approx(2.0)


def test_results_roundtrip_parquet(tmp_path):
    scores = [
        score(stage="a", seed=0, entity_pred=None, answer_status="missing", judge_status="skipped",
              rubric_pass_rate=None, rel_in=None),
        score(stage="c", seed=0, judge_items={"x": {"pass": True, "quote": "q"}}),
        score(stage="d", seed=0, mode=2, discriminating_fraction=0.3),
    ]
    out = tmp_path / "results.parquet"
    write_results(scores, out)
    assert out.is_file()
    for name in ("results.summary.parquet", "results.pairs.parquet", "results.gaps.parquet"):
        assert (tmp_path / name).is_file()
    df = pd.read_parquet(out)
    assert list(df.columns) == RUN_COLUMNS
    assert len(df) == 3
    assert math.isnan(df.loc[0, "rel_in"]) or df.loc[0, "rel_in"] is None
    assert df.loc[0, "answer_status"] == "missing"
    assert json.loads(df.loc[1, "judge_items"]) == {"x": {"pass": True, "quote": "q"}}
    assert df.loc[2, "discriminating_fraction"] == pytest.approx(0.3)
    summary = pd.read_parquet(tmp_path / "results.summary.parquet")
    assert len(summary) == len(aggregate(scores))


def _run_report_cells(source: str) -> tuple[dict, str]:
    """Execute the report's python cells in order; returns (namespace, captured stdout)."""
    cells = re.findall(r"^```\{python\}\n(.*?)^```\s*$", source, flags=re.DOTALL | re.MULTILINE)
    assert cells, "report has no python cells"
    ns: dict = {}
    buf = StringIO()
    with redirect_stdout(buf):
        for cell in cells:
            exec(compile(cell, "report.qmd", "exec"), ns)
    return ns, buf.getvalue()


def test_report_qmd_code_cells_execute_on_fixture(tmp_path):
    scores = [
        score(stage="a", seed=0, rel_in=1.0, mode=1),
        score(stage="a", truth="no_entity", seed=0, rel_in=1.5, entity_pred=False),
        score(stage="c", seed=0, rel_in=2.0),
        score(stage="d", seed=0, rel_in=3.0),
        score(stage="a", seed=0, mode=2, rel_in=2.5, discriminating_fraction=0.4),
    ]
    results = tmp_path / "results.parquet"
    write_results(scores, results)
    source = REPORT.read_text(encoding="utf-8")
    assert 'results_path = "results.parquet"' in source
    source = source.replace('results_path = "results.parquet"', f"results_path = {str(results)!r}")
    ns, out = _run_report_cells(source)
    for name in ("runs", "summary", "pairs", "gaps"):
        assert name in ns, name
    assert len(ns["runs"]) == len(scores)
    assert "<table" in out
    assert "no single" in source.lower() or "no single headline" in source.lower()


@pytest.mark.skipif(shutil.which("quarto") is None, reason="quarto not installed")
def test_quarto_render_report(tmp_path):
    scores = [score(stage="a", seed=0)]
    write_results(scores, tmp_path / "results.parquet")
    shutil.copy(REPORT, tmp_path / "report.qmd")
    subprocess.run(["quarto", "render", str(tmp_path / "report.qmd")], check=True, cwd=tmp_path, timeout=300)
    assert (tmp_path / "report.html").is_file()


def test_cli_end_to_end_with_fake_runs(tmp_path, monkeypatch, capsys):
    import abductbench.evaluate.aggregate as agg
    from abductbench.evaluate import cli
    monkeypatch.setattr(agg, "oracle_scores", lambda c: OracleScores(nrmse_in=1.0, nrmse_extrap=1.0))
    runs = tmp_path / "runs"

    # Run 1: beta-entity-a with a constant law and a valid answer.
    cfg1 = VariantConfig(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1)
    d1 = runs / cfg1.variant_id
    d1.mkdir(parents=True)
    (d1 / "law.py").write_text(CONSTANT_SOURCE, encoding="utf-8")
    (d1 / "answer.md").write_text(VALID_ANSWER, encoding="utf-8")
    (d1 / "transcript.log").write_text("log\n", encoding="utf-8")
    RunRecord(
        variant_id=cfg1.variant_id, workspace=tmp_path / "ws1", law_path=d1 / "law.py",
        answer_path=d1 / "answer.md", transcript_path=d1 / "transcript.log", returncode=0, timed_out=False,
    ).save(d1 / "record.json")

    # Run 2: beta-no_entity-a with nothing produced.
    cfg2 = VariantConfig(family=Family.BETA, truth=Truth.NO_ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1)
    d2 = runs / cfg2.variant_id
    d2.mkdir(parents=True)
    RunRecord(
        variant_id=cfg2.variant_id, workspace=tmp_path / "ws2", law_path=None,
        answer_path=None, transcript_path=d2 / "transcript.log", returncode=1, timed_out=True,
    ).save(d2 / "record.json")

    results = tmp_path / "out" / "results.parquet"
    results.parent.mkdir()
    rc = cli.main([str(runs), str(results), "--no-judge"])
    assert rc == 0
    df = pd.read_parquet(results).set_index("variant_id")
    assert len(df) == 2
    assert df.loc[cfg1.variant_id, "law_status"] == "ok"
    assert df.loc[cfg1.variant_id, "entity_pred"] == True  # noqa: E712
    assert df.loc[cfg1.variant_id, "judge_status"] == "skipped"
    assert df.loc[cfg2.variant_id, "law_status"] == "missing"
    assert df.loc[cfg2.variant_id, "answer_status"] == "missing"
    assert bool(df.loc[cfg2.variant_id, "timed_out"]) is True
    assert (results.parent / "results.summary.parquet").is_file()
    assert (results.parent / "results.pairs.parquet").is_file()
    assert (results.parent / "results.gaps.parquet").is_file()
