"""Catalog tests use synthetic headers only, not commercial game files."""
import struct
import tempfile
import unittest
from pathlib import Path

from tools.catalog_modules import catalog


class CatalogTests(unittest.TestCase):
    def test_xex2_inside_dll_and_xex(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            fake = struct.pack(">4sIIIII", b"XEX2", 1, 0x20, 0, 0x30, 0)
            (root / "bin" / "server_360.dll").write_bytes(fake + b"\x00" * 64)
            (root / "default.xex").write_bytes(fake + b"\x00" * 64)
            (root / "windows.dll").write_bytes(b"MZ" + b"\x00" * 100)
            records, errors = catalog(root)
            self.assertEqual(errors, [])
            self.assertEqual(len(records), 2)
            self.assertEqual(
                {entry["path"] for entry in records},
                {"bin/server_360.dll", "default.xex"},
            )

    def test_bad_xex_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.dll").write_bytes(b"XEX2")
            records, errors = catalog(root)
            self.assertEqual(records, [])
            self.assertEqual(len(errors), 1)
            self.assertIn("bad.dll", errors[0])


if __name__ == "__main__":
    unittest.main()
