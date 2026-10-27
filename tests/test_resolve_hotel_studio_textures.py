"""Synthetic-only tests for automatic hotel studio->VMT->VTFX matches."""
import unittest

from tools.resolve_hotel_studio_textures import resolve_slots,safe_catalog


def row(model="models/props_windows/hotel_window.mdl", candidates=None):
    return {"model":model,"original_placements":45,
            "texture_candidates":candidates or [
                ["models/windows/glass","glass"],
                ["models/windows/frame","frame"]
            ]}


def source(kind,path,where="zip1"):
    suffix=".vmt" if kind=="vmt" else ".360.vtf"
    return (where,{"name":"materials/"+path+suffix})


class StudioTextureMatchTests(unittest.TestCase):
    def test_exact_vmt_base_image_and_multislot_auto_resolution(self):
        tables={"vmt":{
            "models/windows/glass":[source("vmt","models/windows/glass")],
            "models/windows/frame":[source("vmt","models/windows/frame")]
            },
            "vtfx":{
                "models/windows/glass_base":[source("vtfx","models/windows/glass_base")],
                "models/windows/frame_diffuse":[source("vtfx","models/windows/frame_diffuse")]
            }}
        bodies={
          "materials/models/windows/glass.vmt":b'"VertexLitGeneric" { "$basetexture" "models/windows/glass_base" }',
          "materials/models/windows/frame.vmt":b'"VertexLitGeneric" { "$basetexture" "models/windows/frame_diffuse" }'
        }
        result=resolve_slots([row()],tables,lambda label,entry:bodies[entry["name"]])
        self.assertEqual(result["stats"]["matched_slots"],2)
        self.assertEqual(result["stats"]["unmatched_slots"],0)
        self.assertEqual(result["stats"]["unique_original_images"],2)
        self.assertEqual(result["stats"]["weighted_matched_slots"],90)
        self.assertEqual(result["matched"][0]["material"],"models/windows/glass")
        self.assertEqual(result["matched"][0]["texture"],"models/windows/glass_base")
        self.assertEqual(result["matched"][0]["slot"],0)
        self.assertEqual(result["matched"][1]["slot"],1)

    def test_ambiguous_original_image_does_not_guess(self):
        tables={"vmt":{"models/windows/glass":[source("vmt","models/windows/glass")]},
                "vtfx":{"models/windows/glass_base":[
                    source("vtfx","models/windows/glass_base"),
                    source("vtfx","models/windows/glass_base")]}}
        result=resolve_slots([row(candidates=[["models/windows/glass"]])],tables,
                             lambda *args:b'"$basetexture" "models/windows/glass_base"')
        self.assertEqual(result["stats"]["matched_slots"],0)
        self.assertEqual(result["unresolved"][0]["reason"],"missing_or_ambiguous_vtfx")

    def test_missing_basetexture_cannot_be_filled_with_guessed_filenames(self):
        tables={"vmt":{"models/windows/glass":[source("vmt","models/windows/glass")]},
                "vtfx":{"models/windows/glass":[source("vtfx","models/windows/glass")]}}
        result=resolve_slots([row(candidates=[["models/windows/glass"]])],tables,
                             lambda *args:b'"VertexLitGeneric" {}')
        self.assertEqual(result["stats"]["matched_slots"],0)
        self.assertEqual(result["unresolved"][0]["reason"],"vmt_without_basetexture")

    def test_prefers_exact_available_material_candidate_not_popularity(self):
        tables={"vmt":{"glass":[source("vmt","glass")]},
                "vtfx":{"real_image":[source("vtfx","real_image")]}}
        result=resolve_slots([row(candidates=[["models/windows/glass","glass"]])],
                             tables,lambda *args:b'"$basetexture" "real_image"')
        self.assertEqual(result["stats"]["matched_slots"],1)
        self.assertEqual(result["matched"][0]["material"],"glass")

    def test_existing_catalog_must_be_bounded_and_safe(self):
        catalog={"format":"lfd2-original-studio-material-reference-catalog-v1",
                 "models":[row()]}
        self.assertEqual(safe_catalog(catalog),catalog["models"])
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            safe_catalog({**catalog,"models":[row(candidates=[["../../oops"]])]})
        with self.assertRaisesRegex(ValueError,"Expected original"):
            safe_catalog({"format":"invalid","models":[row()]})


if __name__=="__main__":
    unittest.main()
