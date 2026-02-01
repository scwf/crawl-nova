from typing import Callable, Optional
from ..data import ASRData

class BaseASR:
    def __init__(self, audio_input: str):
        self.audio_input = audio_input

    def run(self, callback: Optional[Callable[[int, str], None]] = None) -> ASRData:
        raise NotImplementedError
