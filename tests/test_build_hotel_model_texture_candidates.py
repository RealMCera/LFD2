"""Synthetic-only one-pass provisional original Xbox VMT/VTFX candidate tests.

No original copyrighted game materials, meshes or textures embedded.
"""
import unittest

from tools.build_hotel_model_texture_candidates import (
    PREFIX,plan_provisional
)


def pair(kind,name,where="zip1"):
    return (where,{"name":"materials/"+name+(
        ".vmt" if kind=="vmt" else ".360.vtf")})


def mdl(*candidates):
    return {"model":"models/props_furniture/hotel_chair.mdl",
            "original_placements":47,
            "texture_candidates":[list(group) for group in candidates]}


class StudioExactNameTextureCandidateTests(unittest.TestCase):
    def test_binary_vmt_and_identical_vtfx_yields_explicit_provisional_binding(self):
        name="models/furniture/chair"
        tables={
            "vmt":{name:[pair("vmt",name)]},
            "vtfx":{name:[pair("vtfx",name)]}
        }
        report=plan_provisional([mdl([name])],tables,lambda *_:PREFIX+b"\x00"*20)
        self.assertEqual(report["stats"]["candidate_slots"],1)
        self.assertEqual(report["stats"]["unique_image_names"],1)
        row=report["matches"][0]
        self.assertEqual(row["slot"],0)
        self.assertEqual(row["texture"],name)
        self.assertEqual(row["mapping"],
                         "PROVISIONAL_EXACT_FILENAME_NOT_VMT_VERIFIED")

    def test_duplicate_vtfx_filenames_get_no_unverified_mapping(self):
        name="models/furniture/chair"
        tables={"vmt":{name:[pair("vmt",name)]},
                "vtfx":{name:[pair("vtfx",name),pair("vtfx",name)]}}
        result=plan_provisional([mdl([name])],tables,lambda *_:PREFIX+b"\0"*10)
        self.assertEqual(result["stats"]["candidate_slots"],0)
        self.assertEqual(result["stats"]["unresolved_slots"],1)

    def test_bin_signature_must_be_actual_observed_original_family(self):
        name="models/furniture/chair"
        tables={"vmt":{name:[pair("vmt",name)]},
                "vtfx":{name:[pair("vtfx",name)]}}
        result=plan_provisional([mdl([name])],tables,
                                lambda *_:b"VERTEXLITGENERIC {}")
        self.assertEqual(result["stats"]["candidate_slots"],0)
        self.assertEqual(result["unresolved"][0]["reason"],
                         "vmt_not_observed_binary_family")

    def test_no_nearest_name_guess_and_search_path_fallback(self):
        n="models/furniture/chair",fallback="chair"
        tables={"vmt":{"chair":[pair("vmt","chair")]},
                "vtfx":{"chair":[pair("vtfx","chair")],
                        "models/furniture/chairs":[pair("vtfx","models/furniture/chairs")]}}
        result=plan_provisional([mdl([n[0],fallback])],tables,
                                lambda *_:PREFIX+b"\0"*8)
        self.assertEqual(result["stats"]["candidate_slots"],1)
        self.assertEqual(result["matches"][0]["texture"],fallback)

    def test_unresolved_does_not_artificially_invent_textures(self):
        result=plan_provisional([mdl(["models/unknown/notfound"],
                                     ["models/unknown/none"])],
                                {"vmt":{},"vtfx":{}},lambda *_:b"")
        self.assertEqual(result["stats"]["candidate_slots"],0)
        self.assertEqual(result["stats"]["unresolved_slots"],2)
        self.assertEqual(result["stats"]["unique_image_names"],0)

if __name__=="__main__":
    unittest.main()
