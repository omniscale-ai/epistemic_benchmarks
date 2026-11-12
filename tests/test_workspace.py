import json
import re
from pathlib import Path

import pytest

from abductbench import workspace
from abductbench.config import Family, Stage, TaskBundle, Truth, VariantConfig
from abductbench.tasks import build_task
from abductbench.workspace import make_workspace

# Tokens that must never appear in any public text file, for every stage.
# Case-insensitive substring match.
FORBIDDEN = ["entity", "no_entity", "neutrino", "Neptune", "Vulcan", "truth"]


def cfg(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1):
    return VariantConfig(family=family, truth=truth, stage=stage, seed=seed, mode=mode)


def all_16_configs():
    return [
        cfg(family=f, truth=t, stage=s, seed=0, mode=1)
        for f in Family
        for t in Truth
        for s in Stage
    ]


def tree_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def tree_dirs(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_dir()}


def fake_bundle(public_files: dict) -> TaskBundle:
    return TaskBundle(
        public_files=public_files,
        truth_law=lambda x: x,
        eval_points=lambda: None,
        true_domain={},
        entity=True,
        rubric_id="fake",
        discriminating_queries=frozenset(),
    )


def test_workspace_contains_only_public_files(tmp_path):
    c = cfg(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL)
    bundle = build_task(c)
    task_dir = make_workspace(c, tmp_path)

    assert task_dir.parent == tmp_path
    assert task_dir.name.startswith("task_")
    assert tree_files(task_dir) == set(bundle.public_files)
    expected_dirs = {str(Path(k).parent.as_posix()) for k in bundle.public_files} - {"."}
    assert tree_dirs(task_dir) == expected_dirs
    # Nothing outside the task dir except the index file.
    assert {p.name for p in tmp_path.iterdir()} == {task_dir.name, "_index.json"}


def test_workspace_writes_public_files_byte_exact(tmp_path):
    files = {"a.txt": "héllo\r\nworld\n", "b.bin": b"\x00\xffraw\r\n"}
    root = tmp_path / "root"
    root.mkdir()
    c = cfg()
    real = workspace.build_task
    try:
        workspace.build_task = lambda _cfg: fake_bundle(files)
        task_dir = make_workspace(c, root)
    finally:
        workspace.build_task = real
    assert (task_dir / "a.txt").read_bytes() == "héllo\r\nworld\n".encode("utf-8")
    assert (task_dir / "b.bin").read_bytes() == b"\x00\xffraw\r\n"


def test_nested_public_file_names_create_parent_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "build_task", lambda _cfg: fake_bundle({"sub/deep/x.csv": "a,b\n"}))
    task_dir = make_workspace(cfg(), tmp_path)
    assert (task_dir / "sub" / "deep" / "x.csv").read_text() == "a,b\n"
    assert tree_files(task_dir) == {"sub/deep/x.csv"}


@pytest.mark.parametrize(
    "bad_name",
    ["/etc/passwd", "../escape.txt", "sub/../../escape.txt", "..", "a/..", "C:\\evil.txt", "\\\\server\\x"],
)
def test_rejects_absolute_or_parent_public_names(tmp_path, monkeypatch, bad_name):
    monkeypatch.setattr(workspace, "build_task", lambda _cfg: fake_bundle({bad_name: "x"}))
    with pytest.raises(ValueError):
        make_workspace(cfg(), tmp_path)
    # Nothing escaped the root.
    assert not (tmp_path.parent / "escape.txt").exists()


@pytest.mark.parametrize("config", all_16_configs(), ids=lambda c: c.variant_id)
def test_no_truth_strings_in_public_files(config):
    bundle = build_task(config)
    for name, content in bundle.public_files.items():
        text = content if isinstance(content, str) else content.decode("utf-8", errors="ignore")
        for label, value in (("file name", name), ("content", text)):
            lowered = value.lower()
            for token in FORBIDDEN:
                assert token.lower() not in lowered, (
                    f"{config.variant_id}: forbidden token {token!r} in {label} of {name!r}"
                )


@pytest.mark.parametrize("mode", [1, 2])
@pytest.mark.parametrize("config", all_16_configs(), ids=lambda c: c.variant_id)
def test_no_truth_strings_in_written_workspace_tree(tmp_path_factory, config, mode):
    config = cfg(family=config.family, truth=config.truth, stage=config.stage, seed=0, mode=mode)
    # neutral base dirs: pytest's per-test tmp_path embeds the test id, which would be a false hit
    root = tmp_path_factory.mktemp("w")
    state = tmp_path_factory.mktemp("s") if mode == 2 else None
    ws = make_workspace(config, root, state_root=state)
    seen = 0
    for path in ws.rglob("*"):
        rel = path.relative_to(ws).as_posix()
        texts = [("path", rel)]
        if path.is_file():
            texts.append(("content", path.read_bytes().decode("utf-8", errors="ignore")))
        for label, value in texts:
            lowered = value.lower()
            for token in FORBIDDEN:
                assert token.lower() not in lowered, (
                    f"{config.variant_id}: forbidden token {token!r} in {label} of {rel!r}"
                )
        seen += path.is_file()
    assert seen >= 4
    assert config.variant_id not in "".join(p.name for p in ws.parents)
    assert (ws / "sim").exists() == (mode == 2)


def test_workspace_dir_name_does_not_reveal_variant(tmp_path):
    c = cfg(family=Family.ORBIT, truth=Truth.NO_ENTITY, stage=Stage.COUNTERFACTUAL)
    task_dir = make_workspace(c, tmp_path)
    name = task_dir.name
    assert re.fullmatch(r"task_[0-9a-f]{12}", name)
    assert name != c.variant_id
    lowered = name.lower()
    for word in ("beta", "orbit", "entity", "truth", "stage", "counterfactual"):
        assert word not in lowered
    assert c.variant_id not in name


def test_index_maps_neutral_name_to_variant_id(tmp_path):
    c1 = cfg(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL)
    c2 = cfg(family=Family.BETA, truth=Truth.NO_ENTITY, stage=Stage.HISTORICAL)
    d1 = make_workspace(c1, tmp_path)
    d2 = make_workspace(c2, tmp_path)

    index = json.loads((tmp_path / "_index.json").read_text())
    assert index[d1.name] == c1.variant_id
    assert index[d2.name] == c2.variant_id
    assert len(index) == 2
    # Index lives in root, never inside a task directory.
    assert not (d1 / "_index.json").exists()
    assert not (d2 / "_index.json").exists()


def test_rerun_is_idempotent_and_removes_stale_files(tmp_path, monkeypatch):
    c = cfg()
    monkeypatch.setattr(workspace, "build_task", lambda _cfg: fake_bundle({"a.txt": "one", "sub/b.txt": "two"}))
    d = make_workspace(c, tmp_path)
    (d / "stale.txt").write_text("leftover")
    (d / "sub" / "stale2.txt").write_text("leftover")

    monkeypatch.setattr(workspace, "build_task", lambda _cfg: fake_bundle({"a.txt": "ONE"}))
    d2 = make_workspace(c, tmp_path)
    assert d2 == d
    assert tree_files(d) == {"a.txt"}
    assert (d / "a.txt").read_text() == "ONE"
    assert not (d / "sub").exists()

    index = json.loads((tmp_path / "_index.json").read_text())
    assert index == {d.name: c.variant_id}
