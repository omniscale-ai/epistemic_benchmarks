"""Command line for the episode track.

    python -m abductbench.episode.cli baselines --seeds 0-9 --out results/episode/baselines-<tag>
    python -m abductbench.episode.cli run --world-seed 0 --mechanism carrier --runs-root runs_episode [--dry-run]
    python -m abductbench.episode.cli evaluate runs_episode/<run_id>
    python -m abductbench.episode.cli sandbox-check

``run`` without ``--dry-run`` launches a real, paid agent. It is never called by tests.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from abductbench.episode import baselines as bl
from abductbench.episode.metrics import evaluate_session
from abductbench.episode.protocol import load_session
from abductbench.episode.world import EpisodeConfig


def _seeds(text: str) -> list[int]:
    if "-" in text:
        a, b = text.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in text.split(",")]


def _fmt(x) -> str:
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.3g}"
    return str(x)


def summary_markdown(summary: list[dict], heur: dict, post: list[dict]) -> str:
    cols = ["policy", "condition", "mechanism", "n", "categories", "final_class_correct", "final_P_true",
            "final_ref_P_true", "overconfident_final", "initial_fit_ed", "check_ed", "check_floor", "check_opposite",
            "design_info_ref_step1", "design_frac_menu_max_step1", "forecast_ed_current_step1", "revision_step1",
            "consistent_current"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in summary:
        lines.append("| " + " | ".join(_fmt(r.get(c)) for c in cols) + " |")
    lines += ["", "Single-feature heuristic on the initial spectrum (threshold fitted on train seeds 100-299, test 0-99):", ""]
    for k, v in heur.items():
        lines.append(f"- {k}: train acc {v['train_acc']:.3f}, test acc {v['test_acc']:.3f}, test AUC {v['test_auc']:.3f}")
    import numpy as np

    for mech in ("carrier", "loss"):
        ps = np.array([r["ref_P_carrier"] for r in post if r["mechanism"] == mech])
        ds = np.array([r["ref_dll"] for r in post if r["mechanism"] == mech])
        lines.append(f"- initial data, {mech} worlds (n={ps.size}): max log-LR carrier-loss median {np.median(ds):+.2f}, "
                     f"|dll|<3 (ambiguous): {np.mean(np.abs(ds) < 3):.2f}, dll>=3: {np.mean(ds >= 3):.2f}, "
                     f"dll<=-3: {np.mean(ds <= -3):.2f}; AIC P(carrier) median {np.median(ps):.2f}")
    return "\n".join(lines) + "\n"


def cmd_baselines(a) -> int:
    seeds = _seeds(a.seeds)
    out = Path(a.out)
    t0 = time.time()
    rows = bl.run_table(list(bl.POLICIES), seeds, ("ambiguous",), processes=a.processes)
    rows += bl.run_table(["reference_adaptive", "no_data", "textbook"], seeds, ("no_measurement", "no_data"),
                         processes=a.processes)
    rows += bl.run_table(["reference_adaptive", "reference_repeat"], seeds, ("t0_sufficient",), processes=a.processes)
    summ = bl.summarise(rows)
    heur = bl.heuristic_study(processes=a.processes)
    post = bl.posterior_study(range(0, a.post_seeds), processes=a.processes)
    bl.save(rows, summ, out)
    (out / "heuristic.json").write_text(json.dumps(heur, indent=1))
    (out / "posterior_initial.json").write_text(json.dumps(post, indent=1))
    (out / "summary.md").write_text(summary_markdown(summ, heur, post))
    (out / "manifest.json").write_text(json.dumps({"seeds": seeds, "seconds": time.time() - t0,
                                                   "code": __import__("abductbench.episode.agent", fromlist=["x"]).code_version()},
                                                  indent=1))
    print((out / "summary.md").read_text())
    return 0


def cmd_run(a) -> int:
    from abductbench.episode.agent import run_episode

    cfg = EpisodeConfig(world_seed=a.world_seed, mechanism=a.mechanism, obs_seed=a.obs_seed, agent_rep=a.rep,
                        condition=a.condition, menu=a.menu, family=a.family, tools=a.tools)
    res = run_episode(cfg, Path(a.runs_root), agent="claude", isolation="bwrap", timeout_s=a.timeout,
                      model=a.model, max_budget_usd=a.max_budget_usd, dry_run=a.dry_run)
    if a.dry_run:
        print(json.dumps({"argv": res}, indent=1))
    else:
        print(res)
    return 0


ANCHOR_POLICIES = ("reference_adaptive", "reference_repeat", "phenomenological", "textbook", "no_data", "truth_fed")


def episode_report(res: dict, anchors: dict | None = None) -> str:
    """Human-readable episode report: the chain A -> B -> C -> D with each link's number."""
    L = []
    c = res["config"]
    inst = res["instance"]
    L.append(f"world_seed={c['world_seed']} truth={res['truth_mechanism']} condition={c['condition']} menu={c['menu']}")
    L.append(f"A  initial data: category={inst['category']} (max log-LR carrier-loss = {_fmt(inst['ref_dll_initial'])}, "
             f"AIC P(carrier) = {_fmt(inst['ref_P_carrier_initial'])})")
    for i, st in enumerate(res["steps"], 1):
        u = st["uncertainty_before"]
        L.append(f"B{i} classes={st['classes']} alt differs in class={st['alternative_differs_in_class']} "
                 f"agent P(carrier)={_fmt(u['agent_P_carrier'])} ref={_fmt(u['ref_P_carrier'])} overconfident={u['overconfident']}")
        L.append(f"   measurement={st['measurement']} info own={_fmt(st['design_info_own'])} ref={_fmt(st['design_info_ref'])} "
                 f"(fraction of best menu option {_fmt(st['design_info_ref_frac_of_menu_max'])})")
        if "forecast" in st:
            f = st["forecast"]
            L.append(f"C{i} forecast ED current={_fmt(f['ed_current'])} alternative={_fmt(f['ed_alternative'])} "
                     f"logBF(alt:cur)={_fmt(f['logbf_alt_vs_current'])} +- {_fmt(f['logbf_forecast_noise_sd'])}"
                     + (f" -> {st['revision']['verdict']} ({st['revision']['class_before']} -> {st['revision']['class_after']})"
                        if "revision" in st else ""))
    fin = res.get("final")
    if not fin:
        L.append("D  no final answer")
        return "\n".join(L) + "\n"
    u = fin["uncertainty"]
    L.append(f"D  final class={fin['current_class']} agent P(carrier)={_fmt(u['agent_P_carrier'])} ref={_fmt(u['ref_P_carrier'])} "
             f"overconfident={u['overconfident']} current model consistent with declaration={fin.get('current_consistent')}")
    L.append(f"   hidden check ED={_fmt(fin.get('check_ed'))} (truth floor {_fmt(fin['check_ed_floor_truth'])}, "
             f"opposite mechanism {_fmt(fin['check_ed_opposite_mechanism'])}); initial fit ED={_fmt(fin.get('initial_fit_ed'))}")
    if anchors:
        L.append("   same world, local anchors: " + ", ".join(f"{k} {_fmt(v)}" for k, v in anchors.items()))
    return "\n".join(L) + "\n"


