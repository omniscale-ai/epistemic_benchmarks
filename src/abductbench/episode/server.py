"""Episode server (orchestrator side) and the agent's ``./episode`` client.

The server owns the Session (world, budget, log, snapshots) and runs outside the agent's
sandbox; the agent reaches it only through a unix socket. Requests are one JSON line each:
``{"cmd": "status" | "register" | "measure" | "final", "payload": {...}}``. Responses are one
JSON line. Errors are protocol messages (what to fix), never truth.
"""

from __future__ import annotations

import json
import socketserver
import threading
from pathlib import Path

from abductbench.episode import workspace as wsmod
from abductbench.episode.protocol import ProtocolError, Session

MAX_REQUEST = 1_000_000

CLIENT = r'''#!/usr/bin/env python3
"""Episode client. Usage: ./episode status | register prereg.json | measure | final final.json"""
import json, socket, sys
SOCK = {sock!r}
def main(argv):
    if not argv or argv[0] not in ("status", "register", "measure", "final"):
        print(__doc__); return 1
    cmd, payload = argv[0], None
    if cmd in ("register", "final"):
        if len(argv) != 2:
            print(__doc__); return 1
        try:
            payload = json.load(open(argv[1]))
        except Exception as e:
            print(json.dumps({{"error": f"cannot read {{argv[1]}} as JSON: {{e}}"}})); return 1
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    s.sendall((json.dumps({{"cmd": cmd, "payload": payload}}) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    reply = json.loads(buf.decode() or "{{}}")
    print(json.dumps(reply, indent=1))
    return 0 if "error" not in reply else 1
sys.exit(main(sys.argv[1:]))
'''


def client_text(sock_path: str) -> str:
    return CLIENT.format(sock=sock_path)


class EpisodeService:
    """Applies client requests to a Session; writes measured data into the host workspace."""

    def __init__(self, session: Session, workspace: Path):
        self.s = session
        self.ws = Path(workspace)
        self.lock = threading.Lock()

    def handle(self, req: dict) -> dict:
        with self.lock:
            try:
                return self._handle(req)
            except ProtocolError as e:
                return {"error": str(e)}
            except Exception as e:  # never leak internals beyond the exception type
                self.s._log("server_error", {"error": repr(e)[:2000]})
                return {"error": f"internal error ({type(e).__name__}); request not applied"}

    def _handle(self, req: dict) -> dict:
        cmd = req.get("cmd") if isinstance(req, dict) else None
        if cmd == "status":
            return self.s.status()
        if cmd == "register":
            return self.s.register(req.get("payload"))
        if cmd == "measure":
            q, obs = self.s.measure()
            if self.s.cfg.family == "orbit":
                from abductbench.episode import orbitworkspace as ows

                name = ows.measurement_name(self.s.n_measured, q)
                (self.ws / name).write_text(ows.measurement_text(q, obs))
                return {"measured": q, "file": name, "budget_left": self.s.budget_left}
            name = wsmod.measurement_name(self.s.n_measured, q)
            (self.ws / name).write_text(wsmod.csv_text(obs))
            recorded = len(next(iter(obs.values())))
            return {"measured": q, "events_recorded": recorded, "file": name, "budget_left": self.s.budget_left}
        if cmd == "final":
            return self.s.final(req.get("payload"))
        return {"error": "unknown command"}


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(MAX_REQUEST)
        try:
            req = json.loads(line.decode())
        except Exception:
            reply = {"error": "request is not valid JSON"}
        else:
            reply = self.server.service.handle(req)
        self.wfile.write((json.dumps(reply, default=float) + "\n").encode())


class _Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


def start_server(service: EpisodeService, sock_path: Path) -> tuple[_Server, threading.Thread]:
    sock_path = Path(sock_path)
    if sock_path.exists():
        sock_path.unlink()
    srv = _Server(str(sock_path), _Handler)
    srv.service = service
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, th
