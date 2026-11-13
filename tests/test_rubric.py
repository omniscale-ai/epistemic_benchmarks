from __future__ import annotations

import inspect
import json
import re

import pytest

from abductbench.config import Family, Stage, Truth, VariantConfig, all_variants
from abductbench.evaluate.answer import ParsedAnswer, parse_answer
from abductbench.evaluate.judge import (
    JUDGE_MODEL,
    JudgeResult,
    _extract_json_object,
    _judge_command,
    build_judge_prompt,
    run_judge,
)
from abductbench.evaluate.rubric import RUBRICS_DIR, Rubric, RubricItem, load_rubric
from abductbench.tasks import build_task

EXPECTED_IDS = {
    f"{family}-{truth}-{stage}"
    for family in ("beta", "orbit")
    for truth in ("entity", "no_entity")
    for stage in ("a", "b", "c", "d")
}

ENTITY_ITEMS = {
    "names_hidden_object",
    "anomaly_resolved",
    "alternatives_rejected_with_reason",
    "discriminating_experiment",
    "cause_stated_plainly",
}
NO_ENTITY_ITEMS = {
    "no_entity_posited",
    "real_cause_identified",
    "alternatives_rejected_with_reason",
    "discriminating_experiment",
    "cause_stated_plainly",
}


def _answer(**sections: str) -> ParsedAnswer:
    return ParsedAnswer(status="ok", entity=True, sections=dict(sections))


def _reply(item_ids, passes=None) -> str:
    passes = passes or {}
    items = {
        i: {"pass": passes.get(i, True), "quote": "quoted text", "reason": "because"} for i in item_ids
    }
    return json.dumps({"items": items})


