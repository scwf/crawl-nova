import unittest
import os
import sys
import configparser
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from video_scribe.core import optimize_subtitle
from video_scribe.data import ASRData

class TestOptimizeSubtitle(unittest.TestCase):
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

    def test_optimize_subtitle_real(self):
        if self._should_skip('llm', 'api_key'):
            self.skipTest("Skipping optimization test: No API Key provided in test_config.ini")

        print("Running real optimize_subtitle test...")
        
        # Use real SRT file from resources
        resources_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources')
        # srt_path = os.path.join(resources_dir, "What are enterprise AI Agents？.srt")
        srt_path = os.path.join(resources_dir, "ItzSyfNEptk.srt")
        
        if not os.path.exists(srt_path):
            self.skipTest(f"Resource file not found: {srt_path}")

        # title = "What are enterprise AI Agents?"
        # context = """
        # What are enterprise AI Agents? Every enterprise strives to make its employees more productive and delight its customers with personalized products and services. AI agents have emerged as a breakthrough technology to help realize this potential. These agents operate semi-autonomously or autonomously to understand inputs, make informed decisions, and take actions to accomplish objectives. However, most AI agent projects don't ever make it into production. Watch this video to learn about a new approach by Databricks to help bring AI Agents to production.
        # """
        # full_context = f"{title}\n{context}"
        full_context = """
        ~80% of all companies data is kept in Unstructured formats. This means it's hard to really use it like you would tabular data!<br /><br />IDP (Intelligent Document Processing) is focused on making that Unstructured data more accessible and readily available.<br /><br />In this lesson we take a look at IDP in @databricks and in the next several lessons we will be diving into the code to get data from unstructured to structured.<br /><br />https://www.youtube.com/watch?v=ItzSyfNEptk
        """
        custom_prompt = f"Context: {full_context}"

        # Call optimize
        optimized_data = optimize_subtitle(
            subtitle_data=srt_path,
            model=self.config.get('llm', 'opt_model', fallback='gpt-3.5-turbo'),
            api_key=self.config.get('llm', 'api_key'),
            base_url=self.config.get('llm', 'base_url'),
            custom_prompt=custom_prompt,
            thread_num=10,
            batch_num=10
        )
        
        # Verify
        self.assertIsInstance(optimized_data, ASRData)
        self.assertGreater(len(optimized_data.segments), 0)
        
        # Save output
        save_path = os.path.join(self.output_dir, 'test_optimized.srt')
        optimized_data.save(save_path)
        print(f"Optimized subtitle saved to: {save_path}")
        self.assertTrue(os.path.exists(save_path))

if __name__ == '__main__':
    unittest.main()
