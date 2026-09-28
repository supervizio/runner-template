"""The policy and receipt release-contract-proof.yml stages on a live draft.

The live proof governs this repository itself: it adds supervizio/runner-template
to the shipped policy, attaches a receipt to a draft it creates, and runs
`observe` / `verify-promotion` against GitHub. Both documents used to be written
inline in the workflow, and that workflow only runs on main when its own file
changes. So when the contract started requiring every repository to name its
`bridge_package` and every leg its `runner`, the inline policy went stale without
anything noticing: the proof failed at `stage` from 2026-09-25 (run 36196251579)
until the next unrelated edit of the workflow re-ran it.

Building them here puts them under the unit tests instead. test_live_proof.py
builds both on every change to release-contract/ and walks verify_promotion
through the proof's four checks offline, so a contract change that would break
the live proof now fails release-contract.yml first.

    live_proof.py --repository R --tag T --commit SHA --release-id N \
        --manifest rel/SHA256SUMS --run-id ID --run-attempt N --out proof/

writes proof/policy.json and proof/release-receipt.json. Python >= 3.9, stdlib.
"""

import argparse
import copy
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import release_contract as rc  # noqa: E402

PROOF_LEG = "proof/leg"
MANIFEST_FILE = "SHA256SUMS"
# Never pushed to: the live proof has no candidate. The contract still requires
# every governed repository to name its bridge, and this is the measurement
# package the proofs already use (README section 4).
BRIDGE_PACKAGE = "supervizio/release-contract-bridge-probe"
# Documentation only -- no job is scheduled for this leg; the receipt records a
# result for it directly. It names the image the proof itself runs on.
RUNNER = "ubuntu-26.04"


def proof_policy(repository: str, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The shipped policy plus `repository`, governed by one required leg."""
    policy = copy.deepcopy(base) if base is not None else rc.load_policy()
    policy["repositories"][repository] = {
        "manifest_file": MANIFEST_FILE,
        "bridge_package": BRIDGE_PACKAGE,
        "legs": [
            {
                "id": PROOF_LEG,
                "state": "required",
                "from": "release-contract-proof.yml",
                "runner": RUNNER,
                "scenario": "integrity",
            }
        ],
    }
    rc.validate_policy(policy)
    return policy


def proof_receipt(
    policy: Dict[str, Any],
    repository: str,
    tag: str,
    commit: str,
    release_id: int,
    manifest: Dict[str, str],
    run_id: int,
    run_attempt: int,
    recorded_at: Optional[str] = None,
) -> Dict[str, Any]:
    """A successful receipt for the draft, as `evidence` would have written it."""
    required: List[str] = rc.required_legs(policy, repository)
    receipt = {
        "schema": rc.RECEIPT_SCHEMA,
        "repository": repository,
        "tag": tag,
        "resolved_commit": commit,
        "release_id": release_id,
        "candidate_generation": 1,
        "manifest_file": rc.repo_policy(policy, repository)["manifest_file"],
        "asset_manifest_digest": rc.manifest_digest(manifest),
        "manifest": manifest,
        "support_manifest_digest": None,
        "support": {},
        "required_matrix": required,
        "test_suite_revision": commit,
        "e2e_run_id": run_id,
        "e2e_attempt": run_attempt,
        "results": {leg: "success" for leg in required},
        "verdict": "success",
        "recorded_at": recorded_at or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "restored_from": None,
    }
    rc.validate_receipt(receipt, policy)
    return receipt


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repository", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--release-id", type=int, required=True)
    p.add_argument("--manifest", required=True, help="the canonical manifest file uploaded to the draft")
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--run-attempt", type=int, required=True)
    p.add_argument("--out", required=True, help="directory for policy.json and release-receipt.json")
    args = p.parse_args(argv)
    policy = proof_policy(args.repository)
    with open(args.manifest, "rb") as fh:
        manifest = rc.parse_manifest(fh.read())
    receipt = proof_receipt(policy, args.repository, args.tag, args.commit, args.release_id,
                            manifest, args.run_id, args.run_attempt)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "policy.json"), "w") as fh:
        json.dump(policy, fh, indent=2)
    with open(os.path.join(args.out, policy["receipt_asset"]), "w") as fh:
        json.dump(receipt, fh, indent=2, sort_keys=True)
    print(f"policy and receipt for {args.repository}@{args.tag} release {args.release_id} valid under this contract")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (rc.ContractError, rc.UsageError) as exc:
        print(f"live_proof.py: {exc}", file=sys.stderr)
        sys.exit(1)
