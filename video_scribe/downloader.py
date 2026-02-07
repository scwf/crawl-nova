import os
from pathlib import Path
import yt_dlp
from .utils import setup_logger

logger = setup_logger("downloader")

def download_audio(url: str, output_dir: str) -> str:
    """Download audio from YouTube URL and return the file path."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Downloading audio from {url}...")
        try:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # yt-dlp with postprocessor changes extension
            final_filename = Path(filename).with_suffix('.wav')
            logger.info(f"Downloaded to {final_filename}")
            return str(final_filename)
        except yt_dlp.utils.DownloadError as e:
            err_msg = str(e).lower()
            if "live event" in err_msg or "begin in" in err_msg or "premiere" in err_msg:
                logger.warning(f"Skipping upcoming live event: {url}")
                return None
            raise e
