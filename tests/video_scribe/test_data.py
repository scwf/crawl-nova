import unittest
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock

# Ensure we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from video_scribe.data import ASRData, ASRDataSeg, handle_long_path

class TestASRData(unittest.TestCase):
    def setUp(self):
        self.seg1 = ASRDataSeg("Hello", 1000, 2000)
        self.seg2 = ASRDataSeg("World", 2500, 3000)
        self.data = ASRData([self.seg1, self.seg2])

    def test_init_sorting_and_filtering(self):
        # Test that empty segments are removed and segments are sorted by start_time
        seg_empty = ASRDataSeg("", 0, 100)
        seg_whitespace = ASRDataSeg("   ", 100, 200)
        seg_late = ASRDataSeg("Late", 5000, 6000)
        seg_early = ASRDataSeg("Early", 0, 500)
        
        # Pass in unsorted order
        data = ASRData([seg_late, seg_empty, seg_early, seg_whitespace])
        
        # Expecting only Late and Early
        self.assertEqual(len(data.segments), 2)
        # Sorted by start time
        self.assertEqual(data.segments[0].text, "Early")
        self.assertEqual(data.segments[0].start_time, 0)
        self.assertEqual(data.segments[1].text, "Late")
        self.assertEqual(data.segments[1].start_time, 5000)

    def test_to_txt(self):
        expected_text = "Hello\nWorld"
        self.assertEqual(self.data.to_txt(), expected_text)

    def test_to_srt(self):
        srt_content = self.data.to_srt()
        # Basic checks for content
        self.assertIn("1", srt_content)
        self.assertIn("00:00:01,000 --> 00:00:02,000", srt_content)
        self.assertIn("Hello", srt_content)
        self.assertIn("2", srt_content)
        self.assertIn("00:00:02,500 --> 00:00:03,000", srt_content)
        self.assertIn("World", srt_content)

    def test_to_json(self):
        json_data = self.data.to_json()
        self.assertEqual(len(json_data), 2)
        self.assertIn("1", json_data)
        self.assertIn("2", json_data)
        
        entry_1 = json_data["1"]
        self.assertEqual(entry_1["text"], "Hello")
        self.assertEqual(entry_1["start_time"], 1000)
        self.assertEqual(entry_1["end_time"], 2000)
        
        entry_2 = json_data["2"]
        self.assertEqual(entry_2["text"], "World")

    def test_save_txt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = os.path.join(tmp_dir, "output.txt")
            self.data.save(save_path)
            with open(save_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content, "Hello\nWorld")

    def test_save_srt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = os.path.join(tmp_dir, "output.srt")
            self.data.save(save_path)
            
            with open(save_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Verify basic structure
            self.assertIn("1\n00:00:01,000 --> 00:00:02,000\nHello", content)
            self.assertIn("2\n00:00:02,500 --> 00:00:03,000\nWorld", content)

    def test_save_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = os.path.join(tmp_dir, "output.json")
            self.data.save(save_path)
            
            with open(save_path, "r", encoding="utf-8") as f:
                content = json.load(f)
            
            self.assertEqual(len(content), 2)
            self.assertEqual(content["1"]["text"], "Hello")
            self.assertEqual(content["1"]["start_time"], 1000)
            self.assertEqual(content["1"]["end_time"], 2000)
            
            self.assertEqual(content["2"]["text"], "World")

    def test_save_unsupported_format(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = os.path.join(tmp_dir, "output.xyz")
            with self.assertRaises(ValueError) as cm:
                self.data.save(save_path)
            self.assertIn("Unsupported format", str(cm.exception))

    def test_from_srt(self):
        srt_input = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Hello World\n"
            "\n"
            "2\n"
            "00:00:02,500 --> 00:00:03,500\n"
            "Second Line\n"
        )
        
        data = ASRData.from_srt(srt_input)
        self.assertEqual(len(data.segments), 2)
        
        seg1 = data.segments[0]
        self.assertEqual(seg1.text, "Hello World")
        self.assertEqual(seg1.start_time, 1000)
        self.assertEqual(seg1.end_time, 2000)
        
        seg2 = data.segments[1]
        self.assertEqual(seg2.text, "Second Line")
        self.assertEqual(seg2.start_time, 2500)
        self.assertEqual(seg2.end_time, 3500)

    def test_from_srt_malformed(self):
        # Test tolerance to skips or bad blocks
        srt_input = (
            "Garbage\n"
            "\n"
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Good\n"
        )
        data = ASRData.from_srt(srt_input)
        self.assertEqual(len(data.segments), 1)
        self.assertEqual(data.segments[0].text, "Good")

    def test_cycle_srt_file(self):
        # Full cycle: Create -> Save to File -> Read File -> Parse -> Verify
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = os.path.join(tmp_dir, "cycle.srt")
            
            # 1. Save original data
            self.data.save(save_path)
            
            # 2. Read file content
            with open(save_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # 3. Parse content back
            loaded_data = ASRData.from_srt(content)
            
            # 4. Verify
            self.assertEqual(len(loaded_data.segments), 2)
            
            # Note: Floating point arithmetic or millisecond conversion might cause tiny diffs usually,
            # but here we use integers for ms, so it should be exact unless parsing logic is lossy.
            self.assertEqual(loaded_data.segments[0].start_time, self.seg1.start_time)
            self.assertEqual(loaded_data.segments[0].end_time, self.seg1.end_time)
            self.assertEqual(loaded_data.segments[0].text, self.seg1.text)
            
            self.assertEqual(loaded_data.segments[1].start_time, self.seg2.start_time)
            self.assertEqual(loaded_data.segments[1].end_time, self.seg2.end_time)
            self.assertEqual(loaded_data.segments[1].text, self.seg2.text)
if __name__ == '__main__':
    unittest.main()
