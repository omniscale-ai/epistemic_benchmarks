"""Local baselines for the orbit episode: PYTHONPATH=src .venv/bin/python scripts/orbit_baselines.py 0-9 out_dir"""
import json, sys, time, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
from abductbench.episode import orbitbaselines as ob

if __name__ == "__main__":
    a, b = map(int, sys.argv[1].split("-"))
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=False)
    t = time.time()
    rows = ob.run_table(list(ob.POLICIES), range(a, b + 1), ("ambiguous",), processes=int(sys.argv[3]) if len(sys.argv) > 3 else 6)
    rows += ob.run_table(["reference_adaptive", "no_data", "textbook"], range(a, b + 1), ("no_measurement",), processes=6)
    summ = ob.summarise(rows)
    (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
    (out / "summary.json").write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps(summ, indent=1, default=float)); print("seconds", time.time() - t)
