"""Synthetic-only tests for scanning Xbox Source material directories."""
from collections import Counter
import io
import struct
import unittest
import zipfile

from tools.scan_source_asset_packs import (
    material_key, match_material_names, scan_local_pak, summarize_report,
)
from tools.scan_xbox_zip_directory import scan_directory


def zip_bytes():
    b=io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("materials/plaster/plaster_int_14.vtf.360",b"synthetic")
        z.writestr("materials/tile/tile_ceiling_01.vmt",b"synthetic")
        z.writestr("models/chair.mdl",b"synthetic")
    return b.getvalue()


class PackScanTests(unittest.TestCase):
    def test_console_suffix_and_material_path(self):
        self.assertEqual(
            material_key(r"Materials\Plaster\PLASTER_INT_14.vtf.360"),
            "plaster/plaster_int_14")
        self.assertEqual(
            material_key("materials/tile/tile_ceiling_01.vtfx"),
            "tile/tile_ceiling_01")
        self.assertEqual(
            material_key("materials/metal/metalhull003a.360"),
            "metal/metalhull003a")
        self.assertIsNone(material_key("models/metal/metalhull003a.360"))
        self.assertIsNone(material_key("materials/tile/tile_ceiling_01.dat"))

    def test_candidate_material_and_face_counts(self):
        names=["materials/plaster/plaster_int_14.vtf.360",
               "materials/tile/tile_ceiling_01.vmt",
               "models/chair.mdl",
               "materials/plaster/plaster_int_14.vmt"]
        materials=Counter({"PLASTER/PLASTER_INT_14": 5,
                           "TILE/TILE_CEILING_01":3,"TOOLS/SKYBOX":7})
        r=match_material_names(names, materials)
        self.assertEqual(r["matched_materials"],2)
        self.assertEqual(r["matched_faces"],8)
        self.assertEqual(r["material_files"],3)
        self.assertEqual(len(r["matches"]["plaster/plaster_int_14"]),2)

    def test_scan_synthetic_zip(self):
        pak=zip_bytes()
        report=scan_directory(io.BytesIO(pak),len(pak))
        r=match_material_names(report["filenames"],
                               Counter({"plaster/plaster_int_14":12}))
        self.assertEqual(report["candidate_headers"],3)
        self.assertEqual(r["matched_materials"],1)
        self.assertEqual(r["material_extensions"][".360"],1)

    def test_embedded_bsp_pak_directory(self):
        pack=zip_bytes()
        bsp=bytearray(1036)
        bsp[:4]=b"PSBV"
        struct.pack_into(">I",bsp,4,20)
        for index,raw in ((3,b"\x00"*12),(12,b"\x00"*4),
                          (13,b"\x00"*4),(40,pack)):
            offset=len(bsp)
            bsp.extend(raw)
            struct.pack_into(">4I",bsp,8+index*16,offset,len(raw),0,0)
        r=scan_local_pak(bytes(bsp))
        self.assertEqual(r["candidate_headers"],3)


if __name__ == "__main__":
    unittest.main()
