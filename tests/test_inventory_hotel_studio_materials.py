"""Synthetic-only Source MDL v49 material-table and skin-family tests."""
import struct
import unittest

from tools.bsp_to_browser_mesh import BspError
from tools.inventory_hotel_studio_materials import inspect_studio_materials

MODEL="models/props_furniture/hotel_chair.mdl"


def sample_studio_materials(*,order=">",bad_name=False,skin=1):
    mdl=bytearray(2048)
    mdl[:4]=b"IDST"
    struct.pack_into(order+"II",mdl,4,49,0xF3737E00)
    struct.pack_into(order+"I",mdl,76,len(mdl))
    # Header texture table at 512, two 64-byte mstudiotexture_t rows.
    struct.pack_into(order+"II",mdl,204,2,512)
    struct.pack_into(order+"II",mdl,212,2,400) # CDTEXTURE string offsets
    struct.pack_into(order+"III",mdl,220,2,2,460) # skins: two refs x two families
    struct.pack_into(order+"2i",mdl,400,800,832)
    mdl[800:815]=b"models/props/\x00\x00"
    mdl[832]=0 # empty material fallback path
    mdl[512:516]=struct.pack(order+"i",640-512)
    mdl[576:580]=struct.pack(order+"i",680-576)
    mdl[640:646]=b"chair\x00"
    if bad_name:mdl[640:646]=b"../x!\x00"
    mdl[680:688]=b"cushion\x00"
    struct.pack_into(order+"4H",mdl,460,0,1,1,0 if skin else 2)
    return bytes(mdl)


class StudioMaterialInventoryTests(unittest.TestCase):
    def test_big_endian_texture_names_root_search_paths_and_skin_matrix(self):
        result=inspect_studio_materials(sample_studio_materials(),MODEL)
        self.assertEqual(result["checksum"],"f3737e00")
        self.assertEqual(result["texture_names"],["chair","cushion"])
        self.assertEqual(result["search_paths"],["models/props",""])
        self.assertEqual(result["texture_candidates"][0],
                         ["models/props/chair","chair"])
        self.assertEqual(result["texture_candidates"][1],
                         ["models/props/cushion","cushion"])
        self.assertEqual(result["skin_families"],[[0,1],[1,0]])

    def test_little_endian_source_table_works_too(self):
        result=inspect_studio_materials(sample_studio_materials(order="<"),MODEL)
        self.assertEqual(result["texture_names"],["chair","cushion"])
        self.assertEqual(result["skin_families"],[[0,1],[1,0]])

    def test_reject_original_studio_skin_out_of_bounds(self):
        with self.assertRaisesRegex(BspError,"missing texture"):
            inspect_studio_materials(sample_studio_materials(skin=0),MODEL)

    def test_reject_name_path_traversal_without_exporting_original_data(self):
        with self.assertRaisesRegex(BspError,"Unsafe original studio material name"):
            inspect_studio_materials(sample_studio_materials(bad_name=True),MODEL)

    def test_reject_invalid_cdtexture_offset(self):
        corrupted=bytearray(sample_studio_materials())
        struct.pack_into(">i",corrupted,400,9000000)
        with self.assertRaisesRegex(BspError,"material string offset"):
            inspect_studio_materials(bytes(corrupted),MODEL)

    def test_reject_excessive_texture_count(self):
        corrupted=bytearray(sample_studio_materials())
        struct.pack_into(">I",corrupted,204,5000)
        with self.assertRaisesRegex(BspError,"studio textures"):
            inspect_studio_materials(bytes(corrupted),MODEL)


if __name__=="__main__":
    unittest.main()
