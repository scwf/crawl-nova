"""Subtitle optimization module."""

import atexit
import difflib
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Tuple, Union

import json_repair

from .data import ASRData, ASRDataSeg
from .llm import call_llm
from .prompts import get_prompt
from .alignment import SubtitleAligner
from .utils import setup_logger, count_words

logger = setup_logger("subtitle_optimizer")

MAX_STEPS = 3


class SubtitleOptimizer:
    """Subtitle Optimizer
    
    Optimizes subtitle content using LLM with support for:
    - Agent loop for automatic validation and correction
    - Concurrent batch processing
    - Automatic alignment repair
    """

    def __init__(
        self,
        thread_num: int,
        batch_num: int,
        model: str,
        custom_prompt: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        update_callback: Optional[Callable] = None,
    ):
        """Initialize optimizer
        
        Args:
            thread_num: Number of concurrent threads
            batch_num: Number of subtitles per batch
            model: LLM model name
            custom_prompt: Custom optimization prompt
            api_key: OpenAI API key
            base_url: OpenAI Base URL
            update_callback: Progress update callback
        """
        self.thread_num = thread_num
        self.batch_num = batch_num
        self.model = model
        self.custom_prompt = custom_prompt
        self.api_key = api_key
        self.base_url = base_url
        self.update_callback = update_callback

        self.is_running = True
        self.executor: Optional[ThreadPoolExecutor] = None
        self._init_thread_pool()

    def _init_thread_pool(self) -> None:
        """Initialize thread pool and register cleanup function"""
        self.executor = ThreadPoolExecutor(max_workers=self.thread_num)
        atexit.register(self.stop)

    def optimize_subtitle(self, subtitle_data: Union[str, ASRData]) -> ASRData:
        """Optimize subtitle
        
        Args:
            subtitle_data: Subtitle file path or ASRData object
            
        Returns:
            Optimized ASRData object
        """
        try:
            # Read subtitle
            if isinstance(subtitle_data, str):
                # ASRData.from_subtitle_file is not implemented in video_scribe yet, 
                # assuming input is ASRData or rely on existing from_srt if path is srt?
                # For now let's assume specific format or implement loading
                if subtitle_data.lower().endswith(".srt"):
                     with open(subtitle_data, "r", encoding="utf-8") as f:
                        asr_data = ASRData.from_srt(f.read())
                else:
                    raise NotImplementedError("Only SRT file path or ASRData object is supported")
            else:
                asr_data = subtitle_data

            # Convert to dictionary format
            subtitle_dict = {
                str(i): seg.text for i, seg in enumerate(asr_data.segments, 1)
            }

            # Split into chunks
            chunks = self._split_chunks(subtitle_dict)

            # Parallel optimize
            optimized_dict = self._parallel_optimize(chunks)

            # Create new segments
            new_segments = self._create_segments(asr_data.segments, optimized_dict)

            return ASRData(new_segments)

        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            raise RuntimeError(f"Optimization failed: {str(e)}")

    def _split_chunks(self, subtitle_dict: Dict[str, str]) -> List[Dict[str, str]]:
        """Split subtitle dictionary into chunks"""
        items = list(subtitle_dict.items())
        return [
            dict(items[i : i + self.batch_num])
            for i in range(0, len(items), self.batch_num)
        ]

    def _parallel_optimize(self, chunks: List[Dict[str, str]]) -> Dict[str, str]:
        """Parallel optimize all chunks"""
        if not self.executor:
            raise ValueError("Thread pool not initialized")

        futures = []
        optimized_dict: Dict[str, str] = {}

        # Submit all tasks
        for chunk in chunks:
            future = self.executor.submit(self._optimize_chunk, chunk)
            futures.append((future, chunk))

        # Collect results
        for future, chunk in futures:
            if not self.is_running:
                break

            try:
                result = future.result()
                optimized_dict.update(result)
            except Exception as e:
                logger.error(f"Batch optimization failed: {str(e)}")
                optimized_dict.update(chunk)  # Keep original on failure

        return optimized_dict

    def _optimize_chunk(self, subtitle_chunk: Dict[str, str]) -> Dict[str, str]:
        """Optimize single subtitle chunk"""
        start_idx = next(iter(subtitle_chunk))
        end_idx = next(reversed(subtitle_chunk))
        logger.info(f"Optimizing subtitles: {start_idx} - {end_idx}")

        try:
            result = self.agent_loop(subtitle_chunk)

            if self.update_callback:
                # Need a simple data structure for callback if SubtitleProcessData is not available
                # Or just pass raw data
                # Assuming video_scribe doesn't need complex callback data types yet
                pass

            return result

        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            return subtitle_chunk

    def agent_loop(self, subtitle_chunk: Dict[str, str]) -> Dict[str, str]:
        """Use agent loop to optimize subtitles
        
        LLM -> Validate -> Feedback -> Retry (Max MAX_STEPS)
        """
        # Build prompt
        user_prompt = (
            f"Correct the following subtitles. Keep the original language, do not translate:\n"
            f"<input_subtitle>{str(subtitle_chunk)}</input_subtitle>"
        )

        if self.custom_prompt:
            user_prompt += (
                f"\nReference content:\n<reference>{self.custom_prompt}</reference>"
            )

        messages = [
            {"role": "system", "content": get_prompt("optimize/subtitle")},
            {"role": "user", "content": user_prompt},
        ]

        last_result = None

        # Agent loop
        for step in range(MAX_STEPS):
            # Call LLM
            response = call_llm(
                messages=messages,
                model=self.model,
                temperature=0.2,
                api_key=self.api_key,
                base_url=self.base_url
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise ValueError("LLM returned empty result")

            # Parse result
            parsed_result = json_repair.loads(result_text)
            if not isinstance(parsed_result, dict):
                raise ValueError(
                    f"LLM returned wrong type, expected dict, got {type(parsed_result)}"
                )

            result_dict: Dict[str, str] = parsed_result
            last_result = result_dict

            # Validate result
            is_valid, error_message = self._validate_optimization_result(
                original_chunk=subtitle_chunk, optimized_chunk=result_dict
            )

            if is_valid:
                return self._repair_subtitle(subtitle_chunk, result_dict)

            # Validation failed, add feedback
            logger.warning(
                f"Optimization validation failed, retrying (Step {step + 1}): {error_message}"
            )
            messages.append({"role": "assistant", "content": result_text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Validation failed: {error_message}\n"
                        f"Please fix the errors and output ONLY a valid JSON dictionary."
                    ),
                }
            )

        # Reached max steps
        logger.warning(f"Reached max attempts ({MAX_STEPS}), returning last result")
        return (
            self._repair_subtitle(subtitle_chunk, last_result)
            if last_result
            else subtitle_chunk
        )

    def _validate_optimization_result(
        self, original_chunk: Dict[str, str], optimized_chunk: Dict[str, str]
    ) -> Tuple[bool, str]:
        """Validate optimization result"""
        expected_keys = set(original_chunk.keys())
        actual_keys = set(optimized_chunk.keys())

        # Check key match
        if expected_keys != actual_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys

            error_parts = []
            if missing:
                error_parts.append(f"Missing keys: {sorted(missing)}")
            if extra:
                error_parts.append(f"Extra keys: {sorted(extra)}")

            error_msg = (
                "\n".join(error_parts) + f"\nRequired keys: {sorted(expected_keys)}\n"
                f"Please return the COMPLETE optimized dictionary with ALL {len(expected_keys)} keys."
            )
            return False, error_msg

        # Check for excessive changes (similarity < threshold)
        excessive_changes = []
        for key in expected_keys:
            original_text = original_chunk[key]
            optimized_text = optimized_chunk.get(key, "")

            # Clean text for comparison
            original_cleaned = re.sub(r"\s+", " ", original_text).strip()
            optimized_cleaned = re.sub(r"\s+", " ", optimized_text).strip()

            # Calculate similarity
            matcher = difflib.SequenceMatcher(None, original_cleaned, optimized_cleaned)
            similarity = matcher.ratio()
            similarity_threshold = 0.3 if count_words(original_text) <= 10 else 0.7

            # Low similarity
            if similarity < similarity_threshold:
                excessive_changes.append(
                    f"Key '{key}': similarity {similarity:.1%} < {similarity_threshold:.0%}. "
                    f"Original: '{original_text}' -> Optimized: '{optimized_text}' "
                )

        if excessive_changes:
            error_msg = ";\n".join(excessive_changes)
            error_msg += (
                "\n\nYour optimizations changed the text too much. "
                "Keep high similarity (>=70% for normal text) by making MINIMAL changes: "
                "only fix recognition errors and improve clarity, "
                "but preserve the original wording, length and structure as much as possible."
            )
            return False, error_msg

        return True, ""

    @staticmethod
    def _repair_subtitle(
        original: Dict[str, str], optimized: Dict[str, str]
    ) -> Dict[str, str]:
        """Repair subtitle alignment"""
        try:
            aligner = SubtitleAligner()
            original_list = list(original.values())
            optimized_list = list(optimized.values())

            aligned_source, aligned_target = aligner.align_texts(
                original_list, optimized_list
            )

            if len(aligned_source) != len(aligned_target):
                logger.warning("Alignment length mismatch, returning original optimized result")
                return optimized

            # Rebuild dictionary maintaining original indices
            start_id = next(iter(original.keys()))
            return {
                str(int(start_id) + i): text for i, text in enumerate(aligned_target)
            }

        except Exception as e:
            logger.error(f"Alignment failed: {str(e)}, returning original optimized result")
            return optimized

    @staticmethod
    def _create_segments(
        original_segments: List[ASRDataSeg],
        optimized_dict: Dict[str, str],
    ) -> List[ASRDataSeg]:
        """Create new ASRDataSeg list from optimized dictionary"""
        return [
            ASRDataSeg(
                text=optimized_dict.get(str(i), seg.text),
                start_time=seg.start_time,
                end_time=seg.end_time,
            )
            for i, seg in enumerate(original_segments, 1)
        ]

    def stop(self) -> None:
        """Stop optimizer and cleanup resources"""
        if not self.is_running:
            return

        self.is_running = False

        if self.executor:
            try:
                self.executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            finally:
                self.executor = None
