from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="playquick", description="Terminal music player")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("run", help="Launch the TUI")
    subcommands.add_parser("doctor", help="Inspect the runtime environment")
    scan = subcommands.add_parser("scan", help="Scan a music directory")
    scan.add_argument("paths", nargs="+")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command in (None, "run"):
        from playquick.tui.app import PlayQuickApp

        PlayQuickApp().run()
        return
    if args.command == "doctor":
        from playquick.runtime.doctor import run_doctor

        raise SystemExit(run_doctor())
    if args.command == "scan":
        from playquick.commands import scan_paths

        raise SystemExit(scan_paths(args.paths))

