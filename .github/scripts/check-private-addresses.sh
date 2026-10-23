#!/usr/bin/env bash
# check-private-addresses.sh -- fail if any tracked file holds an RFC 1918
# (private IPv4) address.
#
# This repository is public. A private address in it names a host on someone's
# network, and once pushed it stays readable in history, forks and caches, so
# the only safe state is none at HEAD. Documentation examples use placeholders
# such as <host-ip> or <private-cidr> instead. There is deliberately no
# allowlist: an exception would be the first place a real address hides.
#
# Only file:line is printed, never the matched text, so the CI log does not
# repeat what it found.
#
# Usage: bash .github/scripts/check-private-addresses.sh   (from the repo root)
set -euo pipefail

octet='[0-9]{1,3}'
# A leading digit or dot is excluded so that, for example, the tail of a longer
# dotted version string is not read as an address.
pattern="(^|[^0-9.])(10\\.${octet}\\.${octet}\\.${octet}|172\\.(1[6-9]|2[0-9]|3[01])\\.${octet}\\.${octet}|192\\.168\\.${octet}\\.${octet})"

found=0
while IFS= read -r -d '' file; do
  # A tracked file deleted in the working tree has nothing left to leak.
  [ -f "$file" ] || continue
  # -I skips binary files; -n gives the line, the text is dropped below.
  if lines=$(grep -nIE -- "$pattern" "$file" | cut -d: -f1); then
    for line in $lines; do
      printf '%s:%s: RFC 1918 address\n' "$file" "$line"
    done
    found=1
  fi
done < <(git ls-files -z)

if [ "$found" -ne 0 ]; then
  echo "Private IPv4 addresses found in tracked files (locations above)." >&2
  echo "Replace each with a placeholder or a secrets.* reference." >&2
  exit 1
fi
echo "No RFC 1918 address in tracked files."
