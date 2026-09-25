"""Tests for release_contract.py -- stdlib unittest, no network.

Most of this file is about the validator SAYING NO. A validator that cannot fail
proves nothing, so every rule of README.md has a test that breaks it and expects
a refusal, and `MutationCoverage` fails the suite if a receipt field is added
without one.

Run: python3 -m unittest discover -s release-contract/tests -v
"""

from __future__ import annotations

import base64
import copy
import hashlib
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import release_contract as rc  # noqa: E402

SCRIPT = os.path.join(ROOT, "release_contract.py")
VECTOR = os.path.join(HERE, "vectors", "manifest-v1")
POLICY = rc.load_policy()
PROOF_POLICY = os.path.join(HERE, "proof-policy.json")

AGENT = "supervizio/agent"
LIBPROBE = "supervizio/libprobe"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
OTHER_COMMIT = "fedcba9876543210fedcba9876543210fedcba98"
SUITE_REV = "89abcdef0123456789abcdef0123456789abcdef"


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def agent_manifest():
    return {
        "supervizio-amd64.deb": h("deb"),
        "supervizio-arm64.rpm": h("rpm"),
        "supervizio-linux-amd64": h("bin"),
        "supervizio-windows-amd64.exe": h("exe"),
    }


def pending_receipt(repository=AGENT, manifest=None, support=None, generation=1):
    manifest = manifest if manifest is not None else agent_manifest()
    support = support if support is not None else {"e2e-kit.tar.gz": h("kit")}
    return {
        "schema": rc.RECEIPT_SCHEMA,
        "repository": repository,
        "tag": "v1.4.2",
        "resolved_commit": COMMIT,
        "release_id": 123456,
        "candidate_generation": generation,
        "manifest_file": rc.repo_policy(POLICY, repository)["manifest_file"],
        "asset_manifest_digest": rc.manifest_digest(manifest),
        "manifest": manifest,
        "support_manifest_digest": rc.manifest_digest(support) if support else None,
        "support": support,
        "required_matrix": rc.required_legs(POLICY, repository),
        "test_suite_revision": None,
        "e2e_run_id": None,
        "e2e_attempt": None,
        "results": {},
        "verdict": "pending",
        "recorded_at": "2026-09-23T10:00:00Z",
        "restored_from": None,
    }


def final_receipt(repository=AGENT, overrides=None):
    r = pending_receipt(repository)
    r.update(
        {
            "test_suite_revision": SUITE_REV,
            "e2e_run_id": 4242,
            "e2e_attempt": 1,
            "results": {leg: "success" for leg in r["required_matrix"]},
            "verdict": "success",
            "recorded_at": "2026-09-23T12:00:00Z",
        }
    )
    r.update(overrides or {})
    return r


def asset_list(receipt, digest_of=None):
    """The asset list GitHub would report for a release holding exactly `receipt`."""
    digest_of = digest_of or {}
    assets = [{"name": n, "digest": digest_of.get(n, "sha256:" + d)} for n, d in receipt["manifest"].items()]
    assets.append({"name": receipt["manifest_file"], "digest": digest_of.get(receipt["manifest_file"], receipt["asset_manifest_digest"])})
    assets.append({"name": POLICY["receipt_asset"], "digest": "sha256:" + h(json.dumps(receipt))})
    return assets


def state_for(rcpt, **kw):
    state = {
        "schema": rc.STATE_SCHEMA,
        "repository": rcpt["repository"],
        "tag": rcpt["tag"],
        "tag_commit": rcpt["resolved_commit"],
        "release": {
            "id": rcpt["release_id"],
            "tag_name": rcpt["tag"],
            "draft": True,
            "assets": asset_list(rcpt),
            "receipt": copy.deepcopy(rcpt),
            "receipt_error": None,
        },
    }
    for key, value in kw.items():
        if key in state["release"]:
            state["release"][key] = value
        else:
            state[key] = value
    return state


def dispatch_body(repository=AGENT, **payload_overrides):
    r = pending_receipt(repository)
    body = {
        "event_type": "validate-release",
        "client_payload": {
            "schema": rc.PAYLOAD_SCHEMA,
            "candidate": {k: r[k] for k in rc.CANDIDATE_KEYS},
            "manifest": r["manifest"],
            "support": r["support"],
            "bridge": {"package": rc.repo_policy(POLICY, repository)["bridge_package"], "digest": "sha256:" + h("oci manifest")},
            "required_matrix": r["required_matrix"],
        },
    }
    body["client_payload"].update(payload_overrides)
    return body


def run_for(receipt, **kw):
    run = {
        "id": 4242,
        "run_attempt": 1,
        "repository": {"full_name": "supervizio/runner-template"},
        "path": ".github/workflows/validate-release.yml",
        "event": "repository_dispatch",
        "head_branch": "main",
        "head_sha": SUITE_REV,
        "status": "completed",
        "conclusion": "success",
        "display_title": rc.expected_run_name(receipt),
    }
    run.update(kw)
    return run


def jobs_for(legs, conclusion="success", **per_leg):
    jobs = [{"name": "admit", "status": "completed", "conclusion": "success"}]
    for leg in legs:
        c = per_leg.get(leg, conclusion)
        status = "in_progress" if c is None else "completed"
        jobs.append({"name": rc.LEG_JOB_PREFIX + leg, "status": status, "conclusion": c})
    return jobs


# --------------------------------------------------------------------------------------


class ManifestVector(unittest.TestCase):
    """The published test vector: any implementation must reproduce these bytes."""

    def test_build_reproduces_vector_bytes_and_digest(self):
        entries = rc.build_manifest_from_dir(os.path.join(VECTOR, "files"))
        with open(os.path.join(VECTOR, "SHA256SUMS"), "rb") as fh:
            expected = fh.read()
        with open(os.path.join(VECTOR, "DIGEST")) as fh:
            expected_digest = fh.read().strip()
        self.assertEqual(rc.serialize_manifest(entries), expected)
        self.assertEqual(rc.manifest_digest(entries), expected_digest)
        self.assertEqual(expected_digest, "sha256:e0d809e3e6092223b4f62de7a5b44e1b91caa5902391a3004d81780468f4865f")

    def test_vector_order_is_bytes_not_locale(self):
        with open(os.path.join(VECTOR, "SHA256SUMS")) as fh:
            names = [line.split("  ", 1)[1].rstrip("\n") for line in fh]
        # Uppercase before lowercase, and '.' (0x2e) before '6' (0x36): both orders a
        # UTF-8 locale collation reverses.
        self.assertEqual(names[0], "Z-upper.txt")
        self.assertLess(names.index("supervizio-arm.apk"), names.index("supervizio-arm64.apk"))

    def test_locale_ordered_file_is_refused(self):
        with open(os.path.join(VECTOR, "SHA256SUMS"), "rb") as fh:
            lines = fh.read().split(b"\n")[:-1]
        reordered = b"\n".join(lines[1:] + lines[:1]) + b"\n"  # 'Z-upper.txt' moved last
        with self.assertRaises(rc.ContractError):
            rc.parse_manifest(reordered)


class ManifestCanonicalForm(unittest.TestCase):
    good = rc.serialize_manifest({"a.bin": h("a"), "b.bin": h("b")})

    def refuse(self, data: bytes):
        with self.assertRaises(rc.ContractError):
            rc.parse_manifest(data)

    def test_round_trip(self):
        self.assertEqual(rc.serialize_manifest(rc.parse_manifest(self.good)), self.good)

    def test_crlf(self):
        self.refuse(self.good.replace(b"\n", b"\r\n"))

    def test_missing_final_newline(self):
        self.refuse(self.good[:-1])

    def test_trailing_blank_line(self):
        self.refuse(self.good + b"\n")

    def test_bom(self):
        self.refuse(b"\xef\xbb\xbf" + self.good)

    def test_single_space(self):
        self.refuse(self.good.replace(b"  ", b" ", 1))

    def test_binary_marker(self):
        self.refuse(self.good.replace(b"  ", b" *", 1))

    def test_uppercase_hex(self):
        self.refuse(self.good[:64].upper() + self.good[64:])

    def test_unsorted(self):
        a, b = self.good.split(b"\n")[:2]
        self.refuse(b + b"\n" + a + b"\n")

    def test_duplicate_name(self):
        a = self.good.split(b"\n")[0]
        self.refuse(a + b"\n" + a + b"\n")

    def test_empty(self):
        self.refuse(b"")

    def test_names_differing_only_by_case(self):
        with self.assertRaises(rc.ContractError):
            rc.serialize_manifest({"Probe.h": h("x"), "probe.h": h("y")})

    def test_bad_names(self):
        for name in ("dir/file", "with space", ".hidden", "-dash", "café.deb", "", "x" * 256):
            with self.subTest(name=name), self.assertRaises(rc.ContractError):
                rc.serialize_manifest({name: h("x")})

    def test_short_or_prefixed_digest(self):
        for digest in (h("x")[:63], "sha256:" + h("x"), h("x").upper()):
            with self.subTest(digest=digest), self.assertRaises(rc.ContractError):
                rc.serialize_manifest({"a.bin": digest})

    def test_directory_must_be_flat(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "sub"))
            with open(os.path.join(d, "a.bin"), "wb") as fh:
                fh.write(b"a")
            with self.assertRaises(rc.ContractError):
                rc.build_manifest_from_dir(d)


