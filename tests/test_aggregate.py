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
    AGG_COLUMNS,
    GAP_COLUMNS,
    PAIR_COLUMNS,
    RUN_COLUMNS,
    RunScores,
    aggregate,
    evaluate_run,
    pair_table,
    stage_gap_table,
    write_results,
)
from abductbench.evaluate.oracle import OracleScores
from abductbench.runner import LEDGER_COPY_NAME, RunRecord

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
        error=None,
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
        f"MECHANISM = {json.dumps({k: v for k, v in bundle.true_mechanism.items() if k != 'tolerance'})}\n"
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
    return json.dumps({"items": {i: {"pass": True, "quote": "x", "reason": "ok"} for i in ids}})


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


def _cli_run_dir(runs: Path, cfg: VariantConfig) -> Path:
    d = runs / cfg.variant_id
    d.mkdir(parents=True)
    return d


def test_evaluate_run_oracle_exception_is_recorded(tmp_path, monkeypatch):
    import abductbench.evaluate.aggregate as agg

    cfg = vcfg()
    law = write_law(tmp_path / "ws", CONSTANT_SOURCE)

    def boom(c):
        raise RuntimeError("boom")

    monkeypatch.setattr(agg, "oracle_scores", boom)
    s = evaluate_run(cfg, record_for(cfg, law_path=law), oracle_cache={}, use_judge=False)
    assert s.law_status == "ok"
    assert s.nrmse_in is not None
    assert s.rel_in is None and s.rel_extrap is None
    assert s.error is not None and "boom" in s.error
    json.dumps(dataclasses.asdict(s))


def test_mode2_ledger_reading(tmp_path):
    cfg = vcfg(mode=2)
    run = tmp_path / "run"
    run.mkdir()
    # Budget line, then 1.0 on a non-discriminating type and 5.0 on a discriminating one.
    (run / LEDGER_COPY_NAME).write_text(
        json.dumps({"budget": 100.0}) + "\n"
        + json.dumps({"query_type": "events", "cost": 1.0, "args": {}, "remaining": 99.0}) + "\n"
        + json.dumps({"query_type": "recoil_correlation", "cost": 5.0, "args": {}, "remaining": 94.0}) + "\n",
        encoding="utf-8",
    )
    s = evaluate_run(cfg, record_for(cfg), use_judge=False, run_dir=run)
    assert s.discriminating_fraction == pytest.approx(5.0 / 6.0)

    # Missing ledger in a mode-2 run counts as 0.0, not as a dropped row.
    empty = tmp_path / "empty"
    empty.mkdir()
    s_missing = evaluate_run(cfg, record_for(cfg), use_judge=False, run_dir=empty)
    assert s_missing.discriminating_fraction == 0.0

    # Unreadable ledger also counts as 0.0.
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / LEDGER_COPY_NAME).write_text("{not json\n", encoding="utf-8")
    s_broken = evaluate_run(cfg, record_for(cfg), use_judge=False, run_dir=broken)
    assert s_broken.discriminating_fraction == 0.0

    # Mode 1 never has a discriminating fraction.
    cfg1 = vcfg(mode=1)
    s1 = evaluate_run(cfg1, record_for(cfg1), use_judge=False, run_dir=run)
    assert s1.discriminating_fraction is None


def test_aggregate_visibility_columns():
    scores = [
        score(mode=1, seed=0, timed_out=True),
        score(mode=1, seed=1, timed_out=False, judge_status="judge_error", rubric_pass_rate=None),
        score(mode=1, seed=2, timed_out=False, rubric_pass_rate=0.4),
        score(mode=2, seed=0, discriminating_fraction=0.5),
        score(mode=2, seed=1, discriminating_fraction=None),
    ]
    df = aggregate(scores)
    m1 = df[(df["mode"] == 1)].iloc[0]
    assert m1["timeout_rate"] == pytest.approx(1 / 3)
    assert m1["n_judged"] == 2
    assert m1["n_with_discriminating_fraction"] == 0
    m2 = df[(df["mode"] == 2)].iloc[0]
    assert m2["n_with_discriminating_fraction"] == 1
    assert m2["median_discriminating_fraction"] == pytest.approx(0.5)


