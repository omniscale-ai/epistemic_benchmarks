import json
import math
import re
import subprocess
import threading
from pathlib import Path

import pytest

from abductbench.config import Family, Stage, Truth, VariantConfig
from abductbench.ledger import Ledger, discriminating_fraction
from abductbench.sim_cli import main as sim_main
from abductbench.tasks import answer_query, build_task, query_help
from abductbench.workspace import _dir_name, make_workspace

# Substrings that must never appear in anything an agent can see in a mode-2 workspace.
TRUTH_TOKENS = ["entity", "no_entity", "truth", "neutrino", "Neptune", "Vulcan"]
STAGE_PATTERN = re.compile(r"-[abcd]-s\d")


def cfg(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=2):
    return VariantConfig(family=family, truth=truth, stage=stage, seed=seed, mode=mode)


def assert_no_truth(text: str, c: VariantConfig) -> None:
    lowered = text.lower()
    for token in TRUTH_TOKENS:
        assert token.lower() not in lowered, f"forbidden token {token!r} in output"
    assert c.variant_id not in text
    assert not STAGE_PATTERN.search(text)


def tree_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def make_mode2(tmp_path: Path, c: VariantConfig, budget: float = 20):
    """Return (task_dir, ledger_dir) for a mode-2 workspace with state outside it."""
    task_dir = make_workspace(c, tmp_path / "ws", state_root=tmp_path / "state", budget=budget)
    return task_dir, tmp_path / "state" / _dir_name(c.variant_id)


def cli_base(task_dir: Path, ledger_dir: Path) -> list[str]:
    return ["--token", task_dir.name, "--state-root", str(ledger_dir.parent)]


def test_charge_rejects_overspend_without_changing_state(tmp_path):
    led = Ledger(tmp_path / "l", 10.0)
    assert led.charge("events", 6.0, {"n": 1}) is True
    before = led.log_path.read_bytes()

    assert led.charge("recoil_correlation", 5.0) is False
    for bad in (0.0, -1.0, math.nan, math.inf):
        assert led.charge("events", bad) is False

    assert led.log_path.read_bytes() == before
    assert led.remaining == pytest.approx(4.0)
    assert led.charge("events", 4.0) is True
    assert led.remaining == pytest.approx(0.0)


def test_ledger_outside_workspace(tmp_path):
    c = cfg()
    ws = tmp_path / "ws"
    with pytest.raises(ValueError):
        make_workspace(c, ws, state_root=ws / "state")
    assert not ws.exists()  # refused before anything was written

    task_dir = make_workspace(c, ws, state_root=tmp_path / "state")
    ledger_dir = (tmp_path / "state" / _dir_name(c.variant_id)).resolve()
    assert (ledger_dir / "log.jsonl").exists()
    assert ws.resolve() not in ledger_dir.parents
    assert ledger_dir.parent != ws.resolve()
    # The ledger never lands inside the task directory either.
    assert task_dir.resolve() not in ledger_dir.parents


def test_mode2_requires_state_root(tmp_path):
    with pytest.raises(ValueError):
        make_workspace(cfg(), tmp_path / "ws")


def test_mode1_workspace_unchanged_and_has_no_sim(tmp_path):
    c = cfg(mode=1)
    d = make_workspace(c, tmp_path)
    bundle = build_task(c)
    assert tree_files(d) == set(bundle.public_files)
    for name, content in bundle.public_files.items():
        data = content.encode("utf-8") if isinstance(content, str) else content
        assert (d / name).read_bytes() == data
    assert not (d / "sim").exists()


def test_mode2_layout_and_starter_sample(tmp_path):
    c = cfg(Family.BETA)
    task_dir, _ = make_mode2(tmp_path, c)
    assert tree_files(task_dir) == {
        "task.md", "events.csv", "masses.csv", "detector.md", "sim",
    }
    events_lines = (task_dir / "events.csv").read_text().splitlines()
    assert len(events_lines) == 101  # header + starter sample of 100 events
    task_md = (task_dir / "task.md").read_text()
    assert "./sim measure" in task_md and "./sim budget" in task_md
    assert "20 simulations" in task_md  # default budget is stated
    assert (task_dir / "sim").stat().st_mode & 0o111

    oc = cfg(Family.ORBIT)
    odir, _ = make_mode2(tmp_path / "o", oc)
    assert len((odir / "target_positions.csv").read_text().splitlines()) == 21
    other = (odir / "other_residuals.csv").read_text().splitlines()
    assert len(other) == 1 + 3 * 20  # 20 rows for each of three other bodies