class TrailingGarbage(unittest.TestCase):
    """A valid value followed by anything must be refused. `$` in a Python pattern
    also matches just before a trailing newline, so `re.match` alone let
    'v1.4.2\\n' through as a tag -- and 'a.deb\\n' into a manifest, where it
    serialised a blank line into the bytes being hashed."""

    CASES = [
        (rc.NAME_RE, "a.deb"),
        (rc.HEX64_RE, h("x")),
        (rc.DIGEST_RE, "sha256:" + h("x")),
        (rc.COMMIT_RE, COMMIT),
        (rc.TAG_RE, "v1.4.2"),
        (rc.LEG_RE, "docker/amd64/scratch"),
        (rc.REPO_RE, "supervizio/agent"),
        (rc.TIMESTAMP_RE, "2026-09-24T00:00:00Z"),
    ]

    def test_every_format_refuses_trailing_garbage(self):
        for regex, valid in self.CASES:
            rc._require_match(valid, regex, "field")  # the valid value itself passes
            # Characters no format allows. A letter would not do: 'a.debx' is a name.
            for garbage in ("\n", "\n\n", "\r\n", " ", "\t", "\x00"):
                with self.subTest(pattern=regex.pattern, garbage=garbage), self.assertRaises(rc.ContractError):
                    rc._require_match(valid + garbage, regex, "field")

    def test_receipt_tag_with_trailing_newline(self):
        r = final_receipt()
        r["tag"] = "v1.4.2\n"
        with self.assertRaises(rc.ContractError):
            rc.validate_receipt(r, POLICY)

    def test_manifest_name_with_trailing_newline(self):
        with self.assertRaises(rc.ContractError):
            rc.serialize_manifest({"a.deb\n": h("x")})


class Verdict(unittest.TestCase):
    def test_rules(self):
        legs = ["a", "b"]
        self.assertEqual(rc.derive_verdict(legs, {"a": "success", "b": "success"}), "success")
        self.assertEqual(rc.derive_verdict(legs, {"a": "failure", "b": "cancelled"}), "failure")
        for bad in ("cancelled", "timed_out", "skipped", "missing", "incomplete", "neutral", "action_required", "stale"):
            with self.subTest(result=bad):
                self.assertEqual(rc.derive_verdict(legs, {"a": "success", "b": bad}), "error")
        self.assertEqual(rc.derive_verdict(legs, {"a": "success"}), "error")  # b never reported
        self.assertEqual(rc.derive_verdict([], {}), "error")  # nothing required proves nothing


class ReceiptValid(unittest.TestCase):
    def test_pending_and_final_receipts_pass(self):
        for repository in (AGENT, LIBPROBE):
            with self.subTest(repository=repository):
                rc.validate_receipt(pending_receipt(repository), POLICY)
                rc.validate_receipt(final_receipt(repository), POLICY)

    def test_failed_and_errored_receipts_are_well_formed(self):
        legs = rc.required_legs(POLICY, AGENT)
        failed = final_receipt(overrides={"verdict": "failure"})
        failed["results"][legs[0]] = "failure"
        rc.validate_receipt(failed, POLICY)
        errored = final_receipt(overrides={"verdict": "error"})
        errored["results"][legs[0]] = "timed_out"
        rc.validate_receipt(errored, POLICY)

    def test_extra_legs_beyond_policy_are_allowed(self):
        r = final_receipt()
        r["required_matrix"] = r["required_matrix"] + ["future/leg"]
        r["results"]["future/leg"] = "success"
        rc.validate_receipt(r, POLICY)


def _mutate(path, value):
    def apply(r):
        target = r
        for key in path[:-1]:
            target = target[key]
        if value is DELETE:
            del target[path[-1]]
        else:
            target[path[-1]] = value(r) if callable(value) else value

    return apply


DELETE = object()
FIRST_LEG = rc.required_legs(POLICY, AGENT)[0]

# (description, receipt field it breaks, mutation). Each MUST be refused.
RECEIPT_MUTATIONS = [
    ("wrong schema", "schema", _mutate(["schema"], "supervizio.release-receipt/v0")),
    ("unknown repository", "repository", _mutate(["repository"], "supervizio/other")),
    ("tag without v", "tag", _mutate(["tag"], "1.4.2")),
    ("tag with a slash", "tag", _mutate(["tag"], "v1.4.2/x")),
    ("short commit", "resolved_commit", _mutate(["resolved_commit"], COMMIT[:12])),
    ("uppercase commit", "resolved_commit", _mutate(["resolved_commit"], COMMIT.upper())),
    ("release id 0", "release_id", _mutate(["release_id"], 0)),
    ("release id as bool", "release_id", _mutate(["release_id"], True)),
    ("release id as string", "release_id", _mutate(["release_id"], "123456")),
    ("generation 0", "candidate_generation", _mutate(["candidate_generation"], 0)),
    ("manifest file of the other repo", "manifest_file", _mutate(["manifest_file"], "SHA256SUMS")),
    ("altered manifest entry", "manifest", _mutate(["manifest", "supervizio-amd64.deb"], h("tampered"))),
    ("asset added to manifest", "manifest", _mutate(["manifest", "extra.bin"], h("extra"))),
    ("receipt listed in its own manifest", "manifest", _mutate(["manifest", "release-receipt.json"], h("r"))),
    ("manifest file listed in the manifest", "manifest", _mutate(["manifest", "checksums.txt"], h("c"))),
    ("altered manifest digest", "asset_manifest_digest", _mutate(["asset_manifest_digest"], "sha256:" + h("other"))),
    ("digest without prefix", "asset_manifest_digest", _mutate(["asset_manifest_digest"], lambda r: r["asset_manifest_digest"][7:])),
    ("altered support entry", "support", _mutate(["support", "e2e-kit.tar.gz"], h("other kit"))),
    ("support reuses an asset name", "support", _mutate(["support", "supervizio-amd64.deb"], h("deb"))),
    ("support digest null with support", "support_manifest_digest", _mutate(["support_manifest_digest"], None)),
    ("required matrix weaker than policy", "required_matrix", _mutate(["required_matrix"], lambda r: r["required_matrix"][1:])),
    ("required matrix with a duplicate", "required_matrix", _mutate(["required_matrix"], lambda r: r["required_matrix"] + [FIRST_LEG])),
    ("required matrix empty", "required_matrix", _mutate(["required_matrix"], [])),
    ("final without suite revision", "test_suite_revision", _mutate(["test_suite_revision"], None)),
    ("final without run id", "e2e_run_id", _mutate(["e2e_run_id"], None)),
    ("attempt 0", "e2e_attempt", _mutate(["e2e_attempt"], 0)),
    ("success with a cancelled leg", "results", _mutate(["results", FIRST_LEG], "cancelled")),
    ("success with a timed-out leg", "results", _mutate(["results", FIRST_LEG], "timed_out")),
    ("success with a failed leg", "results", _mutate(["results", FIRST_LEG], "failure")),
    ("required leg absent from results", "results", _mutate(["results", FIRST_LEG], DELETE)),
    ("unknown result value", "results", _mutate(["results", FIRST_LEG], "passed")),
    ("verdict not derivable", "verdict", _mutate(["verdict"], "failure")),
    ("unknown verdict", "verdict", _mutate(["verdict"], "green")),
    ("local-time timestamp", "recorded_at", _mutate(["recorded_at"], "2026-09-23T12:00:00+02:00")),
    ("restoration of the same release", "restored_from", _mutate(["restored_from"], lambda r: {"release_id": r["release_id"], "candidate_generation": 1})),
    ("unknown key", None, _mutate(["signature"], "x")),
    ("missing key", None, _mutate(["restored_from"], DELETE)),
]


