"""Synthetic tests: real retail game files are not used."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "tools" / "compare_xex_modules.py"
SPEC = importlib.util.spec_from_file_location("compare_xex_modules", SRC)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompareXexTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.archive = self.root / "archive"
        self.disc = self.root / "disc"
        self.archive.mkdir()
        self.disc.mkdir()

    def write(self, root, path, payload):
        item = root / path
        item.parent.mkdir(parents=True, exist_ok=True)
        item.write_bytes(payload)
        return item

    def test_identical_modules(self):
        self.write(self.archive, "bin/server_360.dll", b"XEX2a")
        self.write(self.disc, "bin/server_360.dll", b"XEX2a")
        res = MODULE.compare(MODULE.get_modules(self.archive), MODULE.get_modules(self.disc))
        self.assertEqual(res["identical"], ["bin/server_360.dll"])

    def test_changes_same_size_detected(self):
        self.write(self.archive, "default.xex", b"XEX2foo")
        self.write(self.disc, "default.xex", b"XEX2bar")
        res = MODULE.compare(MODULE.get_modules(self.archive), MODULE.get_modules(self.disc))
        self.assertEqual(res["different"], ["default.xex"])

    def test_changes_different_size(self):
        self.write(self.archive, "default.xex", b"XEX2foo")
        self.write(self.disc, "default.xex", b"XEX2f")
        res = MODULE.compare(MODULE.get_modules(self.archive), MODULE.get_modules(self.disc))
        self.assertEqual(res["different"], ["default.xex"])

    def test_missing_modules(self):
        self.write(self.archive, "a.dll", b"XEX2a")
        self.write(self.disc, "b.dll", b"XEX2b")
        res = MODULE.compare(MODULE.get_modules(self.archive), MODULE.get_modules(self.disc))
        self.assertEqual(res["archive_only"], ["a.dll"])
        self.assertEqual(res["disc_only"], ["b.dll"])

    def test_non_xex_ignored(self):
        self.write(self.archive, "movie.bik", b"BINK")
        self.write(self.archive, "file.dll", b"MZ??")
        self.assertEqual(MODULE.get_modules(self.archive), {})

    def test_nested_and_case_insensitive_paths(self):
        self.write(self.archive, "BIN/X.dll", b"XEX2x")
        self.write(self.disc, "bin/x.DLL", b"XEX2x")
        res = MODULE.compare(MODULE.get_modules(self.archive), MODULE.get_modules(self.disc))
        self.assertEqual(res["identical"], ["bin/x.dll"])

    def test_read_only(self):
        a = self.write(self.archive, "default.xex", b"XEX2abc")
        b = self.write(self.disc, "default.xex", b"XEX2abc")
        times = [a.stat().st_mtime_ns, b.stat().st_mtime_ns]
        MODULE.compare(MODULE.get_modules(self.archive), MODULE.get_modules(self.disc))
        self.assertEqual(times, [a.stat().st_mtime_ns, b.stat().st_mtime_ns])

    def test_missing_path_error(self):
        self.assertEqual(MODULE.main(["--archive", str(self.archive), "--disc", str(self.root / "missing")]), 2)

    def test_same_folder_error(self):
        self.assertEqual(MODULE.main(["--archive", str(self.archive), "--disc", str(self.archive)]), 2)


if __name__ == "__main__":
    unittest.main()
