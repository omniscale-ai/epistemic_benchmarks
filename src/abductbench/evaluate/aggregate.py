"""Per-run scores and aggregation over a set of runs.

``evaluate_run`` turns one saved run (``RunRecord``) into one ``RunScores`` row. It never
raises on agent output: a missing or broken law.py or answer.md becomes a status.
``aggregate`` / ``pair_table`` / ``stage_gap_table`` summarise a list of rows (or the
DataFrame read back from ``results.parquet``). There is no single headline number: every
table is split by family, truth, stage and mode.

Parquet layout written by ``write_results(scores, results.parquet)``:

- ``results.parquet``: one row per run (``RUN_COLUMNS``). ``judge_items`` is stored as a
  JSON string (or null); every other column is a plain scalar.
- ``results.summary.parquet``: ``aggregate`` output (family, truth, stage, mode).
- ``results.pairs.parquet``: ``pair_table`` output (family, stage, mode).
- ``results.gaps.parquet``: ``stage_gap_table`` output (family, truth, mode).

Scores are normalized by the oracle (``rel_in``, ``rel_extrap``). Judge errors are never
counted as a pass; they are excluded from rubric means and reported as a count.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np
import pandas as pd

from abductbench.config import VariantConfig, pair_id_of
from abductbench.evaluate.answer import ParsedAnswer, pair_entity_score, parse_answer
from abductbench.evaluate.judge import build_judge_prompt, run_judge
from abductbench.evaluate.law_eval import evaluate_law
from abductbench.evaluate.oracle import NormalizedScores, OracleScores, normalize, oracle_scores
from abductbench.evaluate.rubric import load_rubric
from abductbench.ledger import discriminating_fraction
from abductbench.runner import LEDGER_COPY_NAME, RunRecord
from abductbench.tasks import build_task

# Stand-in for a law.py that was never produced: evaluate_law reports it as "missing".
_NO_LAW = Path("/nonexistent-law-dir") / "law.py"


@dataclass
class RunScores:
    variant_id: str
    family: str
    truth: str
    stage: str
    seed: int
    mode: int
    law_status: str
    law_detail: str
    nrmse_in: float | None
    nrmse_extrap: float | None
    rel_in: float | None
    rel_extrap: float | None
    n_params_proxy: int | None
    domain_score: float | None
    answer_status: str
    entity_pred: bool | None
    entity_truth: bool
    rubric_pass_rate: float | None
    judge_status: str  # 'ok' | 'judge_error' | 'skipped'
    judge_items: dict | None
    discriminating_fraction: float | None  # mode 2 only
    timed_out: bool
    returncode: int | None


RUN_COLUMNS = [f.name for f in fields(RunScores)]
GROUP_KEYS = ["family", "truth", "stage", "mode"]
STAGES = ("a", "b", "c", "d")


def _dir_of(record: RunRecord) -> Path | None:
    for path in (record.transcript_path, record.answer_path, record.law_path):
        if path is not None:
            return Path(path).parent
    return None


def _oracle(cfg: VariantConfig, cache: dict | None) -> OracleScores:
    if cache is None:
        return oracle_scores(cfg)
    if cfg not in cache:
        cache[cfg] = oracle_scores(cfg)
    return cache[cfg]


def evaluate_run(
    cfg: VariantConfig,
    record: RunRecord,
    judge_runner=None,
    oracle_cache: dict | None = None,
    use_judge: bool = True,
    run_dir: Path | None = None,
) -> RunScores:
    """Score one run. ``judge_runner`` is passed to ``run_judge`` (None: the Claude CLI).

    ``run_dir`` is the directory holding ``record.json`` and ``ledger.jsonl``; when omitted
    it is taken from the record's paths. The oracle is only computed when the law ran.
    """
    if record.variant_id != cfg.variant_id:
        raise ValueError(f"record {record.variant_id!r} does not match config {cfg.variant_id!r}")
    bundle = build_task(cfg)

    law = evaluate_law(bundle, record.law_path if record.law_path is not None else _NO_LAW)
    if law.status == "ok":
        norm = normalize(law, _oracle(cfg, oracle_cache))
    else:
        norm = NormalizedScores(rel_in=None, rel_extrap=None)

    if record.answer_path is not None:
        answer = parse_answer(Path(record.answer_path))
    else:
        answer = ParsedAnswer(status="missing", entity=None, sections={})

    judge_status = "skipped"
    judge_items = None
    rubric_rate = None
    if use_judge and answer.status == "ok":
        rubric = load_rubric(bundle.rubric_id)
        expected = [item.id for item in rubric.items]
        result = run_judge(build_judge_prompt(rubric, answer), runner=judge_runner, expected_ids=expected)
        if result.status == "ok":
            judge_status = "ok"
            judge_items = result.items
            passed = sum(1 for item_id in expected if result.items[item_id]["pass"] is True)
            rubric_rate = passed / len(expected)
        else:
            judge_status = "judge_error"

    disc = None
    if cfg.mode == 2:
        base = Path(run_dir) if run_dir is not None else _dir_of(record)
        ledger = None if base is None else base / LEDGER_COPY_NAME
        if ledger is not None and ledger.is_file():
            try:
                disc = discriminating_fraction(ledger, bundle.discriminating_queries)
            except (OSError, ValueError, KeyError):
                disc = None

    return RunScores(
        variant_id=cfg.variant_id,
        family=cfg.family.value,
        truth=cfg.truth.value,
        stage=cfg.stage.value,
        seed=cfg.seed,
        mode=cfg.mode,
        law_status=law.status,
        law_detail=law.detail,
        nrmse_in=law.nrmse_in,
        nrmse_extrap=law.nrmse_extrap,
        rel_in=norm.rel_in,
        rel_extrap=norm.rel_extrap,
        n_params_proxy=law.n_params_proxy,
        domain_score=law.domain_score,
        answer_status=answer.status,
        entity_pred=answer.entity,
        entity_truth=bool(bundle.entity),
        rubric_pass_rate=rubric_rate,
        judge_status=judge_status,
        judge_items=judge_items,
        discriminating_fraction=disc,
        timed_out=bool(record.timed_out),
        returncode=record.returncode,
    )


def _frame(scores) -> pd.DataFrame:
    if isinstance(scores, pd.DataFrame):
        return scores.reset_index(drop=True)
    rows = [asdict(s) if not isinstance(s, dict) else s for s in scores]
    return pd.DataFrame(rows, columns=RUN_COLUMNS)


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def _entity_correct(answer_status, entity_pred, entity_truth) -> list[bool]:
    return [
        status == "ok" and pred is not None and not (isinstance(pred, float) and math.isnan(pred))
        and bool(pred) == bool(truth)
        for status, pred, truth in zip(answer_status, entity_pred, entity_truth)
    ]


def aggregate(scores) -> pd.DataFrame:
    """One row per (family, truth, stage, mode). Accepts a list of RunScores or a DataFrame."""
    df = _frame(scores)
    columns = GROUP_KEYS + [
        "n_runs", "law_ok_rate", "answer_ok_rate", "median_rel_in", "median_rel_extrap",
        "median_domain_score", "rubric_pass_rate_mean", "judge_error_count",
        "entity_correct_rate", "median_discriminating_fraction",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    df = df.assign(_correct=_entity_correct(df.answer_status, df.entity_pred, df.entity_truth))
    rows = []
    for key, g in df.groupby(GROUP_KEYS, sort=True):
        rubric = _num(g.rubric_pass_rate[g.judge_status == "ok"]).dropna()
        rows.append({
            **dict(zip(GROUP_KEYS, key)),
            "n_runs": len(g),
            "law_ok_rate": float((g.law_status == "ok").mean()),
            "answer_ok_rate": float((g.answer_status == "ok").mean()),
            "median_rel_in": _num(g.rel_in).median(),
            "median_rel_extrap": _num(g.rel_extrap).median(),
            "median_domain_score": _num(g.domain_score).median(),
            "rubric_pass_rate_mean": float(rubric.mean()) if len(rubric) else float("nan"),
            "judge_error_count": int((g.judge_status == "judge_error").sum()),
            "entity_correct_rate": float(g._correct.mean()),
            "median_discriminating_fraction": _num(g.discriminating_fraction).median(),
        })
    return pd.DataFrame(rows, columns=columns)


def pair_table(scores) -> pd.DataFrame:
    """Pair-level ENTITY rate per (family, stage, mode).

    A pair counts only when both its members (entity and no_entity, same seed and mode) are
    present; incomplete pairs are reported separately. A pair is correct only when both
    members parsed ok with the correct ENTITY value (``pair_entity_score``).
    """
    df = _frame(scores)
    columns = ["family", "stage", "mode", "n_pairs", "n_incomplete_pairs", "pair_entity_rate"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for (family, stage, mode), g in df.groupby(["family", "stage", "mode"], sort=True):
        answers: dict[str, ParsedAnswer] = {}
        truths: dict[str, bool] = {}
        members: dict[str, set[bool]] = {}
        for r in g.itertuples(index=False):
            answers[r.variant_id] = ParsedAnswer(
                status=r.answer_status,
                entity=None if r.entity_pred is None or pd.isna(r.entity_pred) else bool(r.entity_pred),
            )
            truths[r.variant_id] = bool(r.entity_truth)
            members.setdefault(pair_id_of(r.variant_id), set()).add(bool(r.entity_truth))
        complete = {p for p, t in members.items() if t == {True, False}}
        complete_truths = {v: t for v, t in truths.items() if pair_id_of(v) in complete}
        result = pair_entity_score(answers, complete_truths)
        rate = float(np.mean(list(result.values()))) if result else float("nan")
        rows.append({
            "family": family,
            "stage": stage,
            "mode": int(mode),
            "n_pairs": len(result),
            "n_incomplete_pairs": len(members) - len(complete),
            "pair_entity_rate": rate,
        })
    return pd.DataFrame(rows, columns=columns)


def _diff(agg: pd.DataFrame, stage: str, base: pd.Series, column: str) -> float:
    row = agg[agg.stage == stage]
    if row.empty or base is None:
        return float("nan")
    return float(row[column].iloc[0] - base[column])


def stage_gap_table(scores) -> pd.DataFrame:
    """Differences against stage a, per (family, truth, mode): stage c minus a, stage d minus a.

    Columns are NaN when the stage (or stage a) is absent from the runs.
    """
    agg = aggregate(scores)
    columns = ["family", "truth", "mode"] + [
        f"{metric}_{stage}_minus_a"
        for metric in ("rel_in", "rubric", "entity")
        for stage in ("c", "d")
    ]
    if agg.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for (family, truth, mode), g in agg.groupby(["family", "truth", "mode"], sort=True):
        a_rows = g[g.stage == "a"]
        base = a_rows.iloc[0] if not a_rows.empty else None
        row = {"family": family, "truth": truth, "mode": int(mode)}
        for stage in ("c", "d"):
            row[f"rel_in_{stage}_minus_a"] = _diff(g, stage, base, "median_rel_in")
            row[f"rubric_{stage}_minus_a"] = _diff(g, stage, base, "rubric_pass_rate_mean")
            row[f"entity_{stage}_minus_a"] = _diff(g, stage, base, "entity_correct_rate")
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def sibling_path(results_path: Path, kind: str) -> Path:
    """results.parquet -> results.<kind>.parquet (kind: summary, pairs, gaps)."""
    p = Path(results_path)
    return p.with_name(f"{p.stem}.{kind}.parquet")


def write_results(scores: Iterable[RunScores], results_path: Path) -> None:
    """Write the run rows and the three derived tables next to ``results_path``."""
    scores = list(scores)
    runs = _frame(scores).copy()
    runs["judge_items"] = runs["judge_items"].map(
        lambda v: None if v is None or (isinstance(v, float) and math.isnan(v)) else json.dumps(v, sort_keys=True)
    )
    runs = runs[RUN_COLUMNS]
    runs.to_parquet(results_path, index=False)
    aggregate(scores).to_parquet(sibling_path(results_path, "summary"), index=False)
    pair_table(scores).to_parquet(sibling_path(results_path, "pairs"), index=False)
    stage_gap_table(scores).to_parquet(sibling_path(results_path, "gaps"), index=False)