class ReceiptRefusals(unittest.TestCase):
    def test_every_mutation_is_refused(self):
        for description, _field, mutate in RECEIPT_MUTATIONS:
            receipt = final_receipt()
            mutate(receipt)
            with self.subTest(description):
                with self.assertRaises(rc.ContractError):
                    rc.validate_receipt(receipt, POLICY)

    def test_pending_receipt_cannot_carry_evidence(self):
        for key, value in (("results", {FIRST_LEG: "success"}), ("e2e_run_id", 1), ("test_suite_revision", SUITE_REV)):
            r = pending_receipt()
            r[key] = value
            with self.subTest(key=key), self.assertRaises(rc.ContractError):
                rc.validate_receipt(r, POLICY)

    def test_support_digest_without_support(self):
        r = pending_receipt(support={})
        r["support_manifest_digest"] = "sha256:" + h("x")
        with self.assertRaises(rc.ContractError):
            rc.validate_receipt(r, POLICY)

    def test_failed_receipt_cannot_be_carried_over_by_restoration(self):
        r = final_receipt(overrides={"verdict": "failure", "restored_from": {"release_id": 1, "candidate_generation": 1}})
        r["results"][FIRST_LEG] = "failure"
        with self.assertRaises(rc.ContractError):
            rc.validate_receipt(r, POLICY)


class MutationCoverage(unittest.TestCase):
    """Adding a receipt field without a test that breaks it fails here."""

    def test_every_field_has_a_refusal(self):
        covered = {field for _d, field, _m in RECEIPT_MUTATIONS if field}
        # fields whose only invalid states are covered by dedicated tests above
        covered |= {"support_manifest_digest", "restored_from"}
        self.assertEqual(sorted(rc.RECEIPT_KEYS - covered), [])


class Dispatch(unittest.TestCase):
    def test_valid_body_and_the_pending_receipt_it_implies(self):
        body = dispatch_body()
        rc.validate_dispatch(body, POLICY)
        pending = rc.pending_receipt_from_dispatch(body, "2026-09-23T10:00:00Z")
        self.assertEqual(pending, pending_receipt())

    def test_realistic_agent_payload_is_far_below_the_limit(self):
        # 62 assets (the size of a real agent release) with long names, and every
        # leg the policy knows about including the pending ones.
        manifest = {f"supervizio-0.0.0-some-long-platform-name-{i:03d}.pkg.tar.zst": h(str(i)) for i in range(62)}
        legs = [leg["id"] for leg in POLICY["repositories"][AGENT]["legs"]]
        r = pending_receipt(manifest=manifest)
        body = dispatch_body(
            manifest=manifest,
            required_matrix=legs,
            candidate=dict({k: r[k] for k in rc.CANDIDATE_KEYS}, asset_manifest_digest=rc.manifest_digest(manifest)),
        )
        rc.validate_dispatch(body, POLICY)
        size = len(json.dumps(body, separators=(",", ":")).encode())
        self.assertLess(size, 16 * 1024, size)

    def test_eleven_top_level_properties_are_refused(self):
        body = dispatch_body()
        for i in range(5):
            body["client_payload"][f"x{i}"] = i
        with self.assertRaisesRegex(rc.ContractError, "top-level properties"):
            rc.validate_dispatch(body, POLICY)

    def test_64k_body_is_refused(self):
        manifest = {f"asset-{i:05d}-{'p' * 60}.bin": h(str(i)) for i in range(700)}
        r = pending_receipt(manifest=manifest)
        body = dispatch_body(manifest=manifest, candidate=dict({k: r[k] for k in rc.CANDIDATE_KEYS}))
        with self.assertRaisesRegex(rc.ContractError, "less than 65536"):
            rc.validate_dispatch(body, POLICY)

    def test_refusals(self):
        cases = {
            "event type": lambda b: b.update(event_type="run-e2e"),
            "schema": lambda b: b["client_payload"].update(schema="v0"),
            "other package": lambda b: b["client_payload"]["bridge"].update(package="supervizio/libprobe-release-candidates"),
            "bridge by tag": lambda b: b["client_payload"]["bridge"].update(digest="v1.4.2-g1"),
            "bridge extra key": lambda b: b["client_payload"]["bridge"].update(url="https://example.invalid"),
            "old staging": lambda b: b["client_payload"].update(staging=b["client_payload"].pop("bridge")),
            "weaker matrix": lambda b: b["client_payload"].update(required_matrix=b["client_payload"]["required_matrix"][:3]),
            "manifest/digest mismatch": lambda b: b["client_payload"]["manifest"].update({"supervizio-amd64.deb": h("x")}),
            "unknown candidate key": lambda b: b["client_payload"]["candidate"].update(extra=1),
            "missing support": lambda b: b["client_payload"].pop("support"),
            "extra body key": lambda b: b.update(ref="main"),
        }
        for name, mutate in cases.items():
            body = dispatch_body()
            mutate(body)
            with self.subTest(name), self.assertRaises(rc.ContractError):
                rc.validate_dispatch(body, POLICY)


class Evidence(unittest.TestCase):
    def setUp(self):
        self.pending = pending_receipt()
        self.legs = self.pending["required_matrix"]

    def build(self, jobs, run=None):
        return rc.build_final_receipt(self.pending, run or run_for(self.pending), jobs, POLICY, "2026-09-23T12:00:00Z")

    def test_all_green(self):
        final = self.build(jobs_for(self.legs))
        self.assertEqual(final["verdict"], "success")
        self.assertEqual(final["test_suite_revision"], SUITE_REV)
        self.assertEqual((final["e2e_run_id"], final["e2e_attempt"]), (4242, 1))

    def test_one_failure(self):
        self.assertEqual(self.build(jobs_for(self.legs, **{self.legs[3]: "failure"}))["verdict"], "failure")

    def test_cancelled_and_timed_out_are_errors_not_passes(self):
        for c in ("cancelled", "timed_out", "skipped"):
            with self.subTest(conclusion=c):
                final = self.build(jobs_for(self.legs, **{self.legs[0]: c}))
                self.assertEqual(final["verdict"], "error")
                self.assertEqual(final["results"][self.legs[0]], c)

    def test_leg_without_job_is_missing(self):
        final = self.build(jobs_for(self.legs[1:]))
        self.assertEqual(final["results"][self.legs[0]], "missing")
        self.assertEqual(final["verdict"], "error")

    def test_leg_reported_twice_is_incomplete(self):
        jobs = jobs_for(self.legs) + [{"name": rc.LEG_JOB_PREFIX + self.legs[0], "status": "completed", "conclusion": "success"}]
        final = self.build(jobs)
        self.assertEqual(final["results"][self.legs[0]], "incomplete")
        self.assertEqual(final["verdict"], "error")

    def test_unfinished_job_is_incomplete(self):
        final = self.build(jobs_for(self.legs, **{self.legs[0]: None}))
        self.assertEqual(final["results"][self.legs[0]], "incomplete")
        self.assertEqual(final["verdict"], "error")

    def test_run_must_be_bound_to_this_candidate(self):
        other = dict(self.pending, asset_manifest_digest="sha256:" + h("other bytes"))
        bad_runs = {
            "validated other bytes": run_for(self.pending, display_title=rc.expected_run_name(other)),
            "other generation": run_for(self.pending, display_title=rc.expected_run_name(dict(self.pending, candidate_generation=2))),
            "other commit": run_for(self.pending, display_title=rc.expected_run_name(dict(self.pending, resolved_commit=OTHER_COMMIT))),
            "other repository": run_for(self.pending, repository={"full_name": "someone/fork"}),
            "other workflow": run_for(self.pending, path=".github/workflows/e2e.yml"),
            "manual dispatch": run_for(self.pending, event="workflow_dispatch"),
            "feature branch": run_for(self.pending, head_branch="feat/x"),
            "still running": run_for(self.pending, status="in_progress"),
        }
        for name, run in bad_runs.items():
            with self.subTest(name), self.assertRaises(rc.ContractError):
                self.build(jobs_for(self.legs), run=run)

    def test_evidence_needs_a_pending_receipt(self):
        with self.assertRaises(rc.ContractError):
            rc.build_final_receipt(final_receipt(), run_for(self.pending), jobs_for(self.legs), POLICY, "2026-09-23T12:00:00Z")


