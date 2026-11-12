"""Build the neutral on-disk workspace an agent sees for one variant.

The workspace holds exactly ``bundle.public_files`` under ``root/task_<hash>/``.
The mapping from neutral directory name back to variant_id lives in
``root/_index.json``, outside every task directory.

Mode 2 additionally gets:
- a starter sample of the data tables (the rest is bought through the simulator);
- an executable ``sim`` wrapper that carries only the opaque token, the state root
  and the interpreter/package paths, never the variant;
- a ``task.md`` section describing the simulator. The ledger lives in
  ``state_root/<token>/``, outside the workspace.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import abductbench
from abductbench.config import VariantConfig
from abductbench.ledger import Ledger
from abductbench.tasks import build_task, query_help

SALT = "abductbench-workspace-v1"
INDEX_NAME = "_index.json"
DEFAULT_BUDGET = 20  # simulations (successful `./sim measure` calls)
# The simulator finds a workspace by hashing variant ids over seeds range(TOKEN_SCAN_SEEDS).
TOKEN_SCAN_SEEDS = 100
SIM_NAME = "sim"
# Starter sample for mode 2: first N data rows per table.
STARTER_ROWS = {"events.csv": 100, "target_positions.csv": 20}
# Tables whose rows are grouped by body: first N rows of each body (column 0).
STARTER_ROWS_PER_BODY = {"other_residuals.csv": 20}


def _dir_name(variant_id: str) -> str:
    digest = hashlib.sha1((variant_id + SALT).encode("utf-8")).hexdigest()
    return f"task_{digest[:12]}"


def _check_public_name(name: str) -> PurePosixPath:
    if not name or "\\" in name or PureWindowsPath(name).drive:
        raise ValueError(f"unsafe public file name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"unsafe public file name: {name!r}")
    return path


def _check_mode2(cfg: VariantConfig, root: Path, state_root: Path | None) -> Path:
    """Validate mode-2 arguments before anything is written. Returns the resolved state root."""
    if state_root is None:
        raise ValueError("mode 2 workspaces need state_root (the ledger is kept outside the workspace)")
    if cfg.seed not in range(TOKEN_SCAN_SEEDS):
        raise ValueError(f"mode 2 workspaces need seed in range({TOKEN_SCAN_SEEDS}) for the simulator")
    default = VariantConfig(family=cfg.family, truth=cfg.truth, stage=cfg.stage, seed=cfg.seed, mode=cfg.mode)
    if cfg.n_points != default.n_points or cfg.noise != default.noise:
        raise ValueError("mode 2 workspaces need the default n_points and noise (the simulator resolves variants by id)")
    state = Path(state_root).resolve()
    if state.is_relative_to(Path(root).resolve()):
        raise ValueError("state_root must lie outside the workspace root")
    return state


def _starter_csv(text: str, rows: int | None = None, per_body: int | None = None) -> str:
    lines = text.splitlines()
    header, body = lines[0], lines[1:]
    if rows is not None:
        kept = body[:rows]
    else:
        counts: dict[str, int] = {}
        kept = []
        for line in body:
            key = line.split(",", 1)[0]
            if counts.get(key, 0) < per_body:
                counts[key] = counts.get(key, 0) + 1
                kept.append(line)
    return "\n".join([header, *kept]) + "\n"


def _sim_section(cfg: VariantConfig, budget: float) -> str:
    lines = [
        "",
        "## Simulator (mode 2)",
        "",
        "The data tables above are a starter sample (first rows only). More measurements come from the "
        "`sim` program in this folder:",
        "",
        "- `./sim budget` prints the remaining budget as JSON.",
        "- `./sim measure <query_type> [--arg key=value ...]` prints the answer as JSON and uses up one simulation. "
        "Values are read as JSON when possible, e.g. `--arg n=200`.",
        "- Once the budget is used up, further queries are refused (exit code 2) and returns no data.",
        "",
        f"Total budget: {budget:g} simulations. Each `./sim measure` call is one simulation, whatever the "
        "query type or size (see the per-call limits). Query types and arguments:",
        "",
        query_help(cfg),
        "",
    ]
    return "\n".join(lines)


def _mode2_files(cfg: VariantConfig, files: dict[str, str | bytes], budget: float) -> dict[str, str | bytes]:
    out = dict(files)
    for name, rows in STARTER_ROWS.items():
        if name in out:
            out[name] = _starter_csv(out[name], rows=rows)
    for name, per_body in STARTER_ROWS_PER_BODY.items():
        if name in out:
            out[name] = _starter_csv(out[name], per_body=per_body)
    out["task.md"] = str(out["task.md"]) + _sim_section(cfg, budget)
    return out


def _wrapper_text(token: str, state_root: Path) -> str:
    src = Path(abductbench.__file__).resolve().parents[1]
    python = os.path.abspath(sys.executable)
    return (
        "#!/bin/sh\n"
        f"PYTHONPATH={shlex.quote(str(src))} exec {shlex.quote(python)} -m abductbench.sim_cli "
        f"--token {shlex.quote(token)} --state-root {shlex.quote(str(state_root))} \"$@\"\n"
    )


def make_workspace(
    cfg: VariantConfig,
    root: Path,
    state_root: Path | None = None,
    budget: float = DEFAULT_BUDGET,
) -> Path:
    bundle = build_task(cfg)
    names = {name: _check_public_name(name) for name in bundle.public_files}

    root = Path(root)
    files: dict[str, str | bytes] = dict(bundle.public_files)
    state: Path | None = None
    if cfg.mode == 2:
        state = _check_mode2(cfg, root, state_root)
        files = _mode2_files(cfg, files, budget)

    root.mkdir(parents=True, exist_ok=True)
    task_dir = root / _dir_name(cfg.variant_id)
    if task_dir.exists():
        # Rebuild from scratch so re-running leaves no stale files behind.
        shutil.rmtree(task_dir)
    task_dir.mkdir()

    for name, content in files.items():
        target = task_dir.joinpath(*names[name].parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        target.write_bytes(data)

    if cfg.mode == 2:
        wrapper = task_dir / SIM_NAME
        wrapper.write_text(_wrapper_text(task_dir.name, state))
        os.chmod(wrapper, 0o755)
        # Creating the ledger keeps an existing one (and its budget) untouched on rebuild.
        Ledger(state / task_dir.name, budget)

    index_path = root / INDEX_NAME
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    index[task_dir.name] = cfg.variant_id
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")

    return task_dir
