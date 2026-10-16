"""Script generation: topic -> professional narration script, duration-aware."""
from .base import LLMProvider, generate_script
from .splitter import Scene, split_script, words_for_duration

__all__ = ["LLMProvider", "generate_script", "Scene", "split_script", "words_for_duration"]
