"""Synthetic tests; never require or redistribute commercial game data."""
from __future__ import annotations

import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "tools" / "import_disc_iso.py"
SPEC = importlib.util.spec_from_file_location("import_disc_iso", SRC)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DiscISOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "disc.iso"

    def create_fixture(self, partition=0, *, root_sector=100, root_size=4096, valid=True):
        desc_offset = partition + MODULE.DESCRIPTOR_OFFSET
        length = partition + 150 * MODULE.SECTOR_SIZE
        # truncate makes a sparse file, including for large XGD partition offsets.
        with self.path.open("wb") as stream:
            stream.truncate(length)
            stream.seek(desc_offset)
            data = bytearray(MODULE.SECTOR_SIZE)
            if valid:
                data[:len(MODULE.MAGIC)] = MODULE.MAGIC
                data[-len(MODULE.MAGIC):] = MODULE.MAGIC
            struct.pack_into("<II", data, len(MODULE.MAGIC), root_sector, root_size)
            stream.write(data)
        return self.path

    def test_xiso(self):
        report = MODULE.inspect_iso(self.create_fixture())
        self.assertEqual(report["layout"], "XISO")
        self.assertEqual(report["root_directory_sector"], 100)

    def test_xgd2_sparse(self):
        report = MODULE.inspect_iso(self.create_fixture(0x0FD90000))
        self.assertEqual(report["layout"], "XGD2")

    def test_xgd3_sparse(self):
        report = MODULE.inspect_iso(self.create_fixture(0x02080000))
        self.assertEqual(report["layout"], "XGD3")

    def test_xgd1_sparse(self):
        report = MODULE.inspect_iso(self.create_fixture(0x18300000))
        self.assertEqual(report["layout"], "XGD1")

    def test_bad_magic(self):
        with self.assertRaisesRegex(ValueError, "No valid XDVDFS"):
            MODULE.inspect_iso(self.create_fixture(valid=False))

    def test_bad_root_bounds(self):
        with self.assertRaisesRegex(ValueError, "bounds are invalid"):
            MODULE.inspect_iso(self.create_fixture(root_sector=160))

    def test_probe_is_read_only(self):
        image = self.create_fixture()
        before = image.stat()
        MODULE.inspect_iso(image)
        after = image.stat()
        self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))

    def test_extract_refuses_nonempty_destination(self):
        image = self.create_fixture()
        output = self.root / "existing"
        output.mkdir()
        (output / "existing-file.txt").write_text("keep", encoding="utf-8")
        with patch.object(MODULE.subprocess, "run") as runner:
            with self.assertRaisesRegex(ValueError, "must be empty"):
                MODULE.extract_iso(image, output, "xdvdfs")
            runner.assert_not_called()

    def test_extract_command_handles_spaces(self):
        image = self.create_fixture()
        output = self.root / "destination with spaces"
        with patch.object(MODULE.subprocess, "run") as runner:
            MODULE.extract_iso(image, output, "xdvdfs.exe")
            runner.assert_called_once_with(["xdvdfs.exe", "unpack", str(image), str(output)], check=True)


if __name__ == "__main__":
    unittest.main()
