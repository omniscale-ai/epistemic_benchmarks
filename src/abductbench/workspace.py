"""Build the neutral on-disk workspace an agent sees for one variant.

The workspace holds exactly ``bundle.public_files`` under ``root/task_<hash>/``.
The mapping from neutral directory name back to variant_id lives in
``root/_index.json``, outside every task directory.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath

from abductbench.config import VariantConfig
from abductbench.tasks import build_task

SALT = "abductbench-workspace-v1"
INDEX_NAME = "_index.json"


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


def make_workspace(cfg: VariantConfig, root: Path) -> Path:
    bundle = build_task(cfg)
    names = {name: _check_public_name(name) for name in bundle.public_files}

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    task_dir = root / _dir_name(cfg.variant_id)
    if task_dir.exists():
        # Rebuild from scratch so re-running leaves no stale files behind.
        shutil.rmtree(task_dir)
    task_dir.mkdir()

    for name, content in bundle.public_files.items():
        target = task_dir.joinpath(*names[name].parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        target.write_bytes(data)

    index_path = root / INDEX_NAME
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    index[task_dir.name] = cfg.variant_id
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")

    return task_dir
