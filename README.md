# PlayQuick

PlayQuick is a keyboard-first terminal music player for local libraries, with
an optional experimental Spotify Remote controller. Local audio is played by
an isolated `mpv` process; Spotify audio always remains on an official Spotify
Connect device.

> PlayQuick is an independent project and is not affiliated with or endorsed
> by Spotify AB.

## Development setup

Requirements: Python 3.12–3.14 and [uv](https://docs.astral.sh/uv/).

```console
uv sync --all-groups
uv run playquick doctor
uv run playquick
```

The first release targets glibc-based Linux distributions and Windows on
x86_64 and ARM64. See `docs/installation.md` for platform details.

Documentation: [installation](docs/installation.md), [keyboard controls](docs/keys.md),
[Spotify Remote](docs/spotify.md), [privacy](docs/privacy.md), and
[architecture](docs/architecture.md).

## Status

PlayQuick v0.1 is under active development. Spotify Remote is optional and
experimental because Spotify Developer Mode availability and API contracts can
change independently of PlayQuick.

## License

PlayQuick is released under the MIT License. Managed mpv downloads are separate
programs distributed under their own licenses; see `THIRD_PARTY_NOTICES.md`.