class Promotion(unittest.TestCase):
    """Brief section 4.1: re-check tag target, generation, completeness and the
    real asset hashes right before --draft=false."""

    def setUp(self):
        self.receipt = final_receipt()

    def verify(self, state, **kw):
        return rc.verify_promotion(state, POLICY, **kw)

    def assertRefused(self, state, fragment, **kw):
        failures = self.verify(state, **kw)
        self.assertTrue(failures, "expected a refusal, got PASS")
        self.assertTrue(any(fragment in f for f in failures), failures)

    def test_consistent_draft_is_promotable(self):
        self.assertEqual(self.verify(state_for(self.receipt), expect_generation=1), [])

    def test_libprobe_draft_is_promotable(self):
        self.assertEqual(self.verify(state_for(final_receipt(LIBPROBE))), [])

    def test_tag_repointed(self):
        self.assertRefused(state_for(self.receipt, tag_commit=OTHER_COMMIT), "re-pointed")

    def test_tag_deleted(self):
        self.assertRefused(state_for(self.receipt, tag_commit=None), "does not exist")

    def test_asset_bytes_changed(self):
        assets = asset_list(self.receipt, {"supervizio-amd64.deb": "sha256:" + h("rebuilt")})
        self.assertRefused(state_for(self.receipt, assets=assets), "supervizio-amd64.deb: GitHub digest")

    def test_manifest_file_changed(self):
        assets = asset_list(self.receipt, {"checksums.txt": "sha256:" + h("edited")})
        self.assertRefused(state_for(self.receipt, assets=assets), "checksums.txt: GitHub digest")

    def test_asset_added(self):
        assets = asset_list(self.receipt) + [{"name": "surprise.sh", "digest": "sha256:" + h("x")}]
        self.assertRefused(state_for(self.receipt, assets=assets), "outside the validated manifest")

    def test_asset_removed(self):
        assets = [a for a in asset_list(self.receipt) if a["name"] != "supervizio-arm64.rpm"]
        self.assertRefused(state_for(self.receipt, assets=assets), "lacks asset")

    def test_receipt_not_stored_on_release(self):
        state = state_for(self.receipt, receipt=None)
        self.assertRefused(state, "carries no readable")

    def test_unparseable_receipt(self):
        state = state_for(self.receipt, receipt=None, receipt_error="unparseable: Expecting value")
        self.assertRefused(state, "unparseable")

    def test_cancelled_verdict(self):
        r = final_receipt(overrides={"verdict": "error"})
        r["results"][FIRST_LEG] = "cancelled"
        self.assertRefused(state_for(r), "only 'success' is promotable")

    def test_timed_out_verdict(self):
        r = final_receipt(overrides={"verdict": "error"})
        r["results"][FIRST_LEG] = "timed_out"
        failures = self.verify(state_for(r))
        self.assertTrue(any("timed_out" in f for f in failures), failures)

    def test_failed_verdict(self):
        r = final_receipt(overrides={"verdict": "failure"})
        r["results"][FIRST_LEG] = "failure"
        self.assertRefused(state_for(r), "only 'success' is promotable")

    def test_required_leg_missing(self):
        r = final_receipt(overrides={"verdict": "error"})
        r["results"][FIRST_LEG] = "missing"
        self.assertRefused(state_for(r), f"{FIRST_LEG}=missing")

    def test_forged_success_with_cancelled_leg(self):
        forged = final_receipt()
        forged["results"][FIRST_LEG] = "cancelled"  # verdict still says success
        self.assertRefused(state_for(forged), "stored receipt is invalid")

    def test_forged_receipt_with_weaker_matrix(self):
        forged = final_receipt()
        forged["required_matrix"] = forged["required_matrix"][:5]
        forged["results"] = {leg: "success" for leg in forged["required_matrix"]}
        self.assertRefused(state_for(forged), "omits leg")

    def test_pending_receipt(self):
        self.assertRefused(state_for(pending_receipt()), "only 'success' is promotable")

    def test_generation_mismatch(self):
        self.assertRefused(state_for(self.receipt), "generation", expect_generation=2)

    def test_release_replaced(self):
        self.assertRefused(state_for(self.receipt, id=999), "written for release")

    def test_release_on_other_tag(self):
        self.assertRefused(state_for(self.receipt, tag_name="v1.4.3"), "attached to tag")

    def test_already_published(self):
        self.assertRefused(state_for(self.receipt, draft=False), "not a draft")
        self.assertEqual(self.verify(state_for(self.receipt, draft=False), audit=True), [])

    def test_policy_tightening_never_invalidates_history(self):
        # A release validated when the policy required fewer legs: a NEW candidate
        # with that matrix is refused, the published release still audits clean.
        old = final_receipt()
        old["required_matrix"] = old["required_matrix"][:5]
        old["results"] = {leg: "success" for leg in old["required_matrix"]}
        state = state_for(old, draft=False)
        self.assertRefused(state_for(old), "omits leg")
        self.assertEqual(self.verify(state, audit=True), [])

    def test_audit_still_refuses_tampering(self):
        self.assertRefused(state_for(self.receipt, draft=False, tag_commit=OTHER_COMMIT), "re-pointed", audit=True)
        assets = asset_list(self.receipt, {"supervizio-amd64.deb": "sha256:" + h("rebuilt")})
        self.assertRefused(state_for(self.receipt, draft=False, assets=assets), "GitHub digest", audit=True)
        forged = final_receipt()
        forged["results"][FIRST_LEG] = "cancelled"
        self.assertRefused(state_for(forged, draft=False), "stored receipt is invalid", audit=True)

    def test_supplied_receipt_must_be_the_stored_one(self):
        other = copy.deepcopy(self.receipt)
        other["e2e_run_id"] = 1
        self.assertRefused(state_for(self.receipt), "differs from the receipt stored", receipt=other)

    def test_missing_github_digest_is_unverifiable(self):
        assets = asset_list(self.receipt, {"supervizio-amd64.deb": None})
        self.assertRefused(state_for(self.receipt, assets=assets), "unverifiable")

    def test_local_hash_can_stand_in_and_is_checked(self):
        assets = asset_list(self.receipt, {"supervizio-amd64.deb": None})
        for a in assets:
            if a["name"] == "supervizio-amd64.deb":
                a["local_sha256"] = self.receipt["manifest"]["supervizio-amd64.deb"]
        self.assertEqual(self.verify(state_for(self.receipt, assets=assets)), [])
        for a in assets:
            if a["name"] == "supervizio-amd64.deb":
                a["local_sha256"] = h("tampered in transit")
        self.assertRefused(state_for(self.receipt, assets=assets), "local sha256")

    def test_no_release(self):
        state = state_for(self.receipt)
        state["release"] = None
        self.assertRefused(state, "no release exists")


# --------------------------------------------------------------------------------------
# GitHub adapter against a fake API, and the redirect handling against a real socket
# --------------------------------------------------------------------------------------


class FakeApi(rc.Api):
    def __init__(self, routes, blobs=None):
        super().__init__(token="t", base="https://api.example")
        self.routes = routes
        self.blobs = blobs or {}

    def get(self, path):
        key = path.replace(self.base, "")
        if key not in self.routes:
            return 404, {"message": "Not Found"}, None
        data, nxt = self.routes[key]
        return 200, data, nxt

    def download_asset(self, repository, asset_id):
        return self.blobs[asset_id]


class Adapter(unittest.TestCase):
    def test_tag_resolution(self):
        routes = {
            "/repos/o/r/git/ref/tags/v1.0.0": ({"object": {"type": "commit", "sha": COMMIT}}, None),
            "/repos/o/r/git/ref/tags/v2.0.0": ({"object": {"type": "tag", "sha": "t1"}}, None),
            "/repos/o/r/git/tags/t1": ({"object": {"type": "tag", "sha": "t2"}}, None),
            "/repos/o/r/git/tags/t2": ({"object": {"type": "commit", "sha": OTHER_COMMIT}}, None),
        }
        api = FakeApi(routes)
        self.assertEqual(rc.resolve_tag(api, "o/r", "v1.0.0"), COMMIT)
        self.assertEqual(rc.resolve_tag(api, "o/r", "v2.0.0"), OTHER_COMMIT)  # annotated, nested
        self.assertIsNone(rc.resolve_tag(api, "o/r", "v9.9.9"))

    def test_observe_paginates_and_reads_the_receipt(self):
        r = final_receipt()
        assets = [dict(a, id=i, size=1) for i, a in enumerate(asset_list(r), start=1)]
        receipt_id = next(a["id"] for a in assets if a["name"] == POLICY["receipt_asset"])
        page2 = "https://api.example/repos/supervizio/agent/releases/123456/assets?per_page=100&page=2"
        routes = {
            "/repos/supervizio/agent/git/ref/tags/v1.4.2": ({"object": {"type": "commit", "sha": COMMIT}}, None),
            "/repos/supervizio/agent/releases/123456": ({"id": 123456, "tag_name": "v1.4.2", "draft": True}, None),
            "/repos/supervizio/agent/releases/123456/assets?per_page=100": (assets[:3], page2),
            "/repos/supervizio/agent/releases/123456/assets?per_page=100&page=2": (assets[3:], None),
        }
        api = FakeApi(routes, {receipt_id: json.dumps(r).encode()})
        state = rc.observe_release(api, AGENT, "v1.4.2", 123456, POLICY["receipt_asset"])
        self.assertEqual(len(state["release"]["assets"]), len(assets))
        self.assertEqual(rc.verify_promotion(state, POLICY), [])

    def test_observe_absent_release(self):
        routes = {"/repos/supervizio/agent/git/ref/tags/v1.4.2": ({"object": {"type": "commit", "sha": COMMIT}}, None)}
        state = rc.observe_release(FakeApi(routes), AGENT, "v1.4.2", 1, POLICY["receipt_asset"])
        self.assertIsNone(state["release"])
        self.assertTrue(rc.verify_promotion(state, POLICY))


