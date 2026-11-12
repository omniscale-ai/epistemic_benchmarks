import json
import os
import subprocess
import sys
from pathlib import Path

import time

import pytest

from abductbench import runner
from abductbench.config import Family, Stage, Truth, VariantConfig
from abductbench.ledger import LOG_NAME
from abductbench.runner import (
    AGENT_MODEL,
    RunRecord,
    _agent_command,
    build_agent_prompt,
    make_run,
    run_agent,
)
from abductbench.tasks import build_task
from abductbench.workspace import make_workspace

FAKE = Path(__file__).with_name("fake_agent.py")
FORBIDDEN_PROMPT_WORDS = ["no_entity", "neutrino", "neptune", "vulcan", "truth", "stage", "seed", "variant", "beta", "orbit"]


def cfg(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1):
    return VariantConfig(family=family, truth=truth, stage=stage, seed=seed, mode=mode)


def fake(mode: str = "write") -> list[str]:
    return [sys.executable, str(FAKE), mode]


def tree_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def listed_at_launch(transcript: Path) -> set[str]:
    return {
        line[len("FILE "):]
        for line in transcript.read_text().splitlines()
        if line.startswith("FILE ")
    }


def test_collects_law_and_answer(tmp_path):
    c = cfg()
    ws = make_workspace(c, tmp_path / "ws")
    rec = run_agent(c, ws, tmp_path / "out", agent_cmd=fake("write"), timeout_s=60)
    dest = tmp_path / "out" / c.variant_id
    assert rec.variant_id == c.variant_id
    assert rec.returncode == 0
    assert rec.timed_out is False
    assert rec.law_path == dest / "law.py"
    assert "def law" in rec.law_path.read_text()
    assert rec.answer_path == dest / "answer.md"
    assert "## Law" in rec.answer_path.read_text()
    assert rec.transcript_path == dest / "transcript.log"
    assert rec.transcript_path.is_file()


def test_timeout_marks_timed_out_and_still_collects_files(tmp_path):
    c = cfg()
    ws = make_workspace(c, tmp_path / "ws")
    rec = run_agent(c, ws, tmp_path / "out", agent_cmd=fake("sleep"), timeout_s=2)
    assert rec.timed_out is True
    assert rec.returncode is not None and rec.returncode != 0
    assert rec.law_path is not None and rec.law_path.is_file()
    assert rec.answer_path is not None and rec.answer_path.is_file()
    # The grandchild started by the agent was in the killed process group.
    child_pid = int((ws / "child.pid").read_text())
    for _ in range(50):
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail("grandchild process survived the timeout")


def test_workspace_has_no_hidden_truth_files(tmp_path):
    c = cfg(mode=1)
    bundle = build_task(c)
    ws = make_workspace(c, tmp_path / "ws")
    rec = run_agent(c, ws, tmp_path / "out", agent_cmd=fake("write"), timeout_s=60)
    # The agent's own launch-time listing (printed by fake_agent before any write).
    assert listed_at_launch(rec.transcript_path) == set(bundle.public_files)
    assert tree_files(ws) >= set(bundle.public_files)
    for hidden in ("_index.json", LOG_NAME, "rubric.json"):
        assert hidden not in listed_at_launch(rec.transcript_path)


def test_mode2_workspace_launch_listing_has_no_ledger_or_index(tmp_path):
    c = cfg(mode=2)
    state = tmp_path / "state"
    ws = make_workspace(c, tmp_path / "ws", state_root=state)
    rec = run_agent(c, ws, tmp_path / "out", agent_cmd=fake("nothing"), timeout_s=60)
    seen = listed_at_launch(rec.transcript_path)
    assert "sim" in seen
    assert "_index.json" not in seen
    assert LOG_NAME not in seen
    assert not any(name.endswith(".jsonl") for name in seen)
    assert set(build_task(c).public_files) <= seen


def test_missing_outputs_recorded_not_raised(tmp_path):
    c = cfg()
    ws = make_workspace(c, tmp_path / "ws")
    rec = run_agent(c, ws, tmp_path / "out", agent_cmd=fake("nothing"), timeout_s=60)
    assert rec.returncode == 0
    assert rec.timed_out is False
    assert rec.law_path is None
    assert rec.answer_path is None
    assert rec.transcript_path.is_file()


