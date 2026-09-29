# harness/libprobe/ — the ABI consumer of a published libprobe archive

`consumer.c` includes only the published `probe.h`, links only the published
`libprobe.a`, and asks the archive what a consumer depends on: the version
against the tag, the ABI fingerprint, every carrier's size against the header,
then `probe_init`, a few collectors and `probe_shutdown`, executed for real. It
writes `report.json`; `release_contract.py scenario --stage check` judges it.

`run.sh` compiles and runs it wherever the leg's platform lives: the runner, a
guest, a container. Plain POSIX `sh`, because it runs under the BSDs' `/bin/sh`,
the ksh93 illumos and Solaris ship as `/bin/sh`, Alpine's busybox and Git Bash.
It needs a C compiler and nothing else.

## One `case` arm per platform family

Each arm names the compiler and the system libraries a Rust staticlib needs on
that OS (what `rustc --print native-static-libs` prints for the target) plus the
ones libprobe's collectors call. A missing library is a link error, and a link
error fails the leg: a consumer would hit it too.

| Platform | Compiler | Libraries |
|----------|----------|-----------|
| `illumos-*` | `gcc -m64` (the OmniOS `-build` image has no `cc`) | `-lkstat -lsendfile -llgrp -lsocket -lposix4 -lpthread -lresolv -lnsl -lumem -lgcc_s -lc -lm -lrt` |
| `solaris-*` | `gcc -m64` (the Solaris `-gcc` image) | the illumos list without `-lnsl -lumem`, which Rust's std does not ask for there |

`-lkstat` is libprobe's own (its illumos/Solaris readers use libkstat); the rest
is the standard library's. `-m64` because the archives are LP64 whatever the
compiler's default. The other arms (Linux glibc and musl, macOS, the BSDs,
Windows) are unchanged. `tests/test_release_contract.py` fails if a leg's
platform in `policy.json` matches no arm, since `run.sh` exits 2 there.
