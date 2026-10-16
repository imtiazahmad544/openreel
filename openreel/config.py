"""Central configuration. Everything has a $0 default; keys are optional upgrades."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class Settings:
    # --- providers ---
    llm: str = field(default_factory=lambda: _env("OPENREEL_LLM", "pollinations"))
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY", ""))
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "llama3.1"))
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))

    pexels_api_key: str = field(default_factory=lambda: _env("PEXELS_API_KEY", ""))
    pixabay_api_key: str = field(default_factory=lambda: _env("PIXABAY_API_KEY", ""))

    tts: str = field(default_factory=lambda: _env("OPENREEL_TTS", "edge"))
    voice: str = field(default_factory=lambda: _env("OPENREEL_VOICE", "en-US-AndrewMultilingualNeural"))
    tts_rate: str = field(default_factory=lambda: _env("OPENREEL_TTS_RATE", "-4%"))
    piper_model: str = field(default_factory=lambda: _env("PIPER_MODEL", ""))

    # --- pipeline defaults ---
    aspect: str = field(default_factory=lambda: _env("OPENREEL_ASPECT", "16:9"))
    fps: int = field(default_factory=lambda: int(_env("OPENREEL_FPS", "30")))
    visual_mode: str = field(default_factory=lambda: _env("OPENREEL_VISUAL_MODE", "auto"))
    workdir: str = field(default_factory=lambda: _env("OPENREEL_WORKDIR", ".openreel"))
    http_timeout: int = 60
    retries: int = 3

    @property
    def width(self) -> int:
        return 1080 if self.aspect == "9:16" else 1920

    @property
    def height(self) -> int:
        return 1920 if self.aspect == "9:16" else 1080


FREE_STACK_NOTES = """\
100% FREE STACK (no credit card, $0 required)
- Script   : Pollinations text API (free, no key) | fallbacks: Gemini free tier, Ollama local
- Images   : Pollinations image API (free, no key, FLUX-class models)
- Voice    : edge-tts — Microsoft neural voices, free, no key, word-level timestamps
             fallback: Piper TTS (fully offline, open source)
- Stock    : Pexels + Pixabay free API keys (generous free tiers, optional);
             Wikimedia Commons (no key) as keyless fallback
- Editing  : ffmpeg (free) — Ken Burns, crossfades, caption burn-in, filters
- Captions : derived from TTS word-boundary timestamps (no paid alignment API)
"""
