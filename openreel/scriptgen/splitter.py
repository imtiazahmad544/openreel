"""Duration-aware script splitting: narration text -> timed scenes."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .base import WORDS_PER_MINUTE

# One scene ~ 20-45 s of narration; visuals change at this cadence.
WORDS_PER_SCENE = 75
MIN_SCENE_WORDS = 25


@dataclass
class Scene:
    index: int
    text: str
    visual_prompt: str = ""
    keywords: list[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def est_seconds(self) -> float:
        return self.word_count / WORDS_PER_MINUTE * 60.0


def words_for_duration(duration_minutes: float) -> int:
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")
    return int(duration_minutes * WORDS_PER_MINUTE)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _keywords(text: str, n: int = 4) -> list[str]:
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
        "is", "are", "was", "were", "it", "this", "that", "these", "those",
        "you", "your", "we", "our", "they", "their", "as", "at", "by", "be",
        "have", "has", "had", "will", "would", "can", "not", "but", "from",
    }
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1
    return sorted(freq, key=freq.get, reverse=True)[:n]  # type: ignore[arg-type]


def _visual_prompt(text: str) -> str:
    kw = _keywords(text)
    core = " ".join(text.split()[:24])
    style = "cinematic, high detail, dramatic lighting, 16:9 composition, no text, no watermark"
    if kw:
        return f"{core} ... visual concept: {', '.join(kw)}. {style}"
    return f"{core}. {style}"


def split_script(script_text: str, max_scene_words: int = WORDS_PER_SCENE) -> list[Scene]:
    """Split narration into scenes. Respects paragraph breaks as scene hints."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", script_text.strip()) if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        words = para.split()
        if len(words) <= max_scene_words:
            chunks.append(para)
            continue
        # Long paragraph -> pack sentences into scene-sized chunks.
        current: list[str] = []
        current_words = 0
        for sent in _sentences(para):
            sw = len(sent.split())
            if current and current_words + sw > max_scene_words:
                chunks.append(" ".join(current))
                current, current_words = [], 0
            current.append(sent)
            current_words += sw
        if current:
            chunks.append(" ".join(current))

    # Merge tiny trailing chunk into the previous scene.
    if len(chunks) > 1 and len(chunks[-1].split()) < MIN_SCENE_WORDS:
        tail = chunks.pop()
        chunks[-1] = chunks[-1] + " " + tail

    scenes = []
    for i, chunk in enumerate(chunks):
        scenes.append(Scene(index=i, text=chunk,
                            visual_prompt=_visual_prompt(chunk),
                            keywords=_keywords(chunk)))
    return scenes
