"""Fake agent for protocol tests (NOT a solver). Runs inside the workspace and uses ./episode.

Usage: python3 episode_fake_agent.py [probe_path ...]
Each probe_path is a host path that must NOT be readable from an isolated agent; the result is
written to notes.md. The models are crude placeholders with valid outputs.
"""

import json
import os
import subprocess
import sys

CARRIER = '''
import json
import numpy as np
S = json.loads({setup!r})
MECHANISM = {{"kind": "carrier", "mass": 0.1 * S["Q"]}}
def simulate(query, n, seed):
    rng = np.random.default_rng(seed)
    lo, hi = S["spectrometer_window"]
    T = rng.uniform(lo, S["Q"], n)
    if query["type"] == "calorimeter":
        return {{"deposited_energy": rng.uniform(0, S["Q"], n)}}
    if query["type"] == "spectrum":
        return {{"kinetic_energy": T}}
    return {{"kinetic_energy": T, "recoil_momentum": rng.uniform(0, S["Q"], n)}}
'''

LOSS = '''
import json
import numpy as np
S = json.loads({setup!r})
MECHANISM = {{"kind": "loss"}}
def simulate(query, n, seed):
    rng = np.random.default_rng(seed)
    lo, hi = S["spectrometer_window"]
    if query["type"] == "calorimeter":
        return {{"deposited_energy": rng.normal(S["Q"], S["calorimeter_sigma"], n)}}
    t = query["thickness"]
    T = np.clip(S["Q"] - rng.gamma(2.0 * t, 0.2 * S["Q"], n), lo, hi)
    if query["type"] == "spectrum":
        return {{"kinetic_energy": T}}
    return {{"kinetic_energy": T, "recoil_momentum": np.full(n, 1.5 * S["Q"])}}
'''


def ep(*args):
    r = subprocess.run(["./episode", *args], capture_output=True, text=True)
    return json.loads(r.stdout)


def main(probes):
    notes = []
    for p in probes:
        notes.append(f"probe {p}: {'READABLE' if os.path.exists(p) else 'hidden'}")
    setup = open("setup.json").read()
    os.makedirs("models", exist_ok=True)
    open("models/c.py", "w").write(CARRIER.format(setup=setup))
    open("models/l.py", "w").write(LOSS.format(setup=setup))
    notes.append("status " + json.dumps(ep("status")))
    while ep("status")["budget_left"] > 0:
        pre = {"hypotheses": [{"id": "H1", "role": "current", "model": "models/c.py", "statement": "carrier", "credence": 0.5},
                              {"id": "H2", "role": "alternative", "model": "models/l.py", "statement": "loss", "credence": 0.5}],
               "undetermined": "which", "measurement": {"type": "calorimeter", "n": 50},
               "expected": {"H1": "broad", "H2": "line at Q"}}
        json.dump(pre, open("prereg.json", "w"))
        notes.append("register " + json.dumps(ep("register", "prereg.json"))[:200])
        notes.append("measure " + json.dumps(ep("measure")))
    fin = {"hypotheses": [{"id": "H2", "role": "current", "model": "models/l.py", "statement": "loss", "credence": 0.7},
                          {"id": "H1", "role": "alternative", "model": "models/c.py", "statement": "carrier", "credence": 0.3}],
           "undetermined": "material constants", "predictive_model": "models/l.py"}
    json.dump(fin, open("final.json", "w"))
    notes.append("final " + json.dumps(ep("final", "final.json")))
    notes.append("after " + json.dumps(ep("status")))
    open("notes.md", "w").write("\n".join(notes) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
