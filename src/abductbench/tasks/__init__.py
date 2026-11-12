from __future__ import annotations

import importlib.util

from abductbench.config import Family, TaskBundle, VariantConfig
from abductbench.tasks.beta import build_beta


def build_task(cfg: VariantConfig) -> TaskBundle:
    if cfg.family is Family.BETA:
        return build_beta(cfg)
    if cfg.family is Family.ORBIT:
        if importlib.util.find_spec("abductbench.tasks.orbit") is None:
            raise NotImplementedError("orbit task generator is not implemented yet")
        from abductbench.tasks.orbit import build_orbit

        return build_orbit(cfg)
    raise ValueError(f"unknown family: {cfg.family}")


__all__ = ["build_task", "build_beta"]
