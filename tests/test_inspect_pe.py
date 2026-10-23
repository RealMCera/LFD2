"""Header-only PE parser tests using fabricated, non-game bytes."""
import struct
import unittest

from tools.inspect_pe import parse_pe


def synthetic_pe():
    buf = bytearray(0x400)
    buf[:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, 0x80)
    buf[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<HHIIIHH", buf, 0x84, 0x01F2, 1, 0, 0, 0, 0xE0, 0x010F)
    opt = 0x80 + 24
    struct.pack_into("<H", buf, opt, 0x10B)
    struct.pack_into("<I", buf, opt + 16, 0x10CB8)
    struct.pack_into("<I", buf, opt + 28, 0x82000000)
    struct.pack_into("<I", buf, opt + 56, 0xC0000)
    struct.pack_into("<8sIIIIIIHHI", buf, opt + 0xE0,
                     b".text", 0x20000, 0x1000, 0x200, 0x200,
                     0, 0, 0, 0, 0x60000020)
    return buf


class PeTests(unittest.TestCase):
    def test_image_and_entry(self):
        result = parse_pe(bytes(synthetic_pe()))
        self.assertEqual(result["format"], "PE32")
        self.assertEqual(result["entry_va_from_pe"], "0x82010CB8")
        self.assertEqual(result["sections"], 1)
        self.assertEqual(result["section_table"][0]["name"], ".text")

    def test_bad_mz(self):
        data = synthetic_pe()
        data[:2] = b"NO"
        with self.assertRaisesRegex(ValueError, "MZ"):
            parse_pe(bytes(data))

    def test_bad_pe(self):
        data = synthetic_pe()
        data[0x80:0x84] = b"NOPE"
        with self.assertRaisesRegex(ValueError, "PE signature"):
            parse_pe(bytes(data))

    def test_truncated_sections(self):
        data = synthetic_pe()
        struct.pack_into("<H", data, 0x86, 96)
        with self.assertRaisesRegex(ValueError, "Truncated"):
            parse_pe(bytes(data))


if __name__ == "__main__":
    unittest.main()
