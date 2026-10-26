"""Synthetic entity and private spawn-enrichment tests; no commercial map content."""
import struct
import unittest
from tools.add_bsp_spawns import extract_spawns, parse_spawns, enrich_mesh

SAMPLE = b'''
{
"classname" "worldspawn"
"message" "synthetic"
}
{
"classname" "info_survivor_position"
"origin" "100 200 300"
"angles" "10 90 0"
"targetname" "test survivor"
}
{
"classname" "info_player_start"
"origin" "-50 42 75"
"angle" "180"
}
{
"classname" "info_landmark"
"origin" "0 0 0"
}
'''

class SpawnTests(unittest.TestCase):
    def test_prioritize_player_starts_and_eyelevel(self):
        spawns = parse_spawns(SAMPLE)
        self.assertEqual([p["kind"] for p in spawns],
                         ["info_player_start", "info_survivor_position", "info_landmark"])
        self.assertEqual(spawns[0]["position"], [-50, 42, 139])
        self.assertAlmostEqual(spawns[0]["yaw"], 3.141593, places=5)
        self.assertEqual(spawns[1]["position"], [100, 200, 364])
        self.assertAlmostEqual(spawns[1]["pitch"], -0.174533, places=5)

    def test_reject_bad_origin(self):
        data = b'{"classname" "info_player_start" "origin" "nan 8 9"}'
        self.assertEqual(parse_spawns(data), [])

    def test_limit(self):
        data=b''.join([b'{"classname" "info_player_start" "origin" "1 2 3"}'
                       for _ in range(20)])
        self.assertEqual(len(parse_spawns(data, limit=4)), 4)

    def test_enrich_without_mutating_old_mesh(self):
        original={"format":"source-brush-mesh-0.1","vertices":[0,0,0],"indices":[0]}
        added=enrich_mesh(original,parse_spawns(SAMPLE))
        self.assertNotIn("camera_spawns",original)
        self.assertEqual(len(added["camera_spawns"]),3)

    def test_uncompressed_entity_directory(self):
        data=bytearray(1036)
        data[:4]=b"PSBV"
        struct.pack_into(">I",data,4,20)
        offset=len(data)
        data.extend(SAMPLE)
        struct.pack_into(">4I",data,8,offset,len(SAMPLE),0,0)
        for index, size in ((3, 12), (12, 4), (13, 4)):
            ofs=len(data)
            data.extend(b"\x00" * size)
            struct.pack_into(">4I",data,8+index*16,ofs,size,0,0)
        spawns=extract_spawns(bytes(data))
        self.assertEqual(len(spawns),3)

if __name__ == "__main__":
    unittest.main()
