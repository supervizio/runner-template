#!/usr/bin/env python3
"""Nothing of agent's or libprobe's outlives its job here: the static half.

Rules, checked on every .github/workflows/*.yml and .github/actions/*/action.yml
(stdlib only; the YAML is read by indentation, never executed):

R1  Every step whose `uses:` is actions/upload-artifact carries
    `retention-days: 1` in its own `with:`.
R2  Per file, the number of lines mentioning upload-artifact equals the
    number of `retention-days: 1` lines, and no other retention-days value
    appears. This is supervizio/agent#297's acceptance check, kept true by
    construction (a comment naming the action counts: word it otherwise).
R3  In a PRODUCT workflow or action (one that holds agent's or libprobe's
    downloaded artifacts, checkout, candidate or package bytes; PRODUCT below)
    nothing writes the Actions cache, because the cache outlives the job and a
    public repository's default-branch cache is restorable by any pull
    request's workflow, forks included:
      - no `uses: actions/cache` (cache, cache/save, cache/restore);
      - every actions/setup-* step says `cache: false` (setup-go caches by
        default) and no other `cache:` value appears;
      - no `cache-after-prepare: true` (vmactions syncs the workspace into the
        guest BEFORE prepare, so the cached image holds it), except the jobs
        in CACHE_AFTER_PREPARE_EXCEPTIONS, an open finding listed in CLAUDE.md;
      - no docker `type=gha` cache export.
R4  Anywhere, an actions/cache `path:` never names a product location
    (supervizio, libprobe, agent, a candidate, or the bin/ pkg/ dl/ payload/
    directories the legs download into).
R5  A workflow that mentions a private repository, the App token, the release
    candidate action or a reusable lane must be classified: PRODUCT, or
    NOT_PRODUCT with the reason. A new lane cannot slip past R3 unclassified.

Exit 0 when clean, 1 with one line per violation otherwise.
"""
import os
import re
import sys

PRODUCT = {
    ".github/workflows/e2e.yml",
    ".github/workflows/external-e2e.yml",
    ".github/workflows/agent-packages.yml",
    ".github/workflows/libprobe-solarish.yml",
    ".github/workflows/validate-release.yml",
    ".github/actions/release-candidate/action.yml",
    ".github/actions/qemu-vm/action.yml",
}

NOT_PRODUCT = {
    ".github/workflows/selftest.yml": "reads nothing private (wiring proof)",
    ".github/workflows/sweep.yml": "deletes runs, reads none",
    ".github/workflows/validate-release-doorbell.yml": "posts a status, checks out nothing",
    ".github/workflows/dinit-container-proof.yml": "names agent only to say it is not checked out",
    ".github/workflows/cleanup-product-runs.yml": "deletes runs, reads none",
    ".github/workflows/cleanup-external-e2e.yml": "deletes runs, reads none",
}

# e2e.yml's three Alpine legs need vmactions' post-prepare reboot for psi=1;
# the prepared image they cache holds the synced workspace. Open finding
# (CLAUDE.md, "Product runs: what stays and for how long"). Shrink, never grow.
CACHE_AFTER_PREPARE_EXCEPTIONS = {
    (".github/workflows/e2e.yml", "e2e-linux-alpine-openrc"),
    (".github/workflows/e2e.yml", "e2e-linux-alpine-runit"),
    (".github/workflows/e2e.yml", "e2e-linux-alpine-s6"),
}

MARKERS = re.compile(
    r"supervizio/(agent|libprobe)|source_repo|SOURCE_REPO|create-github-app-token"
    r"|release-candidate|bridge pull|/reusable-"
)
PRODUCT_PATH = re.compile(r"supervizio|libprobe|agent|candidate|(^|[\s/'\"])(bin|pkg|dl|payload)(/|$|\s)")


def indent(line):
    return len(line) - len(line.lstrip(" "))


def strip_comment(line):
    # Good enough for workflow files: a '#' after whitespace starts a comment.
    return re.split(r"\s#", line, maxsplit=1)[0].rstrip()


def steps(lines):
    """Yield (job, first_line_no, [lines]) for each `- ` list item holding a uses:/run:."""
    job = None
    jobs_indent = None
    i = 0
    while i < len(lines):
        line = lines[i]
        s = strip_comment(line)
        if re.match(r"^jobs:\s*$", s):
            jobs_indent = 2
        elif jobs_indent is not None and indent(line) == jobs_indent and re.match(r"^\s+[A-Za-z0-9_-]+:\s*$", s):
            job = s.strip()[:-1]
        m = re.match(r"^(\s*)- ", line)
        if m:
            ind = len(m.group(1))
            block = [line]
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() and not nxt.lstrip().startswith("#") and indent(nxt) <= ind:
                    break
                block.append(nxt)
                j += 1
            yield job, i + 1, block
        i += 1


