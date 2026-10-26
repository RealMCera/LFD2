"""Synthetic-only model directory and entity placement availability tests."""
import unittest

from tools.inspect_hotel_model_assets import (
    vector3,list_model_placements,model_files,model_availability,make_inventory
)
from tests.test_inspect_hotel_elements import make_bsp


class ModelInventoryTests(unittest.TestCase):
    def test_valid_original_dynamic_and_door_entity_transforms(self):
        text=(b'{ "classname" "prop_physics" '
              b'"model" "models/props/hotel/chair.mdl" '
              b'"origin" "10 20 30" "angles" "0 90 0"}\n'
              b'{"classname" "prop_door_rotating" '
              b'"model" "models/props/hotel/door.mdl" "origin" "1 2 3"}\n'
              b'{"classname" "func_brush" "model" "*3" "origin" "0 0 0"}')
        rows=list_model_placements(text)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["angles"],[0,90,0])
        self.assertEqual(rows[1]["model"],"models/props/hotel/door.mdl")

    def test_invalid_positions_and_paths_are_ignored(self):
        raw=b'{"classname" "prop_physics" "model" "models/../../bad.mdl" "origin" "0 0 0"}'
        self.assertEqual(list_model_placements(raw),[])
        self.assertIsNone(vector3("NaN 3 4"))
        self.assertIsNone(vector3("0 0"))
        self.assertEqual(vector3("1.1 -2 3"),[1.1,-2,3])

    def test_model_companion_availability_requires_real_mesh_parts(self):
        files={"models/props/hotel/chair.mdl",
               "models/props/hotel/chair.vvd",
               "models/props/hotel/chair.vtx"}
        record=model_availability(["models/props/hotel/chair.mdl"],files)[0]
        self.assertTrue(record["mesh_ready"])
        self.assertFalse(record["phy"])
        incomplete=model_availability(["models/props/hotel/door.mdl"],files)[0]
        self.assertFalse(incomplete["mesh_ready"])

    def test_supported_vtx_alternative_suffixes(self):
        self.assertIn("models/props/hotel/chair.dx90.vtx",
                      model_files("models/props/hotel/chair.mdl")["vtx"])

    def test_synthetic_bsp_and_zip_names(self):
        paths=["models/props/hotel/door.mdl",
               "models/props/hotel/door.vvd",
               "models/props/hotel/door.vtx",
               "models/props/hotel/chair.mdl"]
        inventory=make_inventory(make_bsp(),paths)
        self.assertEqual(inventory["placement_count"],1)
        self.assertEqual(inventory["entity_models"],1)
        self.assertEqual(inventory["dynamic_availability"][0]["mesh_ready"],True)
        self.assertEqual(inventory["static_model_dictionary_count"],1)


if __name__=="__main__":
    unittest.main()