def test_helper_modules_copied_and_public_py_modules_too_but_not_listed(tmp_path):
    c = cfg()
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "task.md").write_text("task\n")
    (ws / "public.py").write_text("PUBLIC = 1\n")
    (ws / "changed.py").write_text("CHANGED = False\n")
    rec = run_agent(c, ws, tmp_path / "out", agent_cmd=fake("helper"), timeout_s=60)
    dest = tmp_path / "out" / c.variant_id
    assert (dest / "law.py").is_file()
    assert (dest / "helper_mod.py").is_file()
    assert (dest / "changed.py").is_file()
    # an unchanged public module is copied (law.py may import it) but is not the agent's helper
    assert (dest / "public.py").is_file()
    assert not (dest / "task.md").exists()
    assert sorted(p.name for p in rec.helper_paths) == ["changed.py", "helper_mod.py"]


def test_mode2_ledger_copied_and_outside_workspace(tmp_path):
    c = cfg(mode=2)
    runs = tmp_path / "runs"
    rec = make_run(c, runs, agent_cmd=fake("write"), timeout_s=60)
    dest = runs / c.variant_id
    ledger = dest / "ledger.jsonl"
    assert ledger.is_file()
    first = json.loads(ledger.read_text().splitlines()[0])
    assert first == {"budget": 20}
    assert not (rec.workspace / LOG_NAME).exists()
    assert not any(p.name == LOG_NAME for p in rec.workspace.rglob("*"))
    assert not Path(rec.workspace).resolve().is_relative_to(runs / "_s")
    assert not (runs / "_s").resolve().is_relative_to(rec.workspace.resolve())


def test_run_record_json_roundtrip(tmp_path):
    c = cfg()
    rec = make_run(c, tmp_path / "runs", agent_cmd=fake("nothing"), timeout_s=60)
    record_path = tmp_path / "runs" / c.variant_id / "record.json"
    assert record_path.is_file()
    loaded = RunRecord.load(record_path)
    assert loaded == rec
    assert loaded.law_path is None and loaded.answer_path is None
    assert loaded.returncode == 0 and loaded.timed_out is False
    manual = RunRecord(
        variant_id="x", workspace=tmp_path / "w", law_path=tmp_path / "l.py", answer_path=None,
        transcript_path=tmp_path / "t.log", returncode=None, timed_out=True,
    )
    manual.save(tmp_path / "m.json")
    assert RunRecord.load(tmp_path / "m.json") == manual


def test_agent_command_flags(tmp_path):
    prompt = build_agent_prompt(cfg())
    argv = _agent_command(prompt, tmp_path)
    assert argv[0] == "claude"
    assert argv[argv.index("-p") + 1] == prompt
    assert argv[argv.index("--model") + 1] == AGENT_MODEL == "sonnet"
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in argv
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert "--no-session-persistence" in argv
    assert argv[argv.index("--permission-prompts") + 1] == "none"
    assert argv[argv.index("--permission-mode") + 1] == "acceptEdits"
    assert "--restricted" in argv
    assert argv[argv.index("--tools") + 1] == "Read,Write,Edit,Bash"
    disallowed = argv[argv.index("--disallowedTools") + 1]
    assert "WebSearch" in disallowed and "WebFetch" in disallowed and "Task" in disallowed
    assert "--max-turns" not in argv
    assert runner.MAX_BUDGET_USD is None
    assert "--max-budget-usd" not in argv  # no dollar cap by default
    capped = _agent_command(prompt, tmp_path, max_budget_usd=3)
    assert capped[capped.index("--max-budget-usd") + 1] == "3"
    assert _agent_command(prompt, tmp_path, max_budget_usd=2.5)[-1] == "2.5"
    joined = " ".join(argv)
    assert "dangerously-skip-permissions" not in joined


def test_prompt_identical_across_variants_no_forbidden_words():
    prompts = {
        (f, t, s): build_agent_prompt(cfg(family=f, truth=t, stage=s, seed=3, mode=1))
        for f in Family for t in Truth for s in Stage
    }
    assert len(set(prompts.values())) == 1
    text = next(iter(prompts.values()))
    lowered = text.lower()
    for word in FORBIDDEN_PROMPT_WORDS:
        assert word not in lowered, word
    assert "entity" not in text.replace("ENTITY", "")
    entity_lines = [line for line in text.splitlines() if "ENTITY" in line]
    assert len(entity_lines) == 1 and "ENTITY: yes" in entity_lines[0] and "ENTITY: no" in entity_lines[0]
    for needle in ("## Law", "## Limits", "## Explanation", "law.py", "answer.md", "task.md", "DOMAIN"):
        assert needle in text

    mode2 = build_agent_prompt(cfg(mode=2))
    assert mode2 != text
    assert "use ./sim to order more measurements; see task.md" in mode2
    assert "data tables are in the working directory" in text
    assert text.replace("data tables are in the working directory", "X") == mode2.replace(
        "use ./sim to order more measurements; see task.md", "X"
    )


