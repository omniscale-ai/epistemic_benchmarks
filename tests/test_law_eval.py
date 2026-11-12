import ast
import dataclasses
import json
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

from abductbench.config import Family, Stage, Truth, VariantConfig
from abductbench.evaluate import LawResult, evaluate_law
from abductbench.tasks import build_task


def bundle_for(family: Family, truth: Truth = Truth.ENTITY):
    return build_task(
        VariantConfig(family=family, truth=truth, stage=Stage.HISTORICAL, seed=0, mode=1, n_points=400)
    )


def write_law(tmp_path: Path, source: str) -> Path:
    """Write law.py into a fresh workspace-like directory under tmp_path."""
    ws = Path(tempfile.mkdtemp(dir=tmp_path))
    law = ws / "law.py"
    law.write_text(source, encoding="utf-8")
    return law


def perfect_source(bundle) -> str:
    """A law.py that reproduces the truth by interpolating truth values embedded at the eval points."""
    ep = bundle.eval_points()
    x = np.concatenate([ep.in_range, ep.extrapolation]).astype(float)
    x = np.unique(x)
    y = np.asarray(bundle.truth_law(x), dtype=float)
    return (
        "import numpy as np\n"
        f"DOMAIN = {json.dumps({k: list(map(float, v)) for k, v in bundle.true_domain.items()})}\n"
        f"_X = np.array({json.dumps(x.tolist())})\n"
        f"_Y = np.array({json.dumps(y.tolist())})\n"
        "def law(t):\n"
        "    return np.interp(np.asarray(t, dtype=float), _X, _Y)\n"
    )


CONSTANT_SOURCE = (
    "import numpy as np\n"
    "def law(t):\n"
    "    return np.full_like(np.asarray(t, dtype=float), 7.0)\n"
)


def zeros_source(extra: str = "") -> str:
    return (
        "import numpy as np\n"
        f"{extra}\n"
        "def law(t):\n"
        "    return np.zeros_like(np.asarray(t, dtype=float))\n"
    )


@pytest.mark.parametrize("family", [Family.BETA, Family.ORBIT])
def test_perfect_law_scores_near_zero(tmp_path, family):
    b = bundle_for(family)
    law = write_law(tmp_path, perfect_source(b))
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert r.nrmse_in < 1e-9
    assert r.nrmse_extrap < 1e-9
    assert r.domain_score == pytest.approx(1.0)


@pytest.mark.parametrize("family", [Family.BETA, Family.ORBIT])
def test_wrong_law_scores_high(tmp_path, family):
    b = bundle_for(family)
    law = write_law(tmp_path, CONSTANT_SOURCE)
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    # Observed: beta (normalized density) ~0.35, orbit (raw arcsec) well above 1.
    assert r.nrmse_in > 0.2
    assert r.nrmse_extrap > 0.2


def test_n_params_proxy_is_ast_node_count(tmp_path):
    b = bundle_for(Family.ORBIT)
    src = perfect_source(b)
    law = write_law(tmp_path, src)
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert r.n_params_proxy == len(list(ast.walk(ast.parse(src))))


def test_infinite_loop_is_timeout(tmp_path):
    b = bundle_for(Family.ORBIT)
    law = write_law(tmp_path, "import numpy as np\nwhile True:\n    pass\n")
    start = time.monotonic()
    r = evaluate_law(b, law, timeout_s=1.0)
    assert r.status == "timeout"
    assert time.monotonic() - start < 15
    assert r.nrmse_in is None and r.domain_score is None


@pytest.mark.parametrize(
    "body",
    [
        "return np.float64(1.0)",  # scalar instead of an array of the input shape
        "return np.ones(3)",  # wrong length
        "return [[1.0] * len(np.asarray(t)), [1.0]]",  # ragged output
    ],
)
def test_wrong_shape_status(tmp_path, body):
    b = bundle_for(Family.ORBIT)
    law = write_law(
        tmp_path,
        f"import numpy as np\ndef law(t):\n    t = np.asarray(t, dtype=float)\n    {body}\n",
    )
    r = evaluate_law(b, law)
    assert r.status == "bad_shape", r.detail
    assert r.nrmse_in is None