class _Stub:
    """Runner that returns queued replies (or raises queued exceptions) and counts calls."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


# ---- prompt construction -------------------------------------------------


def test_prompt_excludes_law_py(tmp_path):
    sentinel = "SENTINEL_LAW_PY_7f3a"
    (tmp_path / "law.py").write_text(f"# {sentinel}\ndef law(x):\n    return x\n")
    (tmp_path / "answer.md").write_text(
        "## Law\nSee law.py for the formula.\n\n## Limits\nnone\n\n## Explanation\nA hidden particle.\n\n"
        "ENTITY: yes\n"
    )
    answer = parse_answer(tmp_path / "answer.md")
    assert answer.status == "ok"

    prompt = build_judge_prompt(load_rubric("beta-entity-a"), answer)

    assert sentinel not in prompt
    assert "A hidden particle." in prompt


def test_build_judge_prompt_takes_no_law_source():
    params = list(inspect.signature(build_judge_prompt).parameters)
    assert params == ["rubric", "answer"]


def test_prompt_contains_items_truth_and_sections():
    rubric = load_rubric("orbit-no_entity-c")
    prompt = build_judge_prompt(
        rubric, _answer(law="LAW_TEXT", limits="LIMITS_TEXT", explanation="EXPL_TEXT")
    )
    for item in rubric.items:
        assert item.id in prompt
        assert item.criterion in prompt
    assert rubric.truth_summary in prompt
    assert "LAW_TEXT" in prompt and "LIMITS_TEXT" in prompt and "EXPL_TEXT" in prompt


def test_prompt_renders_missing_sections_without_crashing():
    partial = ParsedAnswer(status="missing_sections", entity=None, sections={"law": "only law"})
    prompt = build_judge_prompt(load_rubric("beta-entity-a"), partial)
    assert "only law" in prompt
    assert prompt.count("(missing)") >= 2


# ---- rubric loading and content -------------------------------------------


def test_all_rubric_ids_load():
    # rubric_id depends only on family, truth and stage, so one seed and one mode
    # cover every id while keeping the build fast.
    configs = all_variants(seeds=range(1), modes=(1,))
    found = {build_task(cfg).rubric_id for cfg in configs}
    assert found == EXPECTED_IDS
    for rubric_id in found:
        rubric = load_rubric(rubric_id)
        assert rubric.items
        assert rubric.truth_summary.strip()


def test_all_sixteen_rubric_files_exist_on_disk():
    on_disk = {p.stem for p in RUBRICS_DIR.glob("*.yaml")}
    assert on_disk == EXPECTED_IDS


def test_load_rubric_returns_typed_items():
    rubric = load_rubric("beta-entity-a")
    assert isinstance(rubric, Rubric)
    assert all(isinstance(item, RubricItem) for item in rubric.items)
    assert {item.id for item in rubric.items} == ENTITY_ITEMS


def test_unknown_rubric_id_raises_file_not_found():
    with pytest.raises(FileNotFoundError, match="no-such-rubric"):
        load_rubric("no-such-rubric")


def test_rubric_schema_missing_keys_is_value_error(tmp_path):
    (tmp_path / "beta-entity-a.yaml").write_text(
        "truth_summary: something\nitems:\n  - id: names_hidden_object\n    criterion: x\n"
    )
    with pytest.raises(ValueError, match="applies_when"):
        load_rubric("beta-entity-a", rubrics_dir=tmp_path)


def test_rubric_missing_truth_summary_is_value_error(tmp_path):
    (tmp_path / "beta-entity-a.yaml").write_text(
        "items:\n  - id: names_hidden_object\n    criterion: x\n    applies_when: always\n"
    )
    with pytest.raises(ValueError, match="truth_summary"):
        load_rubric("beta-entity-a", rubrics_dir=tmp_path)


def test_no_entity_rubrics_include_no_entity_posited_and_entity_ones_dont():
    for rubric_id in EXPECTED_IDS:
        ids = {item.id for item in load_rubric(rubric_id).items}
        if "no_entity" in rubric_id:
            assert "no_entity_posited" in ids, rubric_id
            assert "names_hidden_object" not in ids, rubric_id
        else:
            assert "no_entity_posited" not in ids, rubric_id
            assert "names_hidden_object" in ids, rubric_id


def test_rubric_files_have_no_forbidden_numeric_constants():
    # Truth summaries and criteria describe mechanism types only; no numeric constants.
    for rubric_id in EXPECTED_IDS:
        rubric = load_rubric(rubric_id)
        texts = [rubric.truth_summary] + [item.criterion for item in rubric.items]
        for text in texts:
            assert not re.search(r"\d", text.replace("T0", "")), (rubric_id, text)  # "T0" names the baseline stage


# ---- judge parsing and retries --------------------------------------------


def test_valid_json_parsed():
    ids = sorted(ENTITY_ITEMS)
    reply = "Sure, here is the grading.\n```json\n" + _reply(ids) + "\n```\nHope it helps."
    stub = _Stub(reply)
    result = run_judge("prompt", runner=stub, expected_ids=ids)
    assert isinstance(result, JudgeResult)
    assert result.status == "ok"
    assert set(result.items) == set(ids)
    assert result.items["names_hidden_object"] == {"pass": True, "quote": "quoted text", "reason": "because"}
    assert stub.calls == 1


def test_malformed_json_retried_then_judge_error():
    stub = _Stub("this is not json at all", "{still: broken")
    result = run_judge("prompt", runner=stub, retries=1, expected_ids=["a"])
    assert stub.calls == 2
    assert result.status == "judge_error"
    assert result.items == {}
    assert result.detail


def test_partial_items_is_judge_error():
    stub = _Stub(_reply(["a"]))
    result = run_judge("prompt", runner=stub, retries=1, expected_ids=["a", "b"])
    assert result.status == "judge_error"
    assert result.items == {}
    assert stub.calls == 2


def test_extra_items_is_judge_error():
    stub = _Stub(_reply(["a", "b", "c"]))
    result = run_judge("prompt", runner=stub, retries=1, expected_ids=["a", "b"])
    assert result.status == "judge_error"
    assert result.items == {}
    assert stub.calls == 2


def test_non_bool_pass_is_error():
    reply = json.dumps({"items": {"a": {"pass": "yes", "quote": "", "reason": "r"}}})
    stub = _Stub(reply)
    result = run_judge("prompt", runner=stub, retries=0, expected_ids=["a"])
    assert result.status == "judge_error"
    assert result.items == {}


def test_runner_exception_then_success():
    stub = _Stub(RuntimeError("cli crashed"), _reply(["a"]))
    result = run_judge("prompt", runner=stub, retries=1, expected_ids=["a"])
    assert stub.calls == 2
    assert result.status == "ok"
    assert set(result.items) == {"a"}


def test_runner_exception_every_time_is_judge_error():
    stub = _Stub(RuntimeError("timeout"))
    result = run_judge("prompt", runner=stub, retries=1, expected_ids=["a"])
    assert stub.calls == 2
    assert result.status == "judge_error"
    assert "timeout" in result.detail


def test_expected_ids_none_skips_id_check():
    stub = _Stub(_reply(["whatever"]))
    result = run_judge("prompt", runner=stub, retries=0)
    assert result.status == "ok"
    assert set(result.items) == {"whatever"}


# ---- default runner command line (never executes the CLI) -----------------


def test_judge_command_uses_print_model_and_no_web_tools():
    cmd = _judge_command("PROMPT TEXT")
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert JUDGE_MODEL in cmd
    assert cmd[cmd.index("--model") + 1] == JUDGE_MODEL
    assert cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--setting-sources") + 1] == ""
    assert cmd.index("--setting-sources") < cmd.index("--tools")  # variadic --tools goes last
    joined = " ".join(cmd)
    assert "WebFetch" not in joined and "WebSearch" not in joined
    assert "PROMPT TEXT" in cmd


@pytest.mark.parametrize("stage", ["a", "b", "c", "d"])
@pytest.mark.parametrize("family", ["beta", "orbit"])
def test_no_entity_alternatives_criterion_never_offers_the_cause(family, stage):
    rubric = load_rubric(f"{family}-no_entity-{stage}")
    item = next(i for i in rubric.items if i.id == "alternatives_rejected_with_reason")
    assert "NOT the real cause" in item.criterion
    low = item.criterion.lower()
    assert "detector artifact" not in low and "modified force law" not in low and "force-law modification" not in low


# ---- new item ids, reasons, json extraction --------------------------------


def test_every_rubric_has_exactly_the_expected_ids_in_order():
    for rubric_id in EXPECTED_IDS:
        ids = [item.id for item in load_rubric(rubric_id).items]
        if "no_entity" in rubric_id:
            assert ids == ["no_entity_posited", "real_cause_identified", "alternatives_rejected_with_reason",
                           "discriminating_experiment", "cause_stated_plainly"], rubric_id
        else:
            assert ids == ["names_hidden_object", "anomaly_resolved", "alternatives_rejected_with_reason",
                           "discriminating_experiment", "cause_stated_plainly"], rubric_id


def test_no_decimal_numbers_in_criteria():
    for rubric_id in EXPECTED_IDS:
        for item in load_rubric(rubric_id).items:
            assert not re.search(r"\d+\.\d+", item.criterion), (rubric_id, item.id)


def test_alternatives_criterion_wording():
    for rubric_id in EXPECTED_IDS:
        item = next(i for i in load_rubric(rubric_id).items if i.id == "alternatives_rejected_with_reason")
        assert "at least two alternative explanations" in item.criterion
        assert "stated reason for rejection based on the data" in item.criterion


def test_prompt_asks_for_reason():
    prompt = build_judge_prompt(load_rubric("beta-entity-a"), _answer(explanation="x"))
    assert '"reason"' in prompt
    assert "anywhere in the candidate text" in prompt


def test_missing_reason_key_retried_then_judge_error():
    reply = json.dumps({"items": {"a": {"pass": True, "quote": "q"}}})
    stub = _Stub(reply)
    result = run_judge("prompt", runner=stub, retries=1, expected_ids=["a"])
    assert stub.calls == 2
    assert result.status == "judge_error"
    assert result.items == {}


def test_failed_item_with_empty_reason_is_invalid():
    reply = json.dumps({"items": {"a": {"pass": False, "quote": "", "reason": "  "}}})
    stub = _Stub(reply)
    result = run_judge("prompt", runner=stub, retries=1, expected_ids=["a"])
    assert stub.calls == 2
    assert result.status == "judge_error"


def test_passed_item_with_empty_reason_is_ok():
    reply = json.dumps({"items": {"a": {"pass": True, "quote": "q", "reason": ""}}})
    result = run_judge("prompt", runner=_Stub(reply), retries=0, expected_ids=["a"])
    assert result.status == "ok"
    assert result.items["a"]["reason"] == ""


def test_failed_item_with_reason_keeps_reason():
    reply = json.dumps({"items": {"a": {"pass": False, "quote": "", "reason": "never mentioned"}}})
    result = run_judge("prompt", runner=_Stub(reply), retries=0, expected_ids=["a"])
    assert result.status == "ok"
    assert result.items["a"] == {"pass": False, "quote": "", "reason": "never mentioned"}


def test_extract_json_object_prefers_dict_with_items():
    text = 'noise {"foo": 1} more {"items": {"a": 1}} tail {"items": {"b": 2}}'
    assert _extract_json_object(text) == {"items": {"a": 1}}


def test_extract_json_object_falls_back_to_first_dict():
    assert _extract_json_object('x {"foo": 1} {"bar": 2}') == {"foo": 1}
