#!/usr/bin/env python3
"""Executable form of the supervizio release contract (release-contract/README.md).

The README is the normative text. This file is how a machine checks it, and it is
deliberately the ONLY implementation: the private release workflows, the public
validation workflow and reconcil-release all call it rather than re-deriving the
rules in shell. Where the README and this file disagree, this file is the bug.

Standard library only, Python >= 3.9: it has to run unchanged on the self-hosted
runner, on every GitHub-hosted image, and on a maintainer's laptop, with nothing
to install.

Exit codes: 0 the input satisfies the contract, 1 it violates it (the reasons are
printed), 2 the command could not be evaluated (unreadable input, bad arguments,
network). A caller that must fail closed treats anything but 0 as "no".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_POLICY = os.path.join(HERE, "policy.json")

RECEIPT_SCHEMA = "supervizio.release-receipt/v1"
PAYLOAD_SCHEMA = "supervizio.validate-release/v1"
POLICY_SCHEMA = "supervizio.release-policy/v1"
STATE_SCHEMA = "supervizio.release-state/v1"
LEG_JOB_PREFIX = "leg/"
RUN_NAME_PREFIX = "validate-release"

# repository_dispatch limits, from the REST description of POST /repos/{o}/{r}/dispatches:
# "The maximum number of top-level properties is 10. The total size of the JSON
# payload must be less than 64KB." The size is enforced on the whole request body,
# which is strictly larger than client_payload alone -- the conservative reading.
MAX_CLIENT_PAYLOAD_PROPS = 10
MAX_DISPATCH_BYTES = 65536
MAX_EVENT_TYPE_LEN = 100

# Asset names: what GitHub keeps verbatim, what every OS the legs run on can put on
# disk, and what the manifest line format can carry without escaping. No '/', no
# whitespace, no leading dot or dash.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,254}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TAG_RE = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)
LEG_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*(?:/[a-z0-9]+(?:[.-][a-z0-9]+)*)*$")
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?/[A-Za-z0-9._-]+$")
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
MANIFEST_LINE_RE = re.compile(r"^([0-9a-f]{64})  ([^ ]+)$")

VERDICTS = ("pending", "success", "failure", "error")
# Every value a job conclusion can take in the REST API, plus the two this contract
# adds: "missing" (a required leg no job reported) and "incomplete" (a job that had
# not completed, or reported something unrecognised, or was reported twice).
LEG_RESULTS = (
    "success",
    "failure",
    "cancelled",
    "timed_out",
    "skipped",
    "neutral",
    "action_required",
    "stale",
    "missing",
    "incomplete",
)

RECEIPT_KEYS = {
    "schema",
    "repository",
    "tag",
    "resolved_commit",
    "release_id",
    "candidate_generation",
    "manifest_file",
    "asset_manifest_digest",
    "manifest",
    "support_manifest_digest",
    "support",
    "required_matrix",
    "test_suite_revision",
    "e2e_run_id",
    "e2e_attempt",
    "results",
    "verdict",
    "recorded_at",
    "restored_from",
}
CANDIDATE_KEYS = {
    "repository",
    "tag",
    "resolved_commit",
    "release_id",
    "candidate_generation",
    "manifest_file",
    "asset_manifest_digest",
}
CLIENT_PAYLOAD_KEYS = {"schema", "candidate", "manifest", "support", "staging", "required_matrix"}
STAGING_KEYS = {"repository", "release_id", "tag_name"}


class ContractError(Exception):
    """The input is readable but does not satisfy the contract."""


class UsageError(Exception):
    """The command cannot be evaluated at all (exit 2, never mistaken for a verdict)."""


# --------------------------------------------------------------------------------------
# small typed checks -- every one raises ContractError naming the offending field
# --------------------------------------------------------------------------------------


def _is_int(value: Any) -> bool:
    # bool is an int subclass in Python; a JSON `true` is not a release id.
    return isinstance(value, int) and not isinstance(value, bool)


def _require_int(value: Any, field: str, minimum: int) -> None:
    if not _is_int(value) or value < minimum:
        raise ContractError(f"{field} must be an integer >= {minimum}, got {value!r}")


def _require_match(value: Any, regex: "re.Pattern[str]", field: str) -> None:
    # fullmatch, not match: `$` also matches just before a trailing newline, so
    # match() let 'v1.4.2\n' through as a tag.
    if not isinstance(value, str) or not regex.fullmatch(value):
        raise ContractError(f"{field} {value!r} does not match {regex.pattern}")


def _require_keys(obj: Any, expected: set, field: str) -> None:
    if not isinstance(obj, dict):
        raise ContractError(f"{field} must be a JSON object")
    missing = sorted(expected - set(obj))
    unknown = sorted(set(obj) - expected)
    if missing:
        raise ContractError(f"{field} is missing {', '.join(missing)}")
    if unknown:
        # Strict on purpose: a misspelt key would otherwise be silently ignored and
        # the field it meant to set would read as absent. New fields mean a new schema.
        raise ContractError(f"{field} has unknown key(s) {', '.join(unknown)}")


# --------------------------------------------------------------------------------------
# policy
# --------------------------------------------------------------------------------------


def load_policy(path: Optional[str] = None) -> Dict[str, Any]:
    path = path or DEFAULT_POLICY
    try:
        with open(path, "rb") as fh:
            policy = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise UsageError(f"cannot read policy {path}: {exc}") from exc
    validate_policy(policy)
    return policy


def validate_policy(policy: Dict[str, Any]) -> None:
    if not isinstance(policy, dict) or policy.get("schema") != POLICY_SCHEMA:
        raise ContractError(f"policy schema must be {POLICY_SCHEMA!r}")
    staging = policy.get("staging")
    if not isinstance(staging, dict):
        raise ContractError("policy.staging must be an object")
    _require_match(staging.get("repository"), REPO_RE, "policy.staging.repository")
    for key in ("default_branch", "workflow_path", "event_type"):
        if not isinstance(staging.get(key), str) or not staging[key]:
            raise ContractError(f"policy.staging.{key} must be a non-empty string")
    if len(staging["event_type"]) > MAX_EVENT_TYPE_LEN:
        raise ContractError("policy.staging.event_type is longer than GitHub accepts")
    _require_match(policy.get("receipt_asset"), NAME_RE, "policy.receipt_asset")
    reserved = [policy["receipt_asset"]]
    repos = policy.get("repositories")
    if not isinstance(repos, dict) or not repos:
        raise ContractError("policy.repositories must be a non-empty object")
    for repo, spec in repos.items():
        _require_match(repo, REPO_RE, "policy repository")
        if not isinstance(spec, dict):
            raise ContractError(f"policy for {repo} must be an object")
        _require_match(spec.get("manifest_file"), NAME_RE, f"{repo}.manifest_file")
        if spec["manifest_file"] in reserved:
            raise ContractError(f"{repo}.manifest_file collides with a reserved asset")
        legs = spec.get("legs")
        if not isinstance(legs, list) or not legs:
            raise ContractError(f"{repo}.legs must be a non-empty list")
        seen = set()
        for leg in legs:
            if not isinstance(leg, dict):
                raise ContractError(f"{repo}.legs[] must be objects")
            _require_match(leg.get("id"), LEG_RE, f"{repo} leg id")
            if leg["id"] in seen:
                raise ContractError(f"{repo} lists leg {leg['id']!r} twice")
            seen.add(leg["id"])
            if leg.get("state") not in ("required", "pending-merge"):
                raise ContractError(f"{repo} leg {leg['id']}: state must be required|pending-merge")
            if leg["state"] == "pending-merge" and not leg.get("pr"):
                raise ContractError(f"{repo} leg {leg['id']}: a pending leg must name its PR")
        if not any(leg["state"] == "required" for leg in legs):
            raise ContractError(f"{repo} requires no leg at all")


def repo_policy(policy: Dict[str, Any], repository: str) -> Dict[str, Any]:
    spec = policy["repositories"].get(repository)
    if spec is None:
        raise ContractError(
            f"repository {repository!r} is not governed by this contract "
            f"(known: {', '.join(sorted(policy['repositories']))})"
        )
    return spec


def required_legs(policy: Dict[str, Any], repository: str) -> List[str]:
    """The minimum matrix a release of `repository` must pass: every leg in state
    `required`. `pending-merge` legs are listed so they are not forgotten, but they
    cannot be required before the workflow that runs them exists on main."""
    return [leg["id"] for leg in repo_policy(policy, repository)["legs"] if leg["state"] == "required"]


def receipt_reserved_names(policy: Dict[str, Any], receipt: Dict[str, Any]) -> List[str]:
    """The reserved names of the release a receipt describes: its own manifest file,
    which in audit mode may predate a rename in policy.json."""
    return [policy["receipt_asset"], receipt["manifest_file"]]


def reserved_names(policy: Dict[str, Any], repository: str) -> List[str]:
    """Release assets that are NOT manifest entries: the receipt (it describes the
    manifest, so it cannot be inside it) and the manifest file (its bytes ARE the
    manifest; its digest is asset_manifest_digest itself)."""
    return [policy["receipt_asset"], repo_policy(policy, repository)["manifest_file"]]


# --------------------------------------------------------------------------------------
# manifest: {filename: sha256} and its one canonical byte serialisation
# --------------------------------------------------------------------------------------


def check_manifest_entries(entries: Any, field: str = "manifest", reserved: Iterable[str] = (), allow_empty: bool = False) -> None:
    if not isinstance(entries, dict):
        raise ContractError(f"{field} must be a JSON object {{filename: sha256}}")
    if not entries and not allow_empty:
        raise ContractError(f"{field} is empty: a release with no asset validates nothing")
    reserved = set(reserved)
    folded: Dict[str, str] = {}
    for name, digest in entries.items():
        _require_match(name, NAME_RE, f"{field} name")
        if name in reserved:
            raise ContractError(f"{field} lists {name!r}, which is reserved and is not a manifest entry")
        _require_match(digest, HEX64_RE, f"{field}[{name!r}]")
        # Two names that differ only by case are two assets on GitHub and one file on
        # the macOS and Windows legs: whichever lands second overwrites the first.
        key = name.lower()
        if key in folded:
            raise ContractError(f"{field} has {folded[key]!r} and {name!r}, which differ only by case")
        folded[key] = name


def serialize_manifest(entries: Dict[str, str]) -> bytes:
    """`<sha256>  <name>\\n` per entry, ascending BYTE order of name, LF-terminated.

    Exactly GNU `sha256sum` text-mode output sorted under LC_ALL=C, so any shell can
    produce and check it. The sort is by bytes, never by locale: under en_US.UTF-8
    `supervizio-arm64.apk` sorts before `supervizio-arm.apk`, and the digest changes."""
    check_manifest_entries(entries)
    ordered = sorted(entries, key=lambda n: n.encode("ascii"))
    return "".join(f"{entries[n]}  {n}\n" for n in ordered).encode("ascii")


def manifest_digest(entries: Dict[str, str]) -> str:
    return "sha256:" + hashlib.sha256(serialize_manifest(entries)).hexdigest()


def parse_manifest(data: bytes) -> Dict[str, str]:
    """Parse manifest bytes, accepting ONLY the canonical form. A file that
    `sha256sum -c` would accept but that is not canonical (CRLF, locale order,
    `*` binary marker, trailing blank line) is refused: two serialisations of the
    same set would give two digests for one release."""
    if not data:
        raise ContractError("manifest file is empty")
    if data.startswith(b"\xef\xbb\xbf"):
        raise ContractError("manifest file starts with a UTF-8 byte-order mark")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ContractError(f"manifest file is not ASCII: {exc}") from exc
    if "\r" in text:
        raise ContractError("manifest file contains CR (it must be LF-only)")
    if not text.endswith("\n"):
        raise ContractError("manifest file does not end with a newline")
    entries: Dict[str, str] = {}
    previous: Optional[str] = None
    for number, line in enumerate(text[:-1].split("\n"), start=1):
        match = MANIFEST_LINE_RE.fullmatch(line)
        if not match:
            raise ContractError(f"manifest line {number} is not '<64 lowercase hex>  <name>': {line!r}")
        digest, name = match.groups()
        _require_match(name, NAME_RE, f"manifest line {number} name")
        if name in entries:
            raise ContractError(f"manifest line {number}: {name!r} is listed twice")
        if previous is not None and name.encode("ascii") <= previous.encode("ascii"):
            raise ContractError(
                f"manifest line {number}: {name!r} does not sort after {previous!r} in byte order (LC_ALL=C)"
            )
        entries[name] = digest
        previous = name
    check_manifest_entries(entries)
    if serialize_manifest(entries) != data:  # belt and braces: parse and serialise must round-trip
        raise ContractError("manifest file is not in canonical form")
    return entries


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest_from_dir(directory: str, exclude: Iterable[str] = ()) -> Dict[str, str]:
    exclude = set(exclude)
    entries: Dict[str, str] = {}
    try:
        names = sorted(os.listdir(directory))
    except OSError as exc:
        raise UsageError(f"cannot list {directory}: {exc}") from exc
    for name in names:
        if name in exclude:
            continue
        path = os.path.join(directory, name)
        if os.path.islink(path) or not os.path.isfile(path):
            # A release directory is flat. Skipping a subdirectory silently would leave
            # its files unpublished-yet-unlisted; refusing says so.
            raise ContractError(f"{path} is not a regular file; the release directory must be flat")
        entries[name] = sha256_file(path)
    check_manifest_entries(entries)
    return entries


# --------------------------------------------------------------------------------------
# receipt
# --------------------------------------------------------------------------------------


def derive_verdict(required: List[str], results: Dict[str, str]) -> str:
    """success only if EVERY required leg succeeded; failure if one of them failed
    (the candidate is bad); error for everything else -- cancelled, timed out,
    skipped, missing, incomplete. `error` is 'no evidence', never a pass: the gate
    rejects missing credentials, missing results, cancellation and timeouts alike."""
    values = [results.get(leg, "missing") for leg in required]
    if values and all(v == "success" for v in values):
        return "success"
    if any(v == "failure" for v in values):
        return "failure"
    return "error"


def validate_receipt(receipt: Any, policy: Dict[str, Any], audit: bool = False) -> None:
    """Well-formedness and internal consistency. Says nothing about the world: that
    the tag still points where the receipt says is verify_promotion's job.

    audit=True judges an existing receipt by the rules it was written under: its own
    required_matrix and manifest_file, not today's policy. Tightening policy.json
    must never invalidate a release validated before -- the same rule as for
    test_suite_revision. Only a NEW candidate has to meet the current policy."""
    _require_keys(receipt, RECEIPT_KEYS, "receipt")
    if receipt["schema"] != RECEIPT_SCHEMA:
        raise ContractError(f"receipt.schema must be {RECEIPT_SCHEMA!r}, got {receipt['schema']!r}")
    _require_match(receipt["repository"], REPO_RE, "receipt.repository")
    spec = repo_policy(policy, receipt["repository"])
    _require_match(receipt["tag"], TAG_RE, "receipt.tag")
    _require_match(receipt["resolved_commit"], COMMIT_RE, "receipt.resolved_commit")
    _require_int(receipt["release_id"], "receipt.release_id", 1)
    _require_int(receipt["candidate_generation"], "receipt.candidate_generation", 1)
    _require_match(receipt["manifest_file"], NAME_RE, "receipt.manifest_file")
    if receipt["manifest_file"] == policy["receipt_asset"]:
        raise ContractError("receipt.manifest_file cannot be the receipt asset itself")
    if not audit and receipt["manifest_file"] != spec["manifest_file"]:
        raise ContractError(
            f"receipt.manifest_file is {receipt['manifest_file']!r}; {receipt['repository']} publishes "
            f"its manifest as {spec['manifest_file']!r}"
        )
    reserved = receipt_reserved_names(policy, receipt)
    check_manifest_entries(receipt["manifest"], "receipt.manifest", reserved)
    _require_match(receipt["asset_manifest_digest"], DIGEST_RE, "receipt.asset_manifest_digest")
    actual = manifest_digest(receipt["manifest"])
    if actual != receipt["asset_manifest_digest"]:
        raise ContractError(
            f"receipt.asset_manifest_digest is {receipt['asset_manifest_digest']} but its manifest hashes to {actual}"
        )
    check_manifest_entries(receipt["support"], "receipt.support", reserved, allow_empty=True)
    overlap = sorted(set(receipt["support"]) & set(receipt["manifest"]))
    if overlap:
        raise ContractError(f"receipt.support reuses published asset name(s): {', '.join(overlap)}")
    if receipt["support"]:
        _require_match(receipt["support_manifest_digest"], DIGEST_RE, "receipt.support_manifest_digest")
        actual = manifest_digest(receipt["support"])
        if actual != receipt["support_manifest_digest"]:
            raise ContractError(
                f"receipt.support_manifest_digest is {receipt['support_manifest_digest']} but its support set hashes to {actual}"
            )
    elif receipt["support_manifest_digest"] is not None:
        raise ContractError("receipt.support_manifest_digest must be null when receipt.support is empty")

    matrix = receipt["required_matrix"]
    if not isinstance(matrix, list) or not matrix:
        raise ContractError("receipt.required_matrix must be a non-empty list of leg ids")
    for leg in matrix:
        _require_match(leg, LEG_RE, "receipt.required_matrix[]")
    if len(set(matrix)) != len(matrix):
        raise ContractError("receipt.required_matrix lists a leg twice")
    weaker = [] if audit else sorted(set(required_legs(policy, receipt["repository"])) - set(matrix))
    if weaker:
        raise ContractError(
            f"receipt.required_matrix omits leg(s) the policy requires for {receipt['repository']}: {', '.join(weaker)}"
        )

    verdict = receipt["verdict"]
    if verdict not in VERDICTS:
        raise ContractError(f"receipt.verdict must be one of {', '.join(VERDICTS)}, got {verdict!r}")
    _require_match(receipt["recorded_at"], TIMESTAMP_RE, "receipt.recorded_at")
    results = receipt["results"]
    if not isinstance(results, dict):
        raise ContractError("receipt.results must be an object {leg: result}")
    if verdict == "pending":
        for key in ("test_suite_revision", "e2e_run_id", "e2e_attempt"):
            if receipt[key] is not None:
                raise ContractError(f"a pending receipt has no {key} yet; it must be null")
        if results:
            raise ContractError("a pending receipt carries no results")
        if receipt["restored_from"] is not None:
            raise ContractError("a pending receipt cannot be a restoration")
        return

    _require_match(receipt["test_suite_revision"], COMMIT_RE, "receipt.test_suite_revision")
    _require_int(receipt["e2e_run_id"], "receipt.e2e_run_id", 1)
    _require_int(receipt["e2e_attempt"], "receipt.e2e_attempt", 1)
    for leg, value in results.items():
        _require_match(leg, LEG_RE, "receipt.results key")
        if value not in LEG_RESULTS:
            raise ContractError(f"receipt.results[{leg!r}] = {value!r} is not a known result")
    unreported = sorted(set(matrix) - set(results))
    if unreported:
        # The evidence builder writes "missing" for a leg no job reported. A receipt
        # that simply leaves the key out was not built by it.
        raise ContractError(f"receipt.results has no entry for required leg(s): {', '.join(unreported)}")
    derived = derive_verdict(matrix, results)
    if derived != verdict:
        raise ContractError(f"receipt.verdict says {verdict!r} but its results derive {derived!r}")
    restored = receipt["restored_from"]
    if restored is not None:
        _require_keys(restored, {"release_id", "candidate_generation"}, "receipt.restored_from")
        _require_int(restored["release_id"], "receipt.restored_from.release_id", 1)
        _require_int(restored["candidate_generation"], "receipt.restored_from.candidate_generation", 1)
        if verdict != "success":
            raise ContractError("only a successful receipt can be carried over by a restoration")
        if restored["release_id"] == receipt["release_id"]:
            raise ContractError("receipt.restored_from.release_id must name the release that was replaced")


# --------------------------------------------------------------------------------------
# validate-release dispatch payload
# --------------------------------------------------------------------------------------


def expected_run_name(candidate: Dict[str, Any]) -> str:
    """The run-name validate-release.yml must render. It is what binds a public run
    to one candidate: the runs API returns it as display_title, the dispatch payload
    itself is not retrievable afterwards. It carries the commit too, so a doorbell
    reading only the run can address the private commit (about 170 characters; a
    268-character run-name was measured to be kept whole)."""
    return "{} {} {} g{} {} {}".format(
        RUN_NAME_PREFIX,
        candidate["repository"],
        candidate["tag"],
        candidate["candidate_generation"],
        candidate["resolved_commit"],
        candidate["asset_manifest_digest"],
    )


def validate_dispatch(body: Any, policy: Dict[str, Any]) -> None:
    """The full body POSTed to /repos/{staging}/dispatches."""
    if not isinstance(body, dict) or set(body) != {"event_type", "client_payload"}:
        raise ContractError("dispatch body must be exactly {event_type, client_payload}")
    if body["event_type"] != policy["staging"]["event_type"]:
        raise ContractError(f"event_type must be {policy['staging']['event_type']!r}")
    payload = body["client_payload"]
    if not isinstance(payload, dict):
        raise ContractError("client_payload must be an object")
    if len(payload) > MAX_CLIENT_PAYLOAD_PROPS:
        raise ContractError(f"client_payload has {len(payload)} top-level properties; GitHub accepts {MAX_CLIENT_PAYLOAD_PROPS}")
    size = len(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    if size >= MAX_DISPATCH_BYTES:
        raise ContractError(f"dispatch body is {size} bytes; GitHub requires less than {MAX_DISPATCH_BYTES}")
    _require_keys(payload, CLIENT_PAYLOAD_KEYS, "client_payload")
    if payload["schema"] != PAYLOAD_SCHEMA:
        raise ContractError(f"client_payload.schema must be {PAYLOAD_SCHEMA!r}")
    candidate = payload["candidate"]
    _require_keys(candidate, CANDIDATE_KEYS, "client_payload.candidate")
    # Re-use the receipt rules for every field the two share, by checking the pending
    # receipt this payload implies: one definition of "well-formed", not two.
    pending = pending_receipt_from_dispatch(body, recorded_at="1970-01-01T00:00:00Z")
    validate_receipt(pending, policy)
    staging = payload["staging"]
    _require_keys(staging, STAGING_KEYS, "client_payload.staging")
    if staging["repository"] != policy["staging"]["repository"]:
        raise ContractError(f"staging.repository must be {policy['staging']['repository']!r}")
    _require_int(staging["release_id"], "client_payload.staging.release_id", 1)
    _require_match(staging["tag_name"], re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$"), "client_payload.staging.tag_name")
    if len(expected_run_name(candidate)) > 255:
        raise ContractError("the run-name this candidate implies would be longer than 255 characters")


def pending_receipt_from_dispatch(body: Dict[str, Any], recorded_at: str) -> Dict[str, Any]:
    payload = body["client_payload"]
    candidate = payload["candidate"]
    support = payload["support"]
    return {
        "schema": RECEIPT_SCHEMA,
        "repository": candidate["repository"],
        "tag": candidate["tag"],
        "resolved_commit": candidate["resolved_commit"],
        "release_id": candidate["release_id"],
        "candidate_generation": candidate["candidate_generation"],
        "manifest_file": candidate["manifest_file"],
        "asset_manifest_digest": candidate["asset_manifest_digest"],
        "manifest": payload["manifest"],
        "support_manifest_digest": manifest_digest(support) if isinstance(support, dict) and support else None,
        "support": support,
        "required_matrix": payload["required_matrix"],
        "test_suite_revision": None,
        "e2e_run_id": None,
        "e2e_attempt": None,
        "results": {},
        "verdict": "pending",
        "recorded_at": recorded_at,
        "restored_from": None,
    }


# --------------------------------------------------------------------------------------
# evidence: turn a finished public run into the final receipt
# --------------------------------------------------------------------------------------


def results_from_jobs(jobs: List[Dict[str, Any]], required: List[str]) -> Dict[str, str]:
    """One job per leg, named exactly `leg/<leg-id>`. Its conclusion is the leg's
    result. A required leg without such a job is `missing`; a leg reported twice is
    `incomplete` (which of the two would be believed is exactly what must not be
    left to chance); a job not yet completed is `incomplete`."""
    seen: Dict[str, List[Dict[str, Any]]] = {}
    for job in jobs:
        name = job.get("name")
        if not isinstance(name, str) or not name.startswith(LEG_JOB_PREFIX):
            continue
        leg = name[len(LEG_JOB_PREFIX):]
        if not LEG_RE.fullmatch(leg):
            continue
        seen.setdefault(leg, []).append(job)
    results: Dict[str, str] = {}
    for leg, found in seen.items():
        if len(found) != 1:
            results[leg] = "incomplete"
            continue
        job = found[0]
        conclusion = job.get("conclusion")
        if job.get("status") != "completed" or conclusion not in LEG_RESULTS or conclusion in ("missing", "incomplete"):
            results[leg] = "incomplete"
        else:
            results[leg] = conclusion
    for leg in required:
        results.setdefault(leg, "missing")
    return results


def check_run_binding(run: Dict[str, Any], pending: Dict[str, Any], policy: Dict[str, Any]) -> List[str]:
    staging = policy["staging"]
    problems = []
    repo = (run.get("repository") or {}).get("full_name")
    if repo != staging["repository"]:
        problems.append(f"run belongs to {repo!r}, not {staging['repository']!r}")
    if run.get("path") != staging["workflow_path"]:
        problems.append(f"run is {run.get('path')!r}, not {staging['workflow_path']!r}")
    if run.get("event") != "repository_dispatch":
        problems.append(f"run was triggered by {run.get('event')!r}, not repository_dispatch")
    if run.get("head_branch") != staging["default_branch"]:
        problems.append(f"run executed {run.get('head_branch')!r}, not the default branch {staging['default_branch']!r}")
    if run.get("status") != "completed":
        problems.append(f"run is {run.get('status')!r}, not completed")
    expected = expected_run_name(pending)
    if run.get("display_title") != expected:
        problems.append(f"run is titled {run.get('display_title')!r}; this candidate's run must be titled {expected!r}")
    if not isinstance(run.get("head_sha"), str) or not COMMIT_RE.fullmatch(run["head_sha"]):
        problems.append("run has no usable head_sha")
    if not _is_int(run.get("id")) or not _is_int(run.get("run_attempt")):
        problems.append("run has no usable id / run_attempt")
    return problems


def build_final_receipt(pending: Dict[str, Any], run: Dict[str, Any], jobs: List[Dict[str, Any]], policy: Dict[str, Any], recorded_at: str) -> Dict[str, Any]:
    validate_receipt(pending, policy)
    if pending["verdict"] != "pending":
        raise ContractError(f"expected a pending receipt, got verdict {pending['verdict']!r}")
    problems = check_run_binding(run, pending, policy)
    if problems:
        raise ContractError("the run is not evidence for this candidate: " + "; ".join(problems))
    results = results_from_jobs(jobs, pending["required_matrix"])
    final = dict(pending)
    final.update(
        {
            "test_suite_revision": run["head_sha"],
            "e2e_run_id": run["id"],
            "e2e_attempt": run["run_attempt"],
            "results": dict(sorted(results.items())),
            "verdict": derive_verdict(pending["required_matrix"], results),
            "recorded_at": recorded_at,
        }
    )
    validate_receipt(final, policy)
    return final


# --------------------------------------------------------------------------------------
# pre-promotion verification (brief section 4.1, last rule)
# --------------------------------------------------------------------------------------


def verify_promotion(state: Dict[str, Any], policy: Dict[str, Any], receipt: Optional[Dict[str, Any]] = None, expect_generation: Optional[int] = None, audit: bool = False) -> List[str]:
    """Return every reason the release must NOT be promoted; empty means promote.

    `state` is what GitHub says NOW (see observe_release). The receipt checked is
    the one stored ON the release: a receipt that exists only in the promoting
    job's memory was never 'stored before publication'."""
    failures: List[str] = []
    if not isinstance(state, dict) or state.get("schema") != STATE_SCHEMA:
        return [f"state is not a {STATE_SCHEMA} document"]
    release = state.get("release")
    if not isinstance(release, dict):
        return [f"no release exists for {state.get('tag')!r}"]
    stored = release.get("receipt")
    if stored is None:
        why = release.get("receipt_error") or "absent"
        return [f"release {release.get('id')} carries no readable {policy['receipt_asset']} ({why})"]
    if receipt is not None and receipt != stored:
        failures.append("the receipt supplied differs from the receipt stored on the release")
    try:
        validate_receipt(stored, policy, audit=audit)
    except ContractError as exc:
        return failures + [f"stored receipt is invalid: {exc}"]
    r = stored

    if r["verdict"] != "success":
        failures.append(f"verdict is {r['verdict']!r}; only 'success' is promotable")
    not_green = [f"{leg}={r['results'].get(leg, 'missing')}" for leg in r["required_matrix"] if r["results"].get(leg) != "success"]
    if not_green:
        failures.append("required legs without a success result: " + ", ".join(not_green))
    if expect_generation is not None and r["candidate_generation"] != expect_generation:
        failures.append(
            f"receipt is for candidate generation {r['candidate_generation']}, the promotion was asked for {expect_generation}"
        )

    if state.get("repository") != r["repository"] or state.get("tag") != r["tag"]:
        failures.append(f"state describes {state.get('repository')}@{state.get('tag')}, receipt {r['repository']}@{r['tag']}")
    tag_commit = state.get("tag_commit")
    if tag_commit is None:
        failures.append(f"tag {r['tag']} does not exist any more")
    elif tag_commit != r["resolved_commit"]:
        failures.append(f"tag {r['tag']} now resolves to {tag_commit}, the receipt validated {r['resolved_commit']} (tag re-pointed)")

    if release.get("id") != r["release_id"]:
        failures.append(f"release is {release.get('id')}, the receipt was written for release {r['release_id']}")
    if release.get("tag_name") != r["tag"]:
        failures.append(f"release is attached to tag {release.get('tag_name')!r}, not {r['tag']!r}")
    if release.get("draft") is not True and not audit:
        failures.append("release is not a draft: nothing to promote (use --audit to check a published release)")

    assets = release.get("assets")
    if not isinstance(assets, list):
        return failures + ["state lists no assets"]
    observed: Dict[str, Dict[str, Any]] = {}
    for asset in assets:
        name = asset.get("name") if isinstance(asset, dict) else None
        if not isinstance(name, str):
            failures.append("an asset has no name")
            continue
        if name in observed:
            failures.append(f"asset {name!r} is listed twice")
        observed[name] = asset
    expected_names = set(r["manifest"]) | set(receipt_reserved_names(policy, r))
    missing = sorted(expected_names - set(observed))
    extra = sorted(set(observed) - expected_names)
    if missing:
        failures.append("release lacks asset(s): " + ", ".join(missing))
    if extra:
        failures.append("release carries asset(s) outside the validated manifest: " + ", ".join(extra))

    def _check(name: str, want: str) -> None:
        asset = observed.get(name)
        if asset is None:
            return
        api = asset.get("digest")
        local = asset.get("local_sha256")
        if api is None and local is None:
            failures.append(f"{name}: GitHub reports no digest and nothing was hashed locally -- unverifiable")
            return
        if api is not None and api != want:
            failures.append(f"{name}: GitHub digest {api} != validated {want}")
        if local is not None and "sha256:" + str(local) != want:
            failures.append(f"{name}: local sha256 {local} != validated {want}")

    for name, hexdigest in sorted(r["manifest"].items()):
        _check(name, "sha256:" + hexdigest)
    # The manifest file's bytes ARE the canonical serialisation, so its digest must be
    # the asset_manifest_digest itself: that single comparison is what makes a
    # published release checkable with nothing but `sha256sum`.
    _check(r["manifest_file"], r["asset_manifest_digest"])
    return failures


