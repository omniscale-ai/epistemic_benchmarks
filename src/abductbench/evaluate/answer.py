"""Parse agent answer.md files and score entity detection per pair."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from abductbench.config import pair_id_of

Status = Literal["ok", "missing", "no_entity_line", "duplicate_entity_line", "missing_sections"]

SECTION_KEYS = ("law", "limits", "explanation")

# ENTITY line, optionally wrapped in one matching pair of ** or backticks, optional
# trailing period. Group 2 is yes/no. Examples: "ENTITY: yes", "**ENTITY: no**",
# "`ENTITY: no`", "ENTITY: yes.". Only applied to lines outside fenced code blocks.
_ENTITY_RE = re.compile(r"^\s*(\*\*|`)?\s*ENTITY:\s*(yes|no)\s*\.?\s*\1?\s*$", re.IGNORECASE)
# ATX heading, levels 1-4.
_ATX_RE = re.compile(r"^ {0,3}(#{1,4})\s+(.*?)\s*$")
# A line that is only bold text, e.g. "**Law**" or "**Law:**". Counts as a heading only
# when its text is a section key.
_BOLD_LINE_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
# Opening or closing code fence: three or more backticks or tildes.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


@dataclass
class ParsedAnswer:
    status: Status
    entity: bool | None
    sections: dict[str, str] = field(default_factory=dict)


def _entity_value(line: str) -> bool | None:
    """Return True/False for an ENTITY line, or None if the line is not one."""
    m = _ENTITY_RE.match(line)
    if m is None:
        return None
    return m.group(2).lower() == "yes"


def _fence_flags(lines: list[str]) -> list[bool]:
    """Mark each line that is a fence delimiter or lies inside a fenced code block.

    A fence closes only on a line of the same character with at least the same length
    and nothing else on the line. An unclosed fence runs to the end of the file.
    """
    flags: list[bool] = []
    open_marker: str | None = None
    for line in lines:
        fence = _FENCE_RE.match(line)
        if open_marker is None:
            if fence:
                open_marker = fence.group(1)
                flags.append(True)
            else:
                flags.append(False)
            continue
        flags.append(True)
        if (
            fence
            and fence.group(1)[0] == open_marker[0]
            and len(fence.group(1)) >= len(open_marker)
            and line.strip() == fence.group(1)
        ):
            open_marker = None
    return flags


def _heading_key(text: str) -> str:
    """Normalise heading text for matching against SECTION_KEYS.

    Removes closing hashes, bold markers, a leading numbering prefix ("1." or "2)"),
    a trailing colon, surrounding spaces, and case.
    """
    text = re.sub(r"\s+#+$", "", text).replace("**", "").strip()
    text = re.sub(r"^\d+[.)]\s+", "", text)
    return text.rstrip(":").strip().lower()


def parse_answer(path: Path) -> ParsedAnswer:
    try:
        raw = path.read_bytes()
    except OSError:
        return ParsedAnswer(status="missing", entity=None, sections={})

    lines = raw.decode("utf-8", errors="replace").splitlines()
    fenced = _fence_flags(lines)
    entity_idx = [i for i, line in enumerate(lines) if not fenced[i] and _entity_value(line) is not None]

    # Headings are found outside fences only. ATX headings of any level bound a section.
    # Bold-only lines bound a section only when they name a section.
    headings: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        atx = _ATX_RE.match(line)
        if atx:
            headings.append((i, _heading_key(atx.group(2))))
            continue
        bold = _BOLD_LINE_RE.match(line)
        if bold:
            key = _heading_key(bold.group(1))
            if key in SECTION_KEYS:
                headings.append((i, key))

    # Duplicate section headings: the first occurrence with a non-empty body is kept.
    # An empty earlier occurrence is replaced by a later non-empty one.
    sections: dict[str, str] = {}
    for pos, (start, key) in enumerate(headings):
        if key not in SECTION_KEYS or sections.get(key):
            continue
        end = headings[pos + 1][0] if pos + 1 < len(headings) else len(lines)
        # Body keeps fenced lines (even ENTITY-looking ones); it drops unfenced ENTITY lines.
        body_lines = [
            lines[j]
            for j in range(start + 1, end)
            if fenced[j] or _entity_value(lines[j]) is None
        ]
        sections[key] = "\n".join(body_lines).strip()

    if not entity_idx:
        return ParsedAnswer(status="no_entity_line", entity=None, sections=sections)
    if len(entity_idx) > 1:
        return ParsedAnswer(status="duplicate_entity_line", entity=None, sections=sections)

    entity = _entity_value(lines[entity_idx[0]])
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
