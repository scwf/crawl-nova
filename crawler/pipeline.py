"""
pipeline.py - Main Entry Point and Coordinator for Native Python Pipeline.
"""
import os
import time
import queue
import configparser
from datetime import datetime

from common import setup_logger
from stages.source_fetcher import FetcherStage
from stages.content_enricher import EnricherStage
from stages.llm_organizer import OrganizerStage
from stages.result_writer import WriterStage

logger = setup_logger("pipeline")

class NativePipeline:
    def __init__(self, config, batch_timestamp, output_dir):
        self.config = config
        self.batch_timestamp = batch_timestamp
        self.output_dir = output_dir
        
        # Queues
        self.fetch_queue = queue.Queue(maxsize=1000)
        self.enrich_queue = queue.Queue(maxsize=1000)
        self.write_queue = queue.Queue(maxsize=1000)
        
        # Stages
        self.fetcher = FetcherStage(self.fetch_queue, config, batch_timestamp)
        self.enricher = EnricherStage(self.fetch_queue, self.enrich_queue, config, batch_timestamp)
        self.organizer = OrganizerStage(self.enrich_queue, self.write_queue, config)
        self.writer = WriterStage(self.write_queue, output_dir, batch_timestamp)

    def run(self, rss_sources):
        start_time = time.time()
        logger.info(f"🔥 Starting Pipeline Batch: {self.batch_timestamp}")
        
        # 1. Start Consumers (Downstream to Upstream)
        self.writer.start()
        self.organizer.start()
        self.enricher.start()
        
        # 2. Start Producer
        self.fetcher.start(rss_sources)
        
        # 3. Cascading Shutdown (The Coordinator Logic)
        
        # Wait for Fetcher to finish all tasks
        self.fetcher.join()
        
        # Stop Enricher (sends poison pills to itself)
        self.enricher.stop()
        
        # Stop Organizer
        self.organizer.stop()
        
        # Stop Writer
        self.writer.stop()
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Pipeline Finished in {elapsed:.2f}s")

# ================= Configuration Loading =================

def _load_config():
    config = configparser.ConfigParser()
    config.optionxform = str
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config-test.ini')
    config.read(config_path, encoding='utf-8')
    return config

def _load_sources(config):
    def load_weixin():
        accs = {}
        if config.has_section('weixin_accounts'):
            for k in config.options('weixin_accounts'):
                v = config.get('weixin_accounts', k).strip()
                if v: accs[k] = v
        return accs

    def load_x():
        accs = {}
        rsshub_base = config.get('rsshub', 'base_url', fallback='http://127.0.0.1:1200')
        if config.has_section('x_accounts'):
            for k in config.options('x_accounts'):
                v = config.get('x_accounts', k).strip()
                if v: accs[k] = f"{rsshub_base}/twitter/user/{v}"
        return accs

    def load_youtube():
        accs = {}
        if config.has_section('youtube_channels'):
            for k in config.options('youtube_channels'):
                v = config.get('youtube_channels', k).strip()
                if v: accs[k] = f"https://www.youtube.com/feeds/videos.xml?channel_id={v}"
        return accs

    return {
        "weixin": load_weixin(),
        "X": load_x(),
        "YouTube": load_youtube(),
    }

if __name__ == "__main__":
    # Setup
    config = _load_config()
    batch_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    # Load Sources
    sources = _load_sources(config)
    total_sources = sum(len(v) for v in sources.values())
    breakdown = ", ".join([f"{k}: {len(v)}" for k, v in sources.items()])
    logger.info(f"Loaded {total_sources} sources ({breakdown}).")
    
    # Run
    pipeline = NativePipeline(config, batch_ts, output_dir)
    pipeline.run(sources)
