"""Synthetic-only Source BSP UV and material ID tests, no L4D2 game data."""
import struct
import unittest

from tools.bsp_to_browser_mesh import convert, BspError
from tools.add_bsp_material_uvs import augment_mesh


def material_test_bsp():
    bsp=bytearray(1036)
    bsp[:4]=b"PSBV"
    struct.pack_into(">I",bsp,4,20)
    def add(index,raw):
        offset=len(bsp)
        bsp.extend(raw)
        struct.pack_into(">4I",bsp,8+index*16,offset,len(raw),0,0)
    verts=b"".join(struct.pack(">3f",*v)
                   for v in [(0,0,0),(64,0,0),(64,64,0),(0,64,0)])
    add(3,verts)
    add(12,b"".join(struct.pack(">2H",*edge)
                     for edge in [(0,1),(1,2),(2,3),(3,0)]))
    add(13,struct.pack(">4i",0,1,2,3))
    face=bytearray(56)
    struct.pack_into(">i",face,4,0)
    struct.pack_into(">h",face,8,4)
    struct.pack_into(">h",face,10,0)
    struct.pack_into(">h",face,12,-1)
    add(58,bytes(face))
    texdata=bytearray(32)
    struct.pack_into(">3i",texdata,12,0,64,64)
    add(2,texdata)
    texinfo=bytearray(72)
    struct.pack_into(">8f",texinfo,0,1,0,0,0,0,1,0,0)
    struct.pack_into(">2i",texinfo,64,0,0)
    add(6,texinfo)
    add(43,b"plaster/test_material\x00")
    add(44,struct.pack(">i",0))
    return bytes(bsp)


class MaterialUvTests(unittest.TestCase):
    def test_texcoords_match_true_bsp_face_triangulation(self):
        raw=material_test_bsp()
        base=convert(raw)
        base["camera_spawns"]=[{"position":[10,10,64],"kind":"info_player_start"}]
        output=augment_mesh(raw,base)
        self.assertEqual(output["triangle_count"],2)
        self.assertEqual(output["materials"],["plaster/test_material"])
        self.assertEqual(output["triangle_material_ids"],[0,0])
        self.assertEqual(output["corner_uvs"],
                         [0,0,1,0,1,1,0,0,1,1,0,1])
        self.assertEqual(output["camera_spawns"],base["camera_spawns"])
        self.assertNotIn("corner_uvs",base)
        self.assertEqual(output["uv_format"],"source-face-corners-1")

    def test_bad_original_mesh_must_not_be_enriched(self):
        raw=material_test_bsp()
        mesh=convert(raw)
        mesh["vertices"][0]=1234
        with self.assertRaisesRegex(BspError,"differs from original BSP"):
            augment_mesh(raw,mesh)

    def test_bad_material_index_fails_explicitly(self):
        raw=bytearray(material_test_bsp())
        face_offset=struct.unpack_from(">I",raw,8+58*16)[0]
        struct.pack_into(">h",raw,face_offset+10,100)
        with self.assertRaisesRegex(BspError,"No valid material"):
            augment_mesh(bytes(raw),convert(bytes(raw)))

    def test_reject_already_enriched_mesh(self):
        raw=material_test_bsp()
        output=augment_mesh(raw,convert(raw))
        with self.assertRaisesRegex(BspError,"already UV-enriched"):
            augment_mesh(raw,output)


if __name__=="__main__":
    unittest.main()
