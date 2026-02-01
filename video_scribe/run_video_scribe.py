import os
import sys
import argparse
from pathlib import Path

# Ensure the root directory (parent of video_scribe) is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_scribe import process_video, optimize_subtitle

def run_transcribe(args):
    print(f"Processing {args.input}...")
    try:
        process_video(
            video_url_or_path=args.input,
            output_dir=args.output_dir,
            device=args.device,
            language=args.language,
            model_path=args.model_path,
            faster_whisper_program=args.fw_path
        )
        print(f"Success! Check {args.output_dir}/")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def run_optimize(args):
    print(f"Optimizing {args.input}...")
    try:
        if not os.path.exists(args.input):
            print(f"Error: File {args.input} not found.")
            return

        optimized_data = optimize_subtitle(
            subtitle_data=args.input,
            model=args.model,
            custom_prompt=args.prompt,
            api_key=args.api_key,
            base_url=args.base_url,
            thread_num=args.threads,
            batch_num=args.batch_size
        )
        
        # Determine output path
        output_path = args.output
        if not output_path:
            p = Path(args.input)
            # Default to saving as SRT with _optimized suffix if input was srt
            suffix = p.suffix if p.suffix else ".srt"
            output_path = str(p.with_name(p.stem + "_optimized" + suffix))
            
        print(f"Saving to {output_path}...")
        optimized_data.save(output_path)
        print(f"Optimization successful! Saved to {output_path}")
        
    except Exception as e:
        print(f"Error during optimization: {e}")
        import traceback
        traceback.print_exc()

def run_auto_transcribe(args):
    """Run transcription with hardcoded default parameters."""
    print("Running in AUTO TRANSCRIBE mode with default parameters...")
    
    # --- Configuration for AUTO TRANSCRIBE mode ---
    VIDEO_URL = "https://www.youtube.com/watch?v=iZVfuco1L7U" # Me at the zoo (short video)
    OUTPUT_DIR = "test_output"
    DEVICE = "cuda" 
    # ----------------------------------------------
    
    print(f"Processing {VIDEO_URL}...")
    try:
        process_video(
            video_url_or_path=VIDEO_URL,
            output_dir=OUTPUT_DIR,
            device=DEVICE,
            language=None # Use auto-detection
        )
        print(f"Success! Check {OUTPUT_DIR}/")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def run_auto_optimize(args):
    """Run optimization with hardcoded default parameters."""
    print("Running in AUTO OPTIMIZE mode with default parameters...")

    # --- Configuration for AUTO OPTIMIZE mode ---
    # Assuming the transcription output creates an SRT in test_output
    # You might want to update this to point to a valid existing file for testing
    SRT_FILE = r"D:\code\VideoCaptioner\test_output\UK Power Networks Manages Smarter Grids with Databricks and Unity Catalog.srt"
    OUTPUT_PATH = os.path.normpath("test_output/UK Power Networks Manages Smarter Grids with Databricks and Unity Catalog_optimized.srt")
    

    CUSTOM_PROMPT = """
    这个字幕文件的背景信息是：
    UK Power Networks delivers electricity to around 8 million customers across London, the East and South of England. As electric vehicles and hybrid work change when and where people use power, the grid has become far less predictable, making detailed, timely data essential.
    
    With Databricks, the company moved from a traditional data warehouse to a modern platform where teams can store, analyze and experiment with data using AI and machine learning. Unity Catalog governs access to everything from asset conditions and maintenance history to customer vulnerabilities, so only the right people see the right data at the right level.
    
    Working in a single, shared environment makes it easier for the data team to collaborate rather than stitching together three or four separate tools. They can now explore new AI use cases, turn experiments into real products faster and give the business sharper insight into changing demand, helping UK Power Networks run a more efficient and resilient electricity network.
    """
    THREADS = 4
    BATCH_SIZE = 10
    # --------------------------------------------

    if not os.path.exists(SRT_FILE):
        print(f"Error: Input SRT file '{SRT_FILE}' not found.")
        print("Please run 'auto_transcribe' first or update SRT_FILE path in run_video_scribe.py")
        return

    try:
         print(f"Optimizing {SRT_FILE}...")
         optimized_data = optimize_subtitle(
            subtitle_data=SRT_FILE,
            model="deepseek-reasoner",
            custom_prompt=CUSTOM_PROMPT,
            api_key="sk-xxxxx",
            base_url="https://api.deepseek.com/v1",
            thread_num=THREADS,
            batch_num=BATCH_SIZE
        )
         
         print(f"Saving to {OUTPUT_PATH}...")
         optimized_data.save(OUTPUT_PATH)
         print(f"Optimization successful! Saved to {OUTPUT_PATH}")
    except Exception as e:
        print(f"Error during optimization: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Video Captioning and Optimization Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Transcribe command
    parser_transcribe = subparsers.add_parser("transcribe", help="Transcribe video/audio to subtitles")
    parser_transcribe.add_argument("input", help="Input video URL or file path")
    parser_transcribe.add_argument("--output-dir", "-o", default="output", help="Output directory")
    parser_transcribe.add_argument("--device", "-d", default="cuda", help="Device (cuda or cpu)")
    parser_transcribe.add_argument("--language", "-l", help="Language code (e.g. zh, en), default auto-detect")
    parser_transcribe.add_argument("--model-path", help="Path to Faster Whisper model")
    parser_transcribe.add_argument("--fw-path", help="Path to Faster Whisper executable")
    
    # Optimize command
    parser_optimize = subparsers.add_parser("optimize", help="Optimize subtitles using LLM")
    parser_optimize.add_argument("input", help="Input SRT file path")
    parser_optimize.add_argument("--output", "-o", help="Output file path")
    parser_optimize.add_argument("--model", "-m", default="gpt-3.5-turbo", help="LLM model name")
    parser_optimize.add_argument("--api-key", help="OpenAI API Key (or set OPENAI_API_KEY env)")
    parser_optimize.add_argument("--base-url", help="OpenAI Base URL (or set OPENAI_BASE_URL env)")
    parser_optimize.add_argument("--prompt", default="", help="Custom prompt for optimization")
    parser_optimize.add_argument("--threads", type=int, default=4, help="Number of concurrent threads")
    parser_optimize.add_argument("--batch-size", type=int, default=10, help="Batch size for optimization")
    
    # Auto Transcribe command
    subparsers.add_parser("auto_transcribe", help="Run transcription with hardcoded parameters")
    
    # Auto Optimize command
    subparsers.add_parser("auto_optimize", help="Run optimization with hardcoded parameters")

    args = parser.parse_args()
    
    if args.command == "transcribe":
        run_transcribe(args)
    elif args.command == "optimize":
        run_optimize(args)
    elif args.command == "auto_transcribe":
        run_auto_transcribe(args)
    elif args.command == "auto_optimize":
        run_auto_optimize(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
