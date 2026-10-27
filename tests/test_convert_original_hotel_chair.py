"""Synthetic Source 49 MDL / VVD4 / Xbox VTX7 triangle reconstruction tests."""
import struct
import lzma
import unittest
from tools.bsp_to_browser_mesh import BspError
from tools.convert_original_hotel_chair import (
    decode_vvd,studio_meshes,vtx_triangles,convert_original_model,describe_vvd_layout,expanded_vvd,expanded_vtx,diagnose_studio_hierarchy
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

    def test_read_only_vvd_header_diagnostic_for_valid_source_layout(self):
        _mdl,vvd,_vtx=original_tri_test_data()
        details=describe_vvd_layout(vvd)
        self.assertEqual(details["header_version"],4)
        self.assertEqual(details["byte_order"],"big")
        self.assertEqual(details["lod_vertex_counts"][0],3)
        self.assertEqual(details["vertex_data_start"],64)
        self.assertEqual(details["expected_vertex_end_48"],208)
        self.assertEqual(details["file_bytes"],208)
        self.assertEqual(details["hints"][-1],
                         "Bytes available per declared LOD0 vertex: 48.00")

    def test_vvd_invalid_vertex_bounds_shows_real_offsets(self):
        _mdl,vvd,_vtx=original_tri_test_data()
        wrong=bytearray(vvd)
        struct.pack_into(">I",wrong,16,99)
        diagnostic=describe_vvd_layout(wrong)
        self.assertEqual(diagnostic["lod_vertex_counts"][0],99)
        self.assertEqual(diagnostic["expected_vertex_end_48"],4816)
        self.assertEqual(diagnostic["file_bytes"],208)
        with self.assertRaisesRegex(BspError,
            "LOD0=99, vertex_start=64, expected_end=4816, file_bytes=208"):
            decode_vvd(bytes(wrong),"f3737e00")

    def test_vvd_embedded_lzma_signature_is_a_hint_not_a_guess(self):
        _mdl,vvd,_vtx=original_tri_test_data()
        modified=bytearray(vvd)
        modified[64:68]=b"LZMA"
        details=describe_vvd_layout(bytes(modified))
        self.assertTrue(any("LZMA signature" in hint
                            for hint in details["hints"]))

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

    def test_compressed_original_xbox_vtx_bodyparts_reconstruct_real_indices(self):
        mdl,vvd,vtx=original_tri_test_data()
        header=vtx[:36]
        uncompressed=vtx[36:]
        compressed=lzma.compress(uncompressed,format=lzma.FORMAT_RAW,
            filters=[{"id":lzma.FILTER_LZMA1,
                      "dict_size":65536,"lc":3,"lp":0,"pb":2}])
        member=(b"LZMA"+struct.pack("<II",len(uncompressed),len(compressed))
                +b"\x5d"+struct.pack("<I",65536)+compressed)
        xbox=header+member
        unpacked,info=expanded_vtx(xbox,"f3737e00")
        self.assertEqual(unpacked,vtx)
        self.assertEqual(info["compression"],"Valve LZMA")
        report=diagnose_studio_hierarchy(mdl,xbox)
        self.assertTrue(report["vtx_bodypart_lzma_wrapper"])
        self.assertEqual(report["vtx_model_counts"][0]["vtxnummodels"],1)
        actual=convert_original_model(mdl,vvd,xbox)
        self.assertEqual(actual["indices"],[0,1,2])
        self.assertEqual(actual["triangle_count"],1)

    def test_corrupt_xbox_vtx_lzma_size_fails_strictly(self):
        mdl,vvd,vtx=original_tri_test_data()
        raw=vtx[36:]
        compressed=lzma.compress(raw,format=lzma.FORMAT_RAW,
            filters=[{"id":lzma.FILTER_LZMA1,
                      "dict_size":65536,"lc":3,"lp":0,"pb":2}])
        corrupted=(b"LZMA"+struct.pack("<II",len(raw)+8,len(compressed))
                   +b"\x5d"+struct.pack("<I",65536)+compressed)
        with self.assertRaisesRegex(BspError,"Unable to decode Valve LZMA lump|unpacked size mismatch"):
            expanded_vtx(vtx[:36]+corrupted,"f3737e00")

    def test_uncompressed_vtx_hierarchy_diagnostic_reports_model_counts(self):
        mdl,vvd,vtx=original_tri_test_data()
        info=diagnose_studio_hierarchy(mdl,vtx)
        self.assertEqual(info["mdl_model_counts"][0]["mdlnummodels"],1)
        self.assertEqual(info["vtx_model_counts"][0]["vtxnummodels"],1)
        self.assertFalse(info["vtx_bodypart_lzma_wrapper"])
        unchanged,detail=expanded_vtx(vtx,"f3737e00")
        self.assertEqual(unchanged,vtx)
        self.assertEqual(detail["compression"],"none")

    def test_compressed_original_xbox_vvd_replaces_vertex_and_tangent_arrays(self):
        mdl,vvd,vtx=original_tri_test_data()
        # Source header uncompressed; Xbox 360 packs vertex + tangent pools
        # behind a Valve LZMA header beginning at vertexDataStart (byte 64).
        source=bytearray(vvd)
        source+=b"\x00"*(3*16)
        struct.pack_into(">I",source,60,64+3*48)
        raw_vertex_tangent=bytes(source[64:])
        compressed=lzma.compress(raw_vertex_tangent,format=lzma.FORMAT_RAW,
                                 filters=[{"id":lzma.FILTER_LZMA1,
                                           "dict_size":65536,"lc":3,"lp":0,"pb":2}])
        header=(b"LZMA"+struct.pack("<II",len(raw_vertex_tangent),len(compressed))
                +b"\x5d"+struct.pack("<I",65536))
        compressed_vvd=bytes(source[:64])+header+compressed
        report=describe_vvd_layout(compressed_vvd)
        self.assertTrue(
            any("Valve LZMA signature found at VVD vertex offset" in hint
                for hint in report["hints"]),
            "VVD diagnostic must recognize the compressed Xbox vertex block",
        )
        expanded,meta=expanded_vvd(compressed_vvd)
        self.assertEqual(expanded,bytes(source))
        self.assertEqual(meta["compression"],"Valve LZMA")
        self.assertEqual(meta["decoded_vertex_bytes"],144)
        self.assertEqual(meta["decoded_tangent_bytes"],48)
        self.assertEqual(decode_vvd(compressed_vvd,"f3737e00"),
                         decode_vvd(bytes(source),"f3737e00"))
        parsed=convert_original_model(mdl,compressed_vvd,vtx)
        self.assertEqual(parsed["triangle_count"],1)

    def test_compressed_xbox_vvd_rejects_wrong_unpacked_size(self):
        _mdl,vvd,_vtx=original_tri_test_data()
        source=bytearray(vvd)+b"\x00"*(3*16)
        struct.pack_into(">I",source,60,64+3*48)
        raw=bytes(source[64:])
        compressed=lzma.compress(raw,format=lzma.FORMAT_RAW,
                                 filters=[{"id":lzma.FILTER_LZMA1,
                                           "dict_size":65536,"lc":3,"lp":0,"pb":2}])
        bad=(b"LZMA"+struct.pack("<II",len(raw)-8,len(compressed))
             +b"\x5d"+struct.pack("<I",65536)+compressed)
        with self.assertRaisesRegex(BspError,"declared sizes disagree"):
            expanded_vvd(bytes(source[:64])+bad)

    def test_uncompressed_vvd_data_remains_untouched(self):
        _mdl,vvd,_vtx=original_tri_test_data()
        data,meta=expanded_vvd(vvd)
        self.assertEqual(data,vvd)
        self.assertEqual(meta["compression"],"none")

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
