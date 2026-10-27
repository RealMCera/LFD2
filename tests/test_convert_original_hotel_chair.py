"""Synthetic Source 49 MDL / VVD4 / Xbox VTX7 triangle reconstruction tests."""
import struct
import unittest
from tools.bsp_to_browser_mesh import BspError
from tools.convert_original_hotel_chair import (
    decode_vvd,studio_meshes,vtx_triangles,convert_original_model
)

CHECKSUM=0xf3737e00


def original_tri_test_data():
    md=bytearray(4096)
    md[:4]=b"IDST"
    struct.pack_into(">II",md,4,49,CHECKSUM)
    struct.pack_into(">I",md,76,len(md))
    struct.pack_into(">II",md,204,1,1024)
    struct.pack_into(">II",md,232,1,400)
    struct.pack_into(">4I",md,400,0,1,1,16)
    # Bodypart starts at 400; model at 416.
    md[416:428]=b"chair_model\0"
    struct.pack_into(">2I",md,416+72,1,148)
    struct.pack_into(">2I",md,416+80,3,0)
    # mesh at 416+148 = 564: one material and 3 original vertices.
    struct.pack_into(">4i",md,564,0,-148,3,0)

    vv=bytearray(64+3*48)
    vv[:4]=b"IDSV"
    struct.pack_into(">3I",vv,4,4,CHECKSUM,1)
    struct.pack_into(">I",vv,16,3)
    struct.pack_into(">4I",vv,48,0,0,64,0)
    points=[(0.,0.,0.),(32.,0.,0.),(0.,32.,0.)]
    uvs=[(0.,0.),(1.,0.),(0.,1.)]
    for k,(pos,uv) in enumerate(zip(points,uvs)):
        at=64+k*48
        struct.pack_into(">3f",vv,at+16,*pos)
        struct.pack_into(">3f",vv,at+28,0,0,1)
        struct.pack_into(">2f",vv,at+40,*uv)

    tx=bytearray(158)
    struct.pack_into(">I",tx,0,7)
    struct.pack_into(">I",tx,16,CHECKSUM)
    struct.pack_into(">I",tx,20,1)
    struct.pack_into(">II",tx,28,1,36)
    struct.pack_into(">II",tx,36,1,8)  # bodypart
    struct.pack_into(">II",tx,44,1,8)  # model
    struct.pack_into(">IIf",tx,52,1,12,0.)  # LOD
    struct.pack_into(">II",tx,64,1,9)  # mesh header
    struct.pack_into(">6I",tx,73,3,25,3,52,1,58) # stripgroup
    for vi in range(3):
        struct.pack_into(">H",tx,73+25+9*vi+4,vi)
    struct.pack_into(">3H",tx,73+52,0,1,2)
    struct.pack_into(">4I",tx,73+58,3,0,3,0)
    tx[73+58+18]=1  # TRI LIST
    return bytes(md),bytes(vv),bytes(tx)


class OriginalChairTrianglesTests(unittest.TestCase):
    def test_authentic_studio_offset_tree_yields_one_real_triangle(self):
        mdl,vvd,vtx=original_tri_test_data()
        out=convert_original_model(mdl,vvd,vtx)
        self.assertEqual(out["triangle_count"],1)
        self.assertEqual(out["vertex_count"],3)
        self.assertEqual(out["indices"],[0,1,2])
        self.assertEqual(out["vertices"],[0.,0.,0.,32.,0.,0.,0.,32.,0.])
        self.assertEqual(out["uvs"],[0.,0.,1.,0.,0.,1.])
        self.assertEqual(out["triangle_material_ids"],[0])
        self.assertEqual(out["checksum"],"f3737e00")

    def test_checksum_mismatch_fails_before_reconstruction(self):
        mdl,vvd,vtx=original_tri_test_data()
        bad=bytearray(vvd)
        struct.pack_into(">I",bad,8,0xf00dd00d)
        with self.assertRaisesRegex(BspError,"checksum mismatch"):
            convert_original_model(mdl,bytes(bad),vtx)

    def test_bad_stripgroup_index_is_rejected(self):
        mdl,vvd,vtx=original_tri_test_data()
        bad=bytearray(vtx)
        struct.pack_into(">H",bad,73+52+2,17)
        with self.assertRaisesRegex(BspError,"group vertex"):
            convert_original_model(mdl,vvd,bytes(bad))

    def test_invalid_mdl_mesh_backpointer_is_rejected(self):
        mdl,vvd,vtx=original_tri_test_data()
        bad=bytearray(mdl)
        struct.pack_into(">i",bad,568,0)
        with self.assertRaisesRegex(BspError,"mesh association"):
            convert_original_model(bytes(bad),vvd,vtx)

    def test_vvd_fixups_reorder_real_vertex_pool(self):
        mdl,vvd,vtx=original_tri_test_data()
        raw=bytearray(vvd)
        # VVD fixup records must cover all LOD0 vertex ranges in order.
        raw+=b"\0"*12
        struct.pack_into(">4I",raw,48,1,208,64,0)
        struct.pack_into(">3I",raw,208,0,0,3)
        pool=decode_vvd(bytes(raw),"f3737e00")
        self.assertEqual(len(pool),3)


if __name__=="__main__":
    unittest.main()
