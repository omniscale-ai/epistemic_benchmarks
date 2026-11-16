"""Agent-visible workspace of the orbit episode. Identical for both mechanisms of a world seed (tested)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np

from abductbench.episode import orbitfamily as of
from abductbench.episode import orbitworld as ow
from abductbench.tasks import orbit as om

CLIENT_NAME = "episode"


def task_md(s) -> str:
    meta = s.meta
    B = s.cfg.effective_budget
    tgt = meta["target"]
    others = ", ".join(p["name"] for p in meta["planets"][1:])
    menu = ('''`MECHANISM` must be exactly one of:
- `{"kind": "body", "a": a, "gm": gm}`: an unseen body on a circular orbit of radius `a` (unit D, about the
  star) inside the target's orbit, with gravitational parameter `gm`;
- `{"kind": "force", "n": n, "k": k}`: an extra radial acceleration `-k r^(-n)` (towards the star) acting on
  the planets, `r` = distance from the star;
- `{"kind": "other", "description": "..."}`.
''' if s.cfg.menu else '''`MECHANISM` must be `{"description": "..."}`: your mechanism in one or two sentences.
''')
    obs = ("No data files are provided. Qualitatively: the target's heliocentric longitude drifts away from the T0 "
           "prediction by tens of arcseconds over ten cycles.\n" if s.cfg.condition == "no_data" else
           f"- `data/initial_{tgt}_residuals.csv`: residuals of **{tgt}** (observed minus T0, arcsec) at 40 times over "
           "0-10 cycles. They do not look like T0.\n")
    proc = f'''## The episode

You may make up to **{B}** measurement(s). Before each measurement you must register a forecast
(`./{CLIENT_NAME} register prereg.json`): the orchestrator copies your model files, runs each hypothesis
model for the chosen measurement and stores those forecasts *before* measuring; they cannot be changed.
Then `./{CLIENT_NAME} measure` performs exactly that measurement and writes the data to `data/`. You are
never told whether a hypothesis is right.

Measurements you can choose:
- `{{"type": "planet", "planet": P}}`: residuals of another planet P ({others}) at the same 40 times (0-10);
- `{{"type": "extend"}}`: residuals of {tgt} at 20 later times (10.25-15 cycles);
- `{{"type": "dense", "start": t0}}`: residuals of {tgt} at 200 times evenly spread over [t0, t0 + 0.5], t0 in [0, 12];
- `{{"type": "search", "time": t, "lon_min": l1, "lon_max": l2}}`: image a heliocentric-longitude window of at
  most 10 degrees at time t in [0, 15]. A body in the window is detected with probability
  {ow.P_DETECT}; independently the instrument reports a Poisson number (mean {ow.FALSE_RATE}) of false detections
  spread uniformly over the window. The reply lists the detected longitudes.

At the end submit `./{CLIENT_NAME} final final.json` (exactly once; it closes the episode). Your predictive
model will then be used to predict observations you have not seen (other epochs, other planets, dense
series). Predictions are scored with a proper scoring rule: if the data do not decide between hypotheses,
an honest mixture is not penalised against a confident guess. Credences are compared with what the data
available at that moment support.
''' if B > 0 else f'''## The episode

No measurements can be made. Submit `./{CLIENT_NAME} final final.json` (exactly once). Your predictive model
will be used to predict observations you have not seen; predictions are scored with a proper scoring rule,
so an honest mixture is not penalised against a confident guess.
'''
    tools = ("\n`models/hyp_tools.py` (with `models/t0_model.py`) provides exact simulators of both hypothesis kinds of the\n"
             "menu: `residuals_body(a, gm, phase, planet, times)` and `residuals_force(n, k, planet, times)`, plus batch\n"
             "versions for fitting. Using them is optional; fitting their parameters is up to you.\n") if s.cfg.tools else ""
    return f"""# Task: why does {tgt} drift?

## The world

A fictional planetary system. Units: time in cycles, distance in unit D, GM in unit D^3/cycle^2, angles in
arcseconds. Rules that hold exactly:

