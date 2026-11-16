"""End-to-end episode with a fake agent through the socket client; isolation and run bookkeeping.

No real LLM is called: ``agent="claude"`` is only exercised with ``dry_run=True``.
"""

import json
from pathlib import Path

import pytest

from abductbench.episode import modelrun as mr
from abductbench.episode.agent import run_episode
from abductbench.episode.metrics import evaluate_session
from abductbench.episode.protocol import load_session
from abductbench.episode.world import EpisodeConfig

FAKE = (Path(__file__).parent / "episode_fake_agent.py").read_text()
needs_bwrap = pytest.mark.skipif(not mr.bwrap_available(), reason="bwrap not installed")


def _check_run(run_dir: Path, isolation: str):
    run = json.loads((run_dir / "run.json").read_text())
    assert run["episode_closed"] and run["measurements"] == 2 and not run["timed_out"]
    man = json.loads((run_dir / "manifest.json").read_text())
    assert man["isolation"] == isolation and man["config"]["world_seed"] == 1 and man["code"]["git_commit"]
    notes = (run_dir / "workspace_final" / "notes.md").read_text()
    assert "measure" in notes and '"accepted": true' in notes and '"closed": true' in notes
    assert len(list((run_dir / "workspace_final" / "data").glob("measurement_*_calorimeter.csv"))) == 2
    s = load_session(run_dir / "state", allow_unsandboxed=not mr.bwrap_available())
    res = evaluate_session(s, n=400)
    assert res["final"]["current_class"] in ("carrier", "loss", "other")
    assert len(res["steps"]) == 2 and "forecast" in res["steps"][0]
    return notes


@needs_bwrap
def test_fake_agent_isolated(tmp_path):
    runs = tmp_path / "runs"
    cfg = EpisodeConfig(1, "loss")
    probe = str(Path(__file__).resolve().parents[1])  # the repository must be invisible
    run_dir = run_episode(cfg, runs, agent="custom", isolation="bwrap", timeout_s=300,
                          inner_argv=["python3", "fake_agent.py", probe, str(runs)],
                          agent_files={"fake_agent.py": FAKE})
    notes = _check_run(run_dir, "bwrap")
    assert "READABLE" not in notes, notes


def test_fake_agent_unisolated_dry_mode_and_no_overwrite(tmp_path):
    runs = tmp_path / "runs"
    cfg = EpisodeConfig(1, "carrier")
    dirs = [run_episode(cfg, runs, agent="custom", isolation="none", timeout_s=300,
                        inner_argv=["python3", "fake_agent.py"], agent_files={"fake_agent.py": FAKE})
            for _ in range(2)]
    assert dirs[0] != dirs[1]
    for d in dirs:
        _check_run(d, "none")


@needs_bwrap
def test_claude_dry_run_is_isolated_and_never_launched(tmp_path):
    argv = run_episode(EpisodeConfig(0, "carrier"), tmp_path / "runs", agent="claude", isolation="bwrap",
                       model="sonnet", max_budget_usd=2.0, dry_run=True)
    assert argv[0] == "bwrap" and "--unshare-all" in argv and "/work" in argv
    repo = str(Path(__file__).resolve().parents[1])
    mounted = [argv[i + 1] for i, a in enumerate(argv) if a in ("--bind", "--ro-bind")]
    assert not any(m == repo or m.startswith(repo + "/") and ".agent-venv" not in m for m in mounted)
    assert "--max-budget-usd" in argv and "/opt/claude/claude" in argv


def test_claude_refused_without_isolation(tmp_path):
    with pytest.raises(RuntimeError, match="isolation"):
        run_episode(EpisodeConfig(0, "carrier"), tmp_path / "runs", agent="claude", isolation="none")
