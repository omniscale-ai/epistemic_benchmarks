"""Episode protocol: forecast-before-measure, immutability, validation, sandboxed model execution."""

import json
import textwrap
from pathlib import Path

import numpy as np
import pytest

from abductbench.episode import modelrun as mr
from abductbench.episode.protocol import ProtocolError, Session, load_session
from abductbench.episode.server import client_text
from abductbench.episode.workspace import write_workspace
from abductbench.episode.world import EpisodeConfig

needs_bwrap = pytest.mark.skipif(not mr.bwrap_available(), reason="bwrap not installed")

GOOD = """
import numpy as np
S = {setup}
MECHANISM = {mech}
def simulate(query, n, seed):
    rng = np.random.default_rng(seed)
    lo, hi = S["spectrometer_window"]
    if query["type"] == "calorimeter":
        return {{"deposited_energy": rng.normal({cal}, S["calorimeter_sigma"], n)}}
    T = rng.uniform(lo, S["Q"], n)
    if query["type"] == "spectrum":
        return {{"kinetic_energy": T}}
    return {{"kinetic_energy": T, "recoil_momentum": rng.uniform(0, S["Q"], n)}}
"""


def _model(ws: Path, name: str, s: Session, mech: dict, cal: str = 'S["Q"]', body: str | None = None):
    text = body if body is not None else GOOD.format(setup=repr(s.meta), mech=repr(mech), cal=cal)
    (ws / "models" / f"{name}.py").write_text(textwrap.dedent(text))


def _session(tmp_path, mech="carrier", **kw) -> tuple[Session, Path]:
    ws = tmp_path / "ws"
    s = Session(EpisodeConfig(0, mech, **kw), state_dir=tmp_path / "state", workspace=ws,
                allow_unsandboxed=not mr.bwrap_available())
    write_workspace(s, ws, client_text("/nonexistent"))
    return s, ws


def _prereg(meas=None, cur="models/a.py", alt="models/b.py"):
    return {"hypotheses": [{"id": "H1", "role": "current", "model": cur, "statement": "a", "credence": 0.6},
                           {"id": "H2", "role": "alternative", "model": alt, "statement": "b", "credence": 0.4}],
            "undetermined": "x", "measurement": meas or {"type": "calorimeter", "n": 30},
            "expected": {"H1": "broad", "H2": "line"}}


def test_measure_requires_registration_and_budget(tmp_path):
    s, ws = _session(tmp_path)
    _model(ws, "a", s, {"kind": "carrier", "mass": 0.0}, cal='0.5 * S["Q"]')
    _model(ws, "b", s, {"kind": "loss"})
    with pytest.raises(ProtocolError, match="register"):
        s.measure()
    for _ in range(2):
        s.register(_prereg())
        q, obs = s.measure()
        assert q == {"type": "calorimeter", "n": 30} and obs["deposited_energy"].shape == (30,)
        with pytest.raises(ProtocolError):
            s.measure()  # one registration buys one measurement
    with pytest.raises(ProtocolError, match="budget"):
        s.register(_prereg())


def test_forecast_is_frozen_before_measurement(tmp_path):
    s, ws = _session(tmp_path)
    _model(ws, "a", s, {"kind": "carrier", "mass": 0.0}, cal='0.5 * S["Q"]')
    _model(ws, "b", s, {"kind": "loss"})
    s.register(_prereg())
    frozen = s.steps[-1].hyps[0].forecast["deposited_energy"].copy()
    _model(ws, "a", s, {"kind": "carrier", "mass": 0.0}, cal='S["Q"]')  # agent edits its model afterwards
    s.measure()
    assert np.array_equal(s.steps[0].hyps[0].forecast["deposited_energy"], frozen)
    snap = Path(json.loads((tmp_path / "state" / "log.jsonl").read_text().splitlines()[1])["snapshot"])
    assert "0.5 *" in (snap / "a.py").read_text()  # snapshot is the registered version
    s.final({"hypotheses": [{"id": "H1", "role": "current", "model": "models/a.py", "statement": "a", "credence": 0.9}],
             "undetermined": "-", "predictive_model": "models/a.py"})
    loaded = load_session(tmp_path / "state", allow_unsandboxed=not mr.bwrap_available())
    assert np.array_equal(loaded.steps[0].hyps[0].forecast["deposited_energy"], frozen)
    assert loaded.closed and loaded.n_measured == 1
    with pytest.raises(ProtocolError, match="closed"):
        s.register(_prereg())


