"""Run one agent through one episode, with a full manifest and a never-overwritten run directory.

Layout of ``runs_root/<run_id>/`` (run_id = UTC time + random hex; it encodes nothing about the world)::

    manifest.json       full config, seeds, code version, package versions, isolation, agent argv
    state/              protocol state (config, append-only log, model snapshots, arrays)
    transcript.jsonl    agent stdout/stderr
    workspace_final/    copy of the agent workspace after the run
    run.json            return code, timeout, whether the episode was closed

Isolation modes:
- ``bwrap``: the agent process sees only /work (its workspace), its Python (numpy/scipy), the
  claude binary at /opt/claude/claude, /usr,/lib,/bin,/etc read-only, a fresh HOME with a copy of
  the credentials file, and the episode socket at /run/episode/sock. Network is shared (the API
  needs it). The repository, the state directory and other runs are not mounted.
- ``none``: UNISOLATED, for local dry tests with fake agents only. A real ``claude`` run in this
  mode is refused unless ``unsafe_unisolated=True``.
"""

from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy

from abductbench.episode import modelrun as mr
from abductbench.episode.protocol import Session
from abductbench.episode.server import EpisodeService, client_text, start_server
from abductbench.episode.workspace import write_workspace
from abductbench.episode.world import EpisodeConfig

REPO = Path(__file__).resolve().parents[3]
SANDBOX_SOCK = "/run/episode/sock"
SANDBOX_CLAUDE = "/opt/claude/claude"
AGENT_TOOLS = "Read,Write,Edit,Bash"
AGENT_PROMPT = (
    "You are working on a scientific inference episode. Everything you need is in the current "
    "directory. Read task.md first and follow its procedure exactly: register a forecast with "
    "./episode register before every measurement, and finish with ./episode final final.json. "
    "Work only inside the current directory. Stop once the final submission is accepted.\n"
)


@dataclass
class RunPaths:
    run_id: str
    run_dir: Path
    state_dir: Path
    workspace: Path
    sock_dir: Path
    home: Path


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def code_version() -> dict:
    return {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty_paths": [line[3:] for line in _git("status", "--porcelain").splitlines()
                            if "src/" in line or "tests/" in line],
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "bwrap": shutil.which("bwrap") is not None,
    }


def new_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + secrets.token_hex(4)


def prepare(cfg: EpisodeConfig, runs_root: Path, isolation: str, agent_desc: dict,
            allow_unsandboxed_models: bool = False) -> tuple[RunPaths, Session]:
    runs_root = Path(runs_root).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)
    run_id = new_run_id()
    run_dir = runs_root / run_id
    run_dir.mkdir(exist_ok=False)  # never overwrite
    (runs_root / "_w").mkdir(exist_ok=True)
    ws_root = Path(tempfile.mkdtemp(prefix="w-", dir=runs_root / "_w"))
    ws = ws_root / "work"
    home = ws_root / "home"
    home.mkdir()
    sock_dir = Path(tempfile.mkdtemp(prefix="abep-"))  # short path: unix sockets are length-limited
    manifest = {"run_id": run_id, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "config": cfg.to_dict(), "isolation": isolation, "agent": agent_desc,
                "code": code_version(), "model_sandbox": "bwrap" if mr.bwrap_available() else "none"}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    s = Session(cfg, state_dir=run_dir / "state", workspace=ws, manifest=manifest,
                allow_unsandboxed=allow_unsandboxed_models)
    sock_for_client = SANDBOX_SOCK if isolation == "bwrap" else str(sock_dir / "sock")
    write_workspace(s, ws, client_text(sock_for_client))
    return RunPaths(run_id, run_dir, run_dir / "state", ws, sock_dir, home), s


def claude_inner_argv(model: str, max_budget_usd: float | None) -> list[str]:
    argv = [SANDBOX_CLAUDE, "-p", AGENT_PROMPT, "--model", model, "--output-format", "stream-json", "--verbose",
            "--restricted", "--tools", AGENT_TOOLS, "--allowedTools", AGENT_TOOLS,
            "--disallowedTools", "WebSearch,WebFetch,Task", "--permission-mode", "acceptEdits",
            "--permission-prompts", "none", "--setting-sources", "", "--no-session-persistence",
            "--disable-slash-commands"]
    if max_budget_usd is not None:
        argv += ["--max-budget-usd", f"{max_budget_usd:g}"]
    return argv