def uses_of(block):
    m = re.match(r"^\s*-?\s*uses:\s*([^\s#]+)", strip_comment(block[0]).replace("- uses:", "uses:"))
    if m:
        return m.group(1)
    head = indent(block[0]) + 2
    for line in block[1:]:
        s = strip_comment(line)
        if indent(line) == head:
            m = re.match(r"^\s*uses:\s*([^\s#]+)", s)
            if m:
                return m.group(1)
    return None


def keyval(block, key):
    """Values of `key:` anywhere in the step (with: is the only nesting used)."""
    out = []
    for line in block:
        m = re.match(r"^\s*-?\s*" + re.escape(key) + r":\s*(.*)$", strip_comment(line))
        if m:
            out.append(m.group(1).strip().strip("'\""))
    return out


def check_file(rel, text):
    errs = []
    lines = text.splitlines()
    up = sum("upload-artifact" in l for l in lines)
    r1 = sum(bool(re.search(r"retention-days:\s*1\s*$", strip_comment(l))) for l in lines)
    if up != r1:
        errs.append(f"{rel}: {up} line(s) mention upload-artifact but {r1} say 'retention-days: 1' (R2)")
    for n, l in enumerate(lines, 1):
        m = re.search(r"retention-days:\s*(.*)$", strip_comment(l))
        if m and m.group(1).strip() != "1":
            errs.append(f"{rel}:{n}: retention-days is '{m.group(1).strip()}', must be 1 (R2)")

    product = rel in PRODUCT
    if not product and rel not in NOT_PRODUCT and MARKERS.search(text):
        errs.append(f"{rel}: mentions a private repository or a product lane but is in neither PRODUCT nor NOT_PRODUCT of {os.path.basename(__file__)} (R5)")

    for job, n, block in steps(lines):
        uses = uses_of(block) or ""
        if uses.startswith("actions/upload-artifact@"):
            if "1" not in keyval(block, "retention-days"):
                errs.append(f"{rel}:{n}: upload-artifact step without 'retention-days: 1' (R1)")
        if uses.startswith("actions/cache"):
            for p in keyval(block, "path"):
                if PRODUCT_PATH.search(p):
                    errs.append(f"{rel}:{n}: actions/cache path '{p}' names a product location (R4)")
            if product:
                errs.append(f"{rel}:{n}: actions/cache in a product workflow (R3)")
        if not product:
            continue
        if uses.startswith("actions/setup-") and "false" not in keyval(block, "cache"):
            errs.append(f"{rel}:{n}: {uses.split('@')[0]} without 'cache: false' in a product workflow (R3)")
        for v in keyval(block, "cache"):
            if v != "false":
                errs.append(f"{rel}:{n}: 'cache: {v}' in a product workflow (R3)")
        if "true" in keyval(block, "cache-after-prepare") and (rel, job) not in CACHE_AFTER_PREPARE_EXCEPTIONS:
            errs.append(f"{rel}:{n}: cache-after-prepare: true in job {job} of a product workflow (R3)")
        if any("type=gha" in l for l in block):
            errs.append(f"{rel}:{n}: docker type=gha cache in a product workflow (R3)")
    return errs


def files(root):
    wf = os.path.join(root, ".github", "workflows")
    for name in sorted(os.listdir(wf)):
        if name.endswith((".yml", ".yaml")):
            yield os.path.join(wf, name)
    act = os.path.join(root, ".github", "actions")
    if os.path.isdir(act):
        for name in sorted(os.listdir(act)):
            for f in ("action.yml", "action.yaml"):
                p = os.path.join(act, name, f)
                if os.path.isfile(p):
                    yield p


def main(argv):
    root = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)
    root = os.path.normpath(root)
    errs = []
    seen = set()
    for path in files(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        seen.add(rel)
        with open(path, encoding="utf-8") as fh:
            errs += check_file(rel, fh.read())
    for rel in sorted(PRODUCT - seen):
        errs.append(f"{rel}: listed in PRODUCT but missing")
    for rel, job in sorted(CACHE_AFTER_PREPARE_EXCEPTIONS):
        if rel in seen:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                text = fh.read()
            if not any(j == job and "true" in keyval(b, "cache-after-prepare") for j, _, b in steps(text.splitlines())):
                errs.append(f"{rel}: exception for job {job} is stale (no cache-after-prepare: true there): remove it")
    for e in errs:
        print(e)
    if not errs:
        print(f"run retention: {len(seen)} files clean")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
