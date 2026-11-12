"""Run one agent on one variant workspace and collect its answer files.

The runner only builds nothing new and scores nothing: it launches the agent in the
workspace, waits (or kills it at the timeout), and copies ``law.py``, ``answer.md``,
new/changed helper modules at the workspace root, the transcript and (in ``make_run``)
the mode-2 ledger into ``out_dir/<variant_id>/``. It never imports or runs the evaluator,
oracle, rubric or judge; evaluation is a separate step over the saved files.

Default agent: the Claude Code CLI in print mode (``_agent_command``). Flags were checked
against ``claude --help`` (Claude Code CLI of this environment). Choices:

- ``--restricted --tools Read,Write,Edit,Bash``: restricted mode removes the code-running
  tools (Bash) unless ``--tools`` names them, ignores user/project/local settings, and
  confines the file tools to the working directory (plus ``--add-dir``).
- ``--allowedTools Read,Write,Edit,Bash`` and ``--permission-mode acceptEdits`` so that
  nothing blocks on a prompt; ``--permission-prompts none`` makes anything that would prompt
  be denied instead of hanging.
- ``--disallowedTools WebSearch,WebFetch,Task``: no network tools, no subagents.
- ``--setting-sources ""``, ``--disable-slash-commands``, ``--no-session-persistence``.
- No turn cap: ``claude --help`` lists no ``--max-turns`` option, so the only limit is the
  wall-clock ``timeout_s``. Nothing bypasses permissions (no ``--dangerously-skip-permissions``).
- The output is ``stream-json`` (requires ``--verbose``) and is stored as the transcript.

Runtime behaviour of these flags against a live API was NOT exercised here (tests use a
fake agent and never call the real CLI). Verify with a dry run before a serious evaluation.

Isolation limits (best effort, not hard isolation):

- The agent runs as the same OS user as the benchmark. Bash is allowed, so it can read the
  ``src`` tree, the ``state_root`` of the mode-2 simulator and any other file this user can
  read. The mode-2 ``sim`` wrapper reveals the ``state_root`` path, and the package path is
  visible in the interpreter path. Nothing here prevents that.
- The workspace holds only the public task files, but the tool permissions above only stop
  the file tools and the web tools, not Bash.
- For serious evaluation, run the agent in a container or under a separate OS user with
  no read access to the repository or to ``runs_root/_state``.

Output paths: ``run_agent`` replaces ``out_dir/<variant_id>/`` on each call.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from abductbench.config import VariantConfig
from abductbench.ledger import LOG_NAME
from abductbench.workspace import DEFAULT_BUDGET, INDEX_NAME, make_workspace

AGENT_MODEL = "sonnet"
AGENT_TIMEOUT_S = 3600
AGENT_ALLOWED_TOOLS = "Read,Write,Edit,Bash"
AGENT_DISALLOWED_TOOLS = "WebSearch,WebFetch,Task"

LAW_NAME = "law.py"
ANSWER_NAME = "answer.md"
TRANSCRIPT_NAME = "transcript.log"
LEDGER_COPY_NAME = "ledger.jsonl"
RECORD_NAME = "record.json"

MODE_NOTES = {
    1: "Note: data tables are in the working directory.",
    2: "Note: use ./sim to order more measurements; see task.md.",
}

_PROMPT_BODY = """You are solving a scientific inference task. Everything you need is in the current directory.

Steps:
1. Read task.md. It describes the observations, the required signature of law(...) and the keys of DOMAIN.
2. Write law.py. It must define law(...) with exactly the signature given in task.md, and a module-level dict DOMAIN with exactly the keys named in task.md; every DOMAIN value is a (lo, hi) tuple of numbers. law.py must be deterministic, must not read files or use the network, and must run quickly. It may import helper modules that you save in this directory.
3. Write answer.md with exactly three markdown sections, in this order: "## Law", "## Limits", "## Explanation".
   - Law: the law in words, referring to law.py.
   - Limits: where the law applies and where it does not.
   - Explanation: the mechanism in plain language; why this mechanism and not the alternatives; the alternatives you considered and why you rejected each; and which observation or experiment would distinguish your explanation from them.
