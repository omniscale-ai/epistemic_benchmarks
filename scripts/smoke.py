"""End-to-end smoke test over the 16 variants of one seed (mode 1).

Each variant goes through the real pipeline: ``make_run`` builds the workspace and runs a
fake agent, ``evaluate_run`` scores the saved files (law, answer, judge), and
``aggregate`` / ``pair_table`` summarise the rows. The fake agent is this file itself, run
with the hidden ``--copy-agent`` flag: it copies a pre-computed ``law.py`` and ``answer.md``
into its working directory. The judge is a stub that passes every rubric item.

Usage: ``python scripts/smoke.py <root> [--agent oracle|constant_yes|curve_fit|wrong_mechanism] [--seed N]``
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

COPY_FLAG = "--copy-agent"


def _copy_agent(argv: list[str]) -> int:
    """Fake agent: copy the pre-computed law.py and answer.md into the working directory.

    Dispatched before the abductbench import below: the agent subprocess runs with the
    workspace as cwd and the package is not on its sys.path.
    """
    law_src, answer_src = argv
    cwd = Path.cwd()
    shutil.copyfile(law_src, cwd / "law.py")
    shutil.copyfile(answer_src, cwd / "answer.md")
    return 0


if len(sys.argv) > 1 and sys.argv[1] == COPY_FLAG:
    raise SystemExit(_copy_agent(sys.argv[2:]))

import argparse  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
from collections.abc import Callable  # noqa: E402
from dataclasses import asdict  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from abductbench.config import Family, TaskBundle, all_variants  # noqa: E402
from abductbench.evaluate.aggregate import RUN_COLUMNS, RunScores, aggregate, evaluate_run, pair_table  # noqa: E402
from abductbench.evaluate.rubric import Rubric, load_rubric  # noqa: E402
from abductbench.runner import make_run  # noqa: E402
from abductbench.tasks import build_task  # noqa: E402

AGENTS = ("oracle", "constant_yes", "curve_fit", "wrong_mechanism")
AGENT_TIMEOUT_S = 120


def public_mechanism(bundle: TaskBundle) -> dict:
    """The true mechanism without its tolerances (the agent never sees tolerances)."""
    return {k: v for k, v in bundle.true_mechanism.items() if k != "tolerance"}


def wrong_mechanism(bundle: TaskBundle) -> dict:
    """A mechanism of the other kind of the same family, with arbitrary parameters."""
    other = {
        "hidden_body": {"kind": "force_law", "n": 3.0, "k": 1.0},
        "force_law": {"kind": "hidden_body", "a": 1.0, "mass": 1.0},
        "hidden_carriers": {"kind": "detector_response"},
        "detector_response": {"kind": "hidden_carriers", "n_carriers": 2, "mass": 0.0},
    }
    return other[bundle.true_mechanism["kind"]]


def perfect_law_source(bundle: TaskBundle, family: Family, mechanism: dict | None = None) -> str:
    """law.py that interpolates the true law over dense embedded points, with the true DOMAIN.

    ``mechanism`` (if given) is written as the module-level MECHANISM dict; None writes none."""
    ep = bundle.eval_points()
    x = np.unique(np.concatenate([ep.in_range, ep.extrapolation]).astype(float))
    y = np.asarray(bundle.truth_law(x), dtype=float)
    arg = "T" if family is Family.BETA else "t"
    domain = {k: [float(lo), float(hi)] for k, (lo, hi) in bundle.true_domain.items()}
    mech_line = f"MECHANISM = {json.dumps(mechanism)}\n" if mechanism is not None else ""
    return (
        "import numpy as np\n"
        f"DOMAIN = {json.dumps(domain)}\n"
        f"{mech_line}"
        f"_X = np.array({json.dumps(x.tolist())})\n"
        f"_Y = np.array({json.dumps(y.tolist())})\n"
        f"def law({arg}):\n"
        f"    return np.interp(np.asarray({arg}, dtype=float), _X, _Y)\n"
    )


def answer_text(entity: bool) -> str:
    return (
        f"ENTITY: {'yes' if entity else 'no'}\n\n"
        "## Law\n"
        "The observed quantity follows the tabulated law in law.py, which interpolates the fitted curve.\n\n"
        "## Limits\n"
        "The law is only supported over the sampled range; extrapolation reuses the same curve.\n\n"
        "## Explanation\n"
        "The measurements are consistent with the mechanism the public data points to, and the law reproduces them.\n"
    )


def _pass_all_judge(rubric: Rubric) -> Callable[[str], str]:
    reply = json.dumps({"items": {item.id: {"pass": True, "quote": "stub", "reason": "stub"} for item in rubric.items}})
    return lambda prompt: reply


def run_smoke(
    root: Path,
    seed: int = 0,
    agent: str = "oracle",
    judge_stub: Callable[[str], str] | None = None,
    oracle_cache: dict | None = None,
) -> dict:
    """Run the 16 variants of ``seed`` (mode 1) under ``root`` and return the results.

    ``agent="oracle"`` answers with the true ENTITY value; ``"constant_yes"`` always says
    yes; ``"curve_fit"`` has the perfect law but no MECHANISM; ``"wrong_mechanism"`` declares
    the other kind of the family. ``judge_stub`` replaces the default all-pass stub when given. Returns a dict with
    ``runs`` (one row per variant), ``summary`` (aggregate), ``pairs`` (pair_table) and
    ``judge_calls``.
    """
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}; expected one of {AGENTS}")
    cache = {} if oracle_cache is None else oracle_cache
    scores: list[RunScores] = []
    workspaces: list[str] = []
    judge_calls = 0
    with tempfile.TemporaryDirectory(prefix="smoke-inputs-") as tmp:
        for cfg in all_variants(seeds=[seed], modes=(1,)):
            bundle = build_task(cfg)
            law_src = Path(tmp) / f"{cfg.variant_id}-law.py"
            mechanism = {
                "oracle": public_mechanism,
                "constant_yes": public_mechanism,
                "curve_fit": lambda b: None,
                "wrong_mechanism": wrong_mechanism,
            }[agent](bundle)
            law_src.write_text(perfect_law_source(bundle, cfg.family, mechanism), encoding="utf-8")
            entity = bool(bundle.entity) if agent == "oracle" else True
            answer_src = Path(tmp) / f"{cfg.variant_id}-answer.md"
            answer_src.write_text(answer_text(entity), encoding="utf-8")
            agent_cmd = [sys.executable, str(Path(__file__).resolve()), COPY_FLAG, str(law_src), str(answer_src)]
            record = make_run(cfg, Path(root), agent_cmd=agent_cmd, timeout_s=AGENT_TIMEOUT_S)

            rubric = load_rubric(bundle.rubric_id)
            stub = judge_stub if judge_stub is not None else _pass_all_judge(rubric)

            def judge(prompt: str, _stub=stub) -> str:
                nonlocal judge_calls
                judge_calls += 1
                return _stub(prompt)

            scores.append(evaluate_run(cfg, record, judge_runner=judge, oracle_cache=cache))
            workspaces.append(str(record.workspace))

    runs = pd.DataFrame([asdict(s) for s in scores], columns=RUN_COLUMNS)
    runs["workspace"] = workspaces
    return {
        "runs": runs,
        "summary": aggregate(scores),
        "pairs": pair_table(scores),
        "judge_calls": judge_calls,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("--agent", choices=AGENTS, default="oracle")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    result = run_smoke(args.root, seed=args.seed, agent=args.agent)
    runs = result["runs"]
    cols = ["variant_id", "law_status", "nrmse_in", "rel_in", "domain_score", "answer_status", "entity_pred", "entity_truth", "mech_status", "mech_kind_ok", "mech_params_ok"]
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(runs[cols].to_string(index=False))
        print()
        print(result["pairs"].to_string(index=False))
    print(f"\njudge calls: {result['judge_calls']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
