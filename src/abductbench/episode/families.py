"""Family adapters: what the protocol needs to know about a world family (decay or orbit)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Family:
    name: str
    world: Callable  # cfg -> world object (public_metadata, observe_initial, observe, truth_sample)
    validate_measurement: Callable  # dict -> normalised dict (ValueError if invalid)
    model_query: Callable  # measurement -> query passed to the models
    n_forecast: int
    validation_queries: tuple
    validate_sample: Callable  # (query, sample, n, meta) -> checked sample (ModelError)
    validate_mechanism: Callable  # (mechanism, menu, meta) -> normalised (ModelError)


def _decay() -> Family:
    from abductbench.episode import modelrun as mr
    from abductbench.episode.world import World, validate_measurement

    return Family(
        name="decay", world=World, validate_measurement=validate_measurement,
        model_query=lambda m: {k: v for k, v in m.items() if k != "n"}, n_forecast=10000,
        validation_queries=({"type": "spectrum", "thickness": 0.5}, {"type": "calorimeter"},
                            {"type": "recoil_coincidence", "thickness": 1.0}),
        validate_sample=mr.validate_sample,
        validate_mechanism=lambda mech, menu, meta: mr.validate_mechanism(mech, menu, meta["Q"]),
    )


def _orbit() -> Family:
    from abductbench.episode import orbitfamily as of

    return Family(
        name="orbit", world=of.OrbitWorld, validate_measurement=of.validate_measurement,
        model_query=of.model_query, n_forecast=200, validation_queries=of.VALIDATION_QUERIES,
        validate_sample=lambda q, s, n, meta: of.validate_sample(q, s, n),
        validate_mechanism=lambda mech, menu, meta: of.validate_mechanism(mech, menu),
    )


def family_of(cfg) -> Family:
    return {"decay": _decay, "orbit": _orbit}[cfg.family]()
