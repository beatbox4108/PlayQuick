#!/usr/bin/env bash
set -euo pipefail

arch="${1:?architecture is required}"
jobs="${PLAYQUICK_MPV_JOBS:-4}"
builder_commit="cd1edc11dc6887a50f705717619d879f5a93a488"
builder_image="ghcr.io/shinchiro/archlinux@sha256:8be8be63102aebd01d8297d2f96a0be905a979c0e8418e674b7b6d50b46c6df3"
case "${arch}" in
  x86_64) target="x86_64-w64-mingw32" ;;
  arm64) target="aarch64-w64-mingw32" ;;
  *) echo "unsupported architecture: ${arch}" >&2; exit 2 ;;
esac

if [[ "${PLAYQUICK_MPV_CONTAINER:-}" != "1" ]]; then
  docker run --rm \
    --env PLAYQUICK_MPV_CONTAINER=1 \
    --volume "${PWD}:/work" \
    --workdir /work \
    "${builder_image}" \
    bash scripts/build_mpv_windows.sh "${arch}"
  exit
fi

dump_build_logs() {
  find winbuild-out -type f -name '*.log' -print0 2>/dev/null |
    while IFS= read -r -d '' log; do
      echo "===== ${log} ====="
      tail -n 80 "${log}"
    done
}
trap dump_build_logs ERR

git config --global user.name "PlayQuick CI"
git config --global user.email "playquick-ci@users.noreply.github.com"
git config --global --add safe.directory /work

git clone https://github.com/shinchiro/mpv-winbuild-cmake.git winbuild
git -C winbuild checkout "${builder_commit}"

# The pinned OpenSSL snapshot and ngtcp2 main currently disagree on QUIC APIs.
# mpv only requires curl's regular HTTPS support, so omit the optional HTTP/3
# dependency chain while retaining HTTP/1.1, HTTP/2, and TLS.
sed -i \
  -e '/^[[:space:]]*ngtcp2$/d' \
  -e '/^[[:space:]]*nghttp3$/d' \
  -e 's/-DUSE_NGHTTP3=ON/-DUSE_NGHTTP3=OFF/' \
  -e 's/-DUSE_NGTCP2=ON/-DUSE_NGTCP2=OFF/' \
  -e 's/-DUSE_ECH=ON/-DUSE_ECH=OFF/' \
  -e 's/-DUSE_HTTPSRR=ON/-DUSE_HTTPSRR=OFF/' \
  -e 's/-DUSE_PROXY_HTTP3=ON/-DUSE_PROXY_HTTP3=OFF/' \
  winbuild/packages/curl.cmake
if [[ "${arch}" == "x86_64" ]]; then
  cmake --fresh -S winbuild -B winbuild-out -G Ninja \
    -DTARGET_ARCH="${target}" \
    -DSINGLE_SOURCE_LOCATION="${PWD}/src_packages" \
    -DRUSTUP_LOCATION="${PWD}/clang-root/install_rustup" \
    -DENABLE_CCACHE=ON
  ninja -j "${jobs}" -C winbuild-out download || true
  ninja -j "${jobs}" -C winbuild-out gcc
  ninja -j "${jobs}" -C winbuild-out mpv
else
  cmake --fresh -S winbuild -B winbuild-out -G Ninja \
    -DTARGET_ARCH="${target}" \
    -DCOMPILER_TOOLCHAIN=clang \
    -DCMAKE_INSTALL_PREFIX="${PWD}/clang-root" \
    -DMINGW_INSTALL_PREFIX="${PWD}/winbuild-out/${target}" \
    -DSINGLE_SOURCE_LOCATION="${PWD}/src_packages" \
    -DRUSTUP_LOCATION="${PWD}/clang-root/install_rustup" \
    -DENABLE_CCACHE=ON
  ninja -j "${jobs}" -C winbuild-out download || true
  ninja -j "${jobs}" -C winbuild-out llvm
  ninja -j "${jobs}" -C winbuild-out rustup
  ninja -j "${jobs}" -C winbuild-out llvm-clang
  ninja -j "${jobs}" -C winbuild-out mpv
fi

ninja -j "${jobs}" -C winbuild-out mpv-packaging
mpv_archive="$(find winbuild-out -maxdepth 1 -type f -name 'mpv*.7z' -print -quit)"
test -n "${mpv_archive}"
package="mpv-windows-${arch}"
mkdir -p "dist/${package}"
7z x -y "${mpv_archive}" -o"dist/${package}"
test -n "$(find "dist/${package}" -type f -name mpv.exe -print -quit)"
cp THIRD_PARTY_NOTICES.md "dist/${package}/"
cp scripts/build_mpv_windows.sh "dist/${package}/BUILD_RECIPE.sh"
(cd "dist/${package}" && 7z a -tzip -mx=9 "../${package}.zip" .)
