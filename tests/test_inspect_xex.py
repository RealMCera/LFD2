"""Synthetic fixtures only. No game files needed."""
import struct
import tempfile
import unittest
from pathlib import Path

from tools.inspect_xex import inspect_xex


class XexHeaderTests(unittest.TestCase):
    def make_file(self, *, magic=b"XEX2", count=1):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "dummy.xex"
        content = bytearray(512)
        struct.pack_into(">4sIIIII", content, 0, magic, 1, 0x180, 0, 0x100, count)
        if count == 1:
            struct.pack_into(">II", content, 24, 0x00040006, 0x40)
            struct.pack_into(">IIIIBBBBI", content, 0x40,
                             0xAABBCCDD, 0x00010002, 0x00010001,
                             0x12345678, 2, 1, 1, 2, 0x11223344)
        path.write_bytes(content)
        return tmp, path

    def test_execution_id(self):
        tmp, path = self.make_file()
        try:
            r = inspect_xex(path)
            self.assertEqual(r["format"], "XEX2")
            self.assertEqual(r["title_id"], "12345678")
            self.assertEqual(r["media_id"], "AABBCCDD")
            self.assertEqual(r["disc_number"], 1)
            self.assertEqual(r["disc_count"], 2)
            self.assertTrue(r["execution_id_present"])
        finally:
            tmp.cleanup()

    def test_wrong_magic(self):
        tmp, path = self.make_file(magic=b"NOPE")
        try:
            with self.assertRaisesRegex(ValueError, "Not a XEX2"):
                inspect_xex(path)
        finally:
            tmp.cleanup()

    def test_truncated_directory(self):
        tmp, path = self.make_file(count=999)
        try:
            with self.assertRaisesRegex(ValueError, "Unreasonable or truncated"):
                inspect_xex(path)
        finally:
            tmp.cleanup()

    def test_file_format_flags(self):
        tmp, path = self.make_file(count=2)
        try:
            data = bytearray(path.read_bytes())
            struct.pack_into(">II", data, 24, 0x00040006, 0x40)
            struct.pack_into(">II", data, 32, 0x000003FF, 0x80)
            struct.pack_into(">IIIIBBBBI", data, 0x40, 1, 2, 3, 4, 0, 0, 1, 1, 0)
            struct.pack_into(">IHH", data, 0x80, 16, 1, 2)
            path.write_bytes(data)
            report = inspect_xex(path)
            self.assertTrue(report["base_file_format_present"])
            self.assertEqual(report["encryption_type"], "1: normal (encrypted)")
            self.assertEqual(report["compression_type"], "2: normal (LZX)")
            self.assertEqual(report["title_id"], "00000004")
        finally:
            tmp.cleanup()

    def test_file_format_invalid_length(self):
        tmp, path = self.make_file(count=2)
        try:
            data = bytearray(path.read_bytes())
            struct.pack_into(">II", data, 32, 0x000003FF, 0x80)
            struct.pack_into(">IHH", data, 0x80, 4, 1, 2)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "invalid size"):
                inspect_xex(path)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