def orbit_report(res: dict) -> str:
    L = []
    c, inst = res["config"], res["instance"]
    L.append(f"orbit world_seed={c['world_seed']} truth={res['truth_mechanism']} condition={c['condition']} menu={c['menu']}")
    L.append(f"A  category={inst['category']} (max log-LR body-force = {_fmt(inst['ref_dll_initial'])})")
    for i, st in enumerate(res["steps"], 1):
        u = st["uncertainty_before"]
        L.append(f"B{i} classes={st['classes']} agent P(body)={_fmt(u['agent_P_body'])} ref={_fmt(u['ref_P_body'])} "
                 f"overconfident={u['overconfident']}")
        L.append(f"   measurement={st['measurement']} info own={_fmt(st['design_info_own'])} ref={_fmt(st['design_info_ref'])} "
                 f"(fraction of best {_fmt(st['design_info_ref_frac_of_menu_max'])})")
        if "forecast" in st:
            f = st["forecast"]
            L.append(f"C{i} logBF(alt:cur)={_fmt(f['logbf_alt_vs_current'])} +- {_fmt(f['logbf_forecast_noise_sd'])}"
                     + (f" -> {st['revision']['verdict']} (agent class {st['revision']['class_after']}, reference prefers "
                        f"{st['revision']['ref_class_after']})" if "revision" in st else ""))
    fin = res.get("final")
    if fin:
        u = fin["uncertainty"]
        L.append(f"D  final class={fin['current_class']} agent P(body)={_fmt(u['agent_P_body'])} ref={_fmt(u['ref_P_body'])} "
                 f"consistent={fin.get('current_consistent')}")
        L.append(f"   check ED={_fmt(fin.get('check_ed'))} blocks={ {k: round(v, 3) for k, v in (fin.get('check_blocks') or {}).items()} } "
                 f"floor={_fmt(fin['check_ed_floor_truth'])} opposite={_fmt(fin['check_ed_opposite_mechanism'])}")
        if res.get("anchors_check_ed"):
            L.append("   anchors: " + ", ".join(f"{k} {_fmt(v)}" for k, v in res["anchors_check_ed"].items()))
    return "\n".join(L) + "\n"


