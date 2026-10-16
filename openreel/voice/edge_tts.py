"""edge-tts — free Microsoft neural voices, no API key.

WordBoundary events give us precise word timings, which drive captions
with zero extra cost. Note: unofficial endpoint; Piper is the offline fallback.
"""
from __future__ import annotations

import asyncio

from mutagen.mp3 import MP3

from .base import TTSProvider, VoiceResult, WordBoundary

TICKS_PER_SECOND = 10_000_000  # WordBoundary offsets are 100ns ticks


class EdgeTTSProvider(TTSProvider):
    name = "edge"

    def synthesize(self, text: str, dest_path: str) -> VoiceResult:
        import edge_tts  # imported lazily so tests don't need it
        try:
            return asyncio.run(self._run(edge_tts, text, dest_path))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "edge-tts could not reach Microsoft's speech servers. This is a "
                "network issue, not a bug: the websocket handshake is blocked "
                "(corporate proxies/VPNs sometimes do this). Fixes: run on a direct "
                "connection or free Colab/Kaggle runtime, or switch to the fully "
                "offline Piper TTS (OPENREEL_TTS=piper + PIPER_MODEL). "
                f"Underlying error: {exc}") from exc

    async def _run(self, edge_tts, text: str, dest_path: str) -> VoiceResult:
        communicate = edge_tts.Communicate(
            text, self.settings.voice, rate=self.settings.tts_rate)
        words: list[WordBoundary] = []
        with open(dest_path, "wb") as fh:
            async for chunk in communicate.stream():
                ctype = chunk.get("type")
                if ctype == "audio":
                    fh.write(chunk["data"])
                elif ctype == "WordBoundary":
                    start = chunk["offset"] / TICKS_PER_SECOND
                    end = start + chunk["duration"] / TICKS_PER_SECOND
                    words.append(WordBoundary(text=chunk["text"], start=start, end=end))
        duration = self._probe(dest_path)
        if not words:
            # No boundaries received: fall back to even word distribution.
            words = _even_split(text, duration)
        return VoiceResult(audio_path=dest_path, words=words, duration=duration)

    @staticmethod
    def _probe(path: str) -> float:
        try:
            return float(MP3(path).info.length)
        except Exception:  # noqa: BLE001
            return 0.0


def _even_split(text: str, duration: float) -> list[WordBoundary]:
    words = text.split()
    if not words or duration <= 0:
        return []
    per = duration / len(words)
    return [WordBoundary(text=w, start=i * per, end=(i + 1) * per)
            for i, w in enumerate(words)]