@pytest.mark.parametrize("bad", ["np.nan", "np.inf"])
def test_nan_output_status(tmp_path, bad):
    b = bundle_for(Family.BETA)
    law = write_law(
        tmp_path,
        "import numpy as np\n"
        "def law(t):\n"
        "    t = np.asarray(t, dtype=float)\n"
        f"    out = np.zeros_like(t)\n    out[0] = {bad}\n    return out\n",
    )
    r = evaluate_law(b, law)
    assert r.status == "nonfinite", r.detail
    assert r.domain_score is None


def test_missing_file_status(tmp_path):
    b = bundle_for(Family.ORBIT)
    r = evaluate_law(b, tmp_path / "does_not_exist" / "law.py")
    assert isinstance(r, LawResult)
    assert r.status == "missing"
    assert r.nrmse_in is None and r.nrmse_extrap is None and r.n_params_proxy is None
    assert r.domain_score is None


def test_syntax_error_is_crash(tmp_path):
    b = bundle_for(Family.ORBIT)
    law = write_law(tmp_path, "def law(t)\n    return t\n")
    r = evaluate_law(b, law)
    assert r.status == "crash"
    assert "SyntaxError" in r.detail


@pytest.mark.parametrize(
    "source",
    [
        "import numpy as np\ndef law(t):\n    raise ZeroDivisionError('boom')\n",
        "import no_such_module_xyz\ndef law(t):\n    return t\n",
        "import os\nimport numpy as np\ndef law(t):\n    os._exit(3)\n",
        "import numpy as np\nx = 1\n",  # no law defined
    ],
)
def test_runtime_failures_are_crash(tmp_path, source):
    b = bundle_for(Family.ORBIT)
    r = evaluate_law(b, write_law(tmp_path, source))
    assert r.status == "crash", r.detail
    assert r.nrmse_in is None


def test_crash_detail_is_truncated(tmp_path):
    b = bundle_for(Family.ORBIT)
    law = write_law(
        tmp_path,
        "def law(t):\n    raise ValueError('x' * 10000)\n",
    )
    r = evaluate_law(b, law)
    assert r.status == "crash"
    assert len(r.detail) <= 2000


def test_law_cannot_write_into_workspace(tmp_path):
    b = bundle_for(Family.ORBIT)
    law = write_law(
        tmp_path,
        "import numpy as np\n"
        "open('leak.txt', 'w').write('x')\n"
        "def law(t):\n"
        "    return np.zeros_like(np.asarray(t, dtype=float))\n",
    )
    ws = law.parent
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert not (ws / "leak.txt").exists()
    assert not (ws / "__pycache__").exists()
    assert sorted(p.name for p in ws.iterdir()) == ["law.py"]


def test_domain_iou_exact_match(tmp_path):
    b = bundle_for(Family.BETA)
    dom = {k: tuple(map(float, v)) for k, v in b.true_domain.items()}
    law = write_law(tmp_path, zeros_source(f"DOMAIN = {json.dumps({k: list(v) for k, v in dom.items()})}"))
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert r.domain_score == pytest.approx(1.0)


def test_domain_iou_disjoint(tmp_path):
    b = bundle_for(Family.BETA)
    hi = float(b.true_domain["energy_range"][1])
    law = write_law(tmp_path, zeros_source(f"DOMAIN = {{'energy_range': [{hi + 1}, {hi + 2}]}}"))
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert r.domain_score == 0.0


def test_domain_iou_partial_overlap(tmp_path):
    b = dataclasses.replace(bundle_for(Family.BETA), true_domain={"energy_range": (0.0, 10.0)})
    law = write_law(tmp_path, zeros_source("DOMAIN = {'energy_range': (5.0, 15.0)}"))
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert r.domain_score == pytest.approx(1.0 / 3.0)


def test_domain_mean_over_keys_with_missing_and_malformed(tmp_path):
    b = bundle_for(Family.ORBIT)
    t_lo, t_hi = b.true_domain["time_range"]
    # time_range exact (IoU 1), radius_range malformed (0): mean is 0.5
    law = write_law(
        tmp_path,
        zeros_source(f"DOMAIN = {{'time_range': [{t_lo}, {t_hi}], 'radius_range': 'oops'}}"),
    )
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert r.domain_score == pytest.approx(0.5)


def test_no_domain_scores_zero_and_stays_ok(tmp_path):
    b = bundle_for(Family.ORBIT)
    r = evaluate_law(b, write_law(tmp_path, zeros_source()))
    assert r.status == "ok", r.detail
    assert r.domain_score == 0.0


