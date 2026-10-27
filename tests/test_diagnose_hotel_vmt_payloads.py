"""Synthetic metadata-only classification of original Xbox studio VMT payloads."""
from __future__ import annotations
import unittest

from tools.diagnose_hotel_vmt_payloads import (
    material_payload_category,pick_samples
)

def entry(material):
    return ("zip1",{"name":"materials/"+material+".vmt"})

class VmtFormatDiagnosticTests(unittest.TestCase):
    def test_ordinary_plaintext_with_basetexture_is_identified(self):
        raw=b'VertexLitGeneric { "$basetexture" "models/chair/cushion" }'
        info=material_payload_category(raw)
        self.assertEqual(info["kind"],"plain_text_basetexture")
        self.assertTrue(info["parsed_basetexture"])
        self.assertTrue(info["has_ascii_basetexture_token"])

    def test_readable_text_without_basetexture_distinct_from_binary(self):
        info=material_payload_category(
            b'UnlitGeneric { "$selfillum" "1" "$color" "[0 0 0]" }')
        self.assertEqual(info["kind"],"plain_text_no_basetexture")
        self.assertFalse(info["has_ascii_basetexture_token"])

    def test_raw_valve_lzma_signature_detected_without_decompressing(self):
        raw=b"LZMA"+b"\x00"*12+b"\x99"*128
        info=material_payload_category(raw)
        self.assertEqual(info["kind"],"valve_lzma_wrapper")
        self.assertFalse(info["parsed_basetexture"])
        self.assertEqual(info["hex16"][:11],"4c 5a 4d 41")

    def test_nul_heavy_or_unrecognized_coded_vmts_are_not_called_plaintext(self):
        info=material_payload_category(b"\xff\x00\x01\x00"*80)
        self.assertEqual(info["kind"],"utf16_or_binary_nul_heavy")
        self.assertFalse(info["parsed_basetexture"])

    def test_distinct_existing_sources_scanned_once_and_grouped(self):
        models=[{"model":"models/a.mdl","original_placements":10,
                 "texture_candidates":[["models/a"],["models/a"]]},
                {"model":"models/b.mdl","original_placements":5,
                 "texture_candidates":[["models/b"]]}]
        sources={"vmt":{"models/a":[entry("models/a")],
                         "models/b":[entry("models/b")]},
                 "vtfx":{}}
        payloads={"materials/models/a.vmt":b"LZMA"+b"\x00"*28,
                  "materials/models/b.vmt":
                   b'VertexLitGeneric { "$basetexture" "models/b" }'}
        report=pick_samples(models,sources,
                            lambda label,row:payloads[row["name"]],2)
        self.assertEqual(report["unique_vmt_files"],2)
        self.assertEqual(sum(x["file_count"] for x in report["counts_by_kind"]),2)
        first={x["kind"]:x for x in report["counts_by_kind"]}
        self.assertEqual(first["valve_lzma_wrapper"]["file_count"],1)
        self.assertEqual(first["valve_lzma_wrapper"]["referenced_prop_uses"],20)
        self.assertEqual(first["plain_text_basetexture"]["file_count"],1)

if __name__=="__main__":
    unittest.main()
