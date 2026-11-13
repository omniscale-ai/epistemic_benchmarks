"""Re-run the LLM judge over saved runs and report verdicts, reasons and repeat agreement.

Usage: ``python scripts/rejudge.py <runs_dir> <out_json> [--repeat N] [--workers 4] [--limit K]``

For every ``<runs_dir>/*/record.json`` whose answer file parses with status ok, the judge
runs ``--repeat`` times. The output JSON is rewritten after every finished judge call, so a
crash keeps partial results.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path

from abductbench.config import cfg_from_variant_id
from abductbench.evaluate.answer import parse_answer
from abductbench.evaluate.judge import build_judge_prompt, run_judge
from abductbench.evaluate.rubric import load_rubric
from abductbench.runner import RECORD_NAME, RunRecord
from abductbench.tasks import build_task


def _rate(items: dict) -> float:
    return sum(1 for v in items.values() if v["pass"] is True) / len(items)


def summarize(runs: list[dict]) -> dict:
    """Mean rubric pass rate per repeat index, per-item pass rate, and repeat agreement."""
    rates_by_rep: dict[int, list[float]] = defaultdict(list)
    item_pass: dict[str, list[bool]] = defaultdict(list)
    agree_all: list[bool] = []
    agree_item: dict[str, list[bool]] = defaultdict(list)
    for run in runs:
        ok_reps = []
        for k, rep in enumerate(run["repeats"]):
            if rep["status"] != "ok":
                continue
            ok_reps.append(rep["items"])
            rates_by_rep[k].append(_rate(rep["items"]))
            for item_id, v in rep["items"].items():
                item_pass[item_id].append(v["pass"] is True)
        for a, b in combinations(ok_reps, 2):
            for item_id in a:
                same = a[item_id]["pass"] == b[item_id]["pass"]
                agree_all.append(same)
                agree_item[item_id].append(same)
    mean = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    summary = {
        "n_runs": len(runs),
        "mean_rubric_pass_rate_per_repeat": [mean(rates_by_rep[k]) for k in sorted(rates_by_rep)],
        "per_item_pass_rate": {i: mean([float(x) for x in v]) for i, v in sorted(item_pass.items())},
    }
    if agree_all:
        summary["item_agreement"] = mean([float(x) for x in agree_all])
        summary["per_item_agreement"] = {i: mean([float(x) for x in v]) for i, v in sorted(agree_item.items())}
    return summary


def _write(out_json: Path, runs: list[dict]) -> None:
    tmp = out_json.with_name(out_json.name + ".tmp")
    tmp.write_text(json.dumps({"runs": runs, "summary": summarize(runs)}, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, out_json)


def _collect(runs_dir: Path, limit: int | None) -> list[tuple[str, object, object]]:
    found = []
    for rec_path in sorted(Path(runs_dir).glob(f"*/{RECORD_NAME}")):
        record = RunRecord.load(rec_path)
        if record.answer_path is None or not Path(record.answer_path).is_file():
            continue
        answer = parse_answer(Path(record.answer_path))
        if answer.status != "ok":
            continue
        rubric = load_rubric(build_task(cfg_from_variant_id(record.variant_id)).rubric_id)
        found.append((record.variant_id, rubric, answer))
        if limit is not None and len(found) >= limit:
            break
    return found


def rejudge(
    runs_dir: Path,
    out_json: Path,
    repeat: int = 1,
    workers: int = 4,
    limit: int | None = None,
    run: Callable = run_judge,
) -> dict:
    """Judge every eligible run ``repeat`` times; ``run(prompt, expected_ids=...)`` returns a JudgeResult."""
    out_json = Path(out_json)
    targets = _collect(Path(runs_dir), limit)
    slots: list[list[dict | None]] = [[None] * repeat for _ in targets]

    def snapshot() -> list[dict]:
        runs = []
        for (variant_id, _, _), reps in zip(targets, slots):
            done = [r for r in reps if r is not None]
            rates = [_rate(r["items"]) if r["status"] == "ok" else None for r in done]
            runs.append({"variant_id": variant_id, "repeats": done, "rubric_pass_rate_per_repeat": rates})
        return runs

    def one(i: int, k: int) -> tuple[int, int, dict]:
        _, rubric, answer = targets[i]
        result = run(build_judge_prompt(rubric, answer), expected_ids=[it.id for it in rubric.items])
        rep = {"items": result.items, "status": result.status}
        if result.status != "ok":
            rep["detail"] = result.detail
        return i, k, rep

    _write(out_json, snapshot())
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(one, i, k) for i in range(len(targets)) for k in range(repeat)]
        for fut in as_completed(futures):
            i, k, rep = fut.result()
            slots[i][k] = rep
            _write(out_json, snapshot())
    runs = snapshot()
    return {"runs": runs, "summary": summarize(runs)}


def _print_table(result: dict) -> None:
    s = result["summary"]
    print(f"runs judged: {s['n_runs']}")
    print("mean rubric pass rate per repeat: " + ", ".join("n/a" if v is None else f"{v:.3f}" for v in s["mean_rubric_pass_rate_per_repeat"]))
    if "item_agreement" in s:
        print(f"item-level agreement between repeats: {s['item_agreement']:.3f}")
    print(f"{'item':42s} {'pass':>6s} {'agree':>6s}")
    agree = s.get("per_item_agreement", {})
    for item_id, rate in s["per_item_pass_rate"].items():
        a = agree.get(item_id)
        print(f"{item_id:42s} {rate:6.2f} {'' if a is None else format(a, '6.2f'):>6s}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("out_json", type=Path)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)
    result = rejudge(args.runs_dir, args.out_json, args.repeat, args.workers, args.limit)
    _print_table(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
