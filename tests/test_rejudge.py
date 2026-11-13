"""scripts/rejudge.py with stub judges only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rejudge  # noqa: E402

from abductbench.evaluate.judge import JudgeResult  # noqa: E402
from abductbench.evaluate.rubric import load_rubric  # noqa: E402

ANSWER = "## Law\nSee law.py.\n\n## Limits\nnone\n\n## Explanation\nA hidden particle.\n\nENTITY: yes\n"
IDS = [i.id for i in load_rubric("beta-entity-a").items]


def _make_run(runs_dir: Path, variant_id: str, answer: str | None = ANSWER) -> None:
    d = runs_dir / variant_id
    d.mkdir(parents=True)
    ans = None
    if answer is not None:
        (d / "answer.md").write_text(answer)
        ans = str(d / "answer.md")
    (d / "record.json").write_text(json.dumps({
        "variant_id": variant_id, "workspace": str(d), "law_path": None, "answer_path": ans,
        "transcript_path": None, "returncode": 0, "timed_out": False, "helper_paths": [],
    }))


def _result(passes: dict[str, bool]) -> JudgeResult:
    items = {i: {"pass": passes.get(i, True), "quote": "q", "reason": "r"} for i in IDS}
    return JudgeResult(status="ok", items=items)


@pytest.fixture
def runs_dir(tmp_path):
    d = tmp_path / "runs"
    _make_run(d, "beta-entity-a-s0-m1")
    _make_run(d, "beta-entity-a-s1-m1")
    _make_run(d, "beta-entity-a-s2-m1", answer=None)  # no answer: skipped
    _make_run(d, "beta-entity-a-s3-m1", answer="garbage")  # unparsable: skipped
    return d


def test_counts_structure_and_agreement(runs_dir, tmp_path):
    calls = []

    def run(prompt, expected_ids=None):
        calls.append(prompt)
        # Alternate verdicts per call for one item so repeats disagree on it.
        n = len(calls)
        return _result({"discriminating_experiment": n % 2 == 0, "anomaly_resolved": False})

    out = tmp_path / "out.json"
    result = rejudge.rejudge(runs_dir, out, repeat=2, workers=1, run=run)
    assert len(calls) == 4  # 2 eligible runs x 2 repeats
    data = json.loads(out.read_text())
    assert [r["variant_id"] for r in data["runs"]] == ["beta-entity-a-s0-m1", "beta-entity-a-s1-m1"]
    for r in data["runs"]:
        assert len(r["repeats"]) == 2 and len(r["rubric_pass_rate_per_repeat"]) == 2
        assert r["repeats"][0]["status"] == "ok"
        assert r["repeats"][0]["items"]["anomaly_resolved"]["reason"] == "r"
    s = data["summary"]
    assert s["n_runs"] == 2
    assert s["per_item_pass_rate"]["anomaly_resolved"] == 0.0
    assert s["per_item_pass_rate"]["names_hidden_object"] == 1.0
    assert s["per_item_pass_rate"]["discriminating_experiment"] == 0.5
    # Each run's two repeats differ only on discriminating_experiment: 4 of 5 items agree.
    assert s["item_agreement"] == pytest.approx(0.8)
    assert s["per_item_agreement"]["discriminating_experiment"] == 0.0
    assert s["per_item_agreement"]["anomaly_resolved"] == 1.0
    assert len(s["mean_rubric_pass_rate_per_repeat"]) == 2
    assert result["summary"] == s


def test_single_repeat_has_no_agreement(runs_dir, tmp_path):
    out = tmp_path / "o.json"
    rejudge.rejudge(runs_dir, out, workers=2, run=lambda p, expected_ids=None: _result({}))
    s = json.loads(out.read_text())["summary"]
    assert "item_agreement" not in s
    assert s["mean_rubric_pass_rate_per_repeat"] == [1.0]


def test_limit(runs_dir, tmp_path):
    out = tmp_path / "o.json"
    rejudge.rejudge(runs_dir, out, limit=1, run=lambda p, expected_ids=None: _result({}))
    assert len(json.loads(out.read_text())["runs"]) == 1


def test_judge_error_recorded_and_excluded(runs_dir, tmp_path):
    out = tmp_path / "o.json"
    err = JudgeResult(status="judge_error", items={}, detail="bad")
    rejudge.rejudge(runs_dir, out, run=lambda p, expected_ids=None: err)
    data = json.loads(out.read_text())
    assert data["runs"][0]["repeats"][0]["status"] == "judge_error"
    assert data["runs"][0]["rubric_pass_rate_per_repeat"] == [None]
    assert data["summary"]["mean_rubric_pass_rate_per_repeat"] == []


def test_partial_results_survive_crash(runs_dir, tmp_path):
    out = tmp_path / "o.json"
    n = {"c": 0}

    def run(prompt, expected_ids=None):
        n["c"] += 1
        if n["c"] == 2:
            raise KeyboardInterrupt("crash")
        return _result({})

    with pytest.raises(BaseException):
        rejudge.rejudge(runs_dir, out, workers=1, run=run)
    data = json.loads(out.read_text())  # valid JSON written after the first run
    assert data["runs"][0]["repeats"][0]["status"] == "ok"
    assert data["runs"][1]["repeats"] == []
