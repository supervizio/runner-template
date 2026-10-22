"""`.github/scripts/check_run_retention.py` on this repository, and on what it must refuse.

The rules are in the script's docstring; supervizio/agent#297 is why.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
SCRIPT = os.path.join(REPO, ".github", "scripts", "check_run_retention.py")


def load():
    spec = importlib.util.spec_from_file_location("check_run_retention", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CRR = load()

UPLOAD = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1"


def wf(steps, name="x"):
    return "name: %s\non: push\njobs:\n  a:\n    runs-on: ubuntu-26.04\n    steps:\n%s" % (name, steps)


class RunRetention(unittest.TestCase):
    def test_repository_is_clean(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = CRR.main(["check", REPO])
        self.assertEqual(rc, 0, out.getvalue())

    def test_issue_acceptance_counts(self):
        # The issue's own check, per file: grep -c upload-artifact == grep -c 'retention-days: 1'.
        d = os.path.join(REPO, ".github", "workflows")
        for name in sorted(os.listdir(d)):
            if not name.endswith(".yml"):
                continue
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            self.assertEqual(
                sum("upload-artifact" in l for l in lines),
                sum("retention-days: 1" in l for l in lines),
                name,
            )

    def errs(self, rel, text):
        return CRR.check_file(rel, text)

    def test_upload_without_retention(self):
        e = self.errs(".github/workflows/x.yml", wf("      - uses: %s\n        with:\n          name: n\n          path: p\n" % UPLOAD))
        self.assertTrue(any("(R1)" in x for x in e), e)
        self.assertTrue(any("(R2)" in x for x in e), e)

    def test_upload_with_longer_retention(self):
        e = self.errs(".github/workflows/x.yml", wf("      - uses: %s\n        with:\n          path: p\n          retention-days: 7\n" % UPLOAD))
        self.assertTrue(any("must be 1" in x for x in e), e)

    def test_upload_with_one_day_passes(self):
        e = self.errs(".github/workflows/x.yml", wf("      - name: up\n        uses: %s\n        with:\n          path: p\n          retention-days: 1\n" % UPLOAD))
        self.assertEqual(e, [])

    def test_cache_in_product_workflow(self):
        e = self.errs(".github/workflows/e2e.yml", wf("      - uses: actions/cache/restore@0057852bfaa89a56745cba8c7296529d2fc39830\n        with:\n          path: ~/.cache/x\n          key: k\n"))
        self.assertTrue(any("(R3)" in x for x in e), e)

    def test_cache_of_product_path_anywhere(self):
        e = self.errs(".github/workflows/x.yml", wf("      - uses: actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830\n        with:\n          path: pkg/\n          key: k\n"))
        self.assertTrue(any("(R4)" in x for x in e), e)

    def test_setup_go_default_cache_in_product_workflow(self):
        step = "      - uses: actions/setup-go@b7ad1dad31e06c5925ef5d2fc7ad053ef454303e\n        with:\n          go-version-file: agent/go.work\n"
        self.assertTrue(any("cache: false" in x for x in self.errs(".github/workflows/e2e.yml", wf(step))))
        self.assertEqual(self.errs(".github/workflows/e2e.yml", wf(step + "          cache: false\n")), [])

    def test_cache_after_prepare_outside_exceptions(self):
        step = "      - uses: vmactions/alpine-vm@697847385681cdc413604693010eded91e8d9650\n        with:\n          cache-after-prepare: true\n"
        e = self.errs(".github/workflows/external-e2e.yml", wf(step))
        self.assertTrue(any("cache-after-prepare" in x for x in e), e)

    def test_unclassified_lane(self):
        e = self.errs(".github/workflows/new.yml", wf("      - run: echo supervizio/libprobe\n"))
        self.assertTrue(any("(R5)" in x for x in e), e)

    def test_stale_exception_is_reported(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(REPO, ".github"), os.path.join(tmp, ".github"))
            p = os.path.join(tmp, ".github", "workflows", "e2e.yml")
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text.replace("cache-after-prepare: true", "cache-after-prepare: false"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = CRR.main(["check", tmp])
            self.assertEqual(rc, 1)
            self.assertIn("stale", out.getvalue())
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
