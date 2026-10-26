"""Synthetic tests for the one-pass private hotel VMT-to-texture manifest.

All bytes are generated in memory; never use or embed commercial L4D2 assets.
"""
from collections import Counter
import io
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from tools.finish_hotel_materials import (
    normalize_material,extract_basetexture,read_local_member,map_sources,
    pick_source,get_material_plan,find_cached_png,PRIVATE,
)
from tools.scan_xbox_zip_directory import scan_directory
from tools.inspect_xbox_zip import XboxZipError


def archive(items):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_STORED) as z:
        for key,value in items.items():
            z.writestr(key,value)
    blob=stream.getvalue()
    return blob,scan_directory(io.BytesIO(blob),len(blob))


class CompleteHotelTextureTests(unittest.TestCase):
    def test_path_normalization_and_dotted_map_hdr(self):
        self.assertEqual(normalize_material(
            r"MATERIALS\MAPS\C1M1_HOTEL\C-200_5022_1257.HDR.360.VTF"),
            "maps/c1m1_hotel/c-200_5022_1257.hdr")
        for bad in ("../outside","plaster/../../evil","/../../etc",""):
            with self.assertRaises(ValueError):
                normalize_material(bad)

    def test_vmt_basetexture_parses_and_ignores_comments(self):
        data=(b'LightmappedGeneric\n{\n'
              b' // "$basetexture" "WRONG/THING"\n'
              b' "$baseTexture" "Concrete/Concrete_Floor_10"\n'
              b'}\n')
        self.assertEqual(extract_basetexture(data),
                         "concrete/concrete_floor_10")
        self.assertIsNone(extract_basetexture(
            b'LightmappedGeneric { "$surfaceprop" "concrete" }'))
        self.assertIsNone(extract_basetexture(
            b'LightmappedGeneric { "$basetexture" "../SECRET" }'))

    def test_read_stored_vmt_with_real_zip_headers(self):
        data=b'LightmappedGeneric { "$basetexture" "tile/ceiling" }'
        raw,report=archive({"materials/hotel/sample.vmt":data})
        entry=report["entries"][0]
        self.assertEqual(read_local_member(io.BytesIO(raw),len(raw),
                         report["directory_offset"],entry),data)
        bad=dict(entry);bad["method"]=99
        with self.assertRaisesRegex(XboxZipError,"Unsupported"):
            read_local_member(io.BytesIO(raw),len(raw),
                              report["directory_offset"],bad)

    def test_map_priority_and_full_material_plan(self):
        zip_data,zip_report=archive({
            "materials/plaster/wall.vmt":
                b'LightmappedGeneric { "$basetexture" "plaster/wall_art" }',
            "materials/plaster/wall_art.360.vtf":b"dummy",
            "materials/maps/hotel/custom.vmt":
                b'LightmappedGeneric { "$basetexture" "plaster/wall_art" }',
        })
        pak_data,pak_report=archive({
            "materials/maps/hotel/custom.vmt":
                b'LightmappedGeneric { "$basetexture" "maps/hotel/custom_art" }',
            "materials/maps/hotel/custom_art.360.vtf":b"dummy",
        })
        sources=map_sources(zip_report,pak_report)
        self.assertEqual(pick_source(sources,"vmt","maps/hotel/custom")[0],"map")
        streams={"zip1":io.BytesIO(zip_data),"map":io.BytesIO(pak_data)}
        reports={"zip1":zip_report,"map":pak_report}
        sizes={"zip1":len(zip_data),"map":len(pak_data)}
        def read(label,entry):
            return read_local_member(streams[label],sizes[label],
                reports[label]["directory_offset"],entry)
        mesh={"uv_format":"source-face-corners-1",
              "materials":["plaster/wall","maps/hotel/custom",
                           "tools/toolstrigger","tile/not_present"],
              "triangle_material_ids":[0,0,1,1,1,2,3]}
        plan,missing=get_material_plan(mesh,sources,read)
        self.assertEqual({p["material"]:p["texture"] for p in plan},
            {"plaster/wall":"plaster/wall_art",
             "maps/hotel/custom":"maps/hotel/custom_art"})
        self.assertEqual({p["material"]:p["source"] for p in plan},
            {"plaster/wall":"zip1","maps/hotel/custom":"map"})
        self.assertEqual(len(missing),2)
        self.assertEqual(sum(x["triangles"] for x in plan),5)

    def test_flat_png_cache_requires_matching_dimensions(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE) as dirname:
            output=Path(dirname)
            png=output/"textures"/"plaster"/"wall.png"
            png.parent.mkdir(parents=True,exist_ok=True)
            raw=(b"\x89PNG\r\n\x1a\n"+struct.pack(">I",13)+b"IHDR"+
                 struct.pack(">II",128,64)+b"\x08\x02\x00\x00\x00")
            png.write_bytes(raw)
            self.assertEqual(find_cached_png("plaster/wall",128,64,output),png)
            self.assertIsNone(find_cached_png("plaster/wall",64,64,output))

if __name__=="__main__":
    unittest.main()
