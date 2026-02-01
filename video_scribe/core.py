import os
from typing import Optional, Union

from .data import ASRData
from .config import TranscribeConfig, DEFAULT_MODEL_NAME
from .downloader import download_audio
from .asr.factory import create_asr
from .utils import setup_logger
from .resource_manager import ensure_executable, ensure_model

logger = setup_logger("core")

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
    thread_num: int = 4,
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
