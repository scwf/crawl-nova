import json
import math
import os
import platform
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .utils import is_mainly_cjk

# Multi-language word split pattern
_WORD_SPLIT_PATTERN = (
    r"[a-zA-Z\u00c0-\u00ff\u0100-\u017f']+"  # Latin
    r"|[\u0400-\u04ff]+"  # Cyrillic
    r"|[\u0370-\u03ff]+"  # Greek
    r"|[\u0600-\u06ff]+"  # Arabic
    r"|[\u0590-\u05ff]+"  # Hebrew
    r"|\d+"  # Digits
    r"|[\u4e00-\u9fff]"  # CJK
    r"|[\u3040-\u309f]"  # Hiragana
    r"|[\u30a0-\u30ff]"  # Katakana
    r"|[\uac00-\ud7af]"  # Korean
)

def handle_long_path(path: str) -> str:
    if platform.system() == "Windows" and len(path) > 260 and not path.startswith(r"\\?\ "):
        return rf"\\?\{os.path.abspath(path)}"
    return path

class ASRDataSeg:
    def __init__(self, text: str, start_time: int, end_time: int, translated_text: str = ""):
        self.text = text
        self.translated_text = translated_text
        self.start_time = start_time
        self.end_time = end_time

    def to_srt_ts(self) -> str:
        return f"{self._ms_to_srt_time(self.start_time)} --> {self._ms_to_srt_time(self.end_time)}"

    @staticmethod
    def _ms_to_srt_time(ms: int) -> str:
        total_seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(milliseconds):03}"

class ASRData:
    def __init__(self, segments: List[ASRDataSeg]):
        self.segments = [seg for seg in segments if seg.text and seg.text.strip()]
        self.segments.sort(key=lambda x: x.start_time)

    def save(self, save_path: str):
        save_path = handle_long_path(save_path)
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        if save_path.endswith(".srt"):
            self.to_srt(save_path=save_path)
        elif save_path.endswith(".txt"):
            self.to_txt(save_path=save_path)
        elif save_path.endswith(".json"):
             with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.to_json(), f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {save_path}")

    def to_txt(self, save_path=None) -> str:
        text = "\n".join([seg.text for seg in self.segments])
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
        return text

    def to_srt(self, save_path=None) -> str:
        srt_lines = []
        for n, seg in enumerate(self.segments, 1):
            srt_lines.append(f"{n}\n{seg.to_srt_ts()}\n{seg.text}\n")
        srt_text = "\n".join(srt_lines)
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(srt_text)
        return srt_text

    def to_json(self) -> dict:
        result = {}
        for i, seg in enumerate(self.segments, 1):
            result[str(i)] = {
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "text": seg.text
            }
        return result

    @staticmethod
    def from_srt(srt_str: str) -> "ASRData":
        segments = []
        srt_time_pattern = re.compile(
            r"(\d{2}):(\d{2}):(\d{1,2})[.,](\d{3})\s-->\s(\d{2}):(\d{2}):(\d{1,2})[.,](\d{3})"
        )
        blocks = re.split(r"\n\s*\n", srt_str.strip())
        
        for block in blocks:
            lines = block.splitlines()
            if len(lines) < 3: continue
            
            match = srt_time_pattern.match(lines[1])
            if not match: continue
            
            time_parts = list(map(int, match.groups()))
            start_time = time_parts[0]*3600000 + time_parts[1]*60000 + time_parts[2]*1000 + time_parts[3]
            end_time = time_parts[4]*3600000 + time_parts[5]*60000 + time_parts[6]*1000 + time_parts[7]
            
            text = " ".join(lines[2:])
            segments.append(ASRDataSeg(text, start_time, end_time))
            
        return ASRData(segments)
