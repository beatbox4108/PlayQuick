from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="playquick", description="Terminal music player")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("run", help="Launch the TUI")
    doctor = subcommands.add_parser("doctor", help="Inspect the runtime environment")
    doctor.add_argument("--install-mpv", action="store_true")
    doctor.add_argument("--repair-mpv", action="store_true")
    scan = subcommands.add_parser("scan", help="Scan a music directory")
    scan.add_argument("paths", nargs="+")
    spotify = subcommands.add_parser("spotify", help="Manage Spotify Remote authorization")
    spotify.add_argument("action", choices=("login", "logout"))
    spotify.add_argument(
        "--no-browser", action="store_true", help="Print the authorization URL only"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command in (None, "run"):
        from playquick.tui.app import PlayQuickApp

        PlayQuickApp().run()
        return
    if args.command == "doctor":
        from playquick.runtime.doctor import run_doctor

        raise SystemExit(run_doctor(install=args.install_mpv, repair=args.repair_mpv))
    if args.command == "scan":
        from playquick.commands import scan_paths

        raise SystemExit(scan_paths(args.paths))
    if args.command == "spotify":
        from playquick.spotify.commands import spotify_command

        raise SystemExit(spotify_command(args.action, open_browser=not args.no_browser))
