from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np


class Stage(str, Enum):
    HISTORICAL = "a"
    OBFUSCATED = "b"
    COUNTERFACTUAL = "c"
    SYNTHETIC = "d"


class Family(str, Enum):
    BETA = "beta"
    ORBIT = "orbit"


class Truth(str, Enum):
    ENTITY = "entity"
    NO_ENTITY = "no_entity"


@dataclass(frozen=True)
class VariantConfig:
    family: Family
    truth: Truth
    stage: Stage
    seed: int
    mode: int  # 1 or 2
    n_points: int = 2000
    noise: float = 0.05

    @property
    def variant_id(self) -> str:
        return f"{self.family.value}-{self.truth.value}-{self.stage.value}-s{self.seed}-m{self.mode}"

    @property
    def pair_id(self) -> str:
        return f"{self.family.value}-{self.stage.value}-s{self.seed}-m{self.mode}"


def all_variants(seeds=range(5), modes=(1, 2)) -> list[VariantConfig]:
    return [
        VariantConfig(family=f, truth=t, stage=s, seed=seed, mode=m)
        for f in Family
        for t in Truth
        for s in Stage
        for seed in seeds
        for m in modes
    ]


_VARIANT_ID_RE = re.compile(r"(beta|orbit)-(entity|no_entity)-([abcd])-s(\d+)-m([12])")


def cfg_from_variant_id(variant_id: str) -> VariantConfig:
    """Inverse of ``VariantConfig.variant_id``: 'beta-no_entity-c-s3-m2' -> VariantConfig.

    Uses the default noise and n_points. Raises ValueError for any other string.
    """
    m = _VARIANT_ID_RE.fullmatch(variant_id) if isinstance(variant_id, str) else None
    if m is None:
        raise ValueError(f"invalid variant id: {variant_id!r}")
    family, truth, stage, seed, mode = m.groups()
    return VariantConfig(
        family=Family(family),
        truth=Truth(truth),
        stage=Stage(stage),
        seed=int(seed),
        mode=int(mode),
    )


def pair_id_of(variant_id: str) -> str:
    """Drop the truth segment: 'beta-entity-a-s0-m1' -> 'beta-a-s0-m1'."""
    family, _truth, *rest = variant_id.split("-")
    return "-".join([family, *rest])


@dataclass
class EvalPoints:
    in_range: np.ndarray
    extrapolation: np.ndarray


@dataclass
class TaskBundle:
    public_files: dict[str, str | bytes]
    truth_law: Callable[[np.ndarray], np.ndarray]
    eval_points: Callable[[], EvalPoints]
    true_domain: dict[str, tuple[float, float]]
    entity: bool
    rubric_id: str
    discriminating_queries: frozenset[str]
    oracle_family: Callable | None = None
