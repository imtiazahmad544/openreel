"""Piper TTS — fully offline open-source fallback (needs `piper` binary + .onnx model)."""
from __future__ import annotations

import os
import shutil
import subprocess
import wave

from .base import TTSProvider, VoiceResult, _even_split  # noqa: F401  (re-export for tests)


class PiperProvider(TTSProvider):
    name = "piper"

    def synthesize(self, text: str, dest_path: str) -> VoiceResult:
        model = self.settings.piper_model
        piper_bin = shutil.which("piper")
        if not piper_bin or not model or not os.path.exists(model):
            raise RuntimeError(
                "Piper not available: install the `piper` binary and set PIPER_MODEL "
                "to a .onnx voice file (https://github.com/rhasspy/piper)")
        wav_path = dest_path.rsplit(".", 1)[0] + ".wav"
        proc = subprocess.run(
            [piper_bin, "--model", model, "--output_file", wav_path],
            input=text.encode("utf-8"), capture_output=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"piper failed: {proc.stderr.decode()[:300]}")
        duration = self._wav_duration(wav_path)
        # Piper gives no word timings: convert wav -> mp3 for pipeline consistency.
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path,
                        dest_path], check=False, timeout=120)
        from .edge_tts import _even_split
        return VoiceResult(audio_path=dest_path,
                           words=_even_split(text, duration), duration=duration)

    @staticmethod
    def _wav_duration(path: str) -> float:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
