"""Scoring of the declared MECHANISM against ``TaskBundle.true_mechanism``.

Rules (docs/design-addendum-mechanism.md, section 2): a missing declaration is "missing";
a malformed one is "bad"; both count as a wrong kind. A kind different from the truth's is
``kind_ok=False`` with ``params_ok=None``. For a matching kind with parameters, ``params_ok`` is
true when every scored parameter is within tolerance. Tolerances come from
``true_mechanism["tolerance"]`` and fall back to the module defaults below.
"""

from __future__ import annotations

import math
import numbers
from dataclasses import dataclass, field
from typing import Literal

# Default tolerances (the generators put the same values in true_mechanism["tolerance"]).
TOL_A_FACTOR = 1.3  # hidden_body: max(a/a_true, a_true/a)
TOL_N_ABS = 0.25  # force_law: |n - n_true|
TOL_K_REL = 0.3  # force_law: |k - k_true| / |k_true|

# Required numeric keys per known kind.
REQUIRED = {
    "hidden_body": ("a", "mass"),
    "force_law": ("n", "k"),
    "hidden_carriers": ("n_carriers", "mass"),
    "detector_response": (),
    "other": (),
}

Status = Literal["ok", "missing", "bad"]


@dataclass
class MechanismResult:
    status: Status
    declared_kind: str | None = None
    kind_ok: bool = False
    params_ok: bool | None = None
    param_errors: dict[str, float] = field(default_factory=dict)
    detail: str = ""


def _is_num(v) -> bool:
    return isinstance(v, numbers.Real) and not isinstance(v, bool)


def _finite(v) -> bool:
    return _is_num(v) and math.isfinite(float(v))


def _bad(kind, detail) -> MechanismResult:
    return MechanismResult(status="bad", declared_kind=kind, kind_ok=False, detail=detail)


def score_mechanism(true_mechanism: dict, declared: dict | None) -> MechanismResult:
    if declared is None:
        return MechanismResult(status="missing", detail="no MECHANISM declared")
    if not isinstance(declared, dict):
        return _bad(None, "MECHANISM is not a dict")
    kind = declared.get("kind")
    if not isinstance(kind, str):
        return _bad(None, "MECHANISM has no string `kind`")
    required = REQUIRED.get(kind, ())
    for key in required:
        if not _finite(declared.get(key)):
            return _bad(kind, f"key {key!r} of kind {kind!r} is missing or not a finite number")

    true_kind = true_mechanism.get("kind")
    if kind == "other" or kind != true_kind:
        return MechanismResult(status="ok", declared_kind=kind, kind_ok=False, detail="kind differs from truth")

    tol = true_mechanism.get("tolerance") or {}
    errors: dict[str, float] = {}
    if kind == "hidden_body":
        a, a_true = float(declared["a"]), float(true_mechanism["a"])
        if a <= 0:
            return _bad(kind, "a must be > 0")
        errors["a"] = max(a / a_true, a_true / a)
        ok = errors["a"] <= tol.get("a_factor", TOL_A_FACTOR)
    elif kind == "force_law":
        n, k = float(declared["n"]), float(declared["k"])
        n_true, k_true = float(true_mechanism["n"]), float(true_mechanism["k"])
        errors["n"] = abs(n - n_true)
        errors["k"] = abs(k - k_true) / abs(k_true) if k_true != 0 else abs(k - k_true)
        ok = errors["n"] <= tol.get("n_abs", TOL_N_ABS) and errors["k"] <= tol.get("k_rel", TOL_K_REL)
    elif kind == "hidden_carriers":
        nc, mass = float(declared["n_carriers"]), float(declared["mass"])
        nc_true, mass_true = float(true_mechanism["n_carriers"]), float(true_mechanism["mass"])
        errors["n_carriers"] = abs(nc - nc_true)
        errors["mass"] = abs(mass - mass_true)
        mass_tol = tol.get("mass_abs", 0.0)  # the truth always supplies it
        ok = nc == nc_true and errors["mass"] <= mass_tol
    else:  # detector_response and any other parameterless kind
        return MechanismResult(status="ok", declared_kind=kind, kind_ok=True, detail="kind matches")
    return MechanismResult(
        status="ok", declared_kind=kind, kind_ok=True, params_ok=bool(ok), param_errors=errors,
        detail="kind matches; parameters " + ("within" if ok else "outside") + " tolerance",
    )
