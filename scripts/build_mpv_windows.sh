#!/usr/bin/env bash
set -euo pipefail

arch="${1:?architecture is required}"
builder_commit="cd1edc11dc6887a50f705717619d879f5a93a488"
case "${arch}" in
  x86_64) target="x86_64-w64-mingw32" ;;
  arm64) target="aarch64-w64-mingw32" ;;
  *) echo "unsupported architecture: ${arch}" >&2; exit 2 ;;
esac

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  asciidoc automake autopoint bison build-essential ccache clang cmake curl \
  docbook2x flex g++-multilib gcc-multilib gettext git gperf libgcrypt-dev \
  libgmp-dev libmpc-dev libmpfr-dev libtool libtool-bin lld mercurial \
  meson nasm ninja-build p7zip-full pkgconf ragel re2c subversion \
  texinfo unzip yasm
python3 -m pip install --break-system-packages jsonschema mako rst2pdf

git clone https://github.com/shinchiro/mpv-winbuild-cmake.git winbuild
git -C winbuild checkout "${builder_commit}"
cmake -S winbuild -B winbuild-out -G Ninja \
  -DTARGET_ARCH="${target}" \
  -DCOMPILER_TOOLCHAIN=clang \
  -DCMAKE_INSTALL_PREFIX="${PWD}/clang-root" \
  -DMINGW_INSTALL_PREFIX="${PWD}/mingw-root"
ninja -C winbuild-out llvm rustup llvm-clang mpv

mpv_exe="$(find winbuild-out -type f -name mpv.exe -print -quit)"
test -n "${mpv_exe}"
package="mpv-windows-${arch}"
mkdir -p "dist/${package}"
cp "${mpv_exe}" "dist/${package}/mpv.exe"
cp winbuild/LICENSE* "dist/${package}/" 2>/dev/null || true
(cd "dist/${package}" && zip -9 -r "../${package}.zip" .)
