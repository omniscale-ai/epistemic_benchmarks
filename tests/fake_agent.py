"""Stand-in for the Claude Code agent in tests/test_runner.py. Never calls any API.

Run with cwd = workspace. argv[1] selects the behaviour:
  write    law.py and answer.md (default)
  sleep    law.py and answer.md, starts a grandchild (its pid goes to child.pid), then sleeps
  nothing  writes nothing and exits 0
  helper   law.py (importing helper_mod), answer.md, helper_mod.py, and overwrites changed.py

Every mode first prints one "FILE <relpath>" line per file in the cwd, so a test can check
the tree the agent saw at launch.
"""

import subprocess
import sys
import time
from pathlib import Path

LAW = "DOMAIN = {'x': (0.0, 1.0)}\n\n\ndef law(x):\n    return x\n"
ANSWER = "## Law\nlinear\n\n## Limits\nnone\n\n## Explanation\nobvious\n\nENTITY: no\n"


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "write"
    here = Path.cwd()
    for path in sorted(here.rglob("*")):
        if path.is_file():
            print("FILE " + path.relative_to(here).as_posix(), flush=True)
    if mode in ("write", "sleep", "helper"):
        Path("law.py").write_text(LAW)
        Path("answer.md").write_text(ANSWER)
    if mode == "helper":
        Path("helper_mod.py").write_text("VALUE = 1\n")
        Path("law.py").write_text("from helper_mod import VALUE\n" + LAW)
        Path("changed.py").write_text("CHANGED = True\n")
    if mode == "sleep":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        Path("child.pid").write_text(str(child.pid))
        time.sleep(600)


if __name__ == "__main__":
    main()
