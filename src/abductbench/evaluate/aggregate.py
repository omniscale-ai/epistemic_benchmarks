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
from abductbench.evaluate.mechanism import score_mechanism
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
    error: str | None = None  # evaluator-side failure text (e.g. oracle); None when clean
    mech_status: str = "missing"  # 'ok' | 'missing' | 'bad'
    mech_declared_kind: str | None = None
    mech_kind_ok: bool = False
    mech_params_ok: bool | None = None  # None: not scored (wrong kind, parameterless kind)
    mech_param_errors: str | None = None  # JSON dict of measured parameter errors


RUN_COLUMNS = [f.name for f in fields(RunScores)]
GROUP_KEYS = ["family", "truth", "stage", "mode"]
AGG_COLUMNS = GROUP_KEYS + [
    "n_runs", "law_ok_rate", "answer_ok_rate", "median_rel_in", "median_rel_extrap",
    "median_domain_score", "rubric_pass_rate_mean", "n_judged", "judge_error_count",
    "entity_correct_rate", "timeout_rate", "median_discriminating_fraction",
    "n_with_discriminating_fraction",
    "mechanism_kind_rate", "mechanism_params_rate", "n_params_scored",
]
PAIR_COLUMNS = ["family", "stage", "mode", "n_pairs", "n_incomplete_pairs", "pair_entity_rate"]
GAP_METRICS = {
    "rel_in": "median_rel_in",
    "rubric": "rubric_pass_rate_mean",
    "entity": "entity_correct_rate",
    "law_ok_rate": "law_ok_rate",
    "answer_ok_rate": "answer_ok_rate",
    "mechanism_kind_rate": "mechanism_kind_rate",
}
GAP_COLUMNS = ["family", "truth", "mode"] + [
    f"{m}_{s}" for m in GAP_METRICS for s in ("a", "c", "d")
] + [f"{m}_{s}_minus_a" for m in GAP_METRICS for s in ("c", "d")]


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
    error = None
    if law.status == "ok":
        try:
            norm = normalize(law, _oracle(cfg, oracle_cache))
        except Exception as exc:  # oracle failure is not agent output, but must not abort a batch
            error = f"oracle failed: {type(exc).__name__}: {exc}"
            norm = NormalizedScores(rel_in=None, rel_extrap=None)
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
        # A mode-2 run with a missing or unreadable ledger counts as 0.0, so it cannot silently
        # drop out of the median.
        disc = 0.0
        base = Path(run_dir) if run_dir is not None else _dir_of(record)
        ledger = None if base is None else base / LEDGER_COPY_NAME
        if ledger is not None and ledger.is_file():
            try:
                disc = discriminating_fraction(ledger, bundle.discriminating_queries)
            except (OSError, ValueError, KeyError, TypeError):
                disc = 0.0

    # The mechanism axis is scored independently of the prediction axis: law.mechanism is None
    # (-> "missing") when law.py could not be imported or timed out.
    mech = score_mechanism(bundle.true_mechanism, law.mechanism)
    mech_errors = json.dumps(mech.param_errors, sort_keys=True) if mech.param_errors else None

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
        error=error,
        mech_status=mech.status,
        mech_declared_kind=mech.declared_kind,
        mech_kind_ok=bool(mech.kind_ok),
        mech_params_ok=mech.params_ok,
        mech_param_errors=mech_errors,
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


def _flag(v) -> bool | None:
    """Bool or None from a possibly NaN/None parquet cell."""
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA:
        return None
    return bool(v)


def aggregate(scores) -> pd.DataFrame:
    """One row per (family, truth, stage, mode). Accepts a list of RunScores or a DataFrame."""
    df = _frame(scores)
    columns = AGG_COLUMNS
    if df.empty:
        return pd.DataFrame(columns=columns)
    df = df.assign(
        _correct=_entity_correct(df.answer_status, df.entity_pred, df.entity_truth),
        _kind_ok=[_flag(v) is True for v in df.mech_kind_ok],
    )
    rows = []
    for key, g in df.groupby(GROUP_KEYS, sort=True):
        rubric = _num(g.rubric_pass_rate[g.judge_status == "ok"]).dropna()
        scored = [_flag(v) for v in g.mech_params_ok if _flag(v) is not None]
        rows.append({
            **dict(zip(GROUP_KEYS, key)),
            "n_runs": len(g),
            "law_ok_rate": float((g.law_status == "ok").mean()),
            "answer_ok_rate": float((g.answer_status == "ok").mean()),
            "median_rel_in": _num(g.rel_in).median(),
            "median_rel_extrap": _num(g.rel_extrap).median(),
            "median_domain_score": _num(g.domain_score).median(),
            "rubric_pass_rate_mean": float(rubric.mean()) if len(rubric) else float("nan"),
            "n_judged": int((g.judge_status == "ok").sum()),
            "judge_error_count": int((g.judge_status == "judge_error").sum()),
            "entity_correct_rate": float(g._correct.mean()),
            "timeout_rate": float(g.timed_out.astype(bool).mean()),
            "median_discriminating_fraction": _num(g.discriminating_fraction).median(),
            "n_with_discriminating_fraction": int(_num(g.discriminating_fraction).notna().sum()),
            "mechanism_kind_rate": float(g._kind_ok.mean()),
            "mechanism_params_rate": float(np.mean(scored)) if scored else float("nan"),
            "n_params_scored": len(scored),
        })
    return pd.DataFrame(rows, columns=columns)


def pair_table(scores) -> pd.DataFrame:
    """Pair-level ENTITY rate per (family, stage, mode).

    A pair counts only when both its members (entity and no_entity, same seed and mode) are
    present; incomplete pairs are reported separately. A pair is correct only when both
    members parsed ok with the correct ENTITY value (``pair_entity_score``).
    """
    df = _frame(scores)
    columns = PAIR_COLUMNS
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


def stage_gap_table(scores) -> pd.DataFrame:
    """Per (family, truth, mode): each metric at stages a, c, d, and the differences c-a, d-a.

    Gaps compare the runs that survived in each stage. The law_ok and answer_ok columns show
    how many failures sit behind each gap. Values are NaN when a stage is absent.
    """
    agg = aggregate(scores)
    if agg.empty:
        return pd.DataFrame(columns=GAP_COLUMNS)
    rows = []
    for (family, truth, mode), g in agg.groupby(["family", "truth", "mode"], sort=True):
        values = {}
        for stage in ("a", "c", "d"):
            hit = g[g.stage == stage]
            values[stage] = hit.iloc[0] if not hit.empty else None
        row = {"family": family, "truth": truth, "mode": int(mode)}
        for metric, column in GAP_METRICS.items():
            for stage in ("a", "c", "d"):
                v = values[stage]
                row[f"{metric}_{stage}"] = float(v[column]) if v is not None else float("nan")
            for stage in ("c", "d"):
                row[f"{metric}_{stage}_minus_a"] = row[f"{metric}_{stage}"] - row[f"{metric}_a"]
        rows.append(row)
    return pd.DataFrame(rows, columns=GAP_COLUMNS)


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
