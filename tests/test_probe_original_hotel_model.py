"""Synthetic-only original studio triplet tests, no game model data."""
import io
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from tools.probe_original_hotel_model import (
    DEFAULT_MODEL,OUT_DIR,find_components,inspect_model,extract_model,
    parse_source_header,XboxZipError
)
from tools.scan_xbox_zip_directory import scan_directory


def studio_headers(big_endian=True,checksum=0x12345678):
    order=">" if big_endian else "<"
    mdl=bytearray(128)
    mdl[:4]=b"IDST"
    struct.pack_into(order+"II",mdl,4,49,checksum)
    vvd=bytearray(128)
    vvd[:4]=b"IDSV"
    struct.pack_into(order+"III",vvd,4,4,checksum,1)
    vtx=bytearray(128)
    struct.pack_into(order+"I",vtx,0,7)
    struct.pack_into(order+"I",vtx,16,checksum)
    struct.pack_into(order+"I",vtx,20,1)
    struct.pack_into(order+"I",vtx,28,1)
    return bytes(mdl),bytes(vvd),bytes(vtx)


def make_zip(*, checksum=0x12345678, compressed=False):
    mdl,vvd,vtx=studio_headers(checksum=checksum)
    output=io.BytesIO()
    stem=DEFAULT_MODEL[:-4]
    with zipfile.ZipFile(output,"w",compression=(
            zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED)) as zipout:
        zipout.writestr(stem+".mdl",mdl)
        zipout.writestr(stem+".vvd",vvd)
        zipout.writestr(stem+".dx90.360.vtx",vtx)
    return output.getvalue()


class OriginalHotelModelTests(unittest.TestCase):
    def test_real_xbox_studio_suffixes_have_full_triplet(self):
        data=make_zip()
        with io.BytesIO(data) as stream:
            directory=scan_directory(stream,len(data))
            records,info=inspect_model(stream,len(data),directory,DEFAULT_MODEL)
        self.assertEqual(set(records),{"mdl","vvd","vtx"})
        self.assertTrue(info["all_headers_recognized"])
        self.assertTrue(info["checksum_match"])
        self.assertEqual(info["parts"]["mdl"]["endian"],"big")
        self.assertEqual(info["parts"]["vvd"]["version"],4)
        self.assertEqual(info["parts"]["vtx"]["version"],7)

    def test_little_endian_header_fallback(self):
        mdl,vvd,vtx=studio_headers(big_endian=False)
        self.assertEqual(parse_source_header(mdl,"mdl")["endian"],"little")
        self.assertEqual(parse_source_header(vvd,"vvd")["checksum"],"12345678")
        self.assertEqual(parse_source_header(vtx,"vtx")["bodypart_count"],1)

    def test_checksum_mismatch_not_claimed_valid(self):
        data=bytearray(make_zip())
        mdl,vvd,vtx=studio_headers()
        wrong=bytearray(vtx)
        struct.pack_into(">I",wrong,16,0x87654321)
        mem=io.BytesIO()
        stem=DEFAULT_MODEL[:-4]
        with zipfile.ZipFile(mem,"w",compression=zipfile.ZIP_STORED) as out:
            out.writestr(stem+".mdl",mdl)
            out.writestr(stem+".vvd",vvd)
            out.writestr(stem+".dx90.360.vtx",wrong)
        data=mem.getvalue()
        with io.BytesIO(data) as stream:
            directory=scan_directory(stream,len(data))
            _,info=inspect_model(stream,len(data),directory,DEFAULT_MODEL)
        self.assertFalse(info["checksum_match"])

    def test_missing_vtx_refused(self):
        mem=io.BytesIO()
        with zipfile.ZipFile(mem,"w") as zipout:
            zipout.writestr(DEFAULT_MODEL,b"IDST"+b"\0"*128)
        data=mem.getvalue()
        with io.BytesIO(data) as stream:
            report=scan_directory(stream,len(data))
            with self.assertRaisesRegex(XboxZipError,"vvd requires"):
                find_components(report["entries"],DEFAULT_MODEL)

    def test_compressed_zip_member_refused(self):
        data=make_zip(compressed=True)
        with io.BytesIO(data) as stream:
            report=scan_directory(stream,len(data))
            with self.assertRaisesRegex(XboxZipError,"Encrypted/compressed"):
                inspect_model(stream,len(data),report,DEFAULT_MODEL)

    def test_explicit_local_extraction_preserves_only_3_files(self):
        data=make_zip()
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=OUT_DIR) as tmp:
            with io.BytesIO(data) as stream:
                report=scan_directory(stream,len(data))
                records,info=inspect_model(stream,len(data),report,DEFAULT_MODEL)
                saved=extract_model(stream,records,Path(tmp))
                self.assertEqual(len(saved),3)
                for kind,path in zip(records,saved):
                    self.assertEqual(path.stat().st_size,128)
                with self.assertRaisesRegex(XboxZipError,"already existing"):
                    extract_model(stream,records,Path(tmp))
            self.assertEqual(len(list(Path(tmp).rglob("*.*"))),3)

    def test_unsafe_model_path_refused(self):
        data=make_zip()
        with io.BytesIO(data) as stream:
            report=scan_directory(stream,len(data))
            with self.assertRaisesRegex(XboxZipError,"Invalid Source model path"):
                inspect_model(stream,len(data),report,"models/../../wrong.mdl")


if __name__=="__main__":
    unittest.main()
