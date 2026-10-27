"""Synthetic-only original studio triplet tests, no game model data."""
import io
import lzma
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from tools.probe_original_hotel_model import (
    DEFAULT_MODEL,OUT_DIR,find_components,inspect_model,extract_model,
    parse_source_header,decode_xbox_mdl,save_decoded_mdl,studio_model_summary,XboxZipError
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


def source_lzma_wrap(raw):
    properties=b"\x5d"+struct.pack("<I",65536)
    packed=lzma.compress(raw,format=lzma.FORMAT_RAW,
        filters=[{"id":lzma.FILTER_LZMA1,
                  "dict_size":65536,"lc":3,"lp":0,"pb":2}])
    result=b"LZMA"+struct.pack(">II",len(raw),len(packed))+properties+packed
    return result.ljust(64,b"\0")


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

    def test_lzma_wrapped_real_xbox_mdl_decodes_and_checksums_match(self):
        mdl,vvd,vtx=studio_headers(big_endian=True,checksum=0xf3737e00)
        mem=io.BytesIO()
        stem=DEFAULT_MODEL[:-4]
        with zipfile.ZipFile(mem,"w",compression=zipfile.ZIP_STORED) as out:
            out.writestr(stem+".360.mdl",source_lzma_wrap(mdl))
            out.writestr(stem+".360.vvd",vvd)
            out.writestr(stem+".dx90.360.vtx",vtx)
        data=mem.getvalue()
        with io.BytesIO(data) as stream:
            directory=scan_directory(stream,len(data))
            records,info=inspect_model(stream,len(data),directory,DEFAULT_MODEL)
            restored=decode_xbox_mdl(stream,records["mdl"])
        self.assertEqual(restored,mdl)
        self.assertTrue(info["all_headers_recognized"])
        self.assertTrue(info["checksum_match"])
        self.assertEqual(info["parts"]["mdl"]["checksum"],"f3737e00")
        self.assertEqual(info["parts"]["mdl"]["on_disk_encoding"],"Valve LZMA")
        self.assertEqual(info["parts"]["mdl"]["decoded_bytes"],128)

    def test_source_studio_header_counts_are_bounded(self):
        mdl,_,_=studio_headers()
        payload=bytearray(512)
        payload[:len(mdl)]=mdl
        payload[12:32]=b"hotel_chair.mdl\x00\x00\x00\x00\x00"
        struct.pack_into(">I",payload,76,len(payload))
        struct.pack_into(">2I",payload,204,1,400)
        struct.pack_into(">2I",payload,232,1,480)
        parsed=parse_source_header(payload,"mdl")
        summary=studio_model_summary(bytes(payload),parsed)
        self.assertEqual(summary["bodyparts"],1)
        self.assertEqual(summary["textures"],1)
        self.assertEqual(summary["status"],
                         "studiohdr counts and table bounds plausible")
        struct.pack_into(">I",payload,236,65535)
        result=studio_model_summary(bytes(payload),parsed)
        self.assertIn("outside decoded",result["status"])

    def test_refuse_corrupt_lzma_mdl(self):
        mdl,vvd,vtx=studio_headers()
        corrupted=bytearray(source_lzma_wrap(mdl))
        struct.pack_into(">I",corrupted,4,0x7fffffff)
        mem=io.BytesIO()
        stem=DEFAULT_MODEL[:-4]
        with zipfile.ZipFile(mem,"w",compression=zipfile.ZIP_STORED) as out:
            out.writestr(stem+".360.mdl",corrupted)
            out.writestr(stem+".vvd",vvd)
            out.writestr(stem+".dx90.360.vtx",vtx)
        data=mem.getvalue()
        with io.BytesIO(data) as stream:
            directory=scan_directory(stream,len(data))
            with self.assertRaisesRegex(XboxZipError,"Decoded MDL size"):
                inspect_model(stream,len(data),directory,DEFAULT_MODEL)

    def test_save_decoded_mdl_private_and_refuse_overwrite(self):
        mdl,_,_=studio_headers()
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=OUT_DIR) as folder:
            saved=save_decoded_mdl(mdl,DEFAULT_MODEL,Path(folder))
            self.assertEqual(saved.read_bytes(),mdl)
            self.assertTrue(saved.is_relative_to(OUT_DIR))
            with self.assertRaisesRegex(XboxZipError,"already exists"):
                save_decoded_mdl(mdl,DEFAULT_MODEL,Path(folder))

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
