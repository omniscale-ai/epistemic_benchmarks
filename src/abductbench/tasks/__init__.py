from __future__ import annotations

import importlib.util
import math

from abductbench.config import Family, TaskBundle, VariantConfig
from abductbench.tasks import beta as _beta
from abductbench.tasks.beta import build_beta

# Mode-2 query types and their costs, per family. Every key is a legal query_type.
QUERY_COSTS: dict[Family, dict[str, float]] = {
    Family.BETA: {"events": 1.0, "recoil_correlation": 5.0, "target_thickness_scan": 8.0},
    Family.ORBIT: {"residuals": 1.0, "other_body_residuals": 2.0, "search_region": 8.0},
}


ROWS_PER_PRICE_BLOCK = 50


def build_task(cfg: VariantConfig) -> TaskBundle:
    if cfg.family is Family.BETA:
        return build_beta(cfg)
    if cfg.family is Family.ORBIT:
        if importlib.util.find_spec("abductbench.tasks.orbit") is None:
            raise NotImplementedError("orbit task generator is not implemented yet")
        from abductbench.tasks.orbit import build_orbit

        return build_orbit(cfg)
    raise ValueError(f"unknown family: {cfg.family}")


def _base_cost(cfg: VariantConfig, query_type: str) -> float:
    costs = QUERY_COSTS.get(cfg.family, {})
    if not isinstance(query_type, str) or query_type not in costs:
        allowed = ", ".join(sorted(costs))
        raise ValueError(f"unknown query type {query_type!r}; allowed types: {allowed}")
    return costs[query_type]


def query_cost(cfg: VariantConfig, query_type: str, args: dict) -> float:
    """Price of one query with these arguments.

    Row-priced queries (events, residuals, other_body_residuals) cost the base
    amount for each block of ROWS_PER_PRICE_BLOCK rows, or part of a block. The
    other query types cost the base amount. Raises ValueError for unknown types
    or invalid arguments.
    """
    base = _base_cost(cfg, query_type)
    if cfg.family is Family.BETA:
        rows = _beta.row_count(query_type, args)
    else:
        from abductbench.tasks import orbit as _orbit

        rows = _orbit.row_count(cfg, query_type, args)
    if rows is None:
        return base
    return base * math.ceil(rows / ROWS_PER_PRICE_BLOCK)


def query_help(cfg: VariantConfig) -> str:
    """Task.md lines describing the query types of this variant's family."""
    if cfg.family is Family.BETA:
        return _beta.query_help(cfg)
    from abductbench.tasks import orbit as _orbit

    return _orbit.query_help(cfg)


def answer_query(cfg: VariantConfig, query_type: str, args: dict | None = None) -> dict:
    """Generate the JSON-serialisable answer to one mode-2 query (no cost is charged here)."""
    _base_cost(cfg, query_type)  # validates the type
    args = dict(args or {})
    if cfg.family is Family.BETA:
        return _beta.query(cfg, query_type, args)
    from abductbench.tasks import orbit as _orbit

    return _orbit.query(cfg, query_type, args)


__all__ = ["build_task", "build_beta", "answer_query", "query_cost", "query_help", "QUERY_COSTS", "ROWS_PER_PRICE_BLOCK"]