def bwrap_argv(p: RunPaths, inner: list[str], claude_binary: Path | None = None) -> list[str]:
    binds, inner_py = mr._python_binds(mr.agent_python())
    venv_bin = Path(inner_py).parent
    argv = ["bwrap"]
    for d in ("/usr", "/lib", "/lib64", "/bin", "/etc"):
        if Path(d).exists():
            argv += ["--ro-bind", d, d]
    argv += binds
    # /etc/resolv.conf is usually a link into /run/systemd/resolve (systemd-resolved stub): mount it
    # read-only, otherwise DNS fails inside the sandbox (seen in the first real run: EAI_AGAIN).
    if Path("/run/systemd/resolve").is_dir():
        argv += ["--ro-bind", "/run/systemd/resolve", "/run/systemd/resolve"]
    argv += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
             "--bind", str(p.workspace), "/work",
             "--bind", str(p.sock_dir), "/run/episode",
             "--bind", str(p.home), "/home/agent"]
    if claude_binary is not None:
        argv += ["--ro-bind", str(Path(claude_binary).resolve()), SANDBOX_CLAUDE]
    env = {"HOME": "/home/agent", "PATH": f"{venv_bin}:/usr/bin:/bin", "LANG": "C.UTF-8",
           "CLAUDE_CONFIG_DIR": "/home/agent/.claude", "DISABLE_AUTOUPDATER": "1", "VIRTUAL_ENV": str(venv_bin.parent)}
    if os.environ.get("ANTHROPIC_API_KEY"):
        env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    argv += ["--clearenv"]
    for k, v in env.items():
        argv += ["--setenv", k, v]
    argv += ["--unshare-all", "--share-net", "--die-with-parent", "--new-session", "--chdir", "/work", "--", *inner]
    return argv


def _redact(argv: list[str]) -> list[str]:
    out, skip = [], False
    for a in argv:
        if skip:
            out.append("<redacted>")
            skip = False
            continue
        out.append(a)
        if a == "--setenv":
            continue
        if a == "ANTHROPIC_API_KEY":
            skip = True
    return out


def _seed_home(home: Path) -> None:
    """Fresh config dir for the sandboxed claude: only the credentials file is copied."""
    cfg = home / ".claude"
    cfg.mkdir(exist_ok=True)
    src = Path.home() / ".claude" / ".credentials.json"
    if src.is_file():
        dst = cfg / ".credentials.json"
        shutil.copyfile(src, dst)
        dst.chmod(0o600)


def run_episode(cfg: EpisodeConfig, runs_root: Path, *, agent: str = "claude", isolation: str = "bwrap",
                timeout_s: int = 3600, model: str = "sonnet", max_budget_usd: float | None = None,
                inner_argv: list[str] | None = None, agent_files: dict[str, str] | None = None,
                unsafe_unisolated: bool = False, dry_run: bool = False) -> Path | list[str]:
    """Run one episode. ``agent``: "claude" or "custom" (``inner_argv``, e.g. a fake agent script).

    ``dry_run=True`` prepares everything and returns the argv that would be launched, without launching.
    """
    if isolation not in ("bwrap", "none"):
        raise ValueError("isolation must be 'bwrap' or 'none'")
    if agent == "claude" and isolation == "none" and not unsafe_unisolated:
        raise RuntimeError("refusing to run a real agent without isolation (pass unsafe_unisolated=True to override)")
    if isolation == "bwrap" and not mr.bwrap_available():
        raise RuntimeError("bwrap not available: cannot isolate the agent")
    claude_bin = Path(shutil.which("claude") or "") if agent == "claude" else None
    if agent == "claude":
        if not claude_bin or not claude_bin.exists():
            raise RuntimeError("claude binary not found")
        inner = claude_inner_argv(model, max_budget_usd)
        desc = {"kind": "claude", "model": model, "max_budget_usd": max_budget_usd, "timeout_s": timeout_s,
                "claude_binary": str(claude_bin.resolve())}
    else:
        if not inner_argv:
            raise ValueError("custom agents need inner_argv")
        inner = list(inner_argv)
        desc = {"kind": "custom", "argv": inner, "timeout_s": timeout_s}
    p, s = prepare(cfg, runs_root, isolation, desc, allow_unsandboxed_models=not mr.bwrap_available())
    for name, text in (agent_files or {}).items():
        (p.workspace / name).write_text(text)
    if isolation == "bwrap":
        if agent == "claude":
            inner = [SANDBOX_CLAUDE if a == SANDBOX_CLAUDE else a for a in inner]
            _seed_home(p.home)
        argv = bwrap_argv(p, inner, claude_bin if agent == "claude" else None)
        cwd = p.workspace
    else:
        argv = inner
        cwd = p.workspace
    (p.run_dir / "launch.json").write_text(json.dumps({"argv": _redact(argv), "cwd": str(cwd)}, indent=1))
    if dry_run:
        return argv
    service = EpisodeService(s, p.workspace)
    srv, _ = start_server(service, p.sock_dir / "sock")
    t0 = time.time()
    timed_out = False
    try:
        env = None if isolation == "bwrap" else {**{k: v for k, v in os.environ.items()
                                                    if k not in ("PYTHONPATH", "VIRTUAL_ENV")},
                                                 "PATH": f"{mr.agent_python().parent}:{os.environ.get('PATH', '')}"}
        with open(p.run_dir / "transcript.jsonl", "wb") as log:
            proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    env=env, start_new_session=True)
            try:
                proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
    finally:
        srv.shutdown()
        srv.server_close()
        cred = p.home / ".claude" / ".credentials.json"
        if cred.exists():
            cred.unlink()
    shutil.copytree(p.workspace, p.run_dir / "workspace_final", symlinks=True)
    (p.run_dir / "run.json").write_text(json.dumps({
        "returncode": proc.returncode, "timed_out": timed_out, "seconds": time.time() - t0,
        "episode_closed": s.closed, "measurements": s.n_measured, "registrations": s.n_registrations,
    }, indent=1))
    shutil.rmtree(p.sock_dir, ignore_errors=True)
    return p.run_dir
