#!/bin/sh
# Runs one libprobe E2E test bundle: executables cross-built by libprobe's
# own CI, and the plan that says how to run them. No source is involved.
# POSIX sh: it runs on the Linux, macOS and Windows (Git Bash) runners and
# inside the FreeBSD, OpenBSD and NetBSD guests of external-e2e.yml.
#
# Usage:
#   libprobe-e2e-plan.sh check  <bundle>         refuse anything but plan.txt + bin/<file>
#   libprobe-e2e-plan.sh tests  <bundle>         every `run` line; all run, any failure fails
#   libprobe-e2e-plan.sh report <bundle> <json>  the `report` line, stdout into <json>
#
# Plan grammar, one stage per line, single spaces:
#   run    <stage> bin/<file> [args...]
#   report <stage> bin/<file>
# Arguments are restricted to [A-Za-z0-9_:.=-], so a line is never shell.
set -u

die() { echo "::error::$*" >&2; exit 1; }

check() {
  b=$1
  [ -f "$b/plan.txt" ] || die "bundle $b has no plan.txt"
  odd=$(find "$b" ! -type f ! -type d | head -n 1)
  [ -z "$odd" ] || die "bundle holds a non-regular file: $odd"
  odd=$(find "$b" -type f ! -path "$b/plan.txt" ! -path "$b/bin/*" | head -n 1)
  [ -z "$odd" ] || die "bundle holds something other than plan.txt and bin/: $odd"
  odd=$(find "$b/bin" -mindepth 1 -type d | head -n 1)
  [ -z "$odd" ] || die "bundle holds a directory under bin/: $odd"
  if grep -Ev '^(run|report) [a-z0-9._-]+ bin/[A-Za-z0-9._-]+( [A-Za-z0-9_:.=-]+)*$' "$b/plan.txt" >/dev/null; then
    die "plan.txt has a line out of grammar"
  fi
  while read -r _verb _stage bin _rest; do
    [ -f "$b/$bin" ] || die "plan names $bin, absent from the bundle"
  done < "$b/plan.txt"
  # Artifacts do not keep the mode bits.
  chmod +x "$b"/bin/*
  # Apple silicon runs nothing unsigned: ad-hoc sign what the cross linker left.
  if [ "$(uname -s)" = Darwin ]; then
    for f in "$b"/bin/*; do codesign -s - -f "$f" >/dev/null 2>&1 || true; done
  fi
  echo "bundle ok: $(grep -c . "$b/plan.txt") stage(s)"
}

tests() {
  b=$1 failed="" n=0
  check "$b" >/dev/null
  # One stage at a time, every one of them: a red stage must not hide the
  # next binary's result (cargo's --no-fail-fast, as before).
  while read -r verb stage bin args; do
    [ "$verb" = run ] || continue
    n=$((n + 1))
    echo "::group::$stage"
    # shellcheck disable=SC2086 # the arguments are the plan's words
    if (cd "$b" && "./$bin" $args </dev/null); then
      echo "::endgroup::"; echo "PASSED $stage"
    else
      rc=$?; echo "::endgroup::"; echo "FAILED $stage (exit $rc)"; failed="$failed $stage"
    fi
  done < "$b/plan.txt"
  [ "$n" -gt 0 ] || die "plan has no run stage"
  [ -z "$failed" ] || die "failed stages:$failed"
  echo "every stage passed ($n)"
}

report() {
  b=$1 out=$2
  check "$b" >/dev/null
  case "$out" in /*) ;; *) out="$(pwd)/$out" ;; esac
  line=$(grep '^report ' "$b/plan.txt" | head -n 1)
  [ -n "$line" ] || die "plan has no report stage"
  # shellcheck disable=SC2086 # the plan line is split into its words on purpose
  set -- $line
  (cd "$b" && "./$3" </dev/null) > "$out"
}

case "${1:-}" in
  check) check "${2:?bundle}" ;;
  tests) tests "${2:?bundle}" ;;
  report) report "${2:?bundle}" "${3:?output}" ;;
  *) die "usage: $0 check|tests <bundle> | report <bundle> <json>" ;;
esac
