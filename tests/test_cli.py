from playquick.cli import build_parser


def test_default_command_is_tui() -> None:
    assert build_parser().parse_args([]).command is None


def test_scan_accepts_multiple_paths() -> None:
    args = build_parser().parse_args(["scan", "Music", "More Music"])
    assert args.paths == ["Music", "More Music"]


def test_spotify_login_can_skip_opening_a_browser() -> None:
    args = build_parser().parse_args(["spotify", "login", "--no-browser"])

    assert args.action == "login"
    assert args.no_browser
