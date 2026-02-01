from ..config import TranscribeConfig
from .base import BaseASR
from .faster_whisper import FasterWhisperASR

def create_asr(audio_path: str, config: TranscribeConfig) -> BaseASR:
    """Factory to create ASR instance."""
    # Currently only supports Faster Whisper
    return FasterWhisperASR(audio_path, config)
