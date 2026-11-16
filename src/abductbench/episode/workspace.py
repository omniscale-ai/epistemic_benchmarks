"""Agent-visible workspace for one episode: task text, setup, data, example model, client.

Nothing here depends on the mechanism: two worlds of one seed get byte-identical task.md,
setup.json and t0 example (tested). Only the data differ.
"""

from __future__ import annotations

import json
from pathlib import Path

from abductbench.episode.protocol import Session

CLIENT_NAME = "episode"

_RULES = """\
## The world

You work in a fictional physical world. Its rules hold exactly:

1. Relativistic energy and momentum are conserved in every decay. Energies, masses (rest energies)
   and momenta (p times c) are all given in `{unit}`.
2. Every decay distributes the final-state momenta uniformly over the Lorentz-invariant phase space
   allowed by conservation (constant matrix element).
3. A light particle that crosses source material of relative thickness `t` (nominal `t = 1`) loses
   kinetic energy `L = a*t + G`, where `G` is Gamma-distributed with shape `b*t` and scale `c`.
   The constants `a >= 0`, `b > 0`, `c > 0` of this source material have not been measured.
   A particle whose loss exceeds its kinetic energy stops in the source.
4. Instruments (numbers in `setup.json`):
   - spectrometer: kinetic energy of the light particle after it leaves the source, Gaussian
     resolution `spectrometer_sigma`; only events recorded inside `spectrometer_window` are kept;
     stopped particles are never recorded;
   - calorimeter: the source sits inside it; it absorbs the light particle and the daughter
     completely and records the total energy they deposit per decay, resolution `calorimeter_sigma`;
   - recoil detector: momentum magnitude of the daughter, relative resolution
     `recoil_relative_resolution`, in coincidence with the spectrometer. You cannot use it here.

## T0 (the accepted model)

A parent at rest decays into a daughter and a light particle. Masses are in `setup.json`;
`Q = mass_parent - mass_daughter - mass_light`. T0 predicts that the light particle is always
emitted with one and the same kinetic energy (Q minus the tiny recoil energy of the daughter).
`models/t0.py` implements T0 and shows the model interface; it does not explain the data.
"""

_MENU = """\
`MECHANISM` must be exactly one of:
- `{"kind": "carrier", "mass": m}`: besides the daughter and the light particle, the decay emits an
  unobserved neutral particle; `m` is its rest energy in `unit E` (0 <= m < Q);
- `{"kind": "loss"}`: the decay is the T0 two-body decay and the recorded spectrum is shaped by
  energy loss in the source material;
- `{"kind": "other", "description": "..."}`: anything else (free text).
"""

_NO_MENU = """\
`MECHANISM` must be `{"description": "..."}`: your mechanism in one or two sentences.
"""


def _observations(s: Session) -> str:
    c = s.cfg.condition
    if c == "no_data":
        return ("No data files are provided. Qualitatively: at nominal thickness the spectrometer "
                "recorded a broad continuous distribution of kinetic energies below about Q instead of "
                "a single line.\n")
    lines = [f"- `{name}`: {q['n']} events, spectrometer at thickness {q['thickness']:g}."
             for name, (q, _) in zip(initial_names(s), s.initial)]
    return "\n".join(lines) + "\n\nThe recorded spectra do not look like T0.\n"


def initial_names(s: Session) -> list[str]:
    return [f"data/initial_{i + 1}_spectrum_t{q['thickness']:g}.csv" for i, (q, _) in enumerate(s.initial)]


