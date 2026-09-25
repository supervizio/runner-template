# Signing keys

Public OpenPGP keys that `.github/actions/qemu-vm` uses to verify an upstream
cloud image by **signature** instead of by a pinned hash. Only public keys live
here; nothing secret belongs in this directory, or in this public repository.

## Why a key instead of a hash

A pinned sha256 is the stronger claim, and the Alpine, Debian, Fedora and Arch
legs keep one: those upstreams publish each build under its own name and keep
it. Two do not:

- **openSUSE** rebuilds `Leap-16.0-Minimal-VM.x86_64-Cloud.qcow2` in place and
  keeps only the newest build. The pin in `e2e.yml` went stale on 2026-09-24 and
  turned `e2e/vm/opensuse-zypper` red on every agent PR; a pinned build number
  would have turned into a 404 instead.
- **Rocky Linux** moves each GenericCloud build out of `pub/` at the next point
  release.

For those two, `resolve-image.sh` finds the build published now, and the action
takes its sha256 from the checksum file the distribution signs, once `gpgv`
proves that the signature was made by the key named here. The fingerprint is
pinned in the workflow and checked against gpgv's `VALIDSIG` line, so a key file
that ever gained a second key could not widen what is accepted.

## The keys

| File | Key | Fingerprint | Fetched from |
|------|-----|-------------|--------------|
| `opensuse-project-signing-key.asc` | openSUSE Project Signing Key, RSA 4096, expires 2030-05-27 | `AD485664E901B867051AB15F35A2F86E29B700A4` | `https://download.opensuse.org/distribution/leap/16.0/repo/oss/repodata/repomd.xml.key` |
| `rocky-linux-10-release-key.asc` | Release Engineering (Rocky Linux 10), RSA, no expiry | `FC226859C0860BF0DDB95B085B106C736FEDFC85` | `https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-10` |

Both were checked on 2026-09-25: one primary key per file, and each verifies the
signature on its distribution's current image checksum while rejecting the
other's.

## Rotating a key

When a distribution rotates its key (openSUSE's expires on 2030-05-27), the leg
fails with `checksum signed by '<new fingerprint>', expected <old>` or with a
signature that does not verify: loud, never a silent pass. Replace the file from
the distribution's own HTTPS location, confirm the new fingerprint against the
distribution's published key list, and update the fingerprint in `e2e.yml` and
`qemu-vm-selftest.yml` in the same change.
