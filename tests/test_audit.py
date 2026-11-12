import hashlib
import subprocess
from pathlib import Path

import pytest

from abductbench import audit
from abductbench.audit import (
    AUDIT_MODEL,
    audit_all,
    audit_recognizability,
    build_audit_prompt,
    _audit_command,
)
from abductbench.config import Family, Stage, Truth, VariantConfig
from abductbench.workspace import make_workspace


def cfg(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.OBFUSCATED, seed=0, mode=1):
    return VariantConfig(family=family, truth=truth, stage=stage, seed=seed, mode=mode)


def all_16_configs():
    return [
        cfg(family=f, truth=t, stage=s, seed=0, mode=1)
        for f in Family
        for t in Truth
        for s in Stage
    ]


class Recorder:
    """Stub `ask` that records every prompt and returns a fixed reply."""

    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.reply


def test_recognized_when_name_in_reply(tmp_path):
    c = cfg(family=Family.BETA, stage=Stage.HISTORICAL)
    ws = make_workspace(c, tmp_path)
    ask = Recorder("This looks like the neutrino hypothesis of Pauli, from 1930.")

    result = audit_recognizability(c, ws, ask=ask)

    assert result.recognized is True
    assert result.answer == ask.reply
    assert "neutrino" in result.matched
    assert "Pauli" in result.matched
    assert len(ask.prompts) == 1


def test_not_recognized_otherwise(tmp_path):
    c = cfg(family=Family.BETA, stage=Stage.OBFUSCATED)
    ws = make_workspace(c, tmp_path)

    for reply in ["none", "None.", "No", "I don't recognize this task.", "", None]:
        result = audit_recognizability(c, ws, ask=Recorder(reply))
        assert result.recognized is False, reply
        assert result.matched == [], reply
        assert result.answer == ("" if reply is None else reply)


def test_prompt_excludes_variant_id(tmp_path):
    c = cfg(family=Family.BETA, truth=Truth.NO_ENTITY, stage=Stage.OBFUSCATED, seed=0, mode=1)
    ws = make_workspace(c, tmp_path)
    ask = Recorder("none")

    audit_recognizability(c, ws, ask=ask)

    prompt = ask.prompts[0].lower()
    digest = hashlib.sha1((c.variant_id + "abductbench-workspace-v1").encode("utf-8")).hexdigest()
    for forbidden in [
        c.variant_id,
        "no_entity",
        "truth",
        "entity",
        ws.name,
        digest[:12],
        "s0-m1",
    ]:
        assert forbidden.lower() not in prompt, forbidden
    # The task text itself is still there.
    assert (ws / "task.md").read_text().strip()[:80] in ask.prompts[0]


def test_names_present_in_prompt_do_not_count(tmp_path):
    c = cfg(family=Family.ORBIT, truth=Truth.ENTITY, stage=Stage.HISTORICAL)
    ws = make_workspace(c, tmp_path)
    task_text = (ws / "task.md").read_text()
    assert "Uranus" in task_text  # guard: the test is only meaningful if the name is in the task

    only_echo = audit_recognizability(c, ws, ask=Recorder("It looks like Uranus to me."))
    assert only_echo.recognized is False
    assert only_echo.matched == []

    new_name = audit_recognizability(c, ws, ask=Recorder("Uranus, and the work of Le Verrier."))
    assert new_name.recognized is True
    assert new_name.matched == ["Le Verrier"]


def test_audit_command_flags():
    argv = _audit_command("Which discovery is this?")

    assert argv[0] == "claude"
    assert argv[argv.index("-p") + 1] == "Which discovery is this?"
    assert argv[argv.index("--model") + 1] == AUDIT_MODEL == "sonnet"
    assert argv[argv.index("--output-format") + 1] == "text"
    assert argv[argv.index("--tools") + 1] == ""
    assert "--no-session-persistence" in argv
    assert "--disable-slash-commands" in argv
    assert "--system-prompt" in argv
    joined = " ".join(argv)
    assert "WebSearch" not in joined and "WebFetch" not in joined


def test_audit_all_keys_and_runs_all_16_stub(tmp_path, monkeypatch):
    def no_cli(*args, **kwargs):
        raise AssertionError("the real CLI must not be invoked in tests")

    monkeypatch.setattr(audit.subprocess, "run", no_cli)
    configs = all_16_configs()
    ask = Recorder("none")

    results = audit_all(configs, tmp_path, ask=ask)

    assert set(results) == {c.variant_id for c in configs}
    assert len(results) == 16
    assert len(ask.prompts) == 16
    assert all(r.recognized is False for r in results.values())


def test_build_audit_prompt_contains_task_and_snippets():
    prompt = build_audit_prompt("Task body text.", {"events.csv": "a,b\n1,2"})

    assert "Task body text." in prompt
    assert "events.csv" in prompt
    assert "a,b\n1,2" in prompt
    assert "none" in prompt
    assert "Which well-known historical physics discovery" in prompt
