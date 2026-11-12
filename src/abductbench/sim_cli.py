"""Command-line simulator for mode-2 workspaces.

The ``sim`` wrapper written by ``make_workspace`` runs::

    python -m abductbench.sim_cli --token <task dir name> --state-root <dir> measure <type> [--arg k=v ...]
    python -m abductbench.sim_cli --token <task dir name> --state-root <dir> budget

The token is resolved to a variant by hashing the variant ids of mode-2 configs
(no config is stored on disk). Every query is charged in the ledger before
any data is returned.

Exit codes: 0 success, 1 usage or query error, 2 insufficient budget.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from abductbench.config import VariantConfig, all_variants
from abductbench.ledger import LOG_NAME, Ledger
from abductbench.tasks import answer_query, query_cost
from abductbench.workspace import TOKEN_SCAN_SEEDS, _dir_name


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # JSON on stdout, like every other failure
        _emit({"error": message})
        sys.exit(1)


def _emit(obj: dict) -> None:
    print(json.dumps(obj, sort_keys=True))


def resolve_config(token: str) -> VariantConfig | None:
    for cfg in all_variants(seeds=range(TOKEN_SCAN_SEEDS), modes=(2,)):
        if _dir_name(cfg.variant_id) == token:
            return cfg
    return None


def parse_kv(items: list[str]) -> dict:
    args: dict = {}
    for item in items:
        key, sep, raw = item.partition("=")
        if not sep or not key:
            raise ValueError(f"argument {item!r} must have the form key=value")
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
        args[key] = value
    return args


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="sim")
    parser.add_argument("--token", required=True)
    parser.add_argument("--state-root", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    measure = sub.add_parser("measure")
    measure.add_argument("query_type")
    measure.add_argument("--arg", action="append", default=[], metavar="KEY=VALUE")
    sub.add_parser("budget")
    ns = parser.parse_args(argv)

    cfg = resolve_config(ns.token)
    if cfg is None:
        _emit({"error": "unknown workspace token"})
        return 1
    ledger_dir = ns.state_root / ns.token
    if not (ledger_dir / LOG_NAME).exists():
        _emit({"error": "no ledger for this workspace"})
        return 1
    ledger = Ledger(ledger_dir)

    if ns.command == "budget":
        _emit({"remaining": ledger.remaining})
        return 0

    try:
        cost = query_cost(cfg, ns.query_type)
        args = parse_kv(ns.arg)
        ok, result = ledger.spend(
            ns.query_type,
            cost,
            lambda n: (args, answer_query(cfg, ns.query_type, {**args, "_n": n})),
        )
    except ValueError as exc:
        _emit({"error": str(exc)})
        return 1
    if not ok:
        _emit({"error": "insufficient budget", "remaining": ledger.remaining})
        return 2
    _emit(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
