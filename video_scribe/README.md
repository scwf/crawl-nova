# Video Scribe

A standalone, lightweight Python module for video captioning (ASR) and subtitle optimization (LLM), extracted from [VideoCaptioner](https://github.com/WEIFENG2333/VideoCaptioner).

It automatically downloads videos from URLs, transcribes audio using Faster-Whisper, and optionally optimizes subtitles using Large Language Models (LLMs) like OpenAI GPT or DeepSeek.

## Features

- **Automatic Dependency Management**: Automatically downloads `faster-whisper-xxl` and Whisper models (using ModelScope).
- **Flexible Input**: Supports both Video URLs (via `yt-dlp`) and local files.
- **LLM Optimization**: Enhances subtitle quality (fixes typos, punctuation, formatting) using LLMs.
- **Auto Language Detection**: Automatically detects audio source language.
- **GPU Acceleration**: Defaults to CUDA for high performance.
- **Standalone CLI**: Easy-to-use command-line interface.

## Installation

1.  **Clone the repository** (or copy the `video_scribe` folder).
2.  **Install Python Dependencies**:
    ```bash
    pip install -r video_scribe/requirements.txt
    ```
    *Dependencies include: `requests`, `tqdm`, `modelscope`, `yt-dlp`, `openai`, `tenacity`, `json_repair`.*

3.  **Prepare System Dependencies (Optional)**:
    - **7-Zip**: Required for extracting the GPU version of Faster-Whisper.
    - **FFmpeg**: Required by `yt-dlp` for audio extraction.

## CLI Usage

The module comes with a command-line interface `video_scribe/run_video_scribe.py`.

### 1. Transcription

Transcribe a video URL or local file:

```bash
python video_scribe/run_video_scribe.py transcribe "https://www.youtube.com/watch?v=example" --output-dir "output" --device cuda
```

### 2. Optimization

Optimize an existing SRT file using an LLM:

```bash
python video_scribe/run_video_scribe.py optimize "path/to/subtitle.srt" \
  --model gpt-3.5-turbo \
  --api-key "sk-..." \
  --output "path/to/optimized.srt"
```

### 3. Auto Mode (Configuration-based)

Run with pre-configured settings (edit `video_scribe/run_video_scribe.py` to set defaults):

**Auto Transcribe:**
```bash
python video_scribe/run_video_scribe.py auto_transcribe
```

**Auto Optimize:**
```bash
python video_scribe/run_video_scribe.py auto_optimize
```
*Note: Ensure you set your `API_KEY` and file paths in the `run_auto_optimize` function in `video_scribe/run_video_scribe.py` before running.*

## Python API Usage

```python
from video_scribe import process_video, optimize_subtitle

# 1. Transcribe
asr_data = process_video(
    video_url_or_path="https://www.youtube.com/watch?v=example",
    output_dir="output",
    device="cuda"
)

# 2. Optimize
optimized_data = optimize_subtitle(
    subtitle_data=asr_data, # or path to .srt file
    model="gpt-3.5-turbo",
    api_key="sk-...",
    custom_prompt="Context: This is a tech tutorial."
)

# Save results
optimized_data.save("output/optimized.srt")
```

## Directory Structure

```
video_scribe/
├── asr/                # ASR implementations (Faster-Whisper wrapper)
├── bin/                # Downloaded executables
├── models/             # Downloaded Whisper models
├── alignment.py        # Subtitle alignment logic
├── config.py           # Configuration
├── core.py             # Main processing logic
├── data.py             # Data structures
├── downloader.py       # yt-dlp wrapper
├── llm.py              # LLM client (OpenAI compatible)
├── optimize.py         # Optimization logic (Agent loop)
├── prompts.py          # Prompt templates
├── requirements.txt    # Dependencies
├── resource_manager.py # Auto-download logic
└── subprocess_helper.py# Async stream helper
```
