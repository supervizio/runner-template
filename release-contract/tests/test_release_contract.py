"""Tests for release_contract.py -- stdlib unittest, no network.

Most of this file is about the validator SAYING NO. A validator that cannot fail
proves nothing, so every rule of README.md has a test that breaks it and expects
a refusal, and `MutationCoverage` fails the suite if a receipt field is added
without one.

Run: python3 -m unittest discover -s release-contract/tests -v
"""

from __future__ import annotations

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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import release_contract as rc  # noqa: E402

SCRIPT = os.path.join(ROOT, "release_contract.py")
VECTOR = os.path.join(HERE, "vectors", "manifest-v1")
POLICY = rc.load_policy()

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
            "staging": {"repository": "supervizio/runner-template", "release_id": 987654, "tag_name": "stage/agent/v1.4.2/g1"},
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
        r["required_matrix"] = r["required_matrix"] + ["openbsd/amd64/7.3"]
        r["results"]["openbsd/amd64/7.3"] = "success"
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
            "staging repo": lambda b: b["client_payload"]["staging"].update(repository="supervizio/agent"),
            "staging id": lambda b: b["client_payload"]["staging"].update(release_id=0),
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
        self.assertEqual(len(rc.required_legs(POLICY, AGENT)), 34)
        self.assertEqual(len(POLICY["repositories"][AGENT]["legs"]), 53)
        self.assertEqual(len(rc.required_legs(POLICY, LIBPROBE)), 15)

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
        del bad["repositories"][AGENT]["legs"][-1]["pr"]
        with self.assertRaises(rc.ContractError):
            rc.validate_policy(bad)


if __name__ == "__main__":
    unittest.main()
