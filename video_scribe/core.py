import os
from typing import Optional, Union

from .data import ASRData
from .config import TranscribeConfig, DEFAULT_MODEL_NAME
from .downloader import download_audio
from .asr.factory import create_asr
from .utils import setup_logger
from .resource_manager import ensure_executable, ensure_model
import glob
import json

logger = setup_logger("core")

def try_download_youtube_subtitles(url: str, output_dir: str, lang: str = "en") -> Optional[str]:
    """
    Try to download YouTube subtitles using yt-dlp.
    Returns path to the downloaded subtitle file (vtt) if successful, else None.
    """
    # Guard: Only attempt for YouTube URLs
    if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
        return None
        
    import subprocess
    
    # Clean output dir patterns first to avoid confusion with old files
    base_pattern = os.path.join(output_dir, "ytsub_temp.*")
    for f in glob.glob(base_pattern):
        try: os.remove(f)
        except: pass
        
    output_template = os.path.join(output_dir, "ytsub_temp.%(ext)s")
    
    # Try manual subs first, then auto-subs
    # Try manual subs first, then auto-subs
    # We use 'srt' format as it's cleaner via yt-dlp conversion
    cmd = [
        "yt-dlp",
        "--skip-download",   # Don't download video
        "--write-subs",      # Try manual subs
        "--write-auto-subs", # Fallback to auto subs
        "--sub-lang", lang,  # Language code
        "--sub-format", "srt", # Enforce srt
        "--output", output_template,
        url
    ]
    
    try:
        logger.info(f"Attempting to download subtitles for {url} ({lang})...")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check if file exists
        # yt-dlp might name it ytsub_temp.en.srt or similar
        potential_files = glob.glob(os.path.join(output_dir, "ytsub_temp.*.srt"))
        if potential_files:
            return potential_files[0]
            
    except Exception as e:
        logger.warning(f"Failed to download subtitles: {e}")
    
    return None

def process_video(
    video_url_or_path: str, 
    output_dir: str, 
    model_path: Optional[str] = None, # Can be None now
    faster_whisper_program: Optional[str] = None, # Can be None now
    device: str = "cuda",
    language: Optional[str] = None # New parameter
):
    """
    Download video from URL (or use local file) and generate subtitles.
    """
    # 0. Prepare Resources
    logger.info("Step 0: Checking resources...")
    exe_path = ensure_executable(faster_whisper_program)
    
    # Check if model_path is provided, else use default. 
    # Also handle auto-download inside ensure_model
    final_model_path = ensure_model(model_path if model_path else DEFAULT_MODEL_NAME)
    
    logger.info(f"Using Executable: {exe_path}")
    logger.info(f"Using Model: {final_model_path}")

    # Step 0.5: Try to get existing YouTube subtitles (Optimization)
    if not os.path.exists(video_url_or_path):
        target_lang = language if language else "en"
        srt_path = try_download_youtube_subtitles(video_url_or_path, output_dir, target_lang)
        
        if srt_path:
            logger.info("Found YouTube subtitles! Skipping audio transcription.")
            try:
                with open(srt_path, "r", encoding="utf-8") as f:
                    asr_data = ASRData.from_srt(f.read())
                
                # We still need a base name for export
                # Since we didn't download video, we use the video ID or a generic name
                # Try to extract video ID from URL simple way
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(video_url_or_path)
                video_id = parse_qs(parsed_url.query).get('v', ['video'])[0]
                
                # Export immediately
                output_base = os.path.join(output_dir, video_id)
                asr_data.save(output_base + ".srt")
                asr_data.save(output_base + ".txt")
                asr_data.save(output_base + ".json")
                
                # Cleanup temp srt
                try: os.remove(srt_path)
                except: pass
                
                logger.info("Done (using existing subtitles)!")
                return asr_data
                
            except Exception as e:
                logger.warning(f"Failed to parse downloaded subtitles: {e}. Falling back to standard transcription.")

    # 1. Download or Use Local
    if os.path.exists(video_url_or_path):
        logger.info(f"Step 1: Using local file: {video_url_or_path}")
        audio_path = video_url_or_path
    else:
        logger.info("Step 1: Downloading audio...")
        audio_path = download_audio(video_url_or_path, output_dir)
    
    # 2. Config
    
    # 2. Config
    config = TranscribeConfig(
        model_path=final_model_path,
        faster_whisper_program=exe_path,
        language=language, 
        device=device,
        output_dir=output_dir
    )
    
    # 3. Transcribe
    logger.info("Step 2: Transcribing...")
    asr = create_asr(audio_path, config)
    
    def progress_callback(progress, msg):
        logger.info(f"Progress: {progress}%")
        
    asr_data = asr.run(callback=progress_callback)
    
    # 4. Export
    logger.info("Step 3: Exporting...")
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    output_base = os.path.join(output_dir, base_name)
    
    asr_data.save(output_base + ".srt")
    asr_data.save(output_base + ".txt")
    asr_data.save(output_base + ".json")
    
    logger.info("Done!")
    return asr_data


def optimize_subtitle(
    subtitle_data: Union[str, ASRData],
    model: str = "gpt-3.5-turbo",
    custom_prompt: str = "",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    thread_num: int = 10,
    batch_num: int = 10
) -> ASRData:
    """Optimize subtitle content using LLM.
    
    Args:
        subtitle_data: Path to subtitle file or ASRData object.
        model: LLM model to use.
        custom_prompt: Context or specific instructions for optimization.
        api_key: OpenAI API Key.
        base_url: OpenAI Base URL.
        thread_num: Number of concurrent threads.
        batch_num: Number of items per batch.
        
    Returns:
        Optimized ASRData object.
    """
    from .optimize import SubtitleOptimizer
    
    optimizer = SubtitleOptimizer(
        thread_num=thread_num,
        batch_num=batch_num,
        model=model,
        custom_prompt=custom_prompt,
        api_key=api_key,
        base_url=base_url
    )
    
    return optimizer.optimize_subtitle(subtitle_data)
