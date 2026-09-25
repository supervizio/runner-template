#!/usr/bin/env bash
# Prints the file name of the image a distribution publishes RIGHT NOW, in its
# build-numbered form, for a caller that verifies it by signature
# (image-checksum-url / image-signature-url on the qemu-vm action).
#
# Why resolve at all: some upstreams rebuild an image IN PLACE under a stable
# name and keep only the newest build. A sha256 pinned against that name goes
# stale on the next rebuild -- openSUSE did it on 2026-09-24, and the leg went
# red on every agent PR with the agent not involved. A pinned build-numbered
# name is no better: the old build is deleted, so the pin becomes a 404.
# Resolving the current build, then checking it against the checksum file the
# distribution SIGNS, keeps the integrity check and drops the hand-kept pin.
#
# Why the build-numbered name rather than the stable one: the stable name is a
# symlink that each mirror updates on its own schedule, so for a while after a
# rebuild a mirror can serve the old image beside the new checksum. A
# build-numbered file never changes content, so whatever mirror serves it
# serves the bytes the signed checksum describes.
#
# usage:
#   resolve-image.sh mirrorcache <directory-url> <stable-name>
#       openSUSE. download.opensuse.org (MirrorCache) announces the build behind
#       a stable name in an X-Media-Version header, and in the <origin> of the
#       name's .meta4 metalink. The build-numbered file is
#       <stem>-Build<version>.<ext>.
#   resolve-image.sh listing <directory-url> <extended-regex>
#       A plain directory index (Rocky Linux). Prints the highest version
#       (sort -V) of the file names matching the regex, which must name a
#       build-numbered file.
set -euo pipefail

die() { echo "::error::resolve-image: $*" >&2; exit 1; }
fetch() { curl -fsSL --retry 5 --retry-all-errors --max-time 120 "$@"; }

[ $# -eq 3 ] || die "usage: resolve-image.sh mirrorcache|listing <directory-url> <name-or-regex>"
mode=$1 dir=${2%/} arg=$3

case "$mode" in
  mirrorcache)
    ext=${arg##*.} stem=${arg%.*}
    # -I without -L: the header rides on the redirect MirrorCache itself sends,
    # not on whatever the mirror answers.
    ver=$(curl -fsSI --retry 5 --retry-all-errors --max-time 60 "$dir/$arg" \
      | tr -d '\r' | awk -F': *' 'tolower($1) == "x-media-version" { print $2; exit }')
    if [ -z "$ver" ]; then
      # A fallback, so a 404 here is an answer, not something to retry.
      ver=$(curl -fsSL --retry 3 --max-time 60 "$dir/$arg.meta4" 2>/dev/null \
        | sed -n "s|.*<origin[^>]*>.*-Build\([0-9][0-9.]*\)\.${ext}</origin>.*|\1|p" | head -1 || true)
    fi
    [[ "$ver" =~ ^[0-9]+(\.[0-9]+)*$ ]] \
      || die "no build behind $dir/$arg: neither an X-Media-Version header nor a metalink origin"
    echo "${stem}-Build${ver}.${ext}"
    ;;
  listing)
    name=$(fetch "$dir/" | grep -oE "$arg" | sort -uV | tail -1 || true)
    [ -n "$name" ] || die "no file matching /$arg/ in $dir/"
    echo "$name"
    ;;
  *)
    die "unknown mode '$mode' (mirrorcache or listing)"
    ;;
esac
