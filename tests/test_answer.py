from pathlib import Path

from abductbench.config import Family, Stage, Truth, VariantConfig
from abductbench.evaluate.answer import ParsedAnswer, pair_entity_score, parse_answer

GOOD_BODY = """## Law
F = m a

## Limits
Valid for v << c.

## Explanation
Newtonian mechanics fits the data.
"""


def write(tmp_path: Path, text: str | bytes, name: str = "answer.md") -> Path:
    path = tmp_path / name
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def ok_answer(entity: bool) -> ParsedAnswer:
    return ParsedAnswer(
        status="ok",
        entity=entity,
        sections={"law": "x", "limits": "y", "explanation": "z"},
    )


def test_valid_answer_parses(tmp_path):
    path = write(tmp_path, "ENTITY: yes\n\n" + GOOD_BODY)
    parsed = parse_answer(path)
    assert parsed.status == "ok"
    assert parsed.entity is True
    assert set(parsed.sections) == {"law", "limits", "explanation"}
    assert parsed.sections["law"] == "F = m a"
    assert parsed.sections["limits"] == "Valid for v << c."
    assert parsed.sections["explanation"] == "Newtonian mechanics fits the data."


def test_entity_no_parses_false(tmp_path):
    parsed = parse_answer(write(tmp_path, "ENTITY: no\n" + GOOD_BODY))
    assert parsed.status == "ok"
    assert parsed.entity is False


def test_missing_entity_line(tmp_path):
    parsed = parse_answer(write(tmp_path, GOOD_BODY))
    assert parsed.status == "no_entity_line"
    assert parsed.entity is None
    # sections found are still filled in for inspection
    assert set(parsed.sections) == {"law", "limits", "explanation"}


def test_duplicate_entity_line(tmp_path):
    parsed = parse_answer(write(tmp_path, "ENTITY: yes\nENTITY: no\n" + GOOD_BODY))
    assert parsed.status == "duplicate_entity_line"
    assert parsed.entity is None


def test_missing_sections(tmp_path):
    body = "ENTITY: yes\n## Law\nF = m a\n## Explanation\nfine\n"
    parsed = parse_answer(write(tmp_path, body))
    assert parsed.status == "missing_sections"
    assert parsed.entity is True
    assert "limits" not in parsed.sections
    assert parsed.sections["law"] == "F = m a"


def test_missing_file(tmp_path):
    parsed = parse_answer(tmp_path / "does_not_exist.md")
    assert parsed.status == "missing"
    assert parsed.entity is None
    assert parsed.sections == {}


def test_entity_line_inside_section_does_not_break_extraction(tmp_path):
    body = (
        "## Law\nF = m a\nENTITY: yes\n"
        "## Limits\nv << c\n"
        "## Explanation\nok\n"
    )
    parsed = parse_answer(write(tmp_path, body))
    assert parsed.status == "ok"
    assert parsed.entity is True
    assert parsed.sections["law"] == "F = m a"
    assert "ENTITY" not in parsed.sections["law"]


def test_section_containing_only_entity_line_is_empty(tmp_path):
    # the single ENTITY line sits inside Law, so Law's body is empty once it is removed
    body = "## Law\nENTITY: yes\n## Limits\nv\n## Explanation\nok\n"
    parsed = parse_answer(write(tmp_path, body))
    assert parsed.status == "missing_sections"
    assert parsed.entity is True
    assert parsed.sections["law"] == ""


def test_empty_section_is_missing_sections(tmp_path):
    body = "ENTITY: yes\n## Law\n\n   \n## Limits\nv\n## Explanation\nok\n"
    parsed = parse_answer(write(tmp_path, body))
    assert parsed.status == "missing_sections"
    assert parsed.entity is True


def test_heading_levels_case_and_colon_variants(tmp_path):
    body = (
        "ENTITY: YES\n"
        "# law:\nF = m a\n"
        "### LIMITS\nv << c\n"
        "#### Explanation :\nok\n"
    )
    parsed = parse_answer(write(tmp_path, body))
    assert parsed.status == "ok"
    assert parsed.entity is True
    assert parsed.sections["law"] == "F = m a"
    assert parsed.sections["limits"] == "v << c"
    assert parsed.sections["explanation"] == "ok"


def test_section_ends_at_next_heading_of_any_level(tmp_path):
    body = (
        "ENTITY: no\n"
        "## Law\nF = m a\n"
        "## Notes\nunrelated stuff\n"
        "## Limits\nv\n"
        "## Explanation\nok\n"
    )
    parsed = parse_answer(write(tmp_path, body))
    assert parsed.status == "ok"
    assert parsed.sections["law"] == "F = m a"
    assert "unrelated" not in parsed.sections["law"]


def test_entity_line_tolerates_whitespace_and_case(tmp_path):
    parsed = parse_answer(write(tmp_path, "  entity:   No  \n" + GOOD_BODY))
    assert parsed.status == "ok"
    assert parsed.entity is False


def test_non_utf8_bytes_do_not_raise(tmp_path):
    raw = b"ENTITY: yes\n## Law\nF = \xff\xfe m a\n## Limits\n\x80v\n## Explanation\nok\n"
    parsed = parse_answer(write(tmp_path, raw))
    assert parsed.status == "ok"
    assert parsed.entity is True
    assert "F =" in parsed.sections["law"]


def test_constant_yes_scores_zero_on_pairs():
    truth = {}
    answers = {}
    for seed in range(3):
        for stage in Stage:
            for mode in (1, 2):
                for t in Truth:
                    cfg = VariantConfig(Family.BETA, t, stage, seed, mode)
                    truth[cfg.variant_id] = t is Truth.ENTITY
                    answers[cfg.variant_id] = ok_answer(True)
    scores = pair_entity_score(answers, truth)
    assert len(scores) == 3 * 4 * 2
    assert all(v is False for v in scores.values())


def test_correct_answers_score_true_on_pairs():
    truth = {"beta-entity-a-s0-m1": True, "beta-no_entity-a-s0-m1": False}
    answers = {
        "beta-entity-a-s0-m1": ok_answer(True),
        "beta-no_entity-a-s0-m1": ok_answer(False),
    }
    assert pair_entity_score(answers, truth) == {"beta-a-s0-m1": True}


def test_pair_requires_both_members_present():
    truth = {"beta-entity-a-s0-m1": True, "beta-no_entity-a-s0-m1": False}
    answers = {"beta-entity-a-s0-m1": ok_answer(True)}
    assert pair_entity_score(answers, truth) == {"beta-a-s0-m1": False}


def test_pair_false_when_member_not_ok():
    truth = {"beta-entity-a-s0-m1": True, "beta-no_entity-a-s0-m1": False}
    answers = {
        "beta-entity-a-s0-m1": ok_answer(True),
        "beta-no_entity-a-s0-m1": ParsedAnswer(status="no_entity_line", entity=None, sections={}),
    }
    assert pair_entity_score(answers, truth) == {"beta-a-s0-m1": False}


def test_single_member_pair_scored_on_that_member():
    truth = {"beta-entity-a-s0-m1": True}
    assert pair_entity_score({"beta-entity-a-s0-m1": ok_answer(True)}, truth) == {
        "beta-a-s0-m1": True
    }
    assert pair_entity_score({"beta-entity-a-s0-m1": ok_answer(False)}, truth) == {
        "beta-a-s0-m1": False
    }
