"""Only synthetic metadata; no original studio files or geometry."""
import unittest

from tools.report_hotel_scene_bundle import reason_category,summarize_scene

CHAIR="models/props_furniture/hotel_chair.mdl"
WINDOW="models/props_windows/hotel_window.mdl"
DOOR="models/props_windows/hotel_door_sliding.mdl"

class BatchSummaryTests(unittest.TestCase):
    def sample(self):
        return {
            "format":"lfd2-original-hotel-studio-bundle-v1",
            "source_map":"c1m1_hotel.360.bsp",
            "models":[{"model":CHAIR}],
            "placements":[{"model":CHAIR,"origin":[0.,0.,0.],"angles":[0.,0.,0.]}],
            "skipped":[
                {"model":WINDOW,"error":"VTX/MDL model counts disagree"},
                {"model":DOOR,"error":"VTX/MDL mesh counts disagree"},
            ],
            "stats":{"attempted_models":3,"decoded_models":1,"skipped_models":2,
                     "original_placements_included":1,
                     "original_placements_total":9}
        }
    def test_category_matching_never_needs_binary_game_data(self):
        self.assertEqual(reason_category("VTX origMeshVertID outside MDL mesh"),
                         "VTX index/strip layout")
        self.assertEqual(reason_category("VTX group strip invalid Source layout"),
                         "VTX index/strip layout")
        self.assertEqual(reason_category("MDL mesh association/vertex interval invalid"),
                         "MDL vertex indexing")
        self.assertEqual(reason_category("vvd fixups out of bounds"),
                         "VVD vertex layout/fixups")
    def test_priority_uses_original_placement_impact_not_model_count(self):
        scene=self.sample()
        placements=[{"model":WINDOW} for _ in range(7)]+[{"model":DOOR},
                   {"model":CHAIR}]
        result=summarize_scene(scene,original_placements=placements)
        self.assertEqual(result["stats"]["decoded_models"],1)
        self.assertEqual(result["by_error_type"][0]["affected_placements"],7)
        self.assertEqual(result["by_error_type"][0]["category"],
                         "Bodypart/model hierarchy")
        self.assertEqual(result["top_skipped_placements"][0]["model"],WINDOW)
        self.assertEqual(result["top_skipped_placements"][0]["placements"],7)
    def test_reject_wrong_scene_and_invalid_top(self):
        with self.assertRaisesRegex(ValueError,"Not an original"):
            summarize_scene({"format":"not-a-hotel"})
        with self.assertRaisesRegex(ValueError,"top-N"):
            summarize_scene(self.sample(),limit=0)

if __name__=="__main__":
    unittest.main()
