"""Synthetic original Source BSP element inventory tests; no game assets."""
import struct
import lzma
import unittest

from tools.bsp_to_browser_mesh import BspError
from tools.inspect_hotel_elements import (
    entity_summary,read_gamelump_directory,parse_static_dictionary,inspect_bsp,
)


def make_bsp():
    endian=">"
    bsp=bytearray(1036)
    bsp[:4]=b"PSBV"
    struct.pack_into(endian+"I",bsp,4,20)

    def add(i,raw):
        ofs=len(bsp)
        bsp.extend(raw)
        struct.pack_into(endian+"4I",bsp,8+16*i,ofs,len(raw),0,0)

    add(3,b"\0"*12)
    add(12,b"\0"*4)
    add(13,b"\0"*4)
    add(0,b'{\n"classname" "prop_dynamic"\n"model" "models/props/hotel/door.mdl"\n'
          b'"origin" "12 34 56"\n}\n'
          b'{\n"classname" "func_door"\n"origin" "20 40 60"\n}\n')
    static=(struct.pack(">I",1)+b"models/props/hotel/chair.mdl".ljust(128,b"\0")
            +struct.pack(">I",0)+struct.pack(">I",1)+b"\0"*56)
    directory=(struct.pack(">I",1)+b"prps"+struct.pack(">HHII",0,9,20,len(static)))
    add(35,directory+static)
    add(26,b"\0"*176)
    add(33,b"\0"*80)
    return bytes(bsp)


class HotelElementTests(unittest.TestCase):
    def test_entity_counts_are_bounded_and_relevant(self):
        raw=(b'{"classname" "prop_dynamic" "model" "models/test.mdl" '
             b'"origin" "4 5 6"} '
             b'{"classname" "func_door" "origin" "1 2 3"} '
             b'{"classname" "light" "origin" "0 0 0"}')
        result=entity_summary(raw)
        self.assertEqual(result["entity_blocks"],3)
        self.assertEqual(result["prop_and_door_classes"]["prop_dynamic"],1)
        self.assertEqual(result["prop_and_door_classes"]["func_door"],1)
        self.assertEqual(result["model_names"]["models/test.mdl"],1)
        self.assertEqual(result["sample_entities"][0]["origin"],[4,5,6])

    def test_game_lump_directory_and_unknown_id(self):
        raw=struct.pack(">I",1)+b"prps"+struct.pack(">HHII",0,9,20,148)
        entries=read_gamelump_directory(raw,">")
        self.assertEqual(entries[0]["version"],9)
        self.assertEqual(entries[0]["id_raw"],b"prps")
        with self.assertRaises(BspError):
            read_gamelump_directory(struct.pack(">I",10000),">")

    def test_static_dictionary_only_not_prop_records(self):
        payload=(struct.pack(">I",1)+b"models/props/hotel/chair.mdl".ljust(128,b"\0")
                 +struct.pack(">I",0)+struct.pack(">I",1)+b"\0"*56)
        item=parse_static_dictionary(payload,">")
        self.assertEqual(item["prop_count"],1)
        self.assertEqual(item["models"],["models/props/hotel/chair.mdl"])
        self.assertEqual(item["prop_record_bytes_apparent"],56)
        with self.assertRaises(BspError):
            parse_static_dictionary(payload[:100],">")

    def test_compressed_sprp_model_dictionary_using_actual_lzma_wrapper(self):
        bsp=bytearray(make_bsp())
        static=(struct.pack(">I",1)+
                b"models/props/hotel/chair.mdl".ljust(128,b"\0")+
                struct.pack(">I",0)+struct.pack(">I",1)+b"\0"*56)
        properties=bytes([93])+struct.pack("<I",65536)
        raw=lzma.compress(static,format=lzma.FORMAT_RAW,
            filters=[{"id":lzma.FILTER_LZMA1,"dict_size":65536,
                      "lc":3,"lp":0,"pb":2}])
        wrapped=b"LZMA"+struct.pack(">2I",len(static),len(raw))+properties+raw
        game=struct.pack(">I",1)+b"prps"+struct.pack(">HHII",1,9,20,len(static))+wrapped
        at=len(bsp)
        bsp.extend(game)
        struct.pack_into(">4I",bsp,8+35*16,at,len(game),0,0)
        result=inspect_bsp(bytes(bsp))
        self.assertEqual(len(result["static_prop_headers"]),1)
        header=result["static_prop_headers"][0]
        self.assertEqual(header["model_dictionary_entries"],1)
        self.assertEqual(header["prop_count"],1)
        self.assertEqual(header["source"],"game_lump_relative")
        self.assertEqual(header["version"],9)
        self.assertTrue(header["compressed"])

    def test_compressed_flag_is_not_proof_of_decodable_lzma(self):
        bsp=bytearray(make_bsp())
        game=struct.pack(">I",1)+b"prps"+struct.pack(">HHII",1,9,20,156212)+b"NOTLZMA"
        at=len(bsp)
        bsp.extend(game)
        struct.pack_into(">4I",bsp,8+35*16,at,len(game),0,0)
        result=inspect_bsp(bytes(bsp))
        self.assertEqual(result["static_prop_headers"],[])
        self.assertTrue(any("no validated" in x for x in result["game_lump_notes"]))

    def test_end_to_end_synthetic_psbv(self):
        result=inspect_bsp(make_bsp())
        self.assertEqual(result["source_magic"],"PSBV")
        self.assertEqual(result["entities"]["prop_and_door_classes"]["func_door"],1)
        self.assertEqual(result["static_prop_headers"][0]["prop_count"],1)
        self.assertEqual(result["static_prop_headers"][0]["version"],9)
        self.assertEqual(result["static_prop_headers"][0]["source"],"game_lump_relative")
        self.assertEqual(result["displacement_lumps"]["dispinfo_struct_guess_176"],1)


if __name__=="__main__":
    unittest.main()