def cmd_evaluate(a) -> int:
    run_dir = Path(a.run_dir)
    s = load_session(run_dir / "state")
    if s.cfg.family == "orbit":
        from abductbench.episode import orbitbaselines as obl
        from abductbench.episode.orbitmetrics import evaluate_orbit_session

        res = evaluate_orbit_session(s)
        if a.anchors:
            res["anchors_check_ed"] = {}
            for p in ("reference_adaptive", "reference_repeat", "phenomenological", "textbook", "no_data", "truth_fed"):
                try:
                    res["anchors_check_ed"][p] = obl.run_one((p, s.cfg.to_dict()))["final"].get("check_ed")
                except Exception as e:
                    res["anchors_check_ed"][p] = None
                    res.setdefault("anchor_errors", {})[p] = f"{type(e).__name__}: {e}"[:200]
        stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        out = run_dir / f"evaluation-{stamp}.json"
        out.write_text(json.dumps(res, indent=1, default=float))
        rep = orbit_report(res)
        (run_dir / f"report-{stamp}.txt").write_text(rep)
        print(rep)
        print(out)
        return 0
    res = evaluate_session(s)
    if a.anchors:
        anchors = {}
        for p in ANCHOR_POLICIES:
            try:  # some anchors need initial data (e.g. phenomenological under condition no_data)
                anchors[p] = bl.run_one((p, s.cfg.to_dict()))["final"].get("check_ed")
            except Exception as e:
                anchors[p] = None
                res.setdefault("anchor_errors", {})[p] = f"{type(e).__name__}: {e}"[:200]
        res["anchors_check_ed"] = anchors
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    out = run_dir / f"evaluation-{stamp}.json"
    out.write_text(json.dumps(res, indent=1, default=float))
    rep = episode_report(res, res.get("anchors_check_ed"))
    (run_dir / f"report-{stamp}.txt").write_text(rep)
    print(rep)
    print(out)
    return 0


def _latest_eval(run_dir: Path) -> dict | None:
    evs = sorted(run_dir.glob("evaluation-*.json"))
    return json.loads(evs[-1].read_text()) if evs else None


def _orbit_row(d: Path, res: dict) -> dict:
    import re

    c, fin, steps = res["config"], res.get("final") or {}, res.get("steps") or []
    tr = (d / "transcript.jsonl").read_text(errors="replace") if (d / "transcript.jsonl").exists() else ""
    costs = re.findall(r'"total_cost_usd":([0-9.]+)', tr)
    anchors = res.get("anchors_check_ed") or {}
    if not anchors:
        for ev_path in sorted(d.glob("evaluation-*.json"), reverse=True):
            anchors = json.loads(ev_path.read_text()).get("anchors_check_ed") or {}
            if anchors:
                break
    u = fin.get("uncertainty") or {}
    return {
        "run": d.name, "status": "ok", "family": "orbit", "world_seed": c["world_seed"], "truth": c["mechanism"],
        "condition": c["condition"], "menu": c["menu"], "tools": c.get("tools", False), "rep": c["agent_rep"],
        "category": res["instance"]["category"], "measurements": [st["measurement"] for st in steps],
        "own_info": [st.get("design_info_own") for st in steps], "ref_info": [st.get("design_info_ref") for st in steps],
        "frac_best": [st.get("design_info_ref_frac_of_menu_max") for st in steps],
        "B1_P_body": steps[0]["uncertainty_before"]["agent_P_body"] if steps else None,
        "revisions": [st.get("revision", {}).get("verdict") for st in steps],
        "agrees_with_reference": [st.get("revision", {}).get("agrees_with_reference") for st in steps],
        "overconfident_any": any(st["uncertainty_before"]["overconfident"] for st in steps) or bool(u.get("overconfident")),
        "final_class": fin.get("current_class"), "final_P_true": u.get(f"agent_P_{c['mechanism']}"),
        "ref_P_true": (u.get("ref_P_body") if c["mechanism"] == "body" else (1 - u["ref_P_body"]) if u.get("ref_P_body") is not None else None),
        "consistent": fin.get("current_consistent"), "declared_body": fin.get("declared_body"),
        "declared_force": fin.get("declared_force"), "truth_params": fin.get("truth_params"),
        "check_ed": fin.get("check_ed"), "check_blocks": fin.get("check_blocks"), "floor": fin.get("check_ed_floor_truth"),
        "opposite": fin.get("check_ed_opposite_mechanism"), "ref": anchors.get("reference_adaptive"),
        "textbook": anchors.get("textbook"), "no_data": anchors.get("no_data"),
        "cost_usd": float(costs[-1]) if costs else None,
    }