4. Include exactly one machine-readable line in answer.md: "ENTITY: yes" if your best explanation requires a new physical body or particle that is absent from the given T0 model, otherwise "ENTITY: no".
5. Work only inside the current directory. Do not access other locations.
6. When both files are saved, stop.
"""


def build_agent_prompt(cfg: VariantConfig) -> str:
    """Prompt for the agent. Identical for every variant except the one-line mode note."""
    if cfg.mode not in MODE_NOTES:
        raise ValueError(f"unknown mode: {cfg.mode!r}")
    return _PROMPT_BODY + "\n" + MODE_NOTES[cfg.mode] + "\n"


def _agent_command(prompt: str, workspace: Path) -> list[str]:
    """argv for one non-interactive agent run (cwd is set by the caller). See module docstring."""
    return [
        "claude",
        "-p",
        prompt,
        "--model",
        AGENT_MODEL,
        "--output-format",
        "stream-json",
        "--verbose",
        "--restricted",
        "--tools",
        AGENT_ALLOWED_TOOLS,
        "--allowedTools",
        AGENT_ALLOWED_TOOLS,
        "--disallowedTools",
        AGENT_DISALLOWED_TOOLS,
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--add-dir",
        str(Path(workspace).resolve()),
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--disable-slash-commands",
    ]


@dataclass
class RunRecord:
    variant_id: str
    workspace: Path
    law_path: Path | None
    answer_path: Path | None
    transcript_path: Path | None
    returncode: int | None
    timed_out: bool
    # Extra beyond the brief: copied helper modules (new/changed *.py at the workspace root).
    helper_paths: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict:
        def p(value: Path | None) -> str | None:
            return None if value is None else str(value)

        return {
            "variant_id": self.variant_id,
            "workspace": str(self.workspace),
            "law_path": p(self.law_path),
            "answer_path": p(self.answer_path),
            "transcript_path": p(self.transcript_path),
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "helper_paths": [str(x) for x in self.helper_paths],
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunRecord:
        def opt(value: str | None) -> Path | None:
            return None if value is None else Path(value)

        return cls(
            variant_id=data["variant_id"],
            workspace=Path(data["workspace"]),
            law_path=opt(data.get("law_path")),
            answer_path=opt(data.get("answer_path")),
            transcript_path=opt(data.get("transcript_path")),
            returncode=data["returncode"],
            timed_out=bool(data["timed_out"]),
            helper_paths=[Path(x) for x in data.get("helper_paths", [])],
        )

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")

    @classmethod
    def load(cls, path: Path) -> RunRecord:
        return cls.from_dict(json.loads(Path(path).read_text()))


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot(root: Path) -> dict[str, str]:
    """Relative posix path -> sha256 for every regular file under root (symlinks skipped)."""
    return {
        p.relative_to(root).as_posix(): _digest(p)
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    }


def _collect(src: Path, dst: Path) -> Path | None:
    """Copy a regular file. Symlinks are never followed, so host files cannot leak in."""
    if src.is_symlink() or not src.is_file():
        return None
    shutil.copy2(src, dst)
    return dst


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def _launch(argv: Sequence[str], workspace: Path, transcript: Path, timeout_s: int) -> tuple[int | None, bool]:
    env = {**os.environ, "ABDUCTBENCH_AGENT": "1"}
    with transcript.open("wb") as log:
        try:
            proc = subprocess.Popen(
                list(argv),
                cwd=workspace,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
        except OSError as exc:
            log.write(f"failed to start agent: {exc}\n".encode())
            return None, False
        timed_out = False
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Also sweeps children the agent left behind in its process group.
            _kill_group(proc)
    return proc.returncode, timed_out


def run_agent(
    cfg: VariantConfig,
    workspace: Path,
    out_dir: Path,
    agent_cmd: Sequence[str] | None = None,
    timeout_s: int = AGENT_TIMEOUT_S,
) -> RunRecord:
    """Run the agent in ``workspace`` and collect its outputs into ``out_dir/<variant_id>/``.

    Missing outputs are recorded as None, not raised. The evaluator is never run here.
    """
    workspace = Path(workspace)
    if not workspace.is_dir():
        raise FileNotFoundError(f"workspace not found: {workspace}")
    dest = Path(out_dir) / cfg.variant_id
    if workspace.resolve().is_relative_to(dest.resolve()):
        raise ValueError("workspace must not lie inside the output directory")

    before = _snapshot(workspace)
    argv = list(agent_cmd) if agent_cmd is not None else _agent_command(build_agent_prompt(cfg), workspace)

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    transcript = dest / TRANSCRIPT_NAME
    returncode, timed_out = _launch(argv, workspace, transcript, timeout_s)

    law_path = _collect(workspace / LAW_NAME, dest / LAW_NAME)
    answer_path = _collect(workspace / ANSWER_NAME, dest / ANSWER_NAME)
    helper_paths: list[Path] = []
    for src in sorted(workspace.glob("*.py")):
        if src.name == LAW_NAME or src.is_symlink() or not src.is_file():
            continue
        if before.get(src.name) == _digest(src):
            continue  # public file, untouched by the agent
        copied = _collect(src, dest / src.name)
        if copied is not None:
            helper_paths.append(copied)

    return RunRecord(
        variant_id=cfg.variant_id,
        workspace=workspace,
        law_path=law_path,
        answer_path=answer_path,
        transcript_path=transcript,
        returncode=returncode,
        timed_out=timed_out,
        helper_paths=helper_paths,
    )


def make_run(
    cfg: VariantConfig,
    runs_root: Path,
    agent_cmd: Sequence[str] | None = None,
    timeout_s: int = AGENT_TIMEOUT_S,
    budget: float = DEFAULT_BUDGET,
) -> RunRecord:
    """Build a fresh workspace, run the agent, and write ``record.json`` (and the ledger).

    The workspace goes under ``runs_root/_w/w-XXXX/`` (neutral names). Each call gets a fresh mode-2
    state root under ``runs_root/_s/s-XXXX`` so that a re-run starts with the full budget and the ledger
    stays outside the workspace.
    """
    runs_root = Path(runs_root)
    work_parent = runs_root / "_w"
    work_parent.mkdir(parents=True, exist_ok=True)
    # Neutral random names, one private parent per workspace: no variant id in any path the agent
    # sees (cwd, parents, siblings, state root). The mapping lives only in record.json.
    work_root = Path(tempfile.mkdtemp(prefix="w-", dir=work_parent))
    state_root = None
    if cfg.mode == 2:
        state_parent = runs_root / "_s"
        state_parent.mkdir(parents=True, exist_ok=True)
        state_root = Path(tempfile.mkdtemp(prefix="s-", dir=state_parent))
    workspace = make_workspace(cfg, work_root, state_root=state_root, budget=budget)
    # The index maps the neutral task dir back to the variant id; the agent must not read it.
    (work_root / INDEX_NAME).unlink(missing_ok=True)

    record = run_agent(cfg, workspace, runs_root, agent_cmd=agent_cmd, timeout_s=timeout_s)
    dest = runs_root / cfg.variant_id
    if state_root is not None:
        ledger_src = state_root / workspace.name / LOG_NAME
        if ledger_src.is_file():
            shutil.copy2(ledger_src, dest / LEDGER_COPY_NAME)
    record.save(dest / RECORD_NAME)
    return record