# --------------------------------------------------------------------------------------
# GitHub adapter: the only part that talks to the network. Tests replace `Api`.
# --------------------------------------------------------------------------------------


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


class Api:
    """Minimal REST client. Paginates via Link headers; downloads release assets by
    following the redirect WITHOUT the Authorization header (urllib would forward
    it to the storage host, which both leaks it and makes the signed URL fail)."""

    def __init__(self, token: Optional[str] = None, base: Optional[str] = None) -> None:
        self.token = token if token is not None else (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "")
        self.base = (base or os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")

    def _request(self, url: str, accept: str) -> Tuple[int, Dict[str, str], bytes]:
        headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "supervizio-release-contract"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(urllib.request.Request(url, headers=headers), timeout=60) as resp:
                return resp.status, dict(resp.headers.items()), resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers.items()) if exc.headers else {}, exc.read() or b""
        except urllib.error.URLError as exc:
            raise UsageError(f"GET {url}: {exc}") from exc

    def get(self, path: str) -> Tuple[int, Any, Optional[str]]:
        url = path if path.startswith("https://") else self.base + path
        status, headers, body = self._request(url, "application/vnd.github+json")
        link = {k.lower(): v for k, v in headers.items()}.get("link", "")
        nxt = None
        for part in link.split(","):
            m = re.match(r'\s*<([^>]+)>\s*;\s*rel="next"', part)
            if m:
                nxt = m.group(1)
        try:
            data = json.loads(body.decode("utf-8")) if body else None
        except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError are both ValueErrors
            # A proxy error page or a truncated body says nothing about the release:
            # it is "could not evaluate" (exit 2), never a verdict.
            raise UsageError(f"GET {url} -> HTTP {status}: response is not JSON ({type(exc).__name__})") from exc
        return status, data, nxt

    def get_ok(self, path: str) -> Any:
        status, data, _ = self.get(path)
        if status != 200:
            raise UsageError(f"GET {path} -> HTTP {status}: {str(data)[:200]}")
        return data

    def get_all(self, path: str, key: Optional[str] = None) -> List[Any]:
        items: List[Any] = []
        url: Optional[str] = path
        while url:
            status, data, url = self.get(url)
            if status != 200:
                raise UsageError(f"GET {path} -> HTTP {status}")
            items.extend(data[key] if key else data)
        return items

    def download_asset(self, repository: str, asset_id: int) -> bytes:
        url = f"{self.base}/repos/{repository}/releases/assets/{asset_id}"
        status, headers, body = self._request(url, "application/octet-stream")
        if status in (301, 302, 303, 307, 308):
            location = {k.lower(): v for k, v in headers.items()}.get("location")
            if not location:
                raise UsageError(f"asset {asset_id}: redirect without Location")
            req = urllib.request.Request(location, headers={"User-Agent": "supervizio-release-contract"})
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    return resp.read()
            except urllib.error.URLError as exc:
                raise UsageError(f"asset {asset_id}: download failed: {exc}") from exc
        if status == 200:
            return body
        raise UsageError(f"asset {asset_id}: HTTP {status}")


