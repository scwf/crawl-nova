import os
import sys
import zipfile
import requests
from pathlib import Path
from tqdm import tqdm

from .utils import setup_logger
from .config import DEFAULT_BIN_DIR, DEFAULT_MODEL_DIR, FASTER_WHISPER_XXL_URL

logger = setup_logger("resource_manager")

def download_file(url: str, save_path: str):
    """Download a file with progress bar."""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 # 1KB
        
        with open(save_path, 'wb') as f, tqdm(
            desc=os.path.basename(save_path),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(block_size):
                size = f.write(data)
                bar.update(size)
                
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        if os.path.exists(save_path):
            os.remove(save_path)
        raise e

def ensure_executable(program_path: str = None) -> str:
    """
    Ensure faster-whisper-xxl executable exists.
    If program_path is provided, checks if it exists.
    If not, checks default location or downloads it.
    """
    if program_path and os.path.exists(program_path):
        return program_path
    
    # Check default location
    default_exe = os.path.join(DEFAULT_BIN_DIR, "faster-whisper-xxl.exe")
    if os.path.exists(default_exe):
        return default_exe
    
    # Check GPU version location (in subdirectory)
    gpu_exe = os.path.join(DEFAULT_BIN_DIR, "Faster-Whisper-XXL", "faster-whisper-xxl.exe")
    if os.path.exists(gpu_exe):
        return gpu_exe
    
    # Download
    logger.info(f"faster-whisper-xxl not found at {default_exe}. Downloading...")
    
    # Determine filename from URL
    filename = FASTER_WHISPER_XXL_URL.split("/")[-1]
    download_path = os.path.join(DEFAULT_BIN_DIR, filename)
    
    try:
        if not os.path.exists(download_path):
             download_file(FASTER_WHISPER_XXL_URL, download_path)
        
        # Extract if it's a 7z archive
        if download_path.endswith(".7z"):
            logger.info("Extracting 7z archive using system 7z...")
            import subprocess
            try:
                subprocess.run(
                    ["7z", "x", download_path, f"-o{DEFAULT_BIN_DIR}", "-y"], 
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.error(f"Extraction failed: {e}. Please ensure '7z' is installed and in your PATH.")
                raise RuntimeError("Failed to extract 7z archive. Please install 7-Zip.")
            
            # Cleanup archive? Maybe keep it for cache.
            # After extraction, the exe should be at .../Faster-Whisper-XXL/faster-whisper-xxl.exe
            # We need to find it and maybe move it or return that path.
            extracted_subdir = os.path.join(DEFAULT_BIN_DIR, "Faster-Whisper-XXL", "faster-whisper-xxl.exe")
            if os.path.exists(extracted_subdir):
                return extracted_subdir
            
            # Some archives extract directly, check again default location
            if os.path.exists(default_exe):
                return default_exe

        # If it was an exe download (CPU version)
        if download_path.endswith(".exe"):
             # Rename if needed or just return it
             if download_path != default_exe:
                 if os.path.exists(default_exe): os.remove(default_exe)
                 os.rename(download_path, default_exe)
             return default_exe

        return default_exe
    except Exception as e:
        logger.warning(f"Automatic download/extraction failed: {e}")
        raise RuntimeError("Could not setup faster-whisper-xxl.")

def ensure_model(model_name: str = "tiny") -> str:
    """
    Check if model exists locally, else download using ModelScope or HuggingFace.
    Returns the absolute path to the model directory.
    """
    # Check if user provided a full path
    if os.path.exists(model_name):
        return model_name
        
    model_dir = os.path.join(DEFAULT_MODEL_DIR, f"faster-whisper-{model_name}")
    if os.path.exists(model_dir) and os.listdir(model_dir):
        return model_dir
        
    logger.info(f"Model {model_name} not found locally. Downloading to {model_dir}...")
    
    # Try using modelscope first (faster in China)
    try:
        from modelscope import snapshot_download
        logger.info("Using ModelScope for download...")
        # Map simple names to modelscope IDs if necessary. 
        # For faster-whisper, there are mirrors usually. 
        # Example: "pengzhendong/faster-whisper-tiny"
        ms_model_id = f"pengzhendong/faster-whisper-{model_name}"
        
        path = snapshot_download(ms_model_id, local_dir=model_dir)
        return path
    except ImportError:
        logger.warning("modelscope not installed. Install with `pip install modelscope` for faster downloads.")
    except Exception as e:
        logger.warning(f"ModelScope download failed: {e}")

    # Fallback to faster_whisper library's download logic?
    # Or just use huggingface_hub
    try:
        from huggingface_hub import snapshot_download
        logger.info("Using HuggingFace for download...")
        hf_model_id = f"Systran/faster-whisper-{model_name}"
        path = snapshot_download(repo_id=hf_model_id, local_dir=model_dir)
        return path
    except ImportError:
         pass
         
    raise RuntimeError(
        f"Could not auto-download model '{model_name}'. \n"
        "Please install 'modelscope' or 'huggingface_hub', \n"
        "or manually download the model to 'video_scribe/models/'."
    )