1. Newtonian gravity between all bodies (point masses, all orbits in one plane).
2. The four known planets ({", ".join(p["name"] for p in meta["planets"])}) move about the centre of mass C of
   everything that lies inside the innermost planet's orbit. Their published elements at epoch t = 0
   (`setup.json`) are osculating elements about C computed with the published central gravitational
   parameter `gm_central` (the total GM inside the innermost orbit, determined from the planets' motion).
3. Observations are heliocentric ecliptic longitudes, measured from the star {meta["star"]}, with independent
   Gaussian errors of {ow.SIGMA:g} arcsec each.

## T0 (the accepted model)

A single central mass `gm_central` (the star) at rest at C plus the four known planets with their published
GMs. `t0_model.py` integrates T0 (Newtonian N-body, Yoshida 4th order) and returns the heliocentric
longitudes; it is also a toolbox you may reuse. Residuals are observed minus T0.

## Observations

{obs}
{proc}
## Models

A hypothesis is an executable model `models/<name>.py` (numpy and scipy only, no file or network access,
deterministic for a given seed, at most about a minute of CPU for all queries of one call) with

```python
MECHANISM = {{...}}
def simulate(query: dict, n: int, seed: int) -> dict:
    ...
```

`simulate` returns `n` simulated realisations (including the {ow.SIGMA:g} arcsec observation noise) of:
- `{{"type": "residuals", "planet": P, "times": [...]}}` -> `{{"residual_arcsec": array of shape (n, len(times))}}`;
- `{{"type": "search", "time": t, "lon_min": l1, "lon_max": l2}}` -> `{{"count": array of n integers}}` (number of
  detections, true and false).

Any planet and any times in [0, 15.5] may be asked. `models/t0.py` shows the interface (it is T0: zero
residuals plus noise; it does not explain the data). Models run in isolation and can import only files in
`models/` (copy `t0_model.py` there if you want to reuse it).

{menu}{tools}
## Files you submit

`prereg.json` (before each measurement):

```json
{{
  "hypotheses": [
    {{"id": "H1", "role": "current", "model": "models/h1.py", "statement": "...", "credence": 0.6}},
    {{"id": "H2", "role": "alternative", "model": "models/h2.py", "statement": "...", "credence": 0.3}}
  ],
  "undetermined": "what the data so far do not determine",
  "measurement": {{"type": "...", "...": "..."}},
  "expected": {{"H1": "what H1 predicts for this measurement", "H2": "..."}}
}}
```

Exactly one hypothesis has role `current`; at least one `alternative` that is a substantively different
explanation compatible with the data so far. Credences are probabilities summing to at most 1.

`final.json`: the same `hypotheses` list (alternatives optional) with final credences, `"undetermined"`, and
`"predictive_model": "models/<name>.py"`.

`./{CLIENT_NAME} status` shows the remaining budget. Write your reasoning in `notes.md` (read by people, not scored).
"""


def t0_source(s) -> str:
    funcs = (om._state_from_elements, om._initial_state, om._accel_grav, om._integrate, om._longitudes)
    core = "\n\n".join(inspect.getsource(f) for f in funcs)
    meta = s.meta
    head = f'''"""T0 for the orbit task and a small N-body toolbox (numpy only).

t0_longitudes(times) -> dict planet -> heliocentric longitude (radians, unwrapped) at the given times under T0:
the central mass GM_CENTRAL at rest at C plus the known planets (elements about C at epoch t = 0).
Functions below: _state_from_elements(gm, a, e, varpi, L0) -> (x, v); _initial_state(mu, elements) ->
barycentric states; _accel_grav(X, mu); _integrate(accel, x0, v0, dt, n_steps) (Yoshida 4); _longitudes(X).
"""

import math

import numpy as np

GM_CENTRAL = {meta["gm_central"]!r}
PLANETS = {[p["name"] for p in meta["planets"]]!r}
GM_PLANETS = {[p["gm"] for p in meta["planets"]]!r}
ELEMENTS = {[[p["a"], p["e"], float(np.radians(p["longitude_of_pericentre_deg"])), float(np.radians(p["mean_longitude_epoch_deg"]))] for p in meta["planets"]]!r}
DT = {ow.DT!r}

'''
    tail = '''


def t0_longitudes(times):
    times = np.asarray(times, dtype=float)
    n_steps = max(1, int(math.ceil(float(np.max(times)) / DT)))
    mu = np.array([GM_CENTRAL] + GM_PLANETS)
    X = np.zeros((5, 2))
    V = np.zeros((5, 2))
    for i in range(4):
        X[1 + i], V[1 + i] = _state_from_elements(GM_CENTRAL + GM_PLANETS[i], *ELEMENTS[i])
    M = mu.sum()
    X -= (mu[:, None] * X).sum(0) / M
    V -= (mu[:, None] * V).sum(0) / M
    Xs, _ = _integrate(lambda Y: _accel_grav(Y, mu[None]), X[None], V[None], DT, n_steps)
    lam = np.unwrap(_longitudes(Xs)[:, 0, :], axis=0)
    grid = np.arange(n_steps + 1) * DT
    return {p: np.interp(times, grid, lam[:, j]) for j, p in enumerate(PLANETS)}
'''
    return head + core + tail


def t0_example(s) -> str:
    mech = {"kind": "other", "description": "T0: no anomaly"} if s.cfg.menu else {"description": "T0: no anomaly"}
    return f'''"""T0 as a model: zero residuals plus observation noise; no detections beyond false ones."""

import numpy as np

MECHANISM = {json.dumps(mech)}
SIGMA = {ow.SIGMA!r}
FALSE_RATE = {ow.FALSE_RATE!r}


def simulate(query, n, seed):
    rng = np.random.default_rng(seed)
    if query["type"] == "search":
        return {{"count": rng.poisson(FALSE_RATE, n)}}
    return {{"residual_arcsec": rng.normal(0.0, SIGMA, (n, len(query["times"])))}}
'''


TOOLS = '''"""Exact simulators of the two hypothesis kinds of the menu (same integrator and conventions as the world).

Both are optional helpers; using them commits you to nothing. Residuals are noise-free, observed minus T0, in
arcsec, heliocentric (from the star). Each call integrates up to the largest requested time (step DT).

- residuals_body(a, gm, phase, planet, times): an unseen body of gravitational parameter gm on a circular
  orbit of radius a about the star, inside the target's orbit; phase = its heliocentric longitude (radians)
  at t = 0. Star (gm_central - gm) and body orbit C; the planets' published elements are about C.
- residuals_force(n, k, planet, times): extra radial acceleration -k r^(-n) towards the star on the planets.
- residuals_body_batch(rows, planet, times) / residuals_force_batch(rows, n, planet, times): many parameter sets
  at once (rows: list of (a, gm, phase) or of k), returns an array (len(rows), len(times)); much faster per row.
"""

import math

import numpy as np

import t0_model as T

ARCSEC = 180.0 * 3600.0 / math.pi
DT = T.DT


def _accel(X, mu, k, n):
    A = T._accel_grav(X, mu)
    dr = X - X[:, :1, :]
    rr = np.sqrt(np.einsum("bik,bik->bi", dr, dr))
    rr[:, 0] = 1.0
    ext = -k[:, None, None] * dr * rr[..., None] ** (-(n + 1.0))
    ext[:, 0] = 0.0
    A = A + ext
    A[:, 0, :] -= np.einsum("bi,bik->bk", mu[:, 1:], ext[:, 1:]) / mu[:, :1]
    return A


def _rows(params, kind):
    G, X0, V0, K = [], [], [], []
    for p in params:
        a, gm, ph, k = (p[0], p[1], p[2], 0.0) if kind == "body" else (0.25 * T.ELEMENTS[0][0], 0.0, 0.0, p)
        mu = np.array([T.GM_CENTRAL - gm] + list(T.GM_PLANETS) + [gm])
        X = np.zeros((6, 2)); V = np.zeros((6, 2))
        r, v = T._state_from_elements(T.GM_CENTRAL, a, 0.0, 0.0, ph)
        f = gm / T.GM_CENTRAL
        X[0], V[0], X[5], V[5] = -f * r, -f * v, (1 - f) * r, (1 - f) * v
        for i in range(4):
            X[1 + i], V[1 + i] = T._state_from_elements(T.GM_CENTRAL + T.GM_PLANETS[i], *T.ELEMENTS[i])
        X -= (mu[:, None] * X).sum(0) / mu.sum(); V -= (mu[:, None] * V).sum(0) / mu.sum()
        G.append(mu); X0.append(X); V0.append(V); K.append(k)
    return np.array(G), np.stack(X0), np.stack(V0), np.array(K, float)


def _residuals(params, kind, n, planet, times):
    times = np.asarray(times, dtype=float)
    steps = max(1, int(math.ceil(float(np.max(times)) / DT)))
    G, X0, V0, K = _rows(params, kind)
    Xs, _ = T._integrate(lambda Y: _accel(Y, G, K, n), X0, V0, DT, steps)
    lam = np.unwrap(T._longitudes(Xs)[..., :4], axis=0)  # (S, B, 4)
    j = T.PLANETS.index(planet)
    grid = np.arange(steps + 1) * DT
    t0 = T.t0_longitudes(times)[planet]
    return np.stack([(np.interp(times, grid, lam[:, b, j]) - t0) * ARCSEC for b in range(lam.shape[1])])


def residuals_body_batch(rows, planet, times):
    return _residuals(list(rows), "body", 4.0, planet, times)


def residuals_force_batch(rows, n, planet, times):
    return _residuals(list(rows), "force", float(n), planet, times)


def residuals_body(a, gm, phase, planet, times):
    return residuals_body_batch([(a, gm, phase)], planet, times)[0]


def residuals_force(n, k, planet, times):
    return residuals_force_batch([k], n, planet, times)[0]
'''


def _csv(cols: dict) -> str:
    keys = list(cols)
    rows = [",".join(keys)] + [",".join(f"{v:.9g}" for v in vals) for vals in zip(*(cols[k] for k in keys))]
    return "\n".join(rows) + "\n"


def measurement_name(k: int, q: dict) -> str:
    t = q["type"]
    if t == "planet":
        return f"data/measurement_{k}_{q['planet']}_residuals.csv"
    if t == "search":
        return f"data/measurement_{k}_search.json"
    return f"data/measurement_{k}_{of.TARGET}_{t}.csv"


def measurement_text(q: dict, obs: dict) -> str:
    if q["type"] == "search":
        return json.dumps({"time": q["time"], "lon_min": q["lon_min"], "lon_max": q["lon_max"],
                           "detections": int(np.asarray(obs["count"]).ravel()[0]),
                           "longitudes_deg": [float(x) for x in obs.get("longitudes_deg", [])]}, indent=1) + "\n"
    return _csv({"time": obs["time"], "residual_arcsec": obs["residual_arcsec"]})


def write_workspace(s, ws: Path, client_text: str) -> None:
    ws = Path(ws)
    (ws / "data").mkdir(parents=True, exist_ok=False)
    (ws / "models").mkdir()
    (ws / "task.md").write_text(task_md(s))
    (ws / "setup.json").write_text(json.dumps(s.meta, indent=2) + "\n")
    (ws / "t0_model.py").write_text(t0_source(s))
    (ws / "models" / "t0.py").write_text(t0_example(s))
    if s.cfg.tools:
        (ws / "models" / "t0_model.py").write_text(t0_source(s))
        (ws / "models" / "hyp_tools.py").write_text(TOOLS)
    for q, obs in s.initial:
        (ws / f"data/initial_{of.TARGET}_residuals.csv").write_text(_csv({"time": obs["time"], "residual_arcsec": obs["residual_arcsec"]}))
    c = ws / CLIENT_NAME
    c.write_text(client_text)
    c.chmod(0o755)