class _Handler(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):  # noqa: N802
        _Handler.seen.append((self.path, self.headers.get("Authorization")))
        if self.path.startswith("/repos/"):
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/blob?sig=abc")
            self.end_headers()
        else:
            body = b"asset bytes"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):
        pass


class AssetDownload(unittest.TestCase):
    def test_token_is_not_forwarded_to_the_storage_host(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            _Handler.seen = []
            api = rc.Api(token="secret-token", base=f"http://127.0.0.1:{server.server_port}")
            self.assertEqual(api.download_asset("o/r", 7), b"asset bytes")
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(_Handler.seen[0], ("/repos/o/r/releases/assets/7", "Bearer secret-token"))
        self.assertEqual(_Handler.seen[1], ("/blob?sig=abc", None))


class _ErrorPage(http.server.BaseHTTPRequestHandler):
    """A proxy or load balancer answering with something that is not JSON."""

    body = b"<html><body>502 Bad Gateway</body></html>"
    status = 502

    def do_GET(self):  # noqa: N802
        self.send_response(self.status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass


class _InvalidUtf8(_ErrorPage):
    body = b"\xff\xfe\x00 not utf-8"
    status = 200


class ApiErrors(unittest.TestCase):
    def serve(self, handler):
        server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}"

    def test_html_error_page_is_a_usage_error(self):
        api = rc.Api(token="t", base=self.serve(_ErrorPage))
        with self.assertRaises(rc.UsageError):
            api.get("/repos/o/r/releases/1")

    def test_invalid_utf8_is_a_usage_error(self):
        api = rc.Api(token="t", base=self.serve(_InvalidUtf8))
        with self.assertRaises(rc.UsageError):
            api.get("/repos/o/r/releases/1")

    def test_cli_says_could_not_evaluate_not_contract_violated(self):
        # Exit 1 means "the contract is violated". A proxy error page is not evidence
        # about the release, so it must exit 2, and without a traceback.
        env = dict(os.environ, GITHUB_API_URL=self.serve(_ErrorPage), GH_TOKEN="t")
        proc = subprocess.run(
            [sys.executable, SCRIPT, "observe", "--repository", "o/r", "--tag", "v1.0.0", "--release-id", "1"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_malformed_evidence_input_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            pending = os.path.join(d, "pending.json")
            run = os.path.join(d, "run.json")
            jobs = os.path.join(d, "jobs.json")
            for path, obj in ((pending, pending_receipt()), (run, []), (jobs, {"jobs": []})):
                with open(path, "w") as fh:
                    json.dump(obj, fh)
            proc = subprocess.run(
                [sys.executable, SCRIPT, "evidence", "--pending", pending, "--run", run, "--jobs", jobs],
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


# --------------------------------------------------------------------------------------
# the bridge: OCI admission, the leg matrix, and a fake registry over a real socket
# --------------------------------------------------------------------------------------


def bridge_body(files, repository=AGENT, support=None, required_matrix=None):
    """A dispatch body whose manifest is `files` ({name: bytes}); the manifest file's
    bytes are the canonical serialisation, so the whole candidate is real."""
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    support = support or {}
    body = dispatch_body(repository)
    r = pending_receipt(repository, manifest=manifest, support={n: hashlib.sha256(d).hexdigest() for n, d in support.items()})
    payload = body["client_payload"]
    payload["candidate"] = {k: r[k] for k in rc.CANDIDATE_KEYS}
    payload["manifest"] = r["manifest"]
    payload["support"] = r["support"]
    if required_matrix is not None:
        payload["required_matrix"] = required_matrix
    return body


def oci_for(payload, drop=None, tamper=None, extra=None, candidate=None):
    files = rc.candidate_files(payload)
    layers = [(n, d, 10) for n, d in files.items() if n != drop]
    if tamper:
        layers = [(n, h("tampered") if n == tamper else d, s) for n, d, s in layers]
    if extra:
        layers.append((extra, h(extra), 1))
    return rc.build_candidate_manifest(candidate or payload["candidate"], layers)


def with_digest(body, raw):
    body["client_payload"]["bridge"]["digest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    return body["client_payload"]


class BridgeAdmission(unittest.TestCase):
    def setUp(self):
        self.body = bridge_body({"a.bin": b"a", "b.bin": b"b"}, support={"e2e-kit.tar.gz": b"kit"})
        self.payload = self.body["client_payload"]

    def test_consistent_artifact_is_admitted_without_downloading(self):
        raw = oci_for(self.payload)
        layers = rc.check_candidate_manifest(raw, with_digest(self.body, raw))
        self.assertEqual(sorted(layers), ["a.bin", "b.bin", "checksums.txt", "e2e-kit.tar.gz"])
        self.assertEqual(layers["checksums.txt"]["digest"], self.payload["candidate"]["asset_manifest_digest"])

    def test_manifest_is_deterministic(self):
        files = rc.candidate_files(self.payload)
        forward = rc.build_candidate_manifest(self.payload["candidate"], [(n, d, 1) for n, d in files.items()])
        backward = rc.build_candidate_manifest(self.payload["candidate"], [(n, d, 1) for n, d in reversed(list(files.items()))])
        self.assertEqual(forward, backward)

    def test_refusals(self):
        other = dict(self.payload["candidate"], candidate_generation=2)
        cases = {
            "one file's bytes differ": oci_for(self.payload, tamper="a.bin"),
            "manifest file differs": oci_for(self.payload, tamper="checksums.txt"),
            "support file differs": oci_for(self.payload, tamper="e2e-kit.tar.gz"),
            "file missing": oci_for(self.payload, drop="b.bin"),
            "manifest file missing": oci_for(self.payload, drop="checksums.txt"),
            "file added": oci_for(self.payload, extra="payload.sh"),
            "pushed for another generation": oci_for(self.payload, candidate=other),
        }
        for name, raw in cases.items():
            with self.subTest(name), self.assertRaises(rc.ContractError):
                rc.check_candidate_manifest(raw, with_digest(copy.deepcopy(self.body), raw))

    def test_served_bytes_must_hash_to_the_dispatched_digest(self):
        raw = oci_for(self.payload)
        payload = with_digest(self.body, raw)
        with self.assertRaisesRegex(rc.ContractError, "not the dispatched"):
            rc.check_candidate_manifest(raw + b" ", payload)

    def test_structural_refusals(self):
        good = json.loads(oci_for(self.payload))
        mutations = {
            "an archive layer": lambda m: m["layers"][0].update(mediaType="application/vnd.oci.image.layer.v1.tar+gzip"),
            "an image config": lambda m: m.update(config=dict(rc.EMPTY_CONFIG, mediaType="application/vnd.oci.image.config.v1+json")),
            "another artifact type": lambda m: m.update(artifactType="application/vnd.example"),
            "a layer twice": lambda m: m["layers"].append(copy.deepcopy(m["layers"][0])),
            "a path as title": lambda m: m["layers"][0]["annotations"].update({rc.TITLE_ANNOTATION: "../a.bin"}),
            "no layers": lambda m: m.update(layers=[]),
            "no annotation": lambda m: m.pop("annotations"),
        }
        for name, mutate in mutations.items():
            m = copy.deepcopy(good)
            mutate(m)
            raw = json.dumps(m).encode()
            with self.subTest(name), self.assertRaises(rc.ContractError):
                rc.check_candidate_manifest(raw, with_digest(copy.deepcopy(self.body), raw))


class LegMatrix(unittest.TestCase):
    def test_required_legs_are_scheduled_with_their_runner(self):
        legs, unknown = rc.leg_matrix(dispatch_body()["client_payload"], POLICY)
        self.assertEqual(unknown, [])
        self.assertEqual(len(legs), 53)
        self.assertTrue(all(leg["required"] for leg in legs))
        self.assertIn(
            {"id": "windows/arm64", "runner": "windows-11-arm", "required": True, "scenario": None, "host": "native", "platform": ""},
            legs,
        )

    def test_a_harness_leg_tells_the_workflow_where_it_runs(self):
        legs, _ = rc.leg_matrix(dispatch_body(LIBPROBE)["client_payload"], POLICY)
        by_id = {leg["id"]: leg for leg in legs}
        self.assertEqual(
            by_id["bsd/openbsd-amd64"],
            {"id": "bsd/openbsd-amd64", "runner": "ubuntu-24.04", "required": True, "scenario": "abi", "host": "openbsd", "platform": "openbsd-amd64"},
        )
        self.assertEqual((by_id["container/scratch"]["host"], by_id["container/scratch"]["platform"]), ("container-scratch", "linux-amd64-musl"))

    def test_advisory_legs_run_without_being_required(self):
        legs, _ = rc.leg_matrix(dispatch_body(LIBPROBE)["client_payload"], POLICY)
        advisory = [leg["id"] for leg in legs if not leg["required"]]
        self.assertEqual(advisory, rc.advisory_legs(POLICY, LIBPROBE))
        self.assertEqual(len(legs), 15)

    def test_a_leg_nobody_can_run_is_not_scheduled_and_reads_missing(self):
        payload = dispatch_body()["client_payload"]
        payload["required_matrix"] = payload["required_matrix"] + ["future/leg"]
        legs, unknown = rc.leg_matrix(payload, POLICY)
        self.assertEqual(unknown, ["future/leg"])
        self.assertNotIn("future/leg", [leg["id"] for leg in legs])
        results, verdict = rc.judge_jobs(payload, jobs_for([leg["id"] for leg in legs]))
        self.assertEqual((results["future/leg"], verdict), ("missing", "error"))


class Judge(unittest.TestCase):
    def setUp(self):
        self.payload = dispatch_body(LIBPROBE)["client_payload"]
        self.required = self.payload["required_matrix"]

    def test_advisory_failure_does_not_decide(self):
        jobs = jobs_for(self.required) + jobs_for(["bsd/netbsd-arm64"], "failure")[1:]
        results, verdict = rc.judge_jobs(self.payload, jobs)
        self.assertEqual((results["bsd/netbsd-arm64"], verdict), ("failure", "success"))

    def test_required_failure_decides(self):
        self.assertEqual(rc.judge_jobs(self.payload, jobs_for(self.required, **{self.required[0]: "failure"}))[1], "failure")

    def test_skipped_legs_after_a_refused_admission_are_errors(self):
        self.assertEqual(rc.judge_jobs(self.payload, jobs_for(self.required, "skipped"))[1], "error")


class _Registry(http.server.BaseHTTPRequestHandler):
    """Just enough of the OCI distribution API, GHCR-shaped: token exchange, blob
    uploads, manifests, and blob GETs that redirect to a storage host."""

    blobs = {}
    manifests = {}
    seen = []
    corrupt = set()

    def _send(self, status, body=b"", headers=None):
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _authorised(self):
        return self.headers.get("Authorization") == "Bearer registry-token"

    def do_GET(self):  # noqa: N802
        _Registry.seen.append((self.command, self.path, self.headers.get("Authorization")))
        if self.path.startswith("/token"):
            ok = self.headers.get("Authorization") == "Basic " + base64.b64encode(b"actor:gh-token").decode()
            return self._send(200, json.dumps({"token": "registry-token"}).encode()) if ok else self._send(401)
        if self.path.startswith("/storage/"):
            digest = self.path[len("/storage/"):]
            data = _Registry.blobs[digest]
            return self._send(200, data + b"!" if digest in _Registry.corrupt else data)
        if not self._authorised():
            return self._send(401)
        parts = self.path.split("/")
        if "manifests" in parts:
            ref = parts[-1]
            data = _Registry.manifests.get(ref)
            return self._send(200, data, {"Content-Type": rc.OCI_MANIFEST_MEDIA_TYPE}) if data else self._send(404)
        digest = parts[-1]
        if digest not in _Registry.blobs:
            return self._send(404)
        if self.command == "HEAD":
            return self._send(200)
        return self._send(307, headers={"Location": f"http://127.0.0.1:{self.server.server_port}/storage/{digest}"})

    do_HEAD = do_GET

    def do_POST(self):  # noqa: N802
        if not self._authorised():
            return self._send(401)
        return self._send(202, headers={"Location": "/v2/upload/session-1?state=x"})

    def do_PUT(self):  # noqa: N802
        if not self._authorised():
            return self._send(401)
        data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        path, _, query = self.path.partition("?")
        if "/manifests/" in path:
            digest = "sha256:" + hashlib.sha256(data).hexdigest()
            _Registry.manifests[path.split("/")[-1]] = data
            _Registry.manifests[digest] = data
            return self._send(201)
        digest = urllib.parse.parse_qs(query)["digest"][0]
        if "sha256:" + hashlib.sha256(data).hexdigest() != digest:
            return self._send(400)
        _Registry.blobs[digest] = data
        return self._send(201)

    def log_message(self, *args):
        pass


class RegistryRoundTrip(unittest.TestCase):
    def setUp(self):
        _Registry.blobs, _Registry.manifests, _Registry.seen, _Registry.corrupt = {}, {}, [], set()
        server = http.server.HTTPServer(("127.0.0.1", 0), _Registry)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_port}"
        self.files = {"a.bin": os.urandom(3000), "b.bin": os.urandom(10)}
        self.body = bridge_body(self.files)
        self.payload = self.body["client_payload"]
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp))
        src = os.path.join(self.tmp, "src")
        os.makedirs(src)
        for name, data in self.files.items():
            with open(os.path.join(src, name), "wb") as fh:
                fh.write(data)
        with open(os.path.join(src, "checksums.txt"), "wb") as fh:
            fh.write(rc.serialize_manifest(self.payload["manifest"]))
        self.src = src

    def registry(self, actions):
        return rc.Registry(self.payload["bridge"]["package"], actions, user="actor", token="gh-token", base=self.base)

    def test_push_then_pull_by_digest(self):
        digest = rc.push_candidate(self.registry("pull,push"), self.body, self.src, "v1.4.2-g1")
        self.payload["bridge"]["digest"] = digest
        rc.validate_dispatch(self.body, POLICY)
        out = os.path.join(self.tmp, "out")
        names = rc.pull_candidate(self.registry("pull"), self.payload, out)
        self.assertEqual(sorted(names), ["a.bin", "b.bin", "checksums.txt"])
        for name, data in self.files.items():
            with open(os.path.join(out, name), "rb") as fh:
                self.assertEqual(fh.read(), data)
        storage = [s for s in _Registry.seen if s[1].startswith("/storage/")]
        self.assertTrue(storage)
        self.assertTrue(all(auth is None for _, _, auth in storage), "token forwarded to the storage host")

    def test_push_refuses_a_file_that_is_not_the_manifested_one(self):
        with open(os.path.join(self.src, "a.bin"), "ab") as fh:
            fh.write(b"x")
        with self.assertRaisesRegex(rc.ContractError, "a.bin: sha256"):
            rc.push_candidate(self.registry("pull,push"), self.body, self.src, "v1.4.2-g1")
        self.assertEqual(_Registry.manifests, {})

    def test_pull_refuses_bytes_that_do_not_hash_to_their_layer(self):
        digest = rc.push_candidate(self.registry("pull,push"), self.body, self.src, "v1.4.2-g1")
        self.payload["bridge"]["digest"] = digest
        _Registry.corrupt.add("sha256:" + self.payload["manifest"]["a.bin"])
        out = os.path.join(self.tmp, "out")
        with self.assertRaisesRegex(rc.ContractError, "arrived as"):
            rc.pull_candidate(self.registry("pull"), self.payload, out, ["a.bin"])
        self.assertEqual(os.listdir(out), [])

    def test_pull_re_admits_instead_of_trusting_admit(self):
        # A leg is handed the dispatch, not admit's word: pointed at an artifact that
        # lacks a manifested file, it refuses before downloading anything.
        del self.files["b.bin"]
        os.remove(os.path.join(self.src, "b.bin"))
        partial = bridge_body(self.files)
        with open(os.path.join(self.src, "checksums.txt"), "wb") as fh:
            fh.write(rc.serialize_manifest(partial["client_payload"]["manifest"]))
        self.payload["bridge"]["digest"] = rc.push_candidate(self.registry("pull,push"), partial, self.src, "v1.4.2-g1")
        out = os.path.join(self.tmp, "out")
        with self.assertRaisesRegex(rc.ContractError, "candidate artifact"):
            rc.pull_candidate(self.registry("pull"), self.payload, out)
        self.assertFalse(os.path.exists(out))

    def test_pull_by_a_digest_the_registry_does_not_hold(self):
        self.payload["bridge"]["digest"] = "sha256:" + h("nothing")
        with self.assertRaises(rc.UsageError):
            rc.pull_candidate(self.registry("pull"), self.payload, os.path.join(self.tmp, "out"))

    def test_token_exchange_refused(self):
        with self.assertRaises(rc.UsageError):
            rc.Registry(self.payload["bridge"]["package"], "pull", user="actor", token="wrong", base=self.base)


class Scenario(unittest.TestCase):
    def run_cli(self, *args):
        proc = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def test_production_legs_fail_closed_until_wired(self):
        with tempfile.TemporaryDirectory() as d:
            body = os.path.join(d, "body.json")
            with open(body, "w") as fh:
                json.dump(dispatch_body(), fh)
            code, out = self.run_cli("scenario", "--dispatch", body, "--leg", "docker/amd64/scratch", "--dir", d)
        self.assertEqual(code, 1, out)
        self.assertIn("no release scenario is wired", out)

    def test_integrity_scenario_under_the_proof_policy(self):
        files = {"a.bin": b"a"}
        body = bridge_body(files, required_matrix=["proof/linux-amd64", "proof/macos-arm64", "proof/windows-amd64"])
        body["client_payload"]["bridge"]["package"] = "supervizio/release-contract-bridge-probe"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "body.json")
            with open(path, "w") as fh:
                json.dump(body, fh)
            with open(os.path.join(d, "a.bin"), "wb") as fh:
                fh.write(b"a")
            with open(os.path.join(d, "checksums.txt"), "wb") as fh:
                fh.write(rc.serialize_manifest(body["client_payload"]["manifest"]))
            args = ("--policy", PROOF_POLICY, "scenario", "--dispatch", path, "--leg", "proof/linux-amd64", "--dir", d)
            self.assertEqual(self.run_cli(*args)[0], 0)
            with open(os.path.join(d, "a.bin"), "wb") as fh:
                fh.write(b"b")
            self.assertEqual(self.run_cli(*args)[0], 1)
            # The same body is refused by the production policy: wrong package.
            self.assertEqual(self.run_cli("scenario", "--dispatch", path, "--leg", "proof/linux-amd64", "--dir", d)[0], 1)


class AbiScenario(unittest.TestCase):
    """The libprobe harness's host half: what `scenario --stage prepare` refuses
    before anything is compiled, and what `--stage check` refuses afterwards. The
    consumer itself is proven on real archives by validate-release.yml runs."""

    PLATFORM = "linux-amd64"
    LEG = "native/linux-amd64"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp))
        self.cand = os.path.join(self.tmp, "cand")
        self.work = os.path.join(self.tmp, "work")
        os.makedirs(self.cand)
        self.header = b"/* probe.h */\n"
        self.archive = b"!<arch>\nnot really an archive\n"
        self.write_candidate()

    def tarball(self, members):
        import io
        import tarfile

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, data in members:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return buf.getvalue()

    def meta(self, **over):
        meta = {"name": "libprobe", "version": "v1.4.2", "platform": self.PLATFORM, "git_sha": COMMIT,
                "rust_toolchain": "rustc 1.98.1", "abi_sha256": hashlib.sha256(self.archive).hexdigest()}
        meta.update(over)
        return json.dumps(meta).encode()

    def write_candidate(self, members=None, header=None):
        members = members if members is not None else [("libprobe.a", self.archive), ("probe.h", self.header), ("metadata.json", self.meta())]
        files = {f"libprobe-{self.PLATFORM}-v1.4.2.tar.gz": self.tarball(members), "probe.h": header or self.header}
        for name, data in files.items():
            with open(os.path.join(self.cand, name), "wb") as fh:
                fh.write(data)
        self.body = bridge_body(files, repository=LIBPROBE)
        self.payload = self.body["client_payload"]
        self.leg = {leg["id"]: leg for leg in POLICY["repositories"][LIBPROBE]["legs"]}[self.LEG]

    def prepare(self):
        return rc.abi_prepare(self.payload, self.leg, self.cand, self.work)

    def test_prepare_stages_the_published_pair_and_the_harness(self):
        staged = self.prepare()
        self.assertEqual(staged["EXPECTED_VERSION"], "1.4.2")
        self.assertEqual(sorted(os.listdir(self.work)), ["consumer.c", "libprobe.a", "metadata.json", "plan.env", "probe.h", "run.sh"])
        with open(os.path.join(self.work, "plan.env"), "rb") as fh:
            self.assertEqual(fh.read(), b"PLATFORM=linux-amd64\nEXPECTED_VERSION=1.4.2\n")
        with open(os.path.join(self.work, "libprobe.a"), "rb") as fh:
            self.assertEqual(fh.read(), self.archive)

    def test_prepare_refusals(self):
        cases = {
            "the tag metadata.json names": ([("libprobe.a", self.archive), ("probe.h", self.header), ("metadata.json", self.meta(version="v0.2.0"))], None, "version"),
            "another platform": ([("libprobe.a", self.archive), ("probe.h", self.header), ("metadata.json", self.meta(platform="linux-arm64"))], None, "platform"),
            "another archive": ([("libprobe.a", self.archive + b"x"), ("probe.h", self.header), ("metadata.json", self.meta())], None, "abi_sha256"),
            "a header that is not the published one": ([("libprobe.a", self.archive), ("probe.h", b"/* other */"), ("metadata.json", self.meta())], None, "differs"),
            "a member outside the bundle": ([("libprobe.a", self.archive), ("probe.h", self.header), ("metadata.json", self.meta()), ("../evil", b"x")], None, "unexpected member"),
            "a missing member": ([("libprobe.a", self.archive), ("probe.h", self.header)], None, "lacks metadata.json"),
            "a member twice": ([("libprobe.a", self.archive), ("libprobe.a", self.archive), ("probe.h", self.header), ("metadata.json", self.meta())], None, "twice"),
        }
        for name, (members, header, why) in cases.items():
            with self.subTest(name):
                self.write_candidate(members, header)
                with self.assertRaisesRegex(rc.ContractError, why):
                    self.prepare()

    def test_prepare_refuses_a_platform_the_candidate_does_not_publish(self):
        self.leg = dict(self.leg, harness={"platform": "linux-arm64", "host": "native"})
        with self.assertRaisesRegex(rc.ContractError, "publishes no libprobe-linux-arm64-v1.4.2.tar.gz"):
            self.prepare()

    def test_prepare_refuses_bytes_changed_after_the_pull(self):
        with open(os.path.join(self.cand, "probe.h"), "ab") as fh:
            fh.write(b" ")
        with self.assertRaisesRegex(rc.ContractError, "does not match the manifest"):
            self.prepare()

    def report(self, **over):
        checks = [{"name": n, "ok": True, "detail": ""} for n in rc.ABI_REQUIRED_CHECKS]
        report = {"schema": rc.ABI_REPORT_SCHEMA, "expected_version": "1.4.2", "version": "1.4.2", "abi_fingerprint": "0x1", "checks": checks, "ok": True}
        report.update(over)
        os.makedirs(self.work, exist_ok=True)
        with open(os.path.join(self.work, "report.json"), "w") as fh:
            json.dump(report, fh)

    def test_check_accepts_a_complete_green_report(self):
        self.report()
        self.assertEqual(rc.abi_check_report(self.payload, self.work)["version"], "1.4.2")

    def test_check_refusals(self):
        with self.assertRaisesRegex(rc.ContractError, "never ran"):
            rc.abi_check_report(self.payload, self.work)
        green = [{"name": n, "ok": True, "detail": ""} for n in rc.ABI_REQUIRED_CHECKS]
        cases = {
            "the archive's own version": ({"version": "0.2.0"}, "reports version"),
            "the version it was asked for": ({"expected_version": "1.4.1"}, "was asked for"),
            "a failed check": ({"checks": green[:-1] + [{"name": "probe_shutdown", "ok": False, "detail": "x"}]}, "failed"),
            "a check that never ran": ({"checks": green[1:]}, "check version is absent"),
            "an overall not-ok": ({"ok": False}, "does not say ok"),
            "another schema": ({"schema": "x"}, "is not a"),
        }
        for name, (over, why) in cases.items():
            with self.subTest(name):
                self.report(**over)
                with self.assertRaisesRegex(rc.ContractError, why):
                    rc.abi_check_report(self.payload, self.work)