def resolve_tag(api: Api, repository: str, tag: str) -> Optional[str]:
    """Tag -> commit, peeling annotated tags (a tag object may point at another tag
    object). None when the tag does not exist."""
    quoted = urllib.parse.quote(tag, safe="")
    status, ref, _ = api.get(f"/repos/{repository}/git/ref/tags/{quoted}")
    if status == 404:
        return None
    if status != 200 or not isinstance(ref, dict):
        raise UsageError(f"cannot read refs/tags/{tag}: HTTP {status}")
    obj = ref["object"]
    for _ in range(8):
        if obj["type"] == "commit":
            return obj["sha"]
        if obj["type"] != "tag":
            raise ContractError(f"refs/tags/{tag} points at a {obj['type']}, not a commit")
        obj = api.get_ok(f"/repos/{repository}/git/tags/{obj['sha']}")["object"]
    raise ContractError(f"refs/tags/{tag}: annotated-tag chain too deep")


def observe_release(api: Api, repository: str, tag: str, release_id: int, receipt_asset: str, hash_assets: bool = False) -> Dict[str, Any]:
    state: Dict[str, Any] = {"schema": STATE_SCHEMA, "repository": repository, "tag": tag, "tag_commit": resolve_tag(api, repository, tag), "release": None}
    status, release, _ = api.get(f"/repos/{repository}/releases/{release_id}")
    if status == 404:
        return state
    if status != 200:
        raise UsageError(f"cannot read release {release_id}: HTTP {status}")
    assets = api.get_all(f"/repos/{repository}/releases/{release_id}/assets?per_page=100")
    listed = []
    receipt: Any = None
    receipt_error = None
    for asset in assets:
        entry = {"name": asset["name"], "id": asset["id"], "size": asset.get("size"), "digest": asset.get("digest")}
        if hash_assets:
            entry["local_sha256"] = hashlib.sha256(api.download_asset(repository, asset["id"])).hexdigest()
        if asset["name"] == receipt_asset:
            try:
                receipt = json.loads(api.download_asset(repository, asset["id"]).decode("utf-8"))
            except ValueError as exc:
                receipt_error = f"unparseable: {exc}"
        listed.append(entry)
    state["release"] = {
        "id": release["id"],
        "tag_name": release["tag_name"],
        "draft": release["draft"],
        "assets": sorted(listed, key=lambda a: a["name"]),
        "receipt": receipt,
        "receipt_error": receipt_error,
    }
    return state


