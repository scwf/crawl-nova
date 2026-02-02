import unittest
import os
import sys
import configparser
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from video_scribe.core import process_video
from video_scribe.data import ASRData

class TestProcessVideo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load config
        cls.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test_config.ini')
        cls.config = configparser.ConfigParser()
        cls.config.read(cls.config_path)
        
        cls.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
        os.makedirs(cls.output_dir, exist_ok=True)

        # Setup basic logging
        logging.basicConfig(level=logging.INFO)

    def _should_skip(self, section, key, placeholder="your_"):
        if not self.config.has_option(section, key):
            return True
        val = self.config.get(section, key)
        return not val or placeholder in val

    def test_process_video_flow_real(self):
        if self._should_skip('test_data', 'video_url', 'example'):
            self.skipTest("Skipping video process test: No valid video_url provided in test_config.ini")

        video_url = self.config.get('test_data', 'video_url')
        print(f"Running real process_video test for: {video_url}")
        
        try:
            asr_data = process_video(
                video_url_or_path=video_url,
                output_dir=self.output_dir,
            )
            
            self.assertIsInstance(asr_data, ASRData)
            self.assertGreater(len(asr_data.segments), 0)
            
            print("Video processing completed successfully.")
            
        except Exception as e:
            self.fail(f"process_video failed with error: {e}")

if __name__ == '__main__':
    unittest.main()
