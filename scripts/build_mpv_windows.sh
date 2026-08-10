#!/usr/bin/env bash
set -euo pipefail

arch="${1:?architecture is required}"
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

git clone https://github.com/shinchiro/mpv-winbuild-cmake.git winbuild
git -C winbuild checkout "${builder_commit}"
if [[ "${arch}" == "x86_64" ]]; then
  cmake --fresh -S winbuild -B winbuild-out -G Ninja \
    -DTARGET_ARCH="${target}" \
    -DSINGLE_SOURCE_LOCATION="${PWD}/src_packages" \
    -DRUSTUP_LOCATION="${PWD}/clang-root/install_rustup" \
    -DENABLE_CCACHE=ON
  ninja -C winbuild-out download || true
  ninja -C winbuild-out gcc
  ninja -C winbuild-out mpv
else
  cmake --fresh -S winbuild -B winbuild-out -G Ninja \
    -DTARGET_ARCH="${target}" \
    -DCOMPILER_TOOLCHAIN=clang \
    -DCMAKE_INSTALL_PREFIX="${PWD}/clang-root" \
    -DMINGW_INSTALL_PREFIX="${PWD}/winbuild-out/${target}" \
    -DSINGLE_SOURCE_LOCATION="${PWD}/src_packages" \
    -DRUSTUP_LOCATION="${PWD}/clang-root/install_rustup" \
    -DENABLE_CCACHE=ON
  ninja -C winbuild-out download || true
  ninja -C winbuild-out llvm
  ninja -C winbuild-out rustup
  ninja -C winbuild-out llvm-clang
  ninja -C winbuild-out mpv
fi

ninja -C winbuild-out mpv-packaging
mpv_archive="$(find winbuild-out -maxdepth 1 -type f -name 'mpv*.7z' -print -quit)"
test -n "${mpv_archive}"
package="mpv-windows-${arch}"
mkdir -p "dist/${package}"
7z x -y "${mpv_archive}" -o"dist/${package}"
test -n "$(find "dist/${package}" -type f -name mpv.exe -print -quit)"
cp THIRD_PARTY_NOTICES.md "dist/${package}/"
cp scripts/build_mpv_windows.sh "dist/${package}/BUILD_RECIPE.sh"
(cd "dist/${package}" && 7z a -tzip -mx=9 "../${package}.zip" .)