@pytest.mark.parametrize("change,msg", [
    (lambda p: p["hypotheses"].pop(), "alternative"),
    (lambda p: p["hypotheses"][0].update(credence=0.9), "sum to at most 1"),
    (lambda p: p["hypotheses"][1].update(role="current"), "exactly one"),
    (lambda p: p.update(measurement={"type": "recoil_coincidence", "thickness": 0.05}), "measurement"),
    (lambda p: p["expected"].pop("H2"), "expected"),
    (lambda p: p["hypotheses"][0].update(model="../x.py"), "models/"),
    (lambda p: p.update(undetermined=""), "undetermined"),
])
def test_prereg_validation(tmp_path, change, msg):
    s, ws = _session(tmp_path)
    _model(ws, "a", s, {"kind": "carrier", "mass": 0.0})
    _model(ws, "b", s, {"kind": "loss"})
    p = _prereg()
    change(p)
    with pytest.raises(ProtocolError, match=msg):
        s.register(p)
    assert s.n_registrations == 0 and s.budget_left == 2


@pytest.mark.parametrize("body,msg", [
    ("MECHANISM = {'kind': 'loss'}\nimport numpy as np\ndef simulate(q, n, seed):\n    return {'deposited_energy': np.full(n, np.nan)}\n", "non-finite"),
    ("MECHANISM = {'kind': 'loss'}\nimport numpy as np\ndef simulate(q, n, seed):\n    return {'deposited_energy': np.ones(n - 1)}\n", "shape"),
    ("MECHANISM = {'kind': 'loss'}\nimport numpy as np\ndef simulate(q, n, seed):\n    return {'deposited_energy': -1e6 * np.ones(n)}\n", "not physical"),
    ("MECHANISM = {'kind': 'carrier', 'mass': -1.0}\nimport numpy as np\ndef simulate(q, n, seed):\n    return {'deposited_energy': np.ones(n)}\n", "mass"),
    ("MECHANISM = {'kind': 'neutrino'}\nimport numpy as np\ndef simulate(q, n, seed):\n    return {'deposited_energy': np.ones(n)}\n", "MECHANISM"),
    ("raise RuntimeError('boom')\n", "boom"),
])
def test_invalid_models_rejected(tmp_path, body, msg):
    s, ws = _session(tmp_path)
    _model(ws, "a", s, {}, body=body)
    _model(ws, "b", s, {"kind": "loss"})
    with pytest.raises(ProtocolError, match=msg):
        s.register(_prereg())


def test_recorded_energies_outside_window_rejected(tmp_path):
    s, ws = _session(tmp_path)
    body = "MECHANISM = {'kind': 'loss'}\nimport numpy as np\ndef simulate(q, n, seed):\n    return {'kinetic_energy': np.zeros(n)}\n"
    _model(ws, "a", s, {}, body=body)
    _model(ws, "b", s, {"kind": "loss"})
    with pytest.raises(ProtocolError, match="window"):
        s.register(_prereg({"type": "spectrum", "thickness": 1.0, "n": 50}))


def test_no_menu_condition_accepts_free_description(tmp_path):
    s, ws = _session(tmp_path, menu=False)
    _model(ws, "a", s, {"description": "something invisible takes energy"})
    _model(ws, "b", s, {"description": "material"})
    s.register(_prereg())
    assert s.steps[0].hyps[0].mechanism == {"description": "something invisible takes energy"}


@needs_bwrap
def test_model_sandbox_hides_host_files_and_network(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("truth")
    (tmp_path / "m").mkdir()
    (tmp_path / "m" / "x.py").write_text(textwrap.dedent(f"""
        import os, socket, numpy as np
        MECHANISM = {{"kind": "loss"}}
        def simulate(q, n, seed):
            seen = os.path.exists({str(secret)!r}) or os.path.exists({str(Path(__file__).resolve().parents[1])!r})
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=1); net = 1.0
            except OSError:
                net = 0.0
            return {{"deposited_energy": np.array([float(seen), net] + [0.0] * (n - 2))}}
    """))
    out = mr.run_model(tmp_path / "m", "x.py", [{"type": "calorimeter"}], 5, 0)
    assert out.sandbox == "bwrap"
    assert out.samples[0]["deposited_energy"][:2].tolist() == [0.0, 0.0]


def test_responses_do_not_reveal_truth(tmp_path):
    for mech in ("carrier", "loss"):
        s, ws = _session(tmp_path / mech, mech=mech)
        _model(ws, "a", s, {"kind": "carrier", "mass": 0.0})
        _model(ws, "b", s, {"kind": "loss"})
        reply = s.register(_prereg())
        assert set(reply) == {"registered", "measurement", "forecast_summary"}
        assert set(s.status()) == {"budget_left", "closed", "pending_measurement", "registrations", "measurements_done"}


def test_retry_after_failed_registration(tmp_path):
    """A registration rejected by validation must not block the next attempt (seen in a real run)."""
    s, ws = _session(tmp_path)
    _model(ws, "a", s, {"kind": "carrier", "mass": 0.0})
    _model(ws, "b", s, {"kind": "loss"})
    s.register(_prereg())
    s.measure()
    _model(ws, "a", s, {}, body="raise RuntimeError('boom')\n")
    with pytest.raises(ProtocolError, match="boom"):
        s.register(_prereg())
    _model(ws, "a", s, {"kind": "carrier", "mass": 0.0})
    s.register(_prereg())
    s.measure()
    assert s.n_measured == 2
