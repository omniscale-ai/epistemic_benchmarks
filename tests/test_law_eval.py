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
