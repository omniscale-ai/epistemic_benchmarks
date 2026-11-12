from __future__ import annotations

import importlib.util

from abductbench.config import Family, TaskBundle, VariantConfig
from abductbench.tasks import beta as _beta
from abductbench.tasks.beta import build_beta

# Mode-2 query types per family. Every query costs exactly one simulation.
QUERY_TYPES: dict[Family, tuple[str, ...]] = {
    Family.BETA: ("events", "recoil_correlation", "target_thickness_scan"),
    Family.ORBIT: ("residuals", "other_body_residuals", "search_region"),
}

SIMULATION_COST = 1.0  # ledger charge for one successful measure call


def build_task(cfg: VariantConfig) -> TaskBundle:
    if cfg.family is Family.BETA:
        return build_beta(cfg)
    if cfg.family is Family.ORBIT:
        if importlib.util.find_spec("abductbench.tasks.orbit") is None:
            raise NotImplementedError("orbit task generator is not implemented yet")
        from abductbench.tasks.orbit import build_orbit

        return build_orbit(cfg)
    raise ValueError(f"unknown family: {cfg.family}")


def check_query(cfg: VariantConfig, query_type: str, args: dict) -> float:
    """Validate the query type and per-call size caps; return its cost (always one simulation).

    Raises ValueError for unknown types or invalid/oversized arguments, before anything is charged.
    """
    types = QUERY_TYPES.get(cfg.family, ())
    if not isinstance(query_type, str) or query_type not in types:
        raise ValueError(f"unknown query type {query_type!r}; allowed types: {', '.join(sorted(types))}")
    if cfg.family is Family.BETA:
        _beta.row_count(query_type, args)
    else:
        from abductbench.tasks import orbit as _orbit

        _orbit.row_count(cfg, query_type, args)
    return SIMULATION_COST


def query_help(cfg: VariantConfig) -> str:
    """Task.md lines describing the query types of this variant's family."""
    if cfg.family is Family.BETA:
        return _beta.query_help(cfg)
    from abductbench.tasks import orbit as _orbit

    return _orbit.query_help(cfg)


def answer_query(cfg: VariantConfig, query_type: str, args: dict | None = None) -> dict:
    """Generate the JSON-serialisable answer to one mode-2 query (no cost is charged here)."""
    check_query(cfg, query_type, dict(args or {}))  # validates the type and size caps
    args = dict(args or {})
    if cfg.family is Family.BETA:
        return _beta.query(cfg, query_type, args)
    from abductbench.tasks import orbit as _orbit

    return _orbit.query(cfg, query_type, args)


__all__ = ["build_task", "build_beta", "answer_query", "check_query", "query_help", "QUERY_TYPES", "SIMULATION_COST"]
