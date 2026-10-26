"""Synthetic-only header tests. No proprietary images or map bytes."""
import io
import zipfile
import unittest

from tools.probe_xbox_texture_headers import (
    probe_stream, pick_image_entries, inspect_local_header
)
from tools.scan_xbox_zip_directory import scan_directory


def synthetic_zip() -> bytes:
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_STORED) as z:
        z.writestr("materials/plaster/plaster_int_14.360.vtf",b"VTFX"+b"\0"*40)
        z.writestr("materials/tile/tile_ceiling_01.360.vtf",b"VTF\0"+b"\0"*40)
        z.writestr("materials/debug/unrelated.vmt",b"synthetic")
    return stream.getvalue()


class TextureHeaderTests(unittest.TestCase):
    def test_match_and_peek_vtfx_without_extracting(self):
        data=synthetic_zip()
        report, records=probe_stream(io.BytesIO(data),len(data),
                                     {"plaster/plaster_int_14":120},1)
        self.assertEqual(len(records),1)
        r=records[0]
        self.assertEqual(r["status"],"local_header_found")
        self.assertTrue(r["local_filename_matches"])
        self.assertEqual(r["texture_magic"],"VTFX")
        self.assertEqual(r["central_method"],0)
        self.assertEqual(r["local_method"],0)
        self.assertEqual(r["candidate_magic_hex"][:11],"56 54 46 58")
        self.assertEqual(report["candidate_headers"],3)

    def test_standard_vtf_fallback(self):
        data=synthetic_zip()
        _,records=probe_stream(io.BytesIO(data),len(data),
                               {"tile/tile_ceiling_01":4},1)
        self.assertEqual(records[0]["texture_magic"],"VTF")

    def test_reject_invalid_local_offset(self):
        data=synthetic_zip()
        report=scan_directory(io.BytesIO(data),len(data))
        entry=dict(report["entries"][0])
        entry["local_offset"]=len(data)+500
        info=inspect_local_header(io.BytesIO(data),len(data),
                                  report["directory_offset"],entry)
        self.assertEqual(info["status"],"invalid_local_offset")

    def test_missing_local_header_refused(self):
        data=synthetic_zip()
        report=scan_directory(io.BytesIO(data),len(data))
        entry=dict(report["entries"][0])
        entry["local_offset"]=5
        info=inspect_local_header(io.BytesIO(data),len(data),
                                  report["directory_offset"],entry)
        self.assertEqual(info["status"],"missing_PK_local_header")

    def test_only_material_images_selected(self):
        data=synthetic_zip()
        report=scan_directory(io.BytesIO(data),len(data))
        images=pick_image_entries(report,{},10)
        self.assertEqual(len(images),2)
        self.assertTrue(all(item["name"].endswith(".360.vtf") for item in images))


if __name__=="__main__":
    unittest.main()
