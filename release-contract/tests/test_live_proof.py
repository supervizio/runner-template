"""release-contract-proof.yml, offline: the documents it stages and the verdicts it expects.

The live proof runs only on main, and only when its workflow changes; these tests
run on every change to release-contract/. They build the proof's policy and
receipt with the same module the workflow calls (live_proof.py), then replay its
four `verify-promotion` checks on states shaped like what `observe` reports, and
hold the output fragments the workflow greps for to what the validator prints.

Run: python3 -m unittest discover -s release-contract/tests -v
"""

import contextlib
import copy
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import live_proof  # noqa: E402
import release_contract as rc  # noqa: E402

WORKFLOW = os.path.join(os.path.dirname(ROOT), ".github", "workflows", "release-contract-proof.yml")
REPO = "supervizio/runner-template"
TAG = "v0.0.0-proof.36452112279"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
REPOINTED = "fedcba9876543210fedcba9876543210fedcba98"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# The three files the workflow's `stage` job uploads (proof-big.bin is random
# there; any bytes do here).
FILES = {"proof-alpha.bin": b"alpha\n", "proof-beta.bin": b"beta\n", "proof-big.bin": b"\x00" * 4096}


def staged():
    policy = live_proof.proof_policy(REPO)
    manifest = {name: sha(data) for name, data in FILES.items()}
    receipt = live_proof.proof_receipt(policy, REPO, TAG, COMMIT, 424242, manifest, 36452112279, 1)
    return policy, receipt


def observed(receipt, policy, digests=None, tag_commit=COMMIT):
    """What `observe --hash-assets` reports for the draft `stage` built."""
    digests = digests or {}
    manifest_bytes = rc.serialize_manifest(receipt["manifest"])
    receipt_bytes = json.dumps(receipt, indent=2, sort_keys=True).encode()
    blobs = dict(FILES)
    blobs[receipt["manifest_file"]] = manifest_bytes
    blobs[policy["receipt_asset"]] = receipt_bytes
    assets = []
    for name, data in sorted(blobs.items()):
        digest = digests.get(name, "sha256:" + sha(data))
        assets.append({"name": name, "id": len(assets) + 1, "size": len(data), "digest": digest,
                       "local_sha256": digest[len("sha256:"):]})
    return {
        "schema": rc.STATE_SCHEMA,
        "repository": REPO,
        "tag": receipt["tag"],
        "tag_commit": tag_commit,
        "release": {"id": receipt["release_id"], "tag_name": receipt["tag"], "draft": True,
                    "assets": assets, "receipt": copy.deepcopy(receipt), "receipt_error": None},
    }


def expected_fragments():
    """The `check "<label>" 1 "<fragment>"` refusals the workflow asserts."""
    with open(WORKFLOW, encoding="utf-8") as fh:
        text = fh.read()
    return dict(re.findall(r'check "([^"]+)" 1 "([^"]+)"', text))


class LiveProofDocuments(unittest.TestCase):
    def test_the_policy_is_the_shipped_one_plus_this_repository(self):
        policy, _ = staged()
        shipped = rc.load_policy()
        self.assertEqual(set(policy["repositories"]) - set(shipped["repositories"]), {REPO})
        for repo, spec in shipped["repositories"].items():
            self.assertEqual(policy["repositories"][repo], spec, repo)
        self.assertEqual(rc.required_legs(policy, REPO), [live_proof.PROOF_LEG])

    def test_the_entry_the_workflow_wrote_before_is_refused(self):
        # The inline entry release-contract-proof.yml carried until 2026-09-28:
        # no bridge_package, and a leg with no runner. Kept so that the reason the
        # proof was red has a test, not just a commit message.
        policy = rc.load_policy()
        policy["repositories"][REPO] = {"manifest_file": "SHA256SUMS", "legs": [
            {"id": "proof/leg", "state": "required", "from": "release-contract-proof.yml"}]}
        with self.assertRaisesRegex(rc.ContractError, "bridge_package"):
            rc.validate_policy(policy)

    def test_the_receipt_is_valid_and_successful(self):
        policy, receipt = staged()
        rc.validate_receipt(receipt, policy)
        self.assertEqual(receipt["verdict"], "success")
        self.assertEqual(receipt["asset_manifest_digest"], "sha256:" + sha(rc.serialize_manifest(receipt["manifest"])))

    def test_the_command_line_writes_what_the_workflow_uploads(self):
        with tempfile.TemporaryDirectory() as d:
            for name, data in FILES.items():
                with open(os.path.join(d, name), "wb") as fh:
                    fh.write(data)
            manifest = rc.build_manifest_from_dir(d)
            with open(os.path.join(d, "SHA256SUMS"), "wb") as fh:
                fh.write(rc.serialize_manifest(manifest))
            out = os.path.join(d, "proof")
            with contextlib.redirect_stdout(io.StringIO()):
                code = live_proof.main(["--repository", REPO, "--tag", TAG, "--commit", COMMIT, "--release-id", "7",
                                        "--manifest", os.path.join(d, "SHA256SUMS"), "--run-id", "9",
                                        "--run-attempt", "2", "--out", out])
            self.assertEqual(code, 0)
            policy = rc.load_policy(os.path.join(out, "policy.json"))
            with open(os.path.join(out, policy["receipt_asset"])) as fh:
                receipt = json.load(fh)
            rc.validate_receipt(receipt, policy)
            self.assertEqual((receipt["release_id"], receipt["e2e_run_id"], receipt["e2e_attempt"]), (7, 9, 2))
            self.assertEqual(receipt["manifest"], manifest)


class LiveProofChecks(unittest.TestCase):
    """The four checks of the workflow's `verify-live` job, in its order."""

    def setUp(self):
        self.policy, self.receipt = staged()

    def verify(self, state):
        return rc.verify_promotion(state, self.policy, self.receipt, expect_generation=1)

    def test_the_workflow_still_greps_for_two_refusals(self):
        self.assertEqual(set(expected_fragments()), {"asset bytes replaced", "tag re-pointed"})

    def test_consistent_draft_passes(self):
        self.assertEqual(self.verify(observed(self.receipt, self.policy)), [])

    def test_asset_bytes_replaced_is_refused_with_the_text_the_workflow_expects(self):
        state = observed(self.receipt, self.policy, digests={"proof-beta.bin": "sha256:" + sha(b"gamma\n")})
        failures = self.verify(state)
        self.assertTrue(failures)
        self.assertIn(expected_fragments()["asset bytes replaced"], "\n".join(failures))

    def test_asset_bytes_restored_passes_again(self):
        self.assertEqual(self.verify(observed(self.receipt, self.policy)), [])

    def test_tag_re_pointed_is_refused_with_the_text_the_workflow_expects(self):
        failures = self.verify(observed(self.receipt, self.policy, tag_commit=REPOINTED))
        self.assertTrue(failures)
        self.assertIn(expected_fragments()["tag re-pointed"], "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
