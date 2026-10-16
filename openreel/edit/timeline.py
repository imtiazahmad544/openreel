"""Timeline: bind scenes + voice + visuals + captions into timed segments."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..captions.builder import CaptionLine
from ..visuals.base import VisualAsset
from ..voice.base import VoiceResult


@dataclass
class Segment:
    index: int
    text: str
    audio: VoiceResult
    visual: VisualAsset | None
    captions: list[CaptionLine] = field(default_factory=list)
    start: float = 0.0  # absolute start in final video

    @property
    def duration(self) -> float:
        return max(self.audio.duration, 0.5)

    @property
    def end(self) -> float:
        return self.start + self.duration


def assemble_segments(texts: list[str], voices: list[VoiceResult],
                      visuals: list[VisualAsset | None],
                      caption_lines: list[list[CaptionLine]]) -> list[Segment]:
    """Zip scene ingredients; stamp absolute caption offsets."""
    segments: list[Segment] = []
    cursor = 0.0
    for i, (text, voice, visual, lines) in enumerate(zip(texts, voices, visuals, caption_lines)):
        shifted = [CaptionLine(start=l.start + cursor, end=l.end + cursor, text=l.text)
                   for l in lines]
        seg = Segment(index=i, text=text, audio=voice, visual=visual,
                      captions=shifted, start=cursor)
        segments.append(seg)
        cursor = seg.end
    return segments


def total_duration(segments: list[Segment]) -> float:
    return segments[-1].end if segments else 0.0