# --------------------------------------------------------------------------------------
# the CLI: exit codes are the interface workflows rely on
# --------------------------------------------------------------------------------------


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        proc = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def write(self, directory, name, obj):
        path = os.path.join(directory, name)
        with open(path, "w") as fh:
            json.dump(obj, fh)
        return path

    def test_manifest_build_matches_vector(self):
        proc = subprocess.run([sys.executable, SCRIPT, "manifest", "build", "--dir", os.path.join(VECTOR, "files")], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(VECTOR, "SHA256SUMS"), "rb") as fh:
            self.assertEqual(proc.stdout, fh.read())

    def test_manifest_build_excludes_reserved_names(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("a.bin", "checksums.txt", "release-receipt.json"):
                with open(os.path.join(d, name), "w") as fh:
                    fh.write(name)
            code, out = self.run_cli("manifest", "build", "--dir", d, "--repository", AGENT, "--output", os.path.join(d, "checksums.txt"))
            self.assertEqual(code, 0, out)
            with open(os.path.join(d, "checksums.txt"), "rb") as fh:
                self.assertEqual(rc.parse_manifest(fh.read()), {"a.bin": h("a.bin")})

    def test_verify_files(self):
        manifest = os.path.join(VECTOR, "SHA256SUMS")
        with open(os.path.join(VECTOR, "DIGEST")) as fh:
            digest = fh.read().strip()
        files = os.path.join(VECTOR, "files")
        self.assertEqual(self.run_cli("manifest", "verify-files", "--manifest", manifest, "--expect-digest", digest, "--dir", files)[0], 0)
        code, out = self.run_cli("manifest", "verify-files", "--manifest", manifest, "--expect-digest", "sha256:" + h("x"), "--dir", files)
        self.assertEqual(code, 1, out)
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "probe.h"), "w") as fh:
                fh.write("#pragma twice\n")
            code, out = self.run_cli("manifest", "verify-files", "--manifest", manifest, "--expect-digest", digest, "--dir", d, "--only", "probe.h")
            self.assertEqual(code, 1, out)
            self.assertIn("probe.h: sha256", out)

    def test_receipt_and_promotion_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good = self.write(d, "good.json", final_receipt())
            bad_receipt = final_receipt()
            bad_receipt["results"][FIRST_LEG] = "cancelled"
            bad = self.write(d, "bad.json", bad_receipt)
            self.assertEqual(self.run_cli("receipt", "check", good)[0], 0)
            self.assertEqual(self.run_cli("receipt", "check", bad)[0], 1)
            state = self.write(d, "state.json", state_for(final_receipt()))
            repointed = self.write(d, "repointed.json", state_for(final_receipt(), tag_commit=OTHER_COMMIT))
            self.assertEqual(self.run_cli("verify-promotion", "--state", state, "--expect-generation", "1")[0], 0)
            code, out = self.run_cli("verify-promotion", "--state", repointed)
            self.assertEqual(code, 1, out)
            self.assertIn("re-pointed", out)
            self.assertEqual(self.run_cli("receipt", "check", os.path.join(d, "absent.json"))[0], 2)

    def test_dispatch_pending_evidence_chain(self):
        with tempfile.TemporaryDirectory() as d:
            body = self.write(d, "dispatch.json", dispatch_body())
            self.assertEqual(self.run_cli("dispatch", "check", body)[0], 0)
            code, name = self.run_cli("dispatch", "run-name", body)
            self.assertEqual(name.strip(), rc.expected_run_name(pending_receipt()))
            pending_path = os.path.join(d, "pending.json")
            self.assertEqual(self.run_cli("receipt", "pending", "--dispatch", body, "--recorded-at", "2026-09-23T10:00:00Z", "--output", pending_path)[0], 0)
            pending = _load(pending_path)
            run = self.write(d, "run.json", run_for(pending))
            jobs = self.write(d, "jobs.json", {"total_count": 0, "jobs": jobs_for(pending["required_matrix"], **{FIRST_LEG: "cancelled"})})
            final_path = os.path.join(d, "final.json")
            code, out = self.run_cli("evidence", "--pending", pending_path, "--run", run, "--jobs", jobs, "--output", final_path)
            self.assertEqual(code, 0, out)
            final = _load(final_path)
            self.assertEqual(final["verdict"], "error")
            state = self.write(d, "state.json", state_for(final))
            code, out = self.run_cli("verify-promotion", "--state", state)
            self.assertEqual(code, 1, out)


