"""TTS provider interface."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings


@dataclass
class WordBoundary:
    text: str
    start: float  # seconds
    end: float    # seconds


@dataclass
class VoiceResult:
    audio_path: str
    words: list[WordBoundary] = field(default_factory=list)
    duration: float = 0.0  # seconds


class TTSProvider:
    name = "base"

    def __init__(self, settings: Settings):
        self.settings = settings

    def synthesize(self, text: str, dest_path: str) -> VoiceResult:  # pragma: no cover
        raise NotImplementedError


def get_tts_provider(settings: Settings) -> TTSProvider:
    from .edge_tts import EdgeTTSProvider
    from .piper import PiperProvider
    if settings.tts.lower() == "piper":
        return PiperProvider(settings)
    return EdgeTTSProvider(settings)