def test_runner_source_imports_no_evaluator():
    # runner.py itself must not import evaluation code. (The package imports
    # evaluate.oracle through tasks/, which is pre-existing and not executed by the runner.)
    import ast

    tree = ast.parse(Path(runner.__file__).read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    bad = sorted(m for m in modules if m.startswith("abductbench.evaluate") or "judge" in m or "rubric" in m or "oracle" in m)
    assert bad == []


LEAK_WORDS = ["entity", "beta", "orbit", "neutrino", "neptune", "vulcan", "truth"]


@pytest.mark.parametrize("family", list(Family))
@pytest.mark.parametrize("truth", list(Truth))
@pytest.mark.parametrize("stage", list(Stage))
@pytest.mark.parametrize("mode", [1, 2])
def test_launch_paths_and_wrapper_do_not_leak_variant(tmp_path, family, truth, stage, mode):
    import re

    c = cfg(family=family, truth=truth, stage=stage, seed=3, mode=mode)
    runs = tmp_path / "runs"
    rec = make_run(c, runs, agent_cmd=fake("nothing"), timeout_s=60)
    ws = rec.workspace.resolve()
    paths = list(ws.relative_to(runs.resolve()).parts)
    texts = []
    # nothing but the workspace itself is in its parent (no sibling variants, no index)
    assert [p.name for p in ws.parent.iterdir()] == [ws.name]
    if mode == 2:
        wrapper = (ws / "sim").read_text()
        # only the sim token and the state root are variant-neutral by construction
        texts.append(wrapper.split("PYTHONPATH=")[0] + wrapper.split("--token", 1)[1])
        state = Path(re.search(r"--state-root (\S+)", wrapper).group(1).strip("'"))
        paths += list(state.relative_to(runs.resolve()).parts)
    for text in paths + texts:
        low = text.lower()
        for w in LEAK_WORDS + [c.variant_id]:
            assert w.lower() not in low, (w, text)
        assert not re.search(r"-[abcd]-s\d+|-s\d+-m[12]", low)
    record = json.loads((runs / c.variant_id / "record.json").read_text())
    assert record["variant_id"] == c.variant_id


def test_prompt_states_evaluator_limits():
    text = build_agent_prompt(cfg())
    assert "twice" in text and "20 seconds" in text
    assert "numpy and scipy" in text and "helper modules" in text
    assert build_agent_prompt(cfg(mode=1)).split("Note:")[0] == build_agent_prompt(cfg(mode=2)).split("Note:")[0]


def test_agent_environ_prepends_agent_venv_and_drops_python_vars(tmp_path):
    from abductbench.runner import _agent_environ

    venv = tmp_path / "av"
    base = {"PATH": "/usr/bin", "PYTHONPATH": "/repo/src", "VIRTUAL_ENV": "/repo/.venv", "PYTHONHOME": "/x"}
    env = _agent_environ(base, venv)
    assert env["PATH"].split(os.pathsep)[0] == str(venv / "bin")
    assert env["VIRTUAL_ENV"] == str(venv)
    assert "PYTHONPATH" not in env and "PYTHONHOME" not in env
    assert env["ABDUCTBENCH_AGENT"] == "1"
    bare = _agent_environ(base, None)
    assert "VIRTUAL_ENV" not in bare and bare["PATH"] == "/usr/bin"


def test_launch_uses_agent_env_on_path(tmp_path):
    venv = tmp_path / "av"
    (venv / "bin").mkdir(parents=True)
    ws = tmp_path / "ws"
    ws.mkdir()
    script = tmp_path / "probe.py"
    script.write_text(
        "import os, pathlib\n"
        "pathlib.Path('probe.txt').write_text(os.environ['PATH'].split(os.pathsep)[0] + '|' + os.environ.get('PYTHONPATH', 'none'))\n"
    )
    from abductbench.runner import _launch

    rc, timed_out = _launch([sys.executable, str(script)], ws, tmp_path / "t.log", 30, venv)
    assert rc == 0 and not timed_out
    first, pp = (ws / "probe.txt").read_text().split("|")
    assert first == str(venv / "bin") and pp == "none"
