"""Synthetic-only tests for all-pack Xbox model inventory and authentic v9 props."""
import io
import lzma
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from tools.bsp_to_browser_mesh import BspError
from tools.build_hotel_prop_manifest import (
    decode_v9_static_records,decode_static_from_bsp,normalize_archive_path,
    scan_model_archive_directories,build_inventory,diagnose_model_companion_naming
)
from test_inspect_hotel_elements import make_bsp


def make_static_data(records=2):
    names=[b"models/props/hotel/chair.mdl",b"models/props/hotel/door.mdl"]
    blob=bytearray()
    blob+=struct.pack(">I",len(names))
    for name in names:blob+=name.ljust(128,b"\0")
    blob+=struct.pack(">I",1)+struct.pack(">H",0)
    blob+=struct.pack(">I",records)
    for i in range(records):
        entry=bytearray(72)
        struct.pack_into(">3f",entry,0,200.5+i,100+i,2600+i)
        struct.pack_into(">3f",entry,12,0,90*i,0)
        struct.pack_into(">3H",entry,24,i%len(names),0,1)
        struct.pack_into(">i",entry,32,i)
        struct.pack_into(">3f",entry,44,200+i,100+i,2600+i)
        struct.pack_into(">f",entry,56,1.)
        entry[64:68]=b"\xff\xff\xff\xff"
        blob+=entry
    return bytes(blob)


def compressed_bsp(blob):
    bsp=bytearray(make_bsp())
    packed=lzma.compress(blob,format=lzma.FORMAT_RAW,
         filters=[{"id":lzma.FILTER_LZMA1,
                   "dict_size":65536,"lc":3,"lp":0,"pb":2}])
    wrapped=b"LZMA"+struct.pack(">II",len(blob),len(packed))
    wrapped+=b"\x5d"+struct.pack("<I",65536)+packed
    game=struct.pack(">I",1)+b"prps"+struct.pack(">HHII",1,9,20,len(blob))+wrapped
    off=len(bsp)
    bsp.extend(game)
    struct.pack_into(">4I",bsp,8+35*16,off,len(game),0,0)
    return bytes(bsp)


def make_zip(path,entries):
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_STORED) as archive:
        for name in entries:archive.writestr(name,b"synthetic data")


class HotelPropManifestTests(unittest.TestCase):
    def test_real_v9_72_byte_positions_angles_and_model_ids(self):
        info,rows=decode_v9_static_records(make_static_data(),">")
        self.assertEqual(info["prop_count"],2)
        self.assertEqual(info["prop_record_bytes_apparent"],72)
        self.assertEqual(rows[0]["model"],"models/props/hotel/chair.mdl")
        self.assertEqual(rows[1]["angles"],[0.,90.,0.])
        self.assertEqual(rows[0]["origin"],[200.5,100.,2600.])
        self.assertEqual(rows[0]["leaf_count"],1)

    def test_bad_model_index_fails_instead_of_guessing(self):
        data=bytearray(make_static_data())
        start=len(data)-144
        struct.pack_into(">H",data,start+24,500)
        with self.assertRaisesRegex(BspError,"Invalid static v9"):
            decode_v9_static_records(bytes(data),">")

    def test_wrong_stride_does_not_parse_as_valid_positions(self):
        with self.assertRaisesRegex(BspError,"exact 72-byte stride"):
            decode_v9_static_records(make_static_data()+b"\0",">")

    def test_full_compressed_xbox_bsp_static_coordinates(self):
        report,rows,notes=decode_static_from_bsp(
            compressed_bsp(make_static_data()))
        self.assertEqual(report["version"],9)
        self.assertEqual(report["record_stride"],72)
        self.assertEqual(report["count"],2)
        self.assertEqual(report["location"],"game_lump_relative")
        self.assertEqual(len(rows),2)

    def test_scan_model_parts_across_other_zip_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            make_zip(root/"left4dead2"/"zip0.360.zip",
                     ["materials/only.vmt"])
            make_zip(root/"left4dead2"/"zip1.360.zip",
                     ["models/props/hotel/chair.mdl",
                      "models/props/hotel/chair.vvd",
                      "models/props/hotel/chair.360.vtx",
                      "models/props/hotel/door.mdl"])
            sources,packs,problems=scan_model_archive_directories(root)
            self.assertEqual(problems,[])
            self.assertEqual(len(packs),3)
            record=build_inventory(compressed_bsp(make_static_data()),sources)
            self.assertEqual(record["static_count"],2)
            self.assertEqual(record["dynamic_count"],1)
            self.assertEqual(record["total"],3)
            self.assertTrue(any(x["mesh_ready"] for x in record["availability"]))
            self.assertIn("models/props/hotel/chair.360.vtx",sources)

    def test_embedded_map_pak_can_supply_a_local_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            make_zip(root/"left4dead2"/"zip0.360.zip",
                     ["materials/only.vmt"])
            pak=io.BytesIO()
            with zipfile.ZipFile(pak,"w",compression=zipfile.ZIP_STORED) as z:
                z.writestr("models/props/hotel/chair.mdl",b"IDST"+b"\0"*32)
            bsp=bytearray(compressed_bsp(make_static_data()))
            off=len(bsp)
            bsp+=pak.getvalue()
            struct.pack_into(">4I",bsp,8+40*16,off,len(pak.getvalue()),0,0)
            sources,packs,errors=scan_model_archive_directories(root,bytes(bsp))
            self.assertIn("models/props/hotel/chair.mdl",sources)
            self.assertIn("hotel_BSP_embedded_pak",packs)
            self.assertEqual(errors,[])

    def test_model_companion_diagnostic_reports_real_exact_suffixes(self):
        names={
            "models/props_furniture/hotel_chair.mdl":["left4dead2/zip0.360.zip"],
            "models/props_furniture/hotel_chair.vvd":["left4dead2/zip0.360.zip"],
            "models/props_furniture/hotel_chair.360.vtx":["left4dead2/zip0.360.zip"],
            "models/props_furniture/hotel_chair.phy":["left4dead2/zip0.360.zip"],
            "models/props_furniture/hotel_chair_red.mdl":["left4dead2/zip0.360.zip"],
        }
        diagnosis=diagnose_model_companion_naming(
            names,["models/props_furniture/hotel_chair.mdl"])
        report=diagnosis["examples"][0]
        self.assertEqual(report["suffixes"],
                         [".360.vtx",".phy",".vvd"])
        self.assertEqual(report["nearby"],
                         ["models/props_furniture/hotel_chair_red.mdl"])

    def test_canonical_suffixes_and_prefixes(self):
        self.assertEqual(normalize_archive_path(
            "LEFT4DEAD2/MODELS/props/HOTEL/CHAIR.360.MDL"),
            "models/props/hotel/chair.mdl")
        self.assertEqual(normalize_archive_path(
            "models/props/hotel/door.vtx"),
            "models/props/hotel/door.vtx")


if __name__=="__main__":
    unittest.main()
