import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional, List

from ..config import TranscribeConfig
from ..data import ASRData
from .base import BaseASR
from ..subprocess_helper import StreamReader
from ..utils import setup_logger

logger = setup_logger("faster_whisper")

class FasterWhisperASR(BaseASR):
    def __init__(self, audio_input: str, config: TranscribeConfig):
        super().__init__(audio_input)
        self.config = config
        self.process = None

    def _build_command(self, audio_input: str) -> List[str]:
        model_arg = self.config.model_path
        model_dir_arg = None
        
        # Handle absolute model path by splitting into name and directory
        # Example: 
        #   Input: "D:\models\faster-whisper-large-v3"
        #   Result: 
        #     model_arg = "large-v3" (passed to -m)
        #     model_dir_arg = "D:\models" (passed to --model_dir)
        #   This is required because faster-whisper-xxl automatically prepends 'faster-whisper-' 
        #   to the model name and looks inside --model_dir.
        if model_arg and os.path.isabs(str(model_arg)):
            path_obj = Path(model_arg)
            if path_obj.exists():
                folder_name = path_obj.name
                if folder_name.startswith("faster-whisper-"):
                    model_arg = folder_name.replace("faster-whisper-", "", 1)
                else:
                    model_arg = folder_name
                
                cmd_model_dir = str(path_obj.parent)
                model_dir_arg = cmd_model_dir

        cmd = [
            str(self.config.faster_whisper_program),
            "-m", str(model_arg),
            "--print_progress",
            str(audio_input),
            "-d", self.config.device,
            "--output_format", "srt",
            "-o", "source"
        ]
        
        if self.config.language:
            cmd.extend(["-l", self.config.language])
        
        if model_dir_arg:
            cmd.extend(["--model_dir", model_dir_arg])

        if self.config.vad_filter:
            cmd.extend([
                "--vad_filter", "true",
                "--vad_threshold", f"{self.config.vad_threshold:.2f}"
            ])
        else:
             cmd.extend(["--vad_filter", "false"])

        if self.config.prompt:
            cmd.extend(["--initial_prompt", self.config.prompt])

        cmd.extend(["--beep_off"])
        return cmd

    def run(self, callback: Optional[Callable[[int, str], None]] = None) -> ASRData:
        if not callback:
            def callback(p, m): pass

        with tempfile.TemporaryDirectory() as temp_path:
            # We assume input is a file path
            temp_dir = Path(temp_path)
            # Ensure we work with a wav file if possible, or just pass the path
            # The original code copys to temp, let's do that for safety
            wav_path = temp_dir / "audio.wav"
            shutil.copy2(self.audio_input, wav_path)
            
            # Output will be audio.srt in the same dir (since -o source) 
            # OR we specify output dir via command but if we use temp dir we want to capture it there.
            # Original code uses "-o source" which means output to same dir as input.
            output_srt_path = wav_path.with_suffix(".srt")

            cmd = self._build_command(str(wav_path))
            logger.info(f"Running command: {' '.join(cmd)}")

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            reader = StreamReader(self.process)
            reader.start_reading()

            is_finish = False
            last_progress = 0

            while True:
                if self.process.poll() is not None:
                     # Process finished
                    for _, line in reader.get_remaining_output():
                        line = line.strip()
                        if line: logger.info(line)
                    break

                output = reader.get_output(timeout=0.1)
                if output:
                    _, line = output
                    line = line.strip()
                    if line:
                        if match := re.search(r"(\d+)%", line):
                            progress = int(match.group(1))
                            if progress == 100: is_finish = True
                            if progress > last_progress:
                                last_progress = progress
                                callback(progress, f"{progress}%")
                            
                        logger.info(line)
            
            if not output_srt_path.exists():
                raise RuntimeError("ASR failed to generate subtitle file.")

            srt_content = output_srt_path.read_text(encoding="utf-8")
            return ASRData.from_srt(srt_content)
