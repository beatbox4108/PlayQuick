#!/usr/bin/env bash
set -euo pipefail

arch="${1:?architecture is required}"
version="0.41.0"
commit="2c219aa822df18a1b7fd9abe3e151cd93ad67307"

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  build-essential git meson ninja-build pkg-config python3-docutils \
  libasound2-dev libavcodec-dev libavdevice-dev libavfilter-dev \
  libavformat-dev libavutil-dev libjpeg-dev libplacebo-dev libpulse-dev \
  libswresample-dev libswscale-dev libuchardet-dev libva-dev libvdpau-dev \
  libx11-dev libxext-dev libxinerama-dev libxkbcommon-dev libxrandr-dev \
  libxss-dev libxv-dev zlib1g-dev

git clone --filter=blob:none https://github.com/mpv-player/mpv.git mpv-source
git -C mpv-source checkout "${commit}"
test "$(git -C mpv-source describe --tags --exact-match)" = "v${version}"
meson setup mpv-source/build mpv-source \
  --buildtype=release --prefix=/usr \
  -Dlibmpv=false -Dtests=false -Dmanpage-build=disabled
meson compile -C mpv-source/build

package="mpv-linux-${arch}"
mkdir -p "dist/${package}"
cp mpv-source/build/mpv "dist/${package}/mpv"
cp mpv-source/LICENSE.GPL "dist/${package}/LICENSE.GPL"
cp mpv-source/LICENSE.LGPL "dist/${package}/LICENSE.LGPL"
tar -C "dist/${package}" -czf "dist/${package}.tar.gz" .
