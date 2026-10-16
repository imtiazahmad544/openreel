"""Group word timestamps into caption lines; emit SRT and styled ASS."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..voice.base import WordBoundary

MAX_WORDS_PER_LINE = 7
MAX_CHARS_PER_LINE = 42


@dataclass
class CaptionLine:
    start: float
    end: float
    text: str


def build_lines(words: list[WordBoundary],
                max_words: int = MAX_WORDS_PER_LINE) -> list[CaptionLine]:
    """Pack words into readable caption lines."""
    lines: list[CaptionLine] = []
    cur: list[WordBoundary] = []
    cur_chars = 0
    for w in words:
        if cur and (len(cur) >= max_words or cur_chars + len(w.text) > MAX_CHARS_PER_LINE):
            lines.append(CaptionLine(start=cur[0].start, end=cur[-1].end,
                                     text=" ".join(x.text for x in cur)))
            cur, cur_chars = [], 0
        cur.append(w)
        cur_chars += len(w.text) + 1
    if cur:
        lines.append(CaptionLine(start=cur[0].start, end=cur[-1].end,
                                 text=" ".join(x.text for x in cur)))
    return lines


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(lines: list[CaptionLine], path: str, offset: float = 0.0) -> str:
    """Write SRT, shifting every cue by `offset` seconds (for scene placement)."""
    with open(path, "w", encoding="utf-8") as fh:
        for i, line in enumerate(lines, 1):
            fh.write(f"{i}\n{_ts(line.start + offset)} --> {_ts(line.end + offset)}\n"
                     f"{line.text}\n\n")
    return path


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: OpenReel,Arial,64,&H00FFFFFF,&H000019FF,&H80000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ass_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h}:{m:02d}:{s:02d}.{ms // 10:02d}"


def write_ass(lines: list[CaptionLine], path: str, offset: float = 0.0) -> str:
    """Write styled ASS (bold white w/ black outline, bottom-center)."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(ASS_HEADER)
        for line in lines:
            text = line.text.replace(",", "\\,")
            fh.write(f"Dialogue: 0,{_ass_ts(line.start + offset)},"
                     f"{_ass_ts(line.end + offset)},OpenReel,,0,0,0,,{text}\n")
    return path


def _parse_ts(ts: str) -> float:
    ts = ts.replace(",", ":").replace(".", ":")
    h, m, s, ms = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path: str) -> list[CaptionLine]:
    """Parse an SRT file back into caption lines (for Shorts repurposing)."""
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    lines: list[CaptionLine] = []
    for block in re.split(r"\n\s*\n", content.strip()):
        parts = block.strip().split("\n")
        if len(parts) >= 3 and "-->" in parts[1]:
            start_s, end_s = [t.strip() for t in parts[1].split("-->")]
            lines.append(CaptionLine(start=_parse_ts(start_s), end=_parse_ts(end_s),
                                     text=" ".join(parts[2:])))
    return lines
