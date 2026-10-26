"""Synthetic Xbox BSP geometry tests; no commercial map data is included."""
import lzma
import struct
import unittest

from tools.bsp_to_browser_mesh import BspError, convert, decode_valve_lzma, read_directory

def sample_bsp(compress_vertices=False):
    buf=bytearray(1036)
    buf[:4]=b"PSBV"
    struct.pack_into(">I",buf,4,20)
    directory={}
    def add_lump(index,payload,uncompressed=0):
        offset=len(buf)
        directory[index]=(offset,len(payload),0,uncompressed)
        buf.extend(payload)
    verts=b"".join(struct.pack(">3f",*p) for p in [
        (0,0,0),(64,0,0),(64,64,0),(0,64,0)])
    if compress_vertices:
        dictionary=1<<17
        filters=[{"id":lzma.FILTER_LZMA1,"dict_size":dictionary,"lc":3,"lp":0,"pb":2}]
        packed=lzma.compress(verts,format=lzma.FORMAT_RAW,filters=filters)
        props=(2*5+0)*9+3
        compressed=b"LZMA"+struct.pack(">II",len(verts),len(packed))+bytes([props])+struct.pack("<I",dictionary)+packed
        add_lump(3,compressed,len(verts))
    else:
        add_lump(3,verts)
    add_lump(12,b"".join(struct.pack(">2H",*e) for e in [(0,1),(1,2),(2,3),(3,0)]))
    add_lump(13,struct.pack(">4i",0,1,2,3))
    face=bytearray(56)
    struct.pack_into(">i",face,4,0)   # firstedge
    struct.pack_into(">h",face,8,4)   # numedges
    struct.pack_into(">h",face,12,-1) # dispinfo (none)
    add_lump(58,bytes(face))
    for index,entry in directory.items():
        struct.pack_into(">4I",buf,8+index*16,*entry)
    return bytes(buf)


class GeometryTests(unittest.TestCase):
    def test_hdr_face_four_vertices(self):
        data=convert(sample_bsp())
        self.assertEqual(data["face_lump"],58)
        self.assertEqual(data["triangle_count"],2)
        self.assertEqual(len(data["vertices"]),12)
        self.assertEqual(len(data["indices"]),6)
        self.assertEqual(data["bounds"],[[0.0,0.0,0.0],[64.0,64.0,0.0]])

    def test_compressed_vertex_lump(self):
        data=convert(sample_bsp(compress_vertices=True))
        self.assertEqual(data["triangle_count"],2)

    def test_refuse_bad_signature(self):
        data=b"NOPE"+sample_bsp()[4:]
        with self.assertRaisesRegex(BspError,"Not recognized"):
            convert(data)

    def test_refuse_missing_face_lump(self):
        data=bytearray(sample_bsp())
        struct.pack_into(">4I",data,8+58*16,0,0,0,0)
        with self.assertRaisesRegex(BspError,"No HDR"):
            convert(bytes(data))

    def test_layout_detection(self):
        endian,dirs,selected=read_directory(sample_bsp())
        self.assertEqual(endian,">")
        self.assertEqual(selected,"offset_length_version")
        self.assertGreater(dirs[58]["size"],0)


if __name__=="__main__":
    unittest.main()