def collect_runs(runs_root: Path) -> list[dict]:
    """One row per finished, evaluated run (the most recent evaluation of each run)."""
    from abductbench.episode.world import World

    rows = []
    for d in sorted(Path(runs_root).glob("2026*")):
        if not (d / "run.json").exists():
            continue
        run = json.loads((d / "run.json").read_text())
        res = _latest_eval(d)
        if res is None or not run.get("episode_closed"):
            rows.append({"run": d.name, "status": "incomplete_or_unevaluated"})
            continue
        c = res["config"]
        fin = res.get("final") or {}
        steps = res.get("steps") or []
        if c.get("family") == "orbit":
            rows.append(_orbit_row(d, res))
            continue
        w = World(EpisodeConfig.from_dict(c))
        cur = None
        if (d / "state" / "log.jsonl").exists():
            for line in (d / "state" / "log.jsonl").read_text().splitlines():
                ev = json.loads(line)
                if ev["event"] == "final":
                    cur = max(ev["hypotheses"], key=lambda h: (h["credence"], h["role"] == "current"))
        mech = (cur or {}).get("mechanism") or {}
        tr = (d / "transcript.jsonl").read_text(errors="replace") if (d / "transcript.jsonl").exists() else ""
        import re
        costs = re.findall(r'"total_cost_usd":([0-9.]+)', tr)
        anchors = res.get("anchors_check_ed") or {}
        if not anchors:  # anchors depend only on the world; take them from an earlier evaluation if needed
            for ev_path in sorted(d.glob("evaluation-*.json"), reverse=True):
                anchors = json.loads(ev_path.read_text()).get("anchors_check_ed") or {}
                if anchors:
                    break
        rows.append({
            "run": d.name, "status": "ok", "world_seed": c["world_seed"], "truth": c["mechanism"],
            "condition": c["condition"], "menu": c["menu"], "rep": c["agent_rep"],
            "category": res["instance"]["category"],
            "true_mx_over_Q": w.sh.m_x if c["mechanism"] == "carrier" else None,
            "agent_mass_over_Q": (mech.get("mass") / w.Q) if mech.get("kind") == "carrier" else None,
            "behavioural_mass_over_Q": fin.get("current_behavioural_mass_over_Q"),
            "ref_mass_over_Q": None,
            "first_measurement": steps[0]["measurement"]["type"] if steps else None,
            "first_design_frac": steps[0].get("design_info_ref_frac_of_menu_max") if steps else None,
            "B1_P_carrier": steps[0]["uncertainty_before"]["agent_P_carrier"] if steps else None,
            "B1_alt_differs": steps[0]["alternative_differs_in_class"] if steps else None,
            "revisions": [s.get("revision", {}).get("verdict") for s in steps],
            "final_class": fin.get("current_class"),
            "final_P_true": (fin.get("uncertainty") or {}).get(f"agent_P_{c['mechanism']}"),
            "overconfident_any": any(s["uncertainty_before"]["overconfident"] for s in steps)
                                 or bool((fin.get("uncertainty") or {}).get("overconfident")),
            "consistent": fin.get("current_consistent"),
            "check_ed": fin.get("check_ed"), "floor": fin.get("check_ed_floor_truth"),
            "check_ed_energy": (fin.get("check_parts") or {}).get("ed_energy"),
            "check_ed_recoil": (fin.get("check_parts") or {}).get("ed_recoil"),
            "corr_agent": (fin.get("check_parts") or {}).get("corr_agent"),
            "corr_truth": (fin.get("check_parts") or {}).get("corr_truth"),
            "opposite": fin.get("check_ed_opposite_mechanism"),
            "ref": anchors.get("reference_adaptive"), "textbook": anchors.get("textbook"),
            "cost_usd": float(costs[-1]) if costs else None,
        })
    return rows


