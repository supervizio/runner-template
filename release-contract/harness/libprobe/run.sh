#!/bin/sh
# Compile consumer.c against a published libprobe pair and run it.
#
# `release_contract.py scenario` (stage prepare) fills a work directory with the
# published `libprobe.a` and `probe.h` of ONE platform, taken out of the release
# tarball after checking it, plus consumer.c, this script and plan.env. This
# script is then run wherever the platform lives -- natively on a hosted runner,
# inside a BSD guest, inside a container -- which is why it is plain POSIX sh:
# FreeBSD, OpenBSD and NetBSD /bin/sh, Alpine's busybox and Git Bash on Windows
# all run it. It needs a C compiler and nothing else: no Python, no network, no
# token.
#
# Usage: run.sh [all|build|exec]   (default all)
#   build  compile the consumer only -- the scratch leg builds in Alpine and
#          executes in an image that holds nothing but the binary;
#   exec   run an already built consumer.
#
# plan.env sets PLATFORM (a libprobe platform name, e.g. linux-amd64-musl) and
# EXPECTED_VERSION (the tag without its "v"). CC overrides the compiler.
#
# The link lines are the system libraries a Rust staticlib needs on each OS
# (what `rustc --print native-static-libs` names for std) plus the ones
# libprobe's own collectors call into. A missing one is a link error, which
# fails the leg: that is a finding about the published archive -- a consumer
# would hit it too -- not a harness detail to paper over.
#
# Writes report.json (consumer.c's report) next to itself. Exit status is the
# consumer's; `release_contract.py scenario --stage check` then judges the
# report independently, so a run that produced nothing fails there too.
set -eu

mode="${1:-all}"
case "$mode" in all|build|exec) ;; *) echo "run.sh: unknown mode '$mode'" >&2; exit 2 ;; esac
W=$(cd "$(dirname "$0")" && pwd)
cd "$W"
. ./plan.env
: "${PLATFORM:?plan.env sets no PLATFORM}"
: "${EXPECTED_VERSION:?plan.env sets no EXPECTED_VERSION}"

exe=./consumer
cflags="-std=c11 -O1 -Wall -Wextra -I."
case "$PLATFORM" in
  linux-*-musl)
    # Static, so the same binary runs in a FROM scratch image: the musl
    # archive's promise is that it needs no libc on the target.
    cc_default=cc
    libs="-static -lpthread -lm -ldl -lc"
    ;;
  linux-*)
    cc_default=cc
    libs="-lgcc_s -lutil -lrt -lpthread -lm -ldl -lc"
    ;;
  darwin-*)
    cc_default=cc
    libs="-lc -lm -framework CoreFoundation -framework IOKit -framework Metal -framework Security -framework SystemConfiguration -framework DiskArbitration"
    ;;
  freebsd-*)
    cc_default=cc
    libs="-lexecinfo -lpthread -lgcc_s -lc -lm -lrt -lutil -lkvm -ldevstat -lnv"
    ;;
  openbsd-*)
    cc_default=cc
    libs="-lc++abi -lpthread -lc -lm -lutil -lkvm"
    ;;
  netbsd-*)
    cc_default=cc
    libs="-lexecinfo -lpthread -lgcc_s -lc -lm -lrt -lutil -lkvm -lnpf"
    ;;
  windows-amd64)
    cc_default=gcc
    exe=./consumer.exe
    ;;
  windows-arm64)
    # The archive is aarch64-pc-windows-gnullvm: it wants an LLVM mingw
    # toolchain (libunwind, compiler-rt), which the workflow puts on PATH.
    cc_default=aarch64-w64-mingw32-clang
    exe=./consumer.exe
    ;;
  *)
    echo "run.sh: no link recipe for platform '$PLATFORM'" >&2
    exit 2
    ;;
esac
case "$PLATFORM" in
  windows-*)
    libs="-lws2_32 -liphlpapi -lntdll -luserenv -lbcrypt -lpsapi -lpowrprof -lcrypt32 -lwevtapi -lwtsapi32 -lmpr -lwinspool -lnetapi32 -lole32 -loleaut32 -lwbemuuid -lsecur32 -ladvapi32 -lsetupapi -lpdh -lversion -lshell32 -luuid -lkernel32 -lsynchronization"
    ;;
esac
CC="${CC:-$cc_default}"

echo "platform $PLATFORM, expecting version $EXPECTED_VERSION"
if [ "$mode" != exec ]; then
  echo "compiler: $CC ($("$CC" --version 2>&1 | head -n 1))"
  rm -f report.json "$exe"
  # Word splitting of $cflags and $libs is intended.
  # shellcheck disable=SC2086
  "$CC" $cflags -o "$exe" consumer.c libprobe.a $libs
  echo "built $exe"
  [ "$mode" = build ] && exit 0
fi
status=0
"$exe" "$EXPECTED_VERSION" report.json || status=$?
echo "consumer exit status: $status"
exit "$status"
