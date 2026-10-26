"""No commercial data: synthetic Xbox Source material metadata tests."""
import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.inspect_map_materials import inspect_materials, inspect_zip_directory
from tools.bsp_to_browser_mesh import BspError


def synthetic_material_bsp(endian=">", magic=b"PSBV", texture_name=b"hotel/wall_panel"):
    header=bytearray(1036)
    header[:4]=magic
    struct.pack_into(endian+"I",header,4,20)
    payloads={}
    def add(index,raw):
        payloads[index]=(len(header),len(raw))
        header.extend(raw)
    texdata=bytearray(32)
    struct.pack_into(endian+"i",texdata,12,0)
    add(2,texdata)
    texinfo=bytearray(72)
    struct.pack_into(endian+"ii",texinfo,64,0,0)
    add(6,texinfo)
    add(43,texture_name+b"\0")
    add(44,struct.pack(endian+"i",0))
    faces=bytearray(56)
    struct.pack_into(endian+"h",faces,10,0)
    add(58,faces)
    for ix,(offset,size) in payloads.items():
        struct.pack_into(endian+"4I",header,8+ix*16,offset,size,0,0)
    # directory validator requires meaningful geometry entries
    for ix,size in ((3,12),(12,4),(13,4)):
        offset=len(header)
        header.extend(b"\0"*size)
        struct.pack_into(endian+"4I",header,8+ix*16,offset,size,0,0)
    return bytes(header)


class MaterialTests(unittest.TestCase):
    def test_xbox_big_endian(self):
        result=inspect_materials(synthetic_material_bsp())
        self.assertEqual(result["face_lump"],58)
        self.assertEqual(result["materials"]["hotel/wall_panel"],1)
        self.assertEqual(result["unique_materials"],1)
        self.assertEqual(result["unmapped_faces"],0)

    def test_little_endian(self):
        result=inspect_materials(synthetic_material_bsp("<",b"VBSP",b"brick/brickfloor"))
        self.assertEqual(result["materials"]["brick/brickfloor"],1)

    def test_invalid_texdata_reference(self):
        data=bytearray(synthetic_material_bsp())
        # Texdata is the first synthetic section at offset 1036.
        struct.pack_into(">i",data,1036+12,42)
        with self.assertRaisesRegex(BspError,"Invalid texdata name"):
            inspect_materials(bytes(data))

    def test_valid_zip_metadata_only(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"asset.zip"
            with zipfile.ZipFile(path,"w") as archive:
                archive.writestr("materials/hotel/wall.vmt",'placeholder')
                archive.writestr("materials/hotel/wall.vtfx",b"VTFX")
                archive.writestr("sounds/fake.wav",b"nothing")
            result=inspect_zip_directory(path)
            self.assertEqual(result["files"],3)
            self.assertEqual(result["suffixes"][".vmt"],1)
            self.assertEqual(result["suffixes"][".vtfx"],1)
            self.assertEqual(len(result["sample_assets"]),2)


if __name__=="__main__":
    unittest.main()