class ShippedPolicy(unittest.TestCase):
    def test_policy_is_valid_and_sized_as_inventoried(self):
        rc.validate_policy(POLICY)
        self.assertEqual(len(rc.required_legs(POLICY, AGENT)), 53)
        self.assertEqual(len(POLICY["repositories"][AGENT]["legs"]), 53)
        self.assertEqual(len(rc.required_legs(POLICY, LIBPROBE)), 12)
        self.assertEqual(rc.advisory_legs(POLICY, LIBPROBE), ["bsd/freebsd-arm64", "bsd/openbsd-arm64", "bsd/netbsd-arm64"])
        # Nothing may be promoted before a leg's release scenario exists: every
        # agent leg is scheduled, and fails closed, until it is wired. Every
        # libprobe leg runs the ABI consumer on its own platform's archive.
        for leg in POLICY["repositories"][AGENT]["legs"]:
            self.assertIsNone(leg["scenario"], leg["id"])
        for leg in POLICY["repositories"][LIBPROBE]["legs"]:
            self.assertEqual(leg["scenario"], "abi", leg["id"])
            self.assertIn(leg["harness"]["host"], rc.HARNESS_HOSTS)

    def test_policy_refusals(self):
        bad = copy.deepcopy(POLICY)
        bad["repositories"][AGENT]["legs"].append(dict(bad["repositories"][AGENT]["legs"][0]))
        with self.assertRaises(rc.ContractError):
            rc.validate_policy(bad)
        bad = copy.deepcopy(POLICY)
        bad["repositories"][AGENT]["manifest_file"] = POLICY["receipt_asset"]
        with self.assertRaises(rc.ContractError):
            rc.validate_policy(bad)
        bad = copy.deepcopy(POLICY)
        bad["repositories"][AGENT]["legs"][-1]["state"] = "pending-merge"
        with self.assertRaises(rc.ContractError):  # a pending leg must name its PR
            rc.validate_policy(bad)
        for key, value in (("runner", None), ("runner", "ubuntu 24.04"), ("scenario", "run-anything"), ("state", "optional"), ("scenario", "abi")):
            bad = copy.deepcopy(POLICY)
            bad["repositories"][AGENT]["legs"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(rc.ContractError):
                rc.validate_policy(bad)
        for harness in (None, {"platform": "linux-amd64"}, {"platform": "linux amd64", "host": "native"}, {"platform": "linux-amd64", "host": "docker"}):
            bad = copy.deepcopy(POLICY)
            bad["repositories"][LIBPROBE]["legs"][0]["harness"] = harness
            with self.subTest(harness=harness), self.assertRaises(rc.ContractError):
                rc.validate_policy(bad)
        for package in (None, "Supervizio/Agent", "agent", "supervizio/agent candidates"):
            bad = copy.deepcopy(POLICY)
            bad["repositories"][AGENT]["bridge_package"] = package
            with self.subTest(package=package), self.assertRaises(rc.ContractError):
                rc.validate_policy(bad)

    def test_proof_policy_is_valid_and_isolated(self):
        proof = rc.load_policy(PROOF_POLICY)
        self.assertEqual(proof["validation"], POLICY["validation"])
        self.assertEqual(proof["repositories"][AGENT]["bridge_package"], "supervizio/release-contract-bridge-probe")
        # The proof policy may never share a package with production: its legs
        # execute nothing, so a production candidate admitted under it would be
        # "validated" by an integrity check alone.
        production = {spec["bridge_package"] for spec in POLICY["repositories"].values()}
        for spec in proof["repositories"].values():
            self.assertNotIn(spec["bridge_package"], production)


if __name__ == "__main__":
    unittest.main()
