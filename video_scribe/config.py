from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class TranscribeConfig:
    """Simplified transcription configuration."""
    model_path: Optional[str] = None # Name (e.g. "tiny") or Path
    faster_whisper_program: Optional[str] = None # Path to executable
    language: Optional[str] = None # None for auto-detection
    device: str = "cuda"
    output_dir: Optional[str] = None
    vad_filter: bool = True
    vad_threshold: float = 0.5
    prompt: Optional[str] = None

# Default paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_DIR = os.path.join(BASE_DIR, "models")
DEFAULT_BIN_DIR = os.path.join(BASE_DIR, "bin")

# Default Models
DEFAULT_MODEL_NAME = "large-v2"

# Download URLs
# CPU Version (Lightweight, ~80MB, single exe)
FASTER_WHISPER_CPU_URL = "https://modelscope.cn/models/bkfengg/whisper-cpp/resolve/master/whisper-faster.exe"

# GPU Version (Heavy, ~1.35GB, 7z archive, requires 7z to extract)
FASTER_WHISPER_GPU_URL = "https://modelscope.cn/models/bkfengg/whisper-cpp/resolve/master/Faster-Whisper-XXL_r245.2_windows.7z"

# Default to GPU version as requested
FASTER_WHISPER_XXL_URL = FASTER_WHISPER_GPU_URL
