"""Synthetic-only test of one-command original Xbox prop batch export."""
from pathlib import Path
import json
import tempfile
import unittest
import zipfile

from tools.build_hotel_scene_bundle import (
    PRIVATE,load_placements,choose_trio,archive_index,build_bundle,
)
from tools.scan_xbox_zip_directory import scan_xbox_zip
from test_convert_original_hotel_chair import original_tri_test_data

MODEL1="models/props_furniture/hotel_chair.mdl"
MODEL2="models/props_interiors/lightsconce02.mdl"
MISSING="models/missing/missing.mdl"


def setup_scene(root: Path, include_missing=False):
    original_mdl,original_vvd,original_vtx=original_tri_test_data()
    archive=root/"synthetic-xbox.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_STORED) as z:
        for name in (MODEL1,MODEL2):
            stem=name[:-4]
            z.writestr(stem+".mdl",original_mdl)
            z.writestr(stem+".vvd",original_vvd)
            z.writestr(stem+".dx90.360.vtx",original_vtx)
    models=[MODEL1,MODEL1,MODEL2]
    if include_missing:models.append(MISSING)
    placements=[{"class":"prop_static","model":name,
                 "origin":[float(i),2.,3.],"angles":[0.,90.,0.]}
                for i,name in enumerate(models)]
    info={"format":"lfd2-original-prop-placements-v1",
          "source_map":"c1m1_hotel.360.bsp","placements":placements}
    manifest=root/"hotel-all-props.json"
    manifest.write_text(json.dumps(info))
    return archive,manifest


class OriginalBatchTests(unittest.TestCase):
    def test_one_archive_scan_exports_every_supported_model(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE) as tmp:
            root=Path(tmp)
            zipfile_,manifest=setup_scene(root)
            folder=root/"auto"
            scene=build_bundle(zipfile_,manifest,folder)
            self.assertEqual(scene["stats"]["decoded_models"],2)
            self.assertEqual(scene["stats"]["original_placements_included"],3)
            self.assertEqual(len(scene["models"]),2)
            self.assertEqual(len(list((folder/"models").glob("*.mesh.json"))),2)
            self.assertEqual(json.loads((folder/"scene.json").read_text())["stats"],
                             scene["stats"])
            for m in scene["models"]:
                geometry=json.loads((folder/m["file"]).read_text())
                self.assertEqual(geometry["format"],"lfd2-source-original-model-v1")
                self.assertEqual(geometry["model"],m["model"])
                self.assertEqual(geometry["triangle_count"],1)
                self.assertEqual(geometry["checksum"],"f3737e00")
            with self.assertRaisesRegex(ValueError,"new folder"):
                build_bundle(zipfile_,manifest,folder)

    def test_missing_original_studio_triplets_get_skipped_not_faked(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE) as tmp:
            root=Path(tmp)
            archive,manifest=setup_scene(root,include_missing=True)
            scene=build_bundle(archive,manifest,root/"out")
            self.assertEqual(scene["stats"]["attempted_models"],3)
            self.assertEqual(scene["stats"]["skipped_models"],1)
            self.assertEqual(scene["stats"]["decoded_models"],2)
            self.assertEqual(scene["stats"]["original_placements_total"],4)
            self.assertEqual(scene["stats"]["original_placements_included"],3)
            self.assertEqual(scene["skipped"][0]["model"],MISSING)

    def test_archive_duplicate_companion_names_fail_closed(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE) as tmp:
            root=Path(tmp)
            archive,manifest=setup_scene(root)
            report=scan_xbox_zip(archive)
            index,dup=archive_index(report["entries"])
            self.assertEqual(len(choose_trio(MODEL1,index,dup)),3)
            duplicates=set(dup)|{MODEL1}
            with self.assertRaisesRegex(ValueError,"companion ambiguous"):
                choose_trio(MODEL1,index,duplicates)

    def test_invalid_manifest_does_not_write_bundle(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE) as tmp:
            root=Path(tmp)
            archive,manifest=setup_scene(root)
            scene=json.loads(manifest.read_text())
            scene["placements"][0]["model"]="models/../../unsafe.mdl"
            manifest.write_text(json.dumps(scene))
            with self.assertRaisesRegex(Exception,"Invalid Source model path"):
                build_bundle(archive,manifest,root/"out")
            self.assertFalse((root/"out").exists())

    def test_limit_for_small_preview_excludes_other_models(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE) as tmp:
            root=Path(tmp)
            archive,manifest=setup_scene(root)
            scene=build_bundle(archive,manifest,root/"out",limit=1)
            self.assertEqual(scene["stats"]["decoded_models"],1)
            self.assertEqual(scene["stats"]["attempted_models"],1)
            self.assertEqual(len(set(row["model"] for row in scene["placements"])),1)


if __name__=="__main__":
    unittest.main()
