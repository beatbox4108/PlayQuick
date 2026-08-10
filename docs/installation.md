# Installation

## Supported systems

- Linux x86_64 and ARM64: Ubuntu 22.04+, Debian 12+, Fedora 40+, and current Arch
- Windows 10/11 x86_64 and ARM64
- Python 3.12 through 3.14

macOS and musl-based Linux are currently best-effort and require an externally
installed mpv.

## Source installation

```console
git clone https://github.com/beatbox4108/PlayQuick.git
cd PlayQuick
uv sync --all-groups
uv run playquick doctor
uv run playquick
```

PlayQuick searches for mpv in this order: the configured path, `PATH`, then its
managed user runtime. If none is available, the TUI offers to download a
checksum-verified build without administrator privileges.

```console
uv run playquick doctor --install-mpv
uv run playquick doctor --repair-mpv
```

Managed builds are stored below the platform-specific PlayQuick user data
directory. Their source, build recipe, checksums, and license notices are
published alongside each `mpv-v*` GitHub Release.

## Add music

Add semicolon-separated directories in the settings dialog, or scan directly:

```console
uv run playquick scan "/home/me/Music"
```

