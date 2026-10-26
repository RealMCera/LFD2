"""Read-only Xbox ZIP directory parser tests with synthetic archives only."""
import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.inspect_xbox_zip import XboxZipError, inspect_xbox_zip, parse_directory, diagnose_alignment


def make_zip(invalid_extra=False):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",compression=zipfile.ZIP_STORED) as z:
        info=zipfile.ZipInfo("materials/hotel/wall.vmt")
        info.extra=b"\x0e\x00\x00\x00"
        z.writestr(info,b"synthetic only")
        z.writestr("materials/hotel/wall.vtfx",b"VTFX")
        z.writestr("models/stairs.mdl",b"mdl")
    data=bytearray(buf.getvalue())
    if invalid_extra:
        center=data.find(b"PK\x01\x02")
        assert center>=0
        nlen=struct.unpack_from("<H",data,center+28)[0]
        extra=center+46+nlen
        assert data[extra:extra+4]==b"\x0e\x00\x00\x00"
        data[extra:extra+4]=b"\x0e\x00\xcd\x60"   # extra declares 24,781 bytes but holds none
    return bytes(data)


class XboxZipTests(unittest.TestCase):
    def test_simple_zip_directory(self):
        data=make_zip()
        result=parse_directory(io.BytesIO(data),len(data))
        self.assertEqual(result["count"],3)
        self.assertEqual(result["extension_counts"][".vmt"],1)
        self.assertEqual(result["extension_counts"][".vtfx"],1)
        self.assertEqual(result["extension_counts"][".mdl"],1)

    def test_malformed_internal_extra_ignored(self):
        data=make_zip(invalid_extra=True)
        result=parse_directory(io.BytesIO(data),len(data))
        self.assertEqual(result["count"],3)
        self.assertEqual(result["skipped_extra_bytes"],4)
        self.assertIn("materials/hotel/wall.vmt",result["filenames"])

    def test_disk_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"game.360.zip"
            path.write_bytes(make_zip(invalid_extra=True))
            result=inspect_xbox_zip(path)
            self.assertEqual(result["entries_declared"],3)

    def test_missing_eocd(self):
        with self.assertRaisesRegex(XboxZipError,"end-of-central"):
            parse_directory(io.BytesIO(b"not a ZIP"),9)

    def test_declared_directory_offset_invalid(self):
        data=bytearray(make_zip())
        end=data.rfind(b"PK\x05\x06")
        struct.pack_into("<I",data,end+16,0x01000000)
        # Reader is permitted to recover from prefix offsets using EOCD size.
        result=parse_directory(io.BytesIO(data),len(data))
        self.assertEqual(result["count"],3)

    def test_diagnose_corrupt_record_length(self):
        data=bytearray(make_zip())
        center=data.find(b"PK\x01\x02")
        struct.pack_into("<H",data,center+28,1800)
        lines=diagnose_alignment(io.BytesIO(data),len(data))
        self.assertTrue(any("Entry 0" in line and "filename_bytes=1800" in line for line in lines))
        self.assertTrue(any("safe bounds" in line for line in lines))

    def test_diagnose_gap_between_entries(self):
        data=bytearray(make_zip())
        cd=data.find(b"PK\x01\x02")
        filename_len=struct.unpack_from("<H",data,cd+28)[0]
        extra_len=struct.unpack_from("<H",data,cd+30)[0]
        comment_len=struct.unpack_from("<H",data,cd+32)[0]
        nextpos=cd+46+filename_len+extra_len+comment_len
        data[nextpos:nextpos]=b"XYZ"
        eocd=data.rfind(b"PK\x05\x06")
        original_size=struct.unpack_from("<I",data,eocd+12)[0]
        struct.pack_into("<I",data,eocd+12,original_size+3)
        with self.assertRaisesRegex(XboxZipError,"Invalid central header"):
            parse_directory(io.BytesIO(data),len(data))
        lines=diagnose_alignment(io.BytesIO(data),len(data))
        self.assertTrue(any("First candidate delta from expected: +3" in line for line in lines))

    def test_bad_central_entry_length(self):
        data=bytearray(make_zip())
        center=data.find(b"PK\x01\x02")
        struct.pack_into("<H",data,center+28,2000)
        with self.assertRaises(XboxZipError):
            parse_directory(io.BytesIO(data),len(data))


if __name__=="__main__":
    unittest.main()