def test_law_can_import_sibling_module(tmp_path):
    b = bundle_for(Family.ORBIT)
    law = write_law(
        tmp_path,
        "import numpy as np\n"
        "from sib import zero_like\n"
        "def law(t):\n"
        "    return zero_like(np.asarray(t, dtype=float))\n",
    )
    (law.parent / "sib.py").write_text(
        "import numpy as np\ndef zero_like(t):\n    return np.zeros_like(t)\n", encoding="utf-8"
    )
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail
    assert not (law.parent / "__pycache__").exists()


def test_large_stdout_still_ok(tmp_path):
    b = bundle_for(Family.ORBIT)
    law = write_law(
        tmp_path,
        "import sys\nimport numpy as np\n"
        "sys.stdout.write('x' * 1_000_000)\n"
        "def law(t):\n"
        "    return np.zeros_like(np.asarray(t, dtype=float))\n",
    )
    r = evaluate_law(b, law)
    assert r.status == "ok", r.detail


def test_sys_exit_at_import_is_crash(tmp_path):
    b = bundle_for(Family.ORBIT)
    law = write_law(tmp_path, "import sys\nsys.exit(0)\ndef law(t):\n    return t\n")
    r = evaluate_law(b, law)
    assert r.status == "crash", r.detail


def test_per_region_normalisation_orbit():
    from abductbench.evaluate.law_eval import score_predictions

    b = bundle_for(Family.ORBIT)
    ep = b.eval_points()
    t_in, t_ex = b.truth_law(ep.in_range), b.truth_law(ep.extrapolation)
    r_in, r_ex = np.ptp(t_in), np.ptp(t_ex)
    assert r_in > 0 and r_ex > 0 and abs(r_in - r_ex) > 1e-6 * r_in
    d = 0.1 * r_in
    # Constant offset d in the window only: NRMSE_in = d / range_in exactly, NRMSE_ex = 0.
    a_in, a_ex = score_predictions(b, t_in + d, t_ex)
    assert a_in == pytest.approx(d / r_in) and a_ex == pytest.approx(0.0, abs=1e-12)
    # Same offset only in the extrapolation region: NRMSE_ex = d / range_ex, in-window untouched.
    b_in, b_ex = score_predictions(b, t_in, t_ex + d)
    assert b_in == pytest.approx(0.0, abs=1e-12) and b_ex == pytest.approx(d / r_ex)
    # Inflating the extrapolation error leaves NRMSE_in unchanged (no shared scale).
    c_in, _ = score_predictions(b, t_in + d, t_ex + 1000 * r_ex)
    assert c_in == pytest.approx(a_in)


def test_beta_range_ex_floor_and_density_normalisation():
    from abductbench.evaluate.law_eval import EX_RANGE_FLOOR, score_predictions

    b = bundle_for(Family.BETA)
    ep = b.eval_points()
    # A prediction equal to the truth scaled by 3 is renormalised: it scores 0 in both regions.
    s_in, s_ex = score_predictions(b, 3 * b.truth_law(ep.in_range), 3 * b.truth_law(ep.extrapolation))
    assert s_in == pytest.approx(0.0, abs=1e-9) and s_ex == pytest.approx(0.0, abs=1e-9)

    # Flat truth in the extrapolation region: range_ex is floored at 0.05 * range_in.
    x_in, x_ex = np.asarray(ep.in_range), np.asarray(ep.extrapolation)
    t_in = np.sin(x_in * 3.0) + 2.0
    t_ex = np.full(len(x_ex), 0.5)
    stub = dataclasses.replace(b, truth_law=lambda x: np.where(np.isin(x, x_in), np.sin(x * 3.0) + 2.0, 0.5))

    def area(y_in, y_ex):
        xs = np.concatenate([x_in, x_ex])
        o = np.argsort(xs, kind="stable")
        ys = np.concatenate([y_in, y_ex])[o]
        return float(np.sum(0.5 * (ys[1:] + ys[:-1]) * np.diff(xs[o])))

    p_in, p_ex = t_in * 1.1, t_ex + 0.2
    a_t, a_p = area(t_in, t_ex), area(p_in, p_ex)
    rng_in = np.ptp(t_in / a_t)
    expected_ex = np.sqrt(np.mean((p_ex / a_p - t_ex / a_t) ** 2)) / (EX_RANGE_FLOOR * rng_in)
    expected_in = np.sqrt(np.mean((p_in / a_p - t_in / a_t) ** 2)) / rng_in
    s_in2, s_ex2 = score_predictions(stub, p_in, p_ex)
    assert s_ex2 == pytest.approx(expected_ex) and s_in2 == pytest.approx(expected_in)
    assert EX_RANGE_FLOOR == 0.05