def test_measure_returns_data_and_logs(tmp_path):
    def run_sim(task_dir, *args):
        return subprocess.run(
            [str(task_dir / "sim"), *args], capture_output=True, text=True, timeout=300
        )

    # Beta: events draw.
    bdir, bledger = make_mode2(tmp_path / "b", cfg(Family.BETA), budget=10)
    r = run_sim(bdir, "measure", "events", "--arg", "n=5")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["columns"] == ["kinetic_energy", "recoil_energy", "recoil_angle_deg"]
    assert len(data["rows"]) == 5
    budget = json.loads(run_sim(bdir, "budget").stdout)
    assert budget == {"remaining": 9}
    lines = bledger.joinpath("log.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["query_type"] == "events"

    # Orbit: residuals of the target at two times, using the public target name.
    odir, oledger = make_mode2(tmp_path / "o", cfg(Family.ORBIT), budget=10)
    name = (odir / "target_positions.csv").read_text().splitlines()[1].split(",")[0]
    r = run_sim(odir, "measure", "residuals", "--arg", f"body={name}", "--arg", "time=[1.0, 2.5]")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert len(data["time"]) == 2 and len(data["residual_arcsec"]) == 2
    assert json.loads(run_sim(odir, "budget").stdout) == {"remaining": 9}
    assert len(oledger.joinpath("log.jsonl").read_text().splitlines()) == 2


def test_discriminating_fraction(tmp_path):
    led = Ledger(tmp_path / "l", 100.0)
    led.charge("events", 1.0)
    led.charge("recoil_correlation", 5.0)
    led.charge("target_thickness_scan", 8.0)
    disc = {"recoil_correlation", "target_thickness_scan"}
    assert discriminating_fraction(led.log_path, disc) == pytest.approx(13.0 / 14.0)
    empty = Ledger(tmp_path / "e", 10.0)
    assert discriminating_fraction(empty.log_path, disc) == 0.0


def test_unknown_query_type_error_no_truth(tmp_path, capsys):
    c = cfg(Family.BETA, Truth.ENTITY)
    with pytest.raises(ValueError) as info:
        answer_query(c, "bogus", {})
    msg = str(info.value)
    assert "events" in msg and "target_thickness_scan" in msg
    assert_no_truth(msg, c)

    task_dir, ledger_dir = make_mode2(tmp_path, c)
    rc = sim_main([*cli_base(task_dir, ledger_dir), "measure", "bogus"])
    out = capsys.readouterr().out
    assert rc != 0
    assert "error" in json.loads(out)
    assert_no_truth(out, c)
    assert len(ledger_dir.joinpath("log.jsonl").read_text().splitlines()) == 1  # nothing charged


def test_budget_exhaustion_blocks_data(tmp_path, capsys):
    c = cfg(Family.BETA)
    task_dir, ledger_dir = make_mode2(tmp_path, c, budget=2)
    base = cli_base(task_dir, ledger_dir)
    assert sim_main([*base, "measure", "events", "--arg", "n=1"]) == 0
    capsys.readouterr()
    assert sim_main([*base, "measure", "events", "--arg", "n=1"]) == 0
    capsys.readouterr()

    rc = sim_main([*base, "measure", "events", "--arg", "n=1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert json.loads(out) == {"error": "insufficient budget", "remaining": 0.0}

    rc = sim_main([*base, "measure", "recoil_correlation"])  # nothing left
    assert rc == 2
    assert "rows" not in capsys.readouterr().out


def test_log_is_source_of_truth(tmp_path):
    led = Ledger(tmp_path / "l", 10.0)
    assert led.charge("events", 4.0)
    first_line = led.log_path.read_text().splitlines()[0]
    assert json.loads(first_line) == {"budget": 10.0}

    reopened = Ledger(tmp_path / "l", 1000.0)  # budget argument ignored for existing ledgers
    assert reopened.remaining == pytest.approx(6.0)
    assert reopened.charge("events", 7.0) is False
    assert reopened.remaining == pytest.approx(6.0)
    assert Ledger(tmp_path / "l", 1000.0).remaining == pytest.approx(6.0)
    assert json.loads(first_line) == {"budget": 10.0}


def test_concurrent_charges_do_not_overspend(tmp_path):
    path = tmp_path / "l"
    Ledger(path, 25.0)
    results: list[bool] = []

    def worker():
        led = Ledger(path, 25.0)  # its own file handle, as a separate process would have
        for _ in range(10):
            results.append(led.charge("events", 1.0))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(results) == 25
    assert Ledger(path, 25.0).remaining == pytest.approx(0.0)


def test_beta_thickness_scan_differs_by_truth(tmp_path):
    ent = answer_query(cfg(Family.BETA, Truth.ENTITY), "target_thickness_scan", {"_n": 0})
    non = answer_query(cfg(Family.BETA, Truth.NO_ENTITY), "target_thickness_scan", {"_n": 0})
    json.dumps(ent)
    json.dumps(non)
    assert len(ent["summaries"]) == 3
    tails = lambda r: [x["tail_fraction"] for x in r["summaries"]]  # noqa: E731
    # Hidden carrier: same shape at every thickness, but independent noise per thickness.
    ent_hist = [x["histogram"] for x in ent["summaries"]]
    assert len({tuple(h) for h in ent_hist}) > 1
    assert max(tails(ent)) - min(tails(ent)) < 0.03
    # Detector artifact: the energy-loss tail grows with thickness.
    t_non = tails(non)
    assert t_non[-1] - t_non[0] > 0.03


def test_orbit_search_region_detects_only_for_entity(tmp_path):
    lon = hidden_longitude(cfg(Family.ORBIT, Truth.ENTITY), 5.0)

    # A one-degree sector centred on the opposite side of the sky must be empty.
    far = answer_query(
        cfg(Family.ORBIT, Truth.ENTITY), "search_region",
        {"lon_min": (lon + 179.0) % 360.0, "lon_max": (lon + 181.0) % 360.0, "time": 5.0, "_n": 0},
    )
    assert far["candidates"] == []

    none = answer_query(
        cfg(Family.ORBIT, Truth.NO_ENTITY), "search_region",
        {"lon_min": (lon - 10.0) % 360.0, "lon_max": (lon + 10.0) % 360.0, "time": 5.0, "_n": 0},
    )
    assert none["candidates"] == []


def hidden_longitude(c, t):
    """Probe with 30-degree windows (the cap) to locate the hidden body of an entity variant."""
    for lo in range(0, 360, 30):
        r = answer_query(c, "search_region", {"lon_min": float(lo), "lon_max": float(lo + 30), "time": t, "_n": 0})
        if r["candidates"]:
            return r["candidates"][0]["longitude_deg"]
    raise AssertionError("hidden body not found")


def test_search_region_width_cap(tmp_path, capsys):
    c = cfg(Family.ORBIT, Truth.ENTITY, Stage.HISTORICAL)
    lon = hidden_longitude(c, 5.0)
    inside = {"lon_min": (lon - 14.0) % 360.0, "lon_max": (lon + 15.0) % 360.0, "time": 5.0, "_n": 0}
    assert len(answer_query(c, "search_region", inside)["candidates"]) == 1  # width 29, hit
    exact = {"lon_min": (lon - 15.0) % 360.0, "lon_max": (lon + 15.0) % 360.0, "time": 5.0, "_n": 0}
    assert len(answer_query(c, "search_region", exact)["candidates"]) == 1  # width 30 accepted (wraps ok)
    outside = {"lon_min": (lon + 20.0) % 360.0, "lon_max": (lon + 50.0) % 360.0, "time": 5.0, "_n": 0}
    assert answer_query(c, "search_region", outside)["candidates"] == []  # window not containing it
    for lo, hi in [(0.0, 31.0), (0.0, 360.0), (350.0, 21.0), (-10.0, 30.5)]:
        with pytest.raises(ValueError, match="maximum is 30") as exc:
            answer_query(c, "search_region", {"lon_min": lo, "lon_max": hi, "time": 5.0, "_n": 0})
        assert "entity" not in str(exc.value).lower()
    assert "30 degrees wide" in query_help(c)

    c2 = cfg(Family.ORBIT, Truth.ENTITY, Stage.HISTORICAL, mode=2)
    task_dir, ledger_dir = make_mode2(tmp_path, c2)
    base = cli_base(task_dir, ledger_dir)
    n_before = len(ledger_dir.joinpath("log.jsonl").read_text().splitlines())
    rc = sim_main([*base, "measure", "search_region", "--arg", "time=5", "--arg", "lon_min=0", "--arg", "lon_max=31"])
    assert rc == 1
    assert "error" in json.loads(capsys.readouterr().out)
    assert len(ledger_dir.joinpath("log.jsonl").read_text().splitlines()) == n_before  # uncharged
    rc = sim_main([*base, "measure", "search_region", "--arg", "time=5", "--arg", "lon_min=0", "--arg", "lon_max=30"])
    assert rc == 0
    capsys.readouterr()
    assert len(ledger_dir.joinpath("log.jsonl").read_text().splitlines()) == n_before + 1


def all_16_mode2():
    return [
        cfg(f, t, st, seed=0, mode=2) for f in Family for t in Truth for st in Stage
    ]


def sample_results(c: VariantConfig) -> dict[str, dict]:
    """One answer per query type, with the same arguments an agent would plausibly use."""
    if c.family is Family.BETA:
        requests = {
            "events": {"n": 3},
            "recoil_correlation": {"n": 20},
            "target_thickness_scan": {},
        }
    else:
        body = (build_task(c).public_files["known_bodies.csv"]).splitlines()[2].split(",")[0]
        requests = {
            "residuals": {"body": body, "time": [1.0, 2.0]},
            "other_body_residuals": {"time": [1.0]},
            "search_region": {"time": 1.0, "lon_min": 0.0, "lon_max": 30.0},
        }
    out = {}
    for query_type, args in requests.items():
        out[query_type] = answer_query(c, query_type, {**args, "_n": 0})
    return out


@pytest.mark.parametrize("c", all_16_mode2(), ids=lambda c: c.variant_id)
def test_wrapper_contains_no_variant_info(tmp_path, c):
    task_dir, _ = make_mode2(tmp_path, c)
    wrapper = (task_dir / "sim").read_text()
    assert_no_truth(wrapper, c)
    assert c.variant_id not in wrapper
    for path in task_dir.rglob("*"):
        if path.is_file():
            assert_no_truth(path.read_text(errors="ignore"), c)
    assert_no_truth(query_help(c), c)
    for query_type, result in sample_results(c).items():
        assert_no_truth(json.dumps(result, sort_keys=True), c)


@pytest.mark.parametrize("family", [Family.BETA, Family.ORBIT])
def test_task_md_counts_simulations_not_prices(tmp_path, family):
    c = cfg(family)
    task_dir, _ = make_mode2(tmp_path, c)
    text = (task_dir / "task.md").read_text() + query_help(c)
    assert "simulations" in text
    for banned in ("units", "per 50 rows", "Pricing"):
        assert banned not in text, banned


def test_orbit_queries_capped_at_public_window(tmp_path, capsys):
    # Public window is TIME_YR = 10 years; 10..40 years is held out for extrapolation scoring.
    c = cfg(Family.ORBIT, Truth.ENTITY, Stage.HISTORICAL)
    assert answer_query(c, "residuals", {"body": "Uranus", "time": [10.0], "_n": 0})
    for query_type, args in [
        ("residuals", {"body": "Uranus", "time": [12.0]}),
        ("other_body_residuals", {"time": {"start": 9.0, "stop": 14.0, "n": 5}}),
        ("search_region", {"time": 12.0, "lon_min": 0, "lon_max": 360}),
    ]:
        with pytest.raises(ValueError, match="must lie in"):
            answer_query(c, query_type, {**args, "_n": 0})

    task_dir, ledger_dir = make_mode2(tmp_path, c)
    base = cli_base(task_dir, ledger_dir)
    rc = sim_main([*base, "measure", "residuals", "--arg", "body=Uranus", "--arg", "time=[12.0]"])
    assert rc == 1
    assert "error" in json.loads(capsys.readouterr().out)
    assert len(ledger_dir.joinpath("log.jsonl").read_text().splitlines()) == 1  # nothing charged


def test_beta_events_stay_in_public_window():
    # Beta has no energy argument. Events are drawn only inside the public recorded window
    # [0.1 Q, 1.2 Q], so the low extrapolation band [0.02 Q, 0.1 Q) can never appear.
    from abductbench.tasks.beta import WINDOW, _setup

    for truth in Truth:
        c = cfg(Family.BETA, truth, Stage.HISTORICAL)
        s = _setup(c)
        lo, hi = WINDOW[0] * s.Q / s.scale, WINDOW[1] * s.Q / s.scale
        rows = answer_query(c, "events", {"n": 500, "_n": 0})["rows"]
        energies = [r[0] for r in rows]
        assert min(energies) >= lo and max(energies) <= hi


QUERIES_BY_FAMILY = {
    Family.BETA: [
        ("events", ["n=3"]),
        ("recoil_correlation", ["n=5"]),
        ("target_thickness_scan", []),
    ],
    Family.ORBIT: [
        ("residuals", ["body=Uranus", "time=[1.0, 2.0, 3.0]"]),
        ("other_body_residuals", ["time=[1.0, 2.0]"]),
        ("search_region", ["time=1.0", "lon_min=0", "lon_max=10"]),
    ],
}


@pytest.mark.parametrize("family", [Family.BETA, Family.ORBIT])
def test_every_query_type_costs_one_simulation(tmp_path, capsys, family):
    c = cfg(family, Truth.ENTITY, Stage.HISTORICAL)
    queries = QUERIES_BY_FAMILY[family]
    task_dir, ledger_dir = make_mode2(tmp_path, c, budget=10)
    base = cli_base(task_dir, ledger_dir)
    for i, (qt, args) in enumerate(queries, start=1):
        extra = [x for a in args for x in ("--arg", a)]
        assert sim_main([*base, "measure", qt, *extra]) == 0, qt
        capsys.readouterr()
        assert Ledger(ledger_dir).remaining == pytest.approx(10 - i)
    entries = [json.loads(l) for l in ledger_dir.joinpath("log.jsonl").read_text().splitlines()[1:]]
    assert [e["cost"] for e in entries] == [1.0] * len(queries)


@pytest.mark.parametrize("family", [Family.BETA, Family.ORBIT])
def test_budget_of_n_allows_exactly_n_measures(tmp_path, capsys, family):
    c = cfg(family, Truth.ENTITY, Stage.HISTORICAL)
    qt, args = QUERIES_BY_FAMILY[family][0]
    extra = [x for a in args for x in ("--arg", a)]
    task_dir, ledger_dir = make_mode2(tmp_path, c, budget=3)
    base = cli_base(task_dir, ledger_dir)
    for _ in range(3):
        assert sim_main([*base, "measure", qt, *extra]) == 0
        capsys.readouterr()
    assert json.loads(sim_main_budget(base, capsys)) == {"remaining": 0}
    rc = sim_main([*base, "measure", qt, *extra])
    out = capsys.readouterr().out
    assert rc == 2
    assert "rows" not in out and "residual_arcsec" not in out
    assert len(ledger_dir.joinpath("log.jsonl").read_text().splitlines()) == 1 + 3


def test_huge_n_rejected_by_size_cap_and_not_charged(tmp_path, capsys):
    c = cfg(Family.BETA)
    task_dir, ledger_dir = make_mode2(tmp_path, c, budget=5)
    base = cli_base(task_dir, ledger_dir)
    rc = sim_main([*base, "measure", "events", "--arg", "n=100000"])
    assert rc == 1
    assert "error" in json.loads(capsys.readouterr().out)
    assert len(ledger_dir.joinpath("log.jsonl").read_text().splitlines()) == 1
    assert Ledger(ledger_dir).remaining == pytest.approx(5)


def sim_main_budget(base, capsys) -> str:
    assert sim_main([*base, "budget"]) == 0
    return capsys.readouterr().out
