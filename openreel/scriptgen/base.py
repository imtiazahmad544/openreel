"""LLM provider interface + shared generation logic."""
from __future__ import annotations

import time
from dataclasses import dataclass

from ..config import Settings

WORDS_PER_MINUTE = 150  # average narration pace


@dataclass
class LLMProvider:
    """Base class. Subclasses implement `complete(prompt) -> str`."""
    settings: Settings

    name: str = "base"

    def complete(self, prompt: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def complete_retry(self, prompt: str) -> str:
        last: Exception | None = None
        for attempt in range(self.settings.retries):
            try:
                return self.complete(prompt)
            except Exception as exc:  # noqa: BLE001 - provider agnostic
                last = exc
                time.sleep(2 ** attempt)
        raise RuntimeError(f"LLM provider '{self.name}' failed after retries") from last


SCRIPT_SYSTEM = (
    "You are a professional YouTube scriptwriter. Write narration-ready scripts: "
    "spoken language, no stage directions, no [brackets], no markdown headings. "
    "Short punchy sentences. Open with a hook in the first 15 seconds."
)


def build_script_prompt(topic: str, target_words: int, style: str = "documentary") -> str:
    return (
        f"{SCRIPT_SYSTEM}\n\n"
        f"Write a complete {style}-style YouTube narration script about: {topic}\n"
        f"Target length: about {target_words} words ({target_words // WORDS_PER_MINUTE} minutes of narration). "
        f"Structure it as flowing paragraphs separated by blank lines — each paragraph "
        f"will become one video scene, so keep paragraphs focused on a single visual idea. "
        f"End with a call to action (like/subscribe)."
    )


def get_provider(settings: Settings) -> LLMProvider:
    from .pollinations import PollinationsProvider
    from .gemini import GeminiProvider
    from .ollama import OllamaProvider
    from .echo import EchoProvider

    mapping = {
        "pollinations": PollinationsProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
        "echo": EchoProvider,
    }
    cls = mapping.get(settings.llm.lower(), PollinationsProvider)
    return cls(settings)


def generate_script(topic: str, duration_minutes: float, settings: Settings,
                    style: str = "documentary") -> str:
    """Topic -> full narration script sized for the requested duration."""
    from .splitter import words_for_duration
    target = words_for_duration(duration_minutes)
    provider = get_provider(settings)
    return provider.complete_retry(build_script_prompt(topic, target, style)).strip()
