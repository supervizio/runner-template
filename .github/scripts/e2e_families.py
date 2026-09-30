#!/usr/bin/env python3
"""Which of agent's families did the dispatching run build? (e2e.yml, merge lane)

WIRED INTO: the `resolve` job of .github/workflows/e2e.yml, merge lane only
(`inputs.mode != 'release'`). It prints `<family>=true|false` for each family,
which resolve outputs and every leg's `if:` reads: a leg of a family that is
`false` is skipped, and `report` records it `not-built`, which passes. Release
mode never runs this: every leg runs there, and validate-release.yml requires
every one of them.

agent's ci.yml builds only the families a pull request can affect, and says
which in its dispatch: `built`, space-separated. That word decides. Without it
-- a manual dispatch that leaves `built` empty, an agent run older than it -- a
family counts as built when the run carries an artifact of it
(`supervizio-<family>-...`), which is how the illumos and Solaris legs were
decided before any other family could be missing.

FAIL-CLOSED, in the direction that matters: `false` comes only from a word that
omits the family, or from a listing that has none of its artifacts. A word
naming a family this script does not know is an error (the protocol drifted),
and so is a word that names none. A declared family whose artifacts are absent
still runs, and its legs fail at their download, loudly: that is a broken
producer, not a family the change could not reach. No listing and no word:
every family is empty, and every leg runs.

Input: the run's downloadable artifact names on stdin, one per line, when
AGENT_LISTED=true; nothing to read otherwise.
Env: EVENT (github.event_name), PAYLOAD (toJSON(github.event.client_payload)),
INPUT_BUILT (the workflow_dispatch input), AGENT_LISTED.
Output: `<family>=<value>` lines on stdout; `::error::`/`::warning::`/
`::notice::` lines on stderr. Exit 1 on an error.

Pinned by release-contract/tests/test_release_contract.py (E2eFamilies).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

FAMILIES = ("linux", "windows", "darwin", "freebsd", "netbsd", "openbsd", "illumos", "solaris")


def declared_word(event: str, payload: str, input_built: str) -> Optional[str]:
    """The dispatch's `built`, or None when it says nothing."""
    if event == "repository_dispatch":
        try:
            body = json.loads(payload or "null")
        except ValueError:
            body = None
        if isinstance(body, dict) and "built" in body:
            return str(body["built"] if body["built"] is not None else "")
        return None
    if event == "workflow_dispatch" and input_built.strip():
        return input_built
    return None


def decide(word: Optional[str], names: Optional[Set[str]]) -> Tuple[Optional[Dict[str, str]], List[str]]:
    """({family: 'true'|'false'|''}, messages); None instead of the dict on an error."""
    msgs: List[str] = []

    def present(fam: str) -> bool:
        return any(n.startswith(f"supervizio-{fam}-") for n in (names or ()))

    if word is not None:
        tokens = word.split()
        unknown = sorted(set(tokens) - set(FAMILIES))
        if unknown:
            return None, [f"::error::the dispatch says it built {' '.join(unknown)}, which is no family this "
                          f"workflow knows ({' '.join(FAMILIES)}): the dispatch protocol drifted"]
        if not tokens:
            return None, ["::error::the dispatch says it built no family: there is nothing to test"]
        flags = {fam: str(fam in tokens).lower() for fam in FAMILIES}
        if names is not None:
            for fam in FAMILIES:
                if fam in tokens and not present(fam):
                    msgs.append(f"::warning::the dispatch says {fam} was built, but the run carries no "
                                f"supervizio-{fam}-* artifact: its legs will fail at their download")
                if fam not in tokens and present(fam):
                    msgs.append(f"::notice::the run carries {fam} artifacts it does not declare built: "
                                f"{fam}'s legs are not run")
        why = "the dispatch's word"
    elif names is None:
        return {fam: "" for fam in FAMILIES}, ["::warning::no artifact listing and no `built` word: every leg runs"]
    else:
        flags = {fam: str(present(fam)).lower() for fam in FAMILIES}
        why = "the artifacts the run carries (the dispatch has no `built`)"
        if not any(v == "true" for v in flags.values()):
            return None, ["::error::the agent run carries no artifact of any family: nothing here can be tested"]

    # Checks on the families that run, as the pre-check always made them.
    if names is not None:
        if flags["linux"] == "true" and "supervizio-linux-amd64" not in names:
            return None, msgs + ["::error::the agent run built linux but has no downloadable supervizio-linux-amd64 "
                                 "- the docker legs cannot run. If it is expired, dispatch against a newer run."]
        if flags["openbsd"] == "true":
            for arch in ("amd64", "arm64"):
                if f"supervizio-openbsd-{arch}-pkg" not in names:
                    msgs.append(f"::warning::no supervizio-openbsd-{arch}-pkg - e2e-bsd-openbsd-{arch} will fail. "
                                "Its producer is agent's package-openbsd job.")
        if flags["linux"] == "true":
            if "supervizio-amd64.xbps" not in names:
                msgs.append("::warning::no supervizio-amd64.xbps - both void-xbps legs will fail. "
                            "Its producer is agent's packages-xbps job.")
            for a in ("supervizio-linux-amd64-musl", "supervizio-linux-arm64-musl"):
                if a not in names:
                    msgs.append(f"::warning::no {a} - the four gentoo-portage and nixos-nix legs will fail. "
                                "Its producer is agent's build-cross job.")
        for fam in ("illumos", "solaris"):
            if flags[fam] == "true":
                binary = f"supervizio-{fam}-amd64" in names
                pkg = f"supervizio-{fam}-amd64-pkg" in names
                if binary != pkg:
                    msgs.append(f"::warning::only one of supervizio-{fam}-amd64 and supervizio-{fam}-amd64-pkg - "
                                f"e2e-{fam}-amd64 will fail on the other. Its producer is agent's package-solarish job.")
    built = [f for f in FAMILIES if flags[f] == "true"]
    skipped = [f for f in FAMILIES if flags[f] == "false"]
    msgs.append(f"built, per {why}: {' '.join(built) or 'none'}; not built, their legs report not-built: "
                f"{' '.join(skipped) or 'none'}")
    return flags, msgs


def main() -> int:
    word = declared_word(os.environ.get("EVENT", ""), os.environ.get("PAYLOAD", ""),
                         os.environ.get("INPUT_BUILT", ""))
    names: Optional[Set[str]] = None
    if os.environ.get("AGENT_LISTED") == "true":
        names = {line.strip() for line in sys.stdin if line.strip()}
    flags, msgs = decide(word, names)
    for m in msgs:
        print(m, file=sys.stderr)
    if flags is None:
        return 1
    for fam in FAMILIES:
        print(f"{fam}={flags[fam]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
