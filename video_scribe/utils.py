import re

def is_mainly_cjk(text: str) -> bool:
    """Check if the text is mainly CJK characters."""
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]')
    cjk_count = len(cjk_pattern.findall(text))
    return cjk_count > len(text) * 0.5

def setup_logger(name: str):
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

# Multi-language word split pattern - simplified for video_scribe context if needed
# But better to use the robust one from app
_NO_SPACE_LANGUAGES = r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u0e00-\u0eff\u1000-\u109f\u1780-\u17ff\u0900-\u0dff]"

def count_words(text: str) -> int:
    """Count words/characters in text."""
    if not text:
        return 0

    # Count chars for no-space languages
    char_count = len(re.findall(_NO_SPACE_LANGUAGES, text))

    # Remove no-space chars and count words for others
    word_text = re.sub(_NO_SPACE_LANGUAGES, " ", text)
    word_count = len(word_text.strip().split())

    return char_count + word_count
