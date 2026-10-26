"""Synthetic-only tests for selected local Xbox hotel texture batch conversion."""
from collections import Counter
import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools.prepare_hotel_textures import (
    choose_materials,asset_paths,process_one,PRIVATE_ROOT
)
from tools.scan_xbox_zip_directory import scan_directory
from tools.extract_single_vtfx import XboxZipError


def vtfx():
    header=bytearray(0x44+32)
    header[:4]=b"VTFX"
    struct.pack_into(">4I",header,4,0x360,8,0x44,0)
    struct.pack_into(">5H",header,0x14,16,16,1,1,0)
    struct.pack_into(">BB",header,0x1e,0,1)
    struct.pack_into(">I",header,0x30,13)
    return bytes(header)


def pack():
    data=io.BytesIO()
    with zipfile.ZipFile(data,"w",compression=zipfile.ZIP_STORED) as z:
        z.writestr("materials/plaster/plaster_ext_20.360.vtf",vtfx())
        z.writestr("materials/tile/tile_ceiling_01.360.vtf",vtfx())
        z.writestr("materials/tools/toolstrigger.360.vtf",vtfx())
        z.writestr("materials/plaster/plaster_ext_20.vmt",b"synthetic")
    return data.getvalue()


class HotelTextureBatchTests(unittest.TestCase):
    def setUp(self):
        PRIVATE_ROOT.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=PRIVATE_ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_prioritize_geometry_and_skip_tools(self):
        raw=pack()
        report=scan_directory(io.BytesIO(raw),len(raw))
        source=Counter({"TOOLS/TOOLSTRIGGER":9000,
                        "PLASTER/PLASTER_EXT_20":80,
                        "TILE/TILE_CEILING_01":20})
        choices=choose_materials(source,report["entries"],8)
        self.assertEqual([row[0] for row in choices],
                         ["plaster/plaster_ext_20","tile/tile_ceiling_01"])

    def test_refuse_path_traversal(self):
        for name in ("../evil","plaster/../../evil","plaster/a.b","plaster/a b"):
            with self.assertRaises(ValueError):
                asset_paths(name,self.root)

    def test_local_paths_are_private(self):
        vtfx_file,work,png=asset_paths("plaster/plaster_ext_20",self.root)
        self.assertTrue(vtfx_file.is_relative_to(PRIVATE_ROOT))
        self.assertTrue(png.is_relative_to(PRIVATE_ROOT))
        self.assertEqual(png.name,"plaster_ext_20.360_resource_0.png")

    def test_process_one_private_file_only(self):
        data=pack()
        with io.BytesIO(data) as stream:
            report=scan_directory(stream,len(data))
            entry=next(x for x in report["entries"]
                       if x["name"]=="materials/plaster/plaster_ext_20.360.vtf")
            def fake_convert(source,dest,exe):
                dest.mkdir(parents=True)
                image=dest/"plaster_ext_20.360_resource_0.png"
                image.write_bytes(b"synthetic PNG output for mocked converter")
                return [(image,16,16)]
            with patch("tools.prepare_hotel_textures.run_converter",side_effect=fake_convert):
                state,png=process_one(stream,len(data),report["directory_offset"],
                                      entry,"plaster/plaster_ext_20",self.root,
                                      self.root/"fake-converter.exe")
        self.assertEqual(state,"converted")
        self.assertTrue(png.is_file())
        self.assertEqual((self.root/"vtfx/plaster/plaster_ext_20.360.vtf").read_bytes(),vtfx())

    def test_refuse_output_overwrite(self):
        data=pack()
        with io.BytesIO(data) as stream:
            report=scan_directory(stream,len(data))
            entry=next(x for x in report["entries"]
                       if x["name"]=="materials/plaster/plaster_ext_20.360.vtf")
            orig,work,png=asset_paths("plaster/plaster_ext_20",self.root)
            png.parent.mkdir(parents=True)
            png.write_bytes(b"existing private result")
            state,path=process_one(stream,len(data),report["directory_offset"],
                                   entry,"plaster/plaster_ext_20",self.root,
                                   self.root/"fake-converter.exe")
            self.assertEqual(state,"existing_png")
            self.assertEqual(png.read_bytes(),b"existing private result")


if __name__=="__main__":
    unittest.main()