def test_mechanism_read_through_sandbox(tmp_path):
    b = bundle_for(Family.ORBIT)
    src = zeros_source(
        "import numpy as np\n"
        "MECHANISM = {'kind': 'hidden_body', 'a': np.float64(9.5), 'mass': np.float32(0.5), "
        "'extra': np.array([1, 2]), 'n': np.int64(3)}"
    )
    r = evaluate_law(b, write_law(tmp_path, src))
    assert r.status == "ok"
    assert r.mechanism == {"kind": "hidden_body", "a": 9.5, "mass": 0.5, "extra": [1, 2], "n": 3}
    assert isinstance(r.mechanism["a"], float) and isinstance(r.mechanism["n"], int)


def test_mechanism_missing_is_none_and_law_still_ok(tmp_path):
    r = evaluate_law(bundle_for(Family.ORBIT), write_law(tmp_path, zeros_source()))
    assert r.status == "ok" and r.mechanism is None and r.nrmse_in is not None


@pytest.mark.parametrize("bad", ["[1, 2]", "'hidden_body'", "{'kind': object()}", "{1: 2}", "{'kind': 'hidden_body', 'x': object()}"])
def test_mechanism_malformed_keeps_law_ok(tmp_path, bad):
    r = evaluate_law(bundle_for(Family.ORBIT), write_law(tmp_path, zeros_source(f"MECHANISM = {bad}")))
    assert r.status == "ok" and r.nrmse_in is not None
    assert r.mechanism == {"__malformed__": True}


def test_mechanism_nan_in_extra_key_is_mapped_to_none_not_malformed(tmp_path):
    r = evaluate_law(bundle_for(Family.ORBIT), write_law(
        tmp_path, zeros_source("MECHANISM = {'kind': 'hidden_body', 'a': 9.0, 'mass': 1.0, 'x': float('nan')}")))
    assert r.status == "ok"
    assert r.mechanism == {"kind": "hidden_body", "a": 9.0, "mass": 1.0, "x": None}


MECH_SRC = "MECHANISM = {'kind': 'hidden_body', 'a': 9.0, 'mass': 1.0}\n"


def test_mechanism_kept_when_law_nonfinite(tmp_path):
    src = ("import numpy as np\n" + MECH_SRC + "def law(t):\n    t = np.asarray(t, dtype=float)\n"
           "    return np.where(t > 11, np.nan, 0.0)\n")
    r = evaluate_law(bundle_for(Family.ORBIT), write_law(tmp_path, src))
    assert r.status == "nonfinite" and r.mechanism == {"kind": "hidden_body", "a": 9.0, "mass": 1.0}


def test_mechanism_kept_when_law_raises_inside_law(tmp_path):
    src = "import numpy as np\n" + MECH_SRC + "def law(t):\n    raise RuntimeError('boom')\n"
    r = evaluate_law(bundle_for(Family.ORBIT), write_law(tmp_path, src))
    assert r.status == "crash" and r.mechanism == {"kind": "hidden_body", "a": 9.0, "mass": 1.0}


def test_mechanism_kept_when_law_bad_shape(tmp_path):
    src = "import numpy as np\n" + MECH_SRC + "def law(t):\n    return np.zeros(3)\n"
    r = evaluate_law(bundle_for(Family.ORBIT), write_law(tmp_path, src))
    assert r.status == "bad_shape" and r.mechanism == {"kind": "hidden_body", "a": 9.0, "mass": 1.0}


@pytest.mark.parametrize("src", ["MECHANISM = {'kind': 'hidden_body'}\nraise RuntimeError('import boom')\n",
                                 "MECHANISM = {\ndef law(t): pass\n"])
def test_mechanism_missing_when_module_cannot_be_imported(tmp_path, src):
    r = evaluate_law(bundle_for(Family.ORBIT), write_law(tmp_path, src))
    assert r.status == "crash" and r.mechanism is None
