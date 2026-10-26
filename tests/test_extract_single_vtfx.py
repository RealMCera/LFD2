"""Synthetic-only VTFX header and ZIP copy safety tests."""
import io
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from tools.extract_single_vtfx import (
    parse_vtfx_header, inspect_archive, validate_texture, select_entry,
    XboxZipError,
)
from tools.scan_xbox_zip_directory import scan_directory


def vtfx_texture(width=256,height=256,format_id=15) -> bytes:
    blob=bytearray(0x44+256)
    blob[:4]=b"VTFX"
    struct.pack_into(">4I",blob,4,0x360,8,0x44,0)
    struct.pack_into(">5H",blob,0x14,width,height,1,1,0)
    struct.pack_into(">BB",blob,0x1e,0,1)
    struct.pack_into(">I",blob,0x30,format_id)
    struct.pack_into(">I",blob,0x38,0)
    return bytes(blob)


def example_archive(data=None) -> bytes:
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_STORED) as z:
        z.writestr("materials/plaster/plaster_int_14.360.vtf",
                   data if data is not None else vtfx_texture())
    return buffer.getvalue()


class VtfxExtractTests(unittest.TestCase):
    def test_parse_xbox_header(self):
        record=parse_vtfx_header(vtfx_texture())
        self.assertEqual(record["version"],"864.8")
        self.assertEqual(record["width"],256)
        self.assertEqual(record["height"],256)
        self.assertEqual(record["format_name"],"DXT5")
        self.assertEqual(record["header_size"],0x44)
        self.assertEqual(record["resource_count"],1)

    def test_bad_header_rejected(self):
        with self.assertRaises(XboxZipError):
            parse_vtfx_header(b"VTFX")
        with self.assertRaises(XboxZipError):
            parse_vtfx_header(b"WRONG"+b"\0"*70)
        with self.assertRaises(XboxZipError):
            parse_vtfx_header(vtfx_texture(width=0))

    def test_exact_zip_entry_found_and_validated(self):
        content=example_archive()
        with io.BytesIO(content) as stream:
            entry=inspect_archive(stream,len(content),
                                  "materials/plaster/plaster_int_14.360.vtf")
        self.assertEqual(entry["bytes"],len(vtfx_texture()))
        self.assertEqual(entry["header"]["format_name"],"DXT5")
        self.assertEqual(entry["directory_candidates"],1)

    def test_mismatching_name_refused(self):
        content=example_archive()
        with io.BytesIO(content) as stream:
            with self.assertRaisesRegex(XboxZipError,"exactly one"):
                inspect_archive(stream,len(content),"materials/not-this.360.vtf")

    def test_reject_invalid_local_offset(self):
        content=example_archive()
        with io.BytesIO(content) as stream:
            report=scan_directory(stream,len(content))
            entry=dict(report["entries"][0])
            entry["local_offset"]=len(content)+10
            with self.assertRaises(XboxZipError):
                validate_texture(stream,len(content),report["directory_offset"],entry)

    def test_reject_deflate_zip_data(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("materials/plaster/plaster_int_14.360.vtf",vtfx_texture())
        raw=buffer.getvalue()
        with io.BytesIO(raw) as stream:
            with self.assertRaisesRegex(XboxZipError,"Compressed ZIP member"):
                inspect_archive(stream,len(raw),
                                "materials/plaster/plaster_int_14.360.vtf")

    def test_reject_declared_huge_texture(self):
        content=example_archive()
        with io.BytesIO(content) as stream:
            report=scan_directory(stream,len(content))
            entry=dict(report["entries"][0])
            entry["compressed_size"]=20*1024*1024
            entry["uncompressed_size"]=20*1024*1024
            with self.assertRaisesRegex(XboxZipError,"safety limit"):
                validate_texture(stream,len(content),report["directory_offset"],entry)


if __name__=="__main__":
    unittest.main()
