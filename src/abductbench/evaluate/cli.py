"""Evaluate saved runs: ``python -m abductbench.evaluate.cli <runs_dir> <results.parquet> [--no-judge]``.

Walks ``<runs_dir>/*/record.json`` (as written by ``runner.make_run``), scores every run,
and writes ``results.parquet`` plus the ``results.summary/pairs/gaps.parquet`` siblings
(see ``abductbench.evaluate.aggregate``). ``--no-judge`` skips all judge calls, so the
rubric columns are left empty and ``judge_status`` is 'skipped'.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from abductbench.config import cfg_from_variant_id
from abductbench.evaluate.aggregate import evaluate_run, write_results
from abductbench.runner import RunRecord


def _rebase(record: RunRecord, run_dir: Path) -> RunRecord:
    """Point record paths at run_dir when the saved absolute paths no longer exist (moved runs)."""

    def fix(path: Path | None) -> Path | None:
        if path is None or Path(path).exists():
            return path
        candidate = run_dir / Path(path).name
        return candidate if candidate.exists() else path

    record.law_path = fix(record.law_path)
    record.answer_path = fix(record.answer_path)
    record.transcript_path = fix(record.transcript_path)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs_dir", type=Path)
    parser.add_argument("results", type=Path, help="output parquet path, e.g. results.parquet")
    parser.add_argument("--no-judge", action="store_true", help="skip rubric judge calls")
    args = parser.parse_args(argv)

    scores = []
    skipped = 0
    oracle_cache: dict = {}
    record_paths = sorted(args.runs_dir.glob("*/record.json"))
    if not record_paths:
        print(f"warning: no record.json files under {args.runs_dir}", file=sys.stderr)
    for record_path in record_paths:
        run_dir = record_path.parent
        try:
            record = _rebase(RunRecord.load(record_path), run_dir)
            cfg = cfg_from_variant_id(record.variant_id)
            scores.append(
                evaluate_run(
                    cfg,
                    record,
                    oracle_cache=oracle_cache,
                    use_judge=not args.no_judge,
                    run_dir=run_dir,
                )
            )
        except Exception as exc:  # one bad run must not abort the batch
            skipped += 1
            print(f"warning: skipped run {run_dir}: {type(exc).__name__}: {exc}", file=sys.stderr)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    write_results(scores, args.results)
    print(f"evaluated {len(scores)} runs, skipped {skipped} -> {args.results}")
    # Nonzero only when no run could be evaluated at all.
    return 0 if scores else 1


if __name__ == "__main__":
    raise SystemExit(main())
