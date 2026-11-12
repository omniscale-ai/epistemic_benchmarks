"""Parse agent answer.md files and score entity detection per pair."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from abductbench.config import pair_id_of

Status = Literal["ok", "missing", "no_entity_line", "duplicate_entity_line", "missing_sections"]

SECTION_KEYS = ("law", "limits", "explanation")

_ENTITY_RE = re.compile(r"^\s*ENTITY:\s*(yes|no)\s*$", re.IGNORECASE)
_HEADING_RE = re.compile(r"^ {0,3}(#{1,4})\s+(.*?)\s*$")


@dataclass
class ParsedAnswer:
    status: Status
    entity: bool | None
    sections: dict[str, str] = field(default_factory=dict)


def _heading_key(text: str) -> str:
    """Normalise a heading's text: strip closing hashes, trailing colon, case and spaces."""
    text = re.sub(r"\s+#+$", "", text).strip()
    return text.rstrip(":").strip().lower()


def parse_answer(path: Path) -> ParsedAnswer:
    try:
        raw = path.read_bytes()
    except OSError:
        return ParsedAnswer(status="missing", entity=None, sections={})

    lines = raw.decode("utf-8", errors="replace").splitlines()
    entity_idx = [i for i, line in enumerate(lines) if _ENTITY_RE.match(line)]

    # Every heading, of any level, bounds the section that precedes the next one.
    headings: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            headings.append((i, _heading_key(m.group(2))))

    sections: dict[str, str] = {}
    for pos, (start, key) in enumerate(headings):
        if key not in SECTION_KEYS or key in sections:
            continue
        end = headings[pos + 1][0] if pos + 1 < len(headings) else len(lines)
        body_lines = [
            lines[j] for j in range(start + 1, end) if not _ENTITY_RE.match(lines[j])
        ]
        sections[key] = "\n".join(body_lines).strip()

    if not entity_idx:
        return ParsedAnswer(status="no_entity_line", entity=None, sections=sections)
    if len(entity_idx) > 1:
        return ParsedAnswer(status="duplicate_entity_line", entity=None, sections=sections)

    entity = _ENTITY_RE.match(lines[entity_idx[0]]).group(1).lower() == "yes"
    if any(not sections.get(key) for key in SECTION_KEYS):
        return ParsedAnswer(status="missing_sections", entity=entity, sections=sections)
    return ParsedAnswer(status="ok", entity=entity, sections=sections)


def pair_entity_score(
    answers: dict[str, ParsedAnswer], entity_truth: dict[str, bool]
) -> dict[str, bool]:
    """Map pair_id -> True iff every member variant parsed ok with the correct entity value.

    The members of each pair are defined by the keys of ``entity_truth``; a member
    absent from ``answers`` makes its pair False.
    """
    members: dict[str, list[str]] = {}
    for variant_id in entity_truth:
        members.setdefault(pair_id_of(variant_id), []).append(variant_id)

    def correct(variant_id: str) -> bool:
        answer = answers.get(variant_id)
        return (
            answer is not None
            and answer.status == "ok"
            and answer.entity == entity_truth[variant_id]
        )

    return {pair: all(correct(v) for v in ids) for pair, ids in members.items()}