def test_stage_gap_table_law_and_answer_rates():
    scores = [
        score(stage="a", seed=0, law_status="ok", answer_status="ok"),
        score(stage="a", seed=1, law_status="crash", answer_status="ok", rel_in=None),
        score(stage="c", seed=0, law_status="ok", answer_status="missing", entity_pred=None),
        score(stage="d", seed=0, law_status="ok", answer_status="ok"),
    ]
    gt = stage_gap_table(scores)
    row = gt.iloc[0]
    assert row["law_ok_rate_a"] == pytest.approx(0.5)
    assert row["law_ok_rate_c"] == pytest.approx(1.0)
    assert row["law_ok_rate_c_minus_a"] == pytest.approx(0.5)
    assert row["answer_ok_rate_c"] == pytest.approx(0.0)
    assert row["answer_ok_rate_c_minus_a"] == pytest.approx(-1.0)
    assert row["answer_ok_rate_d_minus_a"] == pytest.approx(0.0)


def test_cli_skips_bad_runs_and_writes_the_rest(tmp_path, monkeypatch, capsys):
    import abductbench.evaluate.aggregate as agg
    from abductbench.evaluate import cli

    monkeypatch.setattr(agg, "oracle_scores", lambda c: OracleScores(nrmse_in=1.0, nrmse_extrap=1.0))
    runs = tmp_path / "runs"
    good_cfg = VariantConfig(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1)
    good = _cli_run_dir(runs, good_cfg)
    (good / "law.py").write_text(CONSTANT_SOURCE, encoding="utf-8")
    RunRecord(variant_id=good_cfg.variant_id, workspace=tmp_path, law_path=good / "law.py",
              answer_path=None, transcript_path=None, returncode=0, timed_out=False).save(good / "record.json")
    # Malformed JSON.
    bad_json = runs / "beta-entity-a-s1-m1"
    bad_json.mkdir()
    (bad_json / "record.json").write_text("{not json", encoding="utf-8")
    # Bad variant id inside a valid record.
    bad_id = runs / "bad-id-run"
    bad_id.mkdir()
    RunRecord(variant_id="gamma-entity-a-s0-m1", workspace=tmp_path, law_path=None, answer_path=None,
              transcript_path=None, returncode=0, timed_out=False).save(bad_id / "record.json")

    results = tmp_path / "out" / "results.parquet"
    rc = cli.main([str(runs), str(results), "--no-judge"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "beta-entity-a-s1-m1" in captured.err
    assert "bad-id-run" in captured.err
    assert "skipped 2" in captured.out
    df = pd.read_parquet(results)
    assert list(df["variant_id"]) == [good_cfg.variant_id]


def test_cli_nonzero_exit_when_nothing_evaluated(tmp_path, capsys):
    from abductbench.evaluate import cli

    runs = tmp_path / "runs"
    (runs / "x").mkdir(parents=True)
    (runs / "x" / "record.json").write_text("{not json", encoding="utf-8")
    results = tmp_path / "out" / "results.parquet"
    rc = cli.main([str(runs), str(results), "--no-judge"])
    assert rc != 0
    assert "x" in capsys.readouterr().err
    assert results.is_file()
    assert len(pd.read_parquet(results)) == 0


def test_mechanism_fields_end_to_end(tmp_path):
    cfg = vcfg()
    from abductbench.tasks import build_task

    bundle = build_task(cfg)
    law = write_law(tmp_path / "ok", perfect_source(bundle))
    s = evaluate_run(cfg, record_for(cfg, law_path=law), oracle_cache={}, use_judge=False)
    assert s.mech_status == "ok" and s.mech_declared_kind == "hidden_carriers"
    assert s.mech_kind_ok is True and s.mech_params_ok is True
    assert set(json.loads(s.mech_param_errors)) == {"n_carriers", "mass"}

    # No MECHANISM: law metrics intact, mechanism missing.
    s = evaluate_run(cfg, record_for(cfg, law_path=write_law(tmp_path / "nomech", CONSTANT_SOURCE)),
                     oracle_cache={}, use_judge=False)
    assert s.law_status == "ok" and s.mech_status == "missing"
    assert s.mech_kind_ok is False and s.mech_params_ok is None and s.mech_param_errors is None

    # Wrong kind / malformed / crashed law / no law.
    wrong = CONSTANT_SOURCE + "MECHANISM = {'kind': 'detector_response'}\n"
    s = evaluate_run(cfg, record_for(cfg, law_path=write_law(tmp_path / "w", wrong)), oracle_cache={}, use_judge=False)
    assert (s.mech_status, s.mech_kind_ok, s.mech_params_ok, s.mech_declared_kind) == ("ok", False, None, "detector_response")
    bad = CONSTANT_SOURCE + "MECHANISM = [1]\n"
    s = evaluate_run(cfg, record_for(cfg, law_path=write_law(tmp_path / "b", bad)), oracle_cache={}, use_judge=False)
    assert s.law_status == "ok" and s.mech_status == "bad" and s.mech_kind_ok is False
    crash = "MECHANISM = {'kind': 'hidden_carriers', 'n_carriers': 1, 'mass': 0.0}\ndef law(t):\n    raise ValueError\n"
    s = evaluate_run(cfg, record_for(cfg, law_path=write_law(tmp_path / "c", crash)), oracle_cache={}, use_judge=False)
    # law crashes inside law(): the mechanism axis is scored independently of the prediction axis.
    assert s.law_status == "crash" and s.mech_status == "ok" and s.mech_kind_ok is True and s.mech_params_ok is True
    s = evaluate_run(cfg, record_for(cfg), oracle_cache={}, use_judge=False)
    assert s.mech_status == "missing" and s.mech_kind_ok is False
    json.dumps(dataclasses.asdict(s))


def test_aggregate_and_gap_mechanism_columns(tmp_path):
    rows = [
        score(stage="a", seed=0, mech_status="ok", mech_kind_ok=True, mech_params_ok=True),
        score(stage="a", seed=1, mech_status="ok", mech_kind_ok=True, mech_params_ok=False),
        score(stage="a", seed=2, mech_status="ok", mech_kind_ok=False, mech_params_ok=None),
        score(stage="a", seed=3, mech_status="missing", mech_kind_ok=False),
        score(stage="c", seed=0, mech_status="ok", mech_kind_ok=True, mech_params_ok=True),
        score(stage="c", seed=1, mech_status="ok", mech_kind_ok=True, mech_params_ok=True),
        score(stage="d", seed=0, mech_status="bad", mech_kind_ok=False),
    ]
    agg = aggregate(rows).set_index("stage")
    assert agg.loc["a", "mechanism_kind_rate"] == pytest.approx(0.5)
    assert agg.loc["a", "mechanism_params_rate"] == pytest.approx(0.5) and agg.loc["a", "n_params_scored"] == 2
    assert agg.loc["c", "mechanism_kind_rate"] == 1.0 and agg.loc["c", "mechanism_params_rate"] == 1.0
    assert agg.loc["d", "mechanism_kind_rate"] == 0.0
    assert math.isnan(agg.loc["d", "mechanism_params_rate"]) and agg.loc["d", "n_params_scored"] == 0
    gaps = stage_gap_table(rows).iloc[0]
    assert gaps.mechanism_kind_rate_a == pytest.approx(0.5)
    assert gaps.mechanism_kind_rate_c_minus_a == pytest.approx(0.5)
    assert gaps.mechanism_kind_rate_d_minus_a == pytest.approx(-0.5)
    # Parquet round trip, including None params_ok and the DataFrame input path.
    results = tmp_path / "results.parquet"
    write_results(rows, results)
    df = pd.read_parquet(results)
    assert list(df.columns) == RUN_COLUMNS
    again = aggregate(df).set_index("stage")
    assert again.loc["a", "mechanism_kind_rate"] == pytest.approx(0.5)
    assert again.loc["a", "n_params_scored"] == 2
    assert "mechanism_kind_rate" in pd.read_parquet(tmp_path / "results.summary.parquet").columns


def test_empty_scores_everywhere(tmp_path):
    assert aggregate([]).empty and list(aggregate([]).columns) == AGG_COLUMNS
    assert pair_table([]).empty and list(pair_table([]).columns) == PAIR_COLUMNS
    gt = stage_gap_table([])
    assert gt.empty and list(gt.columns) == GAP_COLUMNS
    results = tmp_path / "results.parquet"
    write_results([], results)
    assert list(pd.read_parquet(results).columns) == RUN_COLUMNS
    assert list(pd.read_parquet(tmp_path / "results.summary.parquet").columns) == AGG_COLUMNS
    assert list(pd.read_parquet(tmp_path / "results.pairs.parquet").columns) == PAIR_COLUMNS
    assert list(pd.read_parquet(tmp_path / "results.gaps.parquet").columns) == GAP_COLUMNS
    source = REPORT.read_text(encoding="utf-8").replace(
        'results_path = "results.parquet"', f"results_path = {str(results)!r}"
    )
    ns, out = _run_report_cells(source)
    assert len(ns["runs"]) == 0 and len(ns["summary"]) == 0
    assert "<table" in out