def fetch_run(api: Api, repository: str, run_id: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    run = api.get_ok(f"/repos/{repository}/actions/runs/{run_id}")
    # filter=latest: the most recent execution of each job, i.e. what a partial
    # re-run of failed legs left as the final word.
    jobs = api.get_all(f"/repos/{repository}/actions/runs/{run_id}/jobs?filter=latest&per_page=100", key="jobs")
    return run, jobs


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _read_json(path: str) -> Any:
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise UsageError(f"cannot read JSON {path}: {exc}") from exc


def _write(data: bytes, output: Optional[str]) -> None:
    if output:
        with open(output, "wb") as fh:
            fh.write(data)
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.flush()


def _dump(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _utc_now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_manifest_build(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    exclude = list(args.exclude or [])
    if args.repository:
        exclude.extend(reserved_names(policy, args.repository))
    if args.output and os.path.dirname(os.path.abspath(args.output)) == os.path.abspath(args.dir):
        exclude.append(os.path.basename(args.output))
    entries = build_manifest_from_dir(args.dir, exclude)
    data = serialize_manifest(entries)
    _write(data, args.output)
    print("sha256:" + hashlib.sha256(data).hexdigest(), file=sys.stderr)
    return 0


def cmd_manifest_check(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    with open(args.file, "rb") as fh:
        data = fh.read()
    parse_manifest(data)
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    if args.expect_digest and digest != args.expect_digest:
        raise ContractError(f"{args.file} hashes to {digest}, expected {args.expect_digest}")
    print(digest)
    return 0


def cmd_manifest_verify_files(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    with open(args.manifest, "rb") as fh:
        data = fh.read()
    entries = parse_manifest(data)
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    if digest != args.expect_digest:
        raise ContractError(f"{args.manifest} hashes to {digest}, not the dispatched {args.expect_digest}")
    names = args.only or sorted(entries)
    problems = []
    for name in names:
        if name not in entries:
            problems.append(f"{name} is not in the manifest")
            continue
        path = os.path.join(args.dir, name)
        if not os.path.isfile(path):
            problems.append(f"{name} is missing from {args.dir}")
            continue
        actual = sha256_file(path)
        if actual != entries[name]:
            problems.append(f"{name}: sha256 {actual} != manifest {entries[name]}")
    if problems:
        raise ContractError("; ".join(problems))
    print(f"PASS {len(names)} file(s) match {digest}")
    return 0


def cmd_receipt_check(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    receipt = _read_json(args.file)
    validate_receipt(receipt, policy)
    print(f"PASS receipt {receipt['repository']}@{receipt['tag']} g{receipt['candidate_generation']} verdict={receipt['verdict']}")
    return 0


def cmd_receipt_pending(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    body = _read_json(args.dispatch)
    validate_dispatch(body, policy)
    pending = pending_receipt_from_dispatch(body, args.recorded_at or _utc_now())
    validate_receipt(pending, policy)
    _write(_dump(pending), args.output)
    return 0


def cmd_dispatch_check(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    body = _read_json(args.file)
    validate_dispatch(body, policy)
    size = len(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    print(f"PASS dispatch {size} bytes, run-name: {expected_run_name(body['client_payload']['candidate'])}")
    return 0


def cmd_run_name(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    doc = _read_json(args.file)
    candidate = doc["client_payload"]["candidate"] if "client_payload" in doc else doc
    print(expected_run_name(candidate))
    return 0


def cmd_evidence(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    pending = _read_json(args.pending)
    if args.run_id is not None:
        run, jobs = fetch_run(Api(), policy["staging"]["repository"], args.run_id)
    else:
        if not (args.run and args.jobs):
            raise UsageError("evidence needs --run-id, or both --run and --jobs")
        run = _read_json(args.run)
        jobs_doc = _read_json(args.jobs)
        jobs = jobs_doc["jobs"] if isinstance(jobs_doc, dict) else jobs_doc
    final = build_final_receipt(pending, run, jobs, policy, args.recorded_at or _utc_now())
    _write(_dump(final), args.output)
    print(f"verdict={final['verdict']}", file=sys.stderr)
    return 0


def cmd_observe(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    state = observe_release(Api(), args.repository, args.tag, args.release_id, policy["receipt_asset"], args.hash_assets)
    _write(_dump(state), args.output)
    return 0


def cmd_verify_promotion(args: argparse.Namespace, policy: Dict[str, Any]) -> int:
    state = _read_json(args.state)
    receipt = _read_json(args.receipt) if args.receipt else None
    failures = verify_promotion(state, policy, receipt, args.expect_generation, args.audit)
    if failures:
        print("FAIL do not promote:")
        for reason in failures:
            print(f"  - {reason}")
        return 1
    r = state["release"]["receipt"]
    print(f"PASS promote {r['repository']}@{r['tag']} release {r['release_id']} g{r['candidate_generation']} {r['asset_manifest_digest']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="release_contract.py", description=__doc__.split("\n")[0])
    p.add_argument("--policy", help="policy file (default: policy.json next to this script)")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("manifest", help="canonical {filename: sha256} manifest").add_subparsers(dest="sub", required=True)
    b = m.add_parser("build", help="hash a flat directory into the canonical manifest")
    b.add_argument("--dir", required=True)
    b.add_argument("--exclude", action="append", help="file name to leave out (repeatable)")
    b.add_argument("--repository", help="also leave out that repository's reserved names (manifest file, receipt)")
    b.add_argument("--output")
    b.set_defaults(func=cmd_manifest_build)
    c = m.add_parser("check", help="refuse a non-canonical manifest file, print its digest")
    c.add_argument("file")
    c.add_argument("--expect-digest")
    c.set_defaults(func=cmd_manifest_check)
    v = m.add_parser("verify-files", help="check downloaded files against a manifest pinned by digest")
    v.add_argument("--manifest", required=True)
    v.add_argument("--expect-digest", required=True)
    v.add_argument("--dir", required=True)
    v.add_argument("--only", action="append", help="verify only this file (repeatable)")
    v.set_defaults(func=cmd_manifest_verify_files)

    r = sub.add_parser("receipt", help="release receipt").add_subparsers(dest="sub", required=True)
    rc = r.add_parser("check", help="well-formedness and internal consistency")
    rc.add_argument("file")
    rc.set_defaults(func=cmd_receipt_check)
    rp = r.add_parser("pending", help="the pending receipt a dispatch body implies")
    rp.add_argument("--dispatch", required=True)
    rp.add_argument("--recorded-at")
    rp.add_argument("--output")
    rp.set_defaults(func=cmd_receipt_pending)

    d = sub.add_parser("dispatch", help="validate-release dispatch body").add_subparsers(dest="sub", required=True)
    dc = d.add_parser("check")
    dc.add_argument("file")
    dc.set_defaults(func=cmd_dispatch_check)
    dn = d.add_parser("run-name", help="the run-name validate-release.yml must render")
    dn.add_argument("file")
    dn.set_defaults(func=cmd_run_name)

    e = sub.add_parser("evidence", help="final receipt from a pending receipt and the finished public run")
    e.add_argument("--pending", required=True)
    e.add_argument("--run-id", type=int)
    e.add_argument("--run")
    e.add_argument("--jobs")
    e.add_argument("--recorded-at")
    e.add_argument("--output")
    e.set_defaults(func=cmd_evidence)

    o = sub.add_parser("observe", help="what GitHub says about a release NOW (network)")
    o.add_argument("--repository", required=True)
    o.add_argument("--tag", required=True)
    o.add_argument("--release-id", type=int, required=True)
    o.add_argument("--hash-assets", action="store_true", help="also download and hash every asset")
    o.add_argument("--output")
    o.set_defaults(func=cmd_observe)

    vp = sub.add_parser("verify-promotion", help="the checks that must pass right before --draft=false")
    vp.add_argument("--state", required=True)
    vp.add_argument("--receipt", help="must equal the receipt stored on the release")
    vp.add_argument("--expect-generation", type=int)
    vp.add_argument(
        "--audit",
        action="store_true",
        help="check a release that may already be published, against the matrix its receipt was validated with",
    )
    vp.set_defaults(func=cmd_verify_promotion)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        policy = load_policy(args.policy)
        return args.func(args, policy)
    except ContractError as exc:
        print(f"FAIL {exc}")
        return 1
    except (UsageError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        # Exit 1 is reserved for a PROVEN violation, raised as ContractError. An input
        # this tool could not make sense of proves nothing either way.
        print(f"ERROR could not evaluate: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
