"""Fake orbit agent for protocol tests (NOT a solver). Uses ./episode; writes two models that really
integrate N-body hypotheses with the public t0_model toolbox (copied into models/), to exercise the
sandbox CPU limits, then registers, measures and submits a final answer."""

import json
import os
import shutil
import subprocess
import sys

BODY = '''
import math, numpy as np
import t0_model as T
MECHANISM = {"kind": "body", "a": 0.25 * T.ELEMENTS[0][0], "gm": 3e-4}
_cache = {}
def _run(h):
    if h in _cache: return _cache[h]
    a, m = 0.25 * T.ELEMENTS[0][0], 3e-4
    mu = np.array([T.GM_CENTRAL - m] + T.GM_PLANETS + [m])
    X = np.zeros((6, 2)); V = np.zeros((6, 2))
    r, v = T._state_from_elements(T.GM_CENTRAL, a, 0.0, 0.0, 0.0)
    f = m / T.GM_CENTRAL
    X[0], V[0], X[5], V[5] = -f * r, -f * v, (1 - f) * r, (1 - f) * v
    for i in range(4):
        X[1 + i], V[1 + i] = T._state_from_elements(T.GM_CENTRAL + T.GM_PLANETS[i], *T.ELEMENTS[i])
    n = int(math.ceil(h / T.DT))
    Xs, _ = T._integrate(lambda Y: T._accel_grav(Y, mu[None]), X[None], V[None], T.DT, n)
    lam = np.unwrap(T._longitudes(Xs)[:, 0, :4], axis=0)
    _cache[h] = (np.arange(n + 1) * T.DT, lam)
    return _cache[h]
def simulate(query, n, seed):
    rng = np.random.default_rng(seed)
    if query["type"] == "search":
        return {"count": rng.poisson(0.3, n) + (rng.random(n) < 0.8) * 0}
    t = np.asarray(query["times"], float)
    g, lam = _run(15.5)
    j = T.PLANETS.index(query["planet"])
    t0 = T.t0_longitudes(t)[query["planet"]]
    mu = (np.interp(t, g, lam[:, j]) - t0) * 206264.80624709636
    return {"residual_arcsec": mu[None, :] + rng.normal(0, 1.0, (n, len(t)))}
'''

FORCE = '''
import numpy as np
MECHANISM = {"kind": "force", "n": 4.0, "k": 1e-6}
def simulate(query, n, seed):
    rng = np.random.default_rng(seed)
    if query["type"] == "search":
        return {"count": rng.poisson(0.3, n)}
    t = np.asarray(query["times"], float)
    return {"residual_arcsec": (-3.0 * t)[None, :] + rng.normal(0, 1.0, (n, len(t)))}
'''


def ep(*args):
    return json.loads(subprocess.run(["./episode", *args], capture_output=True, text=True).stdout)


def main(probes):
    notes = [f"probe {p}: {'READABLE' if os.path.exists(p) else 'hidden'}" for p in probes]
    shutil.copy("t0_model.py", "models/t0_model.py")
    open("models/b.py", "w").write(BODY)
    open("models/f.py", "w").write(FORCE)
    plan = [{"type": "dense", "start": 2.0}, {"type": "search", "time": 3.0, "lon_min": 10.0, "lon_max": 20.0}]
    for meas in plan:
        if ep("status")["budget_left"] <= 0:
            break
        pre = {"hypotheses": [{"id": "H1", "role": "current", "model": "models/f.py", "statement": "force", "credence": 0.5},
                              {"id": "H2", "role": "alternative", "model": "models/b.py", "statement": "body", "credence": 0.5}],
               "undetermined": "which", "measurement": meas, "expected": {"H1": "-", "H2": "-"}}
        json.dump(pre, open("prereg.json", "w"))
        notes.append("register " + json.dumps(ep("register", "prereg.json"))[:300])
        notes.append("measure " + json.dumps(ep("measure")))
    fin = {"hypotheses": [{"id": "H2", "role": "current", "model": "models/b.py", "statement": "body", "credence": 0.6}],
           "undetermined": "mass", "predictive_model": "models/b.py"}
    json.dump(fin, open("final.json", "w"))
    notes.append("final " + json.dumps(ep("final", "final.json")))
    notes.append("after " + json.dumps(ep("status")))
    open("notes.md", "w").write("\n".join(notes) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