def task_md(s: Session) -> str:
    B = s.cfg.effective_budget
    meta = s.meta
    procedure = f"""\
## The episode

You may make up to **{B}** measurement(s). Before each measurement you must register a forecast
(`./{CLIENT_NAME} register prereg.json`). The orchestrator copies your model files, runs each
hypothesis model for the chosen measurement and stores those forecasts *before* measuring; a
registered forecast cannot be changed afterwards. Then `./{CLIENT_NAME} measure` performs exactly
that measurement and writes the data to `data/`. You are never told whether a hypothesis is right.

Measurements you can choose (n is the number of recorded events, 1 to {meta['max_events_per_measurement']}):
- `{{"type": "spectrum", "thickness": t, "n": n}}` with t in [{meta['thickness_range'][0]}, {meta['thickness_range'][1]}];
- `{{"type": "calorimeter", "n": n}}`.

A measurement has a fixed maximum exposure: if almost every particle stops in the source, a
spectrum measurement may record fewer than n events (the reply says how many).

At the end submit `./{CLIENT_NAME} final final.json` (exactly once; it closes the episode). Your
predictive model will then be used to predict observations you have not seen, including conditions
and instruments this interface does not offer (other thicknesses, the recoil detector). Predictions
are scored with a proper scoring rule: if the data do not decide between hypotheses, an honest
mixture is not penalised against a confident guess. Credences are compared with what the data
available at that moment support.
""" if B > 0 else f"""\
## The episode

No measurements can be made in this episode. Submit `./{CLIENT_NAME} final final.json` (exactly once;
it closes the episode). Your predictive model will be used to predict observations you have not seen,
including conditions and instruments this interface does not offer (other thicknesses, the recoil
detector). Predictions are scored with a proper scoring rule: if the information does not decide between
hypotheses, an honest mixture is not penalised against a confident guess.
"""
    menu = _MENU if s.cfg.menu else _NO_MENU
    return f"""# Task: what shapes this decay spectrum?

{_RULES.format(unit=meta['energy_unit'])}
## Observations

{_observations(s)}
{procedure}
## Models

A hypothesis is an executable model: a Python file `models/<name>.py` (numpy and scipy only, no
file or network access, deterministic for a given seed, `n` up to 10000 in a few seconds) with

```python
MECHANISM = {{...}}
def simulate(query: dict, n: int, seed: int) -> dict:
    ...
```

`simulate` returns `n` simulated recorded observations, in `{meta['energy_unit']}`, for the query:
- `{{"type": "spectrum", "thickness": t}}` -> `{{"kinetic_energy": array}}` (inside the window);
- `{{"type": "calorimeter"}}` -> `{{"deposited_energy": array}}`;
- `{{"type": "recoil_coincidence", "thickness": t}}` -> `{{"kinetic_energy": array, "recoil_momentum": array}}`
  (spectrometer energy and daughter momentum magnitude of the same recorded events).

{menu}
## Files you submit

`prereg.json` (before each measurement):

```json
{{
  "hypotheses": [
    {{"id": "H1", "role": "current", "model": "models/h1.py", "statement": "...", "credence": 0.6}},
    {{"id": "H2", "role": "alternative", "model": "models/h2.py", "statement": "...", "credence": 0.3}}
  ],
  "undetermined": "what the data so far do not determine",
  "measurement": {{"type": "...", "n": 400}},
  "expected": {{"H1": "what H1 predicts for this measurement", "H2": "..."}}
}}
```

Exactly one hypothesis has role `current`; at least one `alternative` that is a substantively
different explanation compatible with the data so far. Credences are probabilities and sum to at
most 1 (the remainder is "something else").

`final.json`: the same `hypotheses` list (alternatives optional) with your final credences,
`"undetermined"`, and `"predictive_model": "models/<name>.py"`.

`./{CLIENT_NAME} status` shows the remaining budget. Write your reasoning in `notes.md` (read by
people, not scored).
"""


T0_MODEL = '''"""T0 model: two-body decay, no energy loss in the source. Example of the model interface."""

import numpy as np

_SETUP = {setup}

MECHANISM = {mechanism}


def _two_body():
    M, m1, m3 = _SETUP["mass_parent"], _SETUP["mass_light"], _SETUP["mass_daughter"]
    E1 = (M * M + m1 * m1 - m3 * m3) / (2.0 * M)
    T1 = E1 - m1
    return T1, np.sqrt(T1 * (T1 + 2.0 * m1)), _SETUP["Q"] - T1


def simulate(query, n, seed):
    rng = np.random.default_rng(seed)
    T1, p1, T3 = _two_body()
    if query["type"] == "calorimeter":
        return {{"deposited_energy": T1 + T3 + rng.normal(0.0, _SETUP["calorimeter_sigma"], n)}}
    lo, hi = _SETUP["spectrometer_window"]
    T = []
    while sum(len(x) for x in T) < n:
        x = T1 + rng.normal(0.0, _SETUP["spectrometer_sigma"], 2 * n)
        T.append(x[(x >= lo) & (x <= hi)])
    T = np.concatenate(T)[:n]
    if query["type"] == "spectrum":
        return {{"kinetic_energy": T}}
    p = p1 * (1.0 + _SETUP["recoil_relative_resolution"] * rng.normal(size=n))
    return {{"kinetic_energy": T, "recoil_momentum": p}}
'''


def t0_model(s: Session) -> str:
    mech = {"kind": "other", "description": "T0: two-body decay, no energy loss"} if s.cfg.menu else \
        {"description": "T0: two-body decay, no energy loss"}
    return T0_MODEL.format(setup=json.dumps(s.meta, indent=4), mechanism=json.dumps(mech))


def csv_text(obs: dict) -> str:
    keys = sorted(obs)
    rows = [",".join(keys)] + [",".join(f"{v:.9g}" for v in vals) for vals in zip(*(obs[k] for k in keys))]
    return "\n".join(rows) + "\n"


def measurement_name(k: int, q: dict) -> str:
    if q["type"] == "spectrum":
        return f"data/measurement_{k}_spectrum_t{q['thickness']:g}.csv"
    return f"data/measurement_{k}_calorimeter.csv"


def write_workspace(s: Session, ws: Path, client_text: str) -> None:
    if s.cfg.family == "orbit":
        from abductbench.episode import orbitworkspace

        return orbitworkspace.write_workspace(s, ws, client_text)
    ws = Path(ws)
    (ws / "data").mkdir(parents=True, exist_ok=False)
    (ws / "models").mkdir()
    (ws / "task.md").write_text(task_md(s))
    (ws / "setup.json").write_text(json.dumps(s.meta, indent=2) + "\n")
    for name, (_q, obs) in zip(initial_names(s), s.initial):
        (ws / name).write_text(csv_text(obs))
    (ws / "models" / "t0.py").write_text(t0_model(s))
    client = ws / CLIENT_NAME
    client.write_text(client_text)
    client.chmod(0o755)

