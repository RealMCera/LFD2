"""Synthetic (not game-derived) Source map header tests."""
import struct
import unittest
from tools.probe_source_assets import probe_bsp_header

class SourceHeaderTests(unittest.TestCase):
    def make(self, magic=b"VBSP", endian="<", layout="offset_length_version"):
        header = bytearray(1036)
        header[:4] = magic
        struct.pack_into(endian + "i", header, 4, 21)
        offset = 8 + 3 * 16
        values = (1050, 512, 0) if layout == "offset_length_version" else (0, 1050, 512)
        struct.pack_into(endian + "iii", header, offset, *values)
        return bytes(header)

    def test_little_endian_header(self):
        meta = probe_bsp_header(self.make(), 5000)
        self.assertEqual(meta["version_candidate"], 21)
        self.assertEqual(meta["endian_candidate"], "little")
        self.assertEqual(meta["layouts"]["offset_length_version"]["sample_lumps"]["vertices"]["bytes"], 512)

    def test_swapped_candidate(self):
        meta = probe_bsp_header(self.make(b"PSBV", ">"), 5000)
        self.assertEqual(meta["endian_candidate"], "big")
        self.assertEqual(meta["version_candidate"], 21)

    def test_l4d2_order_candidate(self):
        meta = probe_bsp_header(self.make(layout="version_offset_length"), 5000)
        self.assertEqual(meta["layouts"]["version_offset_length"]["sample_lumps"]["vertices"]["bytes"], 512)

    def test_short_header(self):
        meta = probe_bsp_header(b"VBSP", 4)
        self.assertIn("too short", meta["status"])

    def test_unknown_header(self):
        meta = probe_bsp_header(b"XXXX" + bytes(1032), 1036)
        self.assertIn("unrecognized", meta["status"])

if __name__ == "__main__":
    unittest.main()
