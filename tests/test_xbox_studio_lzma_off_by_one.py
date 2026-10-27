"""Synthetic Valve raw LZMA no-end-marker regression for Xbox studio files.

The compatibility exception is intentionally opt-in: never weaken map lumps,
never guess a full missing data record, and never accept a complete EOS stream
that claims the wrong decoded size.
"""
import io
import lzma
import struct
import unittest

from tools.bsp_to_browser_mesh import BspError,decode_valve_lzma
from tools.probe_original_hotel_model import decode_xbox_mdl,parse_source_header


FILTER={"id":lzma.FILTER_LZMA1,"dict_size":65536,"lc":3,"lp":0,"pb":2}
PROPERTY=b"\x5d"+struct.pack("<I",65536)


def compressed_model_no_end_marker():
    """Synthesize an MDL with a no-EOS range coder and ONE surplus output."""
    mdl=bytearray(1024)
    mdl[:4]=b"IDST"
    struct.pack_into(">II",mdl,4,49,0xF3737E00)
    struct.pack_into(">I",mdl,76,len(mdl))
    mdl[500:520]=bytes(range(20))
    # This represents output from a studio compressor whose end flush may
    # yield one more byte than the independently declared Source model size.
    raw=bytes(mdl)+b"\x00"
    coded=lzma.compress(raw,format=lzma.FORMAT_RAW,filters=[FILTER])
    no_eos=coded[:-1]
    return bytes(mdl),coded,no_eos


def wrap(coded: bytes,actual: int) -> bytes:
    return b"LZMA"+struct.pack("<II",actual,len(coded))+PROPERTY+coded


class XboxStudioOneByteLzmaTests(unittest.TestCase):
    def test_no_eos_single_trailing_byte_allowed_only_in_studio_mode(self):
        mdl,_complete,no_eos=compressed_model_no_end_marker()
        wrapped=wrap(no_eos,len(mdl))
        decoder=lzma.LZMADecompressor(format=lzma.FORMAT_RAW,filters=[FILTER])
        result=decoder.decompress(no_eos)
        self.assertEqual(result,mdl+b"\x00")
        self.assertFalse(decoder.eof)

        with self.assertRaisesRegex(BspError,"expected 1024 bytes; got 1025"):
            decode_valve_lzma(wrapped,1024,"<")
        recovered=decode_valve_lzma(
            wrapped,1024,"<",allow_studio_no_eos=True
        )
        self.assertEqual(recovered,mdl)
        self.assertEqual(parse_source_header(recovered,"mdl")["version"],49)
        record={"offset":0,"length":len(wrapped)}
        self.assertEqual(decode_xbox_mdl(io.BytesIO(wrapped),record),mdl)

    def test_complete_end_marker_cannot_claim_smaller_output(self):
        mdl,complete,_no_eos=compressed_model_no_end_marker()
        wrapped=wrap(complete,len(mdl))
        with self.assertRaisesRegex(BspError,"expected 1024 bytes; got 1025"):
            decode_valve_lzma(wrapped,1024,"<",allow_studio_no_eos=True)

    def test_two_surplus_bytes_still_fail(self):
        mdl,_complete,no_eos=compressed_model_no_end_marker()
        with self.assertRaisesRegex(BspError,"expected 1023 bytes; got 1025"):
            decode_valve_lzma(
                wrap(no_eos,len(mdl)-1),len(mdl)-1,"<",
                allow_studio_no_eos=True
            )

    def test_larger_expected_size_or_corrupt_member_fails(self):
        mdl,_complete,no_eos=compressed_model_no_end_marker()
        with self.assertRaisesRegex(BspError,"Unable to decode Valve LZMA"):
            decode_valve_lzma(wrap(no_eos,len(mdl)+2),len(mdl)+2,
                              "<",allow_studio_no_eos=True)
        # Deliberate trailing bytes beyond the declared compressed ZIP member
        # cannot be used to authorize a one-byte compatibility adjustment.
        with self.assertRaisesRegex(BspError,"expected 1024 bytes; got 1025"):
            decode_valve_lzma(wrap(no_eos,len(mdl))+b"\x00",
                              len(mdl),"<",allow_studio_no_eos=True)


if __name__=="__main__":
    unittest.main()
