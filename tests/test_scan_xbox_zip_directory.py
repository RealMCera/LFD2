"""Synthetic-only tests for bounded central-directory signature scanning."""
import io
import struct
import unittest
import zipfile

from tools.scan_xbox_zip_directory import scan_directory
from tools.inspect_xbox_zip import XboxZipError


def sample_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("materials/plaster/plaster_int_14.vmt", "synthetic")
        z.writestr("materials/tile/tile_ceiling_01.vtfx", b"synthetic")
        z.writestr("models/test.mdl", b"synthetic")
    return bytes(buf.getvalue())


def insert_directory_gap(raw, count=58):
    data = bytearray(raw)
    first = data.find(b"PK\x01\x02")
    assert first >= 0
    n, e, c = struct.unpack_from("<3H", data, first + 28)
    nextpos = first + 46 + n + e + c
    data[nextpos:nextpos] = b"\x00" * count
    eocd = data.rfind(b"PK\x05\x06")
    old = struct.unpack_from("<I", data, eocd + 12)[0]
    struct.pack_into("<I", data, eocd + 12, old + count)
    return bytes(data)


class RawCentralScanTests(unittest.TestCase):
    def test_standard_zip_count_and_materials(self):
        raw = sample_zip()
        report = scan_directory(io.BytesIO(raw), len(raw))
        self.assertEqual(report["candidate_headers"], 3)
        self.assertEqual(report["eocd_count"], 3)
        self.assertEqual(report["adjacent_pairs"], 2)
        self.assertEqual(report["overlapping_pairs"], 0)
        self.assertEqual(report["extensions"][".vmt"], 1)
        self.assertEqual(report["extensions"][".vtfx"], 1)
        self.assertIn("materials/plaster/plaster_int_14.vmt", report["filenames"])

    def test_58_byte_directory_gap_scanned_without_following_header_lengths(self):
        raw = insert_directory_gap(sample_zip())
        report = scan_directory(io.BytesIO(raw), len(raw))
        self.assertEqual(report["candidate_headers"], 3)
        self.assertEqual(report["eocd_count"], 3)
        self.assertEqual(report["small_gap_pairs"], 1)
        self.assertEqual(report["largest_gap"], 58)
        self.assertEqual(report["overlapping_pairs"], 0)

    def test_long_gap_works_in_diagnostic_even_if_sequential_parser_refuses(self):
        raw = insert_directory_gap(sample_zip(), 180)
        report = scan_directory(io.BytesIO(raw), len(raw))
        self.assertEqual(report["candidate_headers"], 3)
        self.assertEqual(report["large_gap_pairs"], 1)
        self.assertEqual(report["largest_gap"], 180)

    def test_invalid_eocd_stops(self):
        raw = sample_zip()[:-22]
        with self.assertRaises(XboxZipError):
            scan_directory(io.BytesIO(raw), len(raw))


if __name__ == "__main__":
    unittest.main()
