"""Per-variant rubrics: binary criteria for the explanation section, plus the truth summary.

Each rubric lives in ``rubrics/<rubric_id>.yaml`` at the repository root, outside any
agent workspace. The rubric holds only mechanism-level text; it never holds numeric
true constants.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# <repo>/src/abductbench/evaluate/rubric.py -> parents[3] is the repository root.
RUBRICS_DIR = Path(__file__).resolve().parents[3] / "rubrics"

_ID_RE = re.compile(r"[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class RubricItem:
    id: str
    criterion: str
    applies_when: str


@dataclass(frozen=True)
class Rubric:
    rubric_id: str
    items: list[RubricItem] = field(default_factory=list)
    truth_summary: str = ""


def _require_str(mapping: dict, key: str, where: str) -> str:
    if key not in mapping:
        raise ValueError(f"{where}: missing key {key!r}")
    value = mapping[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: {key!r} must be a non-empty string")
    return value


def _parse(rubric_id: str, data: object, where: str) -> Rubric:
    if not isinstance(data, dict):
        raise ValueError(f"{where}: top level must be a mapping")
    truth_summary = _require_str(data, "truth_summary", where)
    if "items" not in data:
        raise ValueError(f"{where}: missing key 'items'")
    raw_items = data["items"]
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError(f"{where}: 'items' must be a non-empty list")

    items: list[RubricItem] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        at = f"{where}: items[{index}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{at} must be a mapping")
        item_id = _require_str(raw, "id", at)
        if item_id in seen:
            raise ValueError(f"{at}: duplicate item id {item_id!r}")
        seen.add(item_id)
        items.append(
            RubricItem(
                id=item_id,
                criterion=_require_str(raw, "criterion", at),
                applies_when=_require_str(raw, "applies_when", at),
            )
        )
    return Rubric(rubric_id=rubric_id, items=items, truth_summary=truth_summary.strip())


def load_rubric(rubric_id: str, rubrics_dir: Path | None = None) -> Rubric:
    """Load and validate ``<rubrics_dir>/<rubric_id>.yaml``.

    Raises FileNotFoundError for an unknown (or malformed) id and ValueError when the
    YAML does not match the schema.
    """
    directory = RUBRICS_DIR if rubrics_dir is None else Path(rubrics_dir)
    path = directory / f"{rubric_id}.yaml"
    if not _ID_RE.fullmatch(rubric_id) or not path.is_file():
        raise FileNotFoundError(f"no rubric for id {rubric_id!r} in {directory}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _parse(rubric_id, data, str(path))