def cmd_aggregate(a) -> int:
    rows = collect_runs(Path(a.runs_root))
    ok = [r for r in rows if r["status"] == "ok"]
    cols = ["run", "world_seed", "truth", "condition", "menu", "rep", "category", "true_mx_over_Q", "agent_mass_over_Q", "behavioural_mass_over_Q",
            "first_measurement", "B1_P_carrier", "revisions", "final_class", "final_P_true", "overconfident_any",
            "consistent", "check_ed", "ref", "textbook", "floor", "cost_usd"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in ok:
        lines.append("| " + " | ".join(_fmt(r.get(k)) for k in cols) + " |")
    text = "\n".join(lines) + "\n"
    skipped = [r["run"] for r in rows if r["status"] != "ok"]
    text += f"\nNot included (incomplete, failed or unevaluated): {', '.join(skipped) or 'none'}\n"
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    out.with_suffix(".json").write_text(json.dumps(rows, indent=1, default=float))
    print(text)
    return 0


def cmd_sandbox_check(_a) -> int:
    """Free checks: claude starts inside the sandbox (``--version`` only) and host paths are hidden."""
    from abductbench.episode.agent import RunPaths, bwrap_argv

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for d in ("work", "sock", "home"):
            (tmp / d).mkdir()
        p = RunPaths("check", tmp, tmp, tmp / "work", tmp / "sock", tmp / "home")
        claude = shutil.which("claude")
        repo = str(Path(__file__).resolve().parents[3])
        probe = ["/bin/sh", "-c", f"test -e {repo} && echo REPO_VISIBLE || echo repo_hidden; "
                                  "test -e /home/mark && echo HOME_DIR_PRESENT || echo home_dir_absent; "
                                  f"ls {Path.home()}/.claude/projects >/dev/null 2>&1 && echo PROJECTS_VISIBLE || echo projects_hidden; "
                                  "python3 -c 'import numpy, scipy, sys; print(\"numpy ok\", sys.prefix)'"]
        print(subprocess.run(bwrap_argv(p, probe), capture_output=True, text=True).stdout)
        if claude:
            r = subprocess.run(bwrap_argv(p, ["/opt/claude/claude", "--version"], Path(claude)),
                               capture_output=True, text=True, timeout=60)
            print("claude --version inside sandbox:", r.returncode, r.stdout.strip(), r.stderr.strip()[:300])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="abductbench.episode.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("baselines")
    b.add_argument("--seeds", default="0-9")
    b.add_argument("--post-seeds", type=int, default=40)
    b.add_argument("--processes", type=int, default=8)
    b.add_argument("--out", required=True)
    r = sub.add_parser("run")
    r.add_argument("--world-seed", type=int, required=True)
    r.add_argument("--mechanism", choices=("carrier", "loss", "body", "force"), required=True)
    r.add_argument("--family", choices=("decay", "orbit"), default="decay")
    r.add_argument("--tools", action="store_true", help="orbit + menu: ship exact simulators of both hypothesis kinds")
    r.add_argument("--obs-seed", type=int, default=0)
    r.add_argument("--rep", type=int, default=0)
    r.add_argument("--condition", default="ambiguous")
    r.add_argument("--menu", action=argparse.BooleanOptionalAction, default=True)
    r.add_argument("--runs-root", default="runs_episode")
    r.add_argument("--model", default="sonnet")
    r.add_argument("--timeout", type=int, default=3600)
    r.add_argument("--max-budget-usd", type=float, default=None)
    r.add_argument("--dry-run", action="store_true")
    e = sub.add_parser("evaluate")
    e.add_argument("run_dir")
    e.add_argument("--anchors", action=argparse.BooleanOptionalAction, default=True,
                   help="also run local baselines on the same world for comparison")
    g = sub.add_parser("aggregate")
    g.add_argument("--runs-root", default="runs_episode")
    g.add_argument("--out", default="results/episode/runs_summary.md")
    sub.add_parser("sandbox-check")
    a = ap.parse_args(argv)
    return {"baselines": cmd_baselines, "run": cmd_run, "evaluate": cmd_evaluate,
            "sandbox-check": cmd_sandbox_check, "aggregate": cmd_aggregate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
