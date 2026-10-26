"""Synthetic VTFX files and mocked converter; no downloaded executable/assets."""
import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.convert_local_vtfx import (
    png_dimensions, run_converter, verify_vtfx, ConversionError, PRIVATE_ROOT
)


def vtfx(width=512,height=512):
    header=bytearray(80)
    header[:4]=b"VTFX"
    struct.pack_into(">4I",header,4,0x360,8,68,0)
    struct.pack_into(">5H",header,20,width,height,1,1,0)
    struct.pack_into(">BB",header,30,0,1)
    struct.pack_into(">I",header,48,13)
    return bytes(header)


def png_header(width=512,height=512):
    return b"\x89PNG\r\n\x1a\n"+struct.pack(">I",13)+b"IHDR"+struct.pack(">II",width,height)+b"\x08\x02\x00\x00\x00"


class ConvertVtfxTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=PRIVATE_ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.input=self.root/"wall.360.vtf"
        self.input.write_bytes(vtfx())
        self.output=self.root/"png"
        self.executable=self.root/"vtfx_reader.exe"
        self.executable.write_bytes(b"dummy binary never executed")

    def test_header_and_png_dimensions(self):
        self.assertEqual(verify_vtfx(self.input)["width"],512)
        testpng=self.root/"sample.png"
        testpng.write_bytes(png_header())
        self.assertEqual(png_dimensions(testpng),(512,512))

    def test_invokes_external_converter_without_shell(self):
        def mock_run(argv,**kwargs):
            self.output.mkdir(parents=True,exist_ok=True)
            (self.output/"wall.png").write_bytes(png_header())
        with patch("tools.convert_local_vtfx.subprocess.run",side_effect=mock_run) as runner:
            rows=run_converter(self.input,self.output,self.executable)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][1:],(512,512))
        runner.assert_called_once_with([str(self.executable),"-i",str(self.input),
                                         "-o",str(self.output)],check=True,timeout=180)

    def test_refuses_existing_output(self):
        self.output.mkdir()
        (self.output/"precious.png").write_bytes(png_header())
        with self.assertRaisesRegex(ConversionError,"Output must be empty"):
            run_converter(self.input,self.output,self.executable)

    def test_rejects_wrong_image_dimensions(self):
        def mock_run(argv,**kwargs):
            self.output.mkdir(parents=True,exist_ok=True)
            (self.output/"wall.png").write_bytes(png_header(16,16))
        with patch("tools.convert_local_vtfx.subprocess.run",side_effect=mock_run):
            with self.assertRaisesRegex(ConversionError,"No PNG matched"):
                run_converter(self.input,self.output,self.executable)

    def test_private_input_and_output_only(self):
        with self.assertRaisesRegex(ConversionError,"ignored research/local"):
            run_converter(self.input,Path(tempfile.gettempdir())/"out",self.executable)
        with self.assertRaisesRegex(ConversionError,"Input must stay"):
            verify_vtfx(Path(__file__).resolve())


if __name__=="__main__":
    unittest.main()
