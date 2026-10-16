import os

from openreel.captions.builder import (
    build_lines, write_ass, write_srt, _ts, _ass_ts,
)
from openreel.voice.base import WordBoundary
from openreel.voice.edge_tts import _even_split


def _words(n=10, per=0.4):
    return [WordBoundary(text=f"w{i}", start=i * per, end=(i + 1) * per)
            for i in range(n)]


def test_build_lines_packs_words():
    lines = build_lines(_words(10), max_words=4)
    assert len(lines) == 3
    assert lines[0].text == "w0 w1 w2 w3"
    assert lines[0].start == 0.0
    assert lines[2].end == 10 * 0.4


def test_build_lines_empty():
    assert build_lines([]) == []


def test_write_srt_format(tmp_path):
    p = str(tmp_path / "c.srt")
    write_srt(build_lines(_words(3)), p, offset=1.5)
    txt = open(p, encoding="utf-8").read()
    assert txt.startswith("1\n00:00:01,500 --> 00:00:02,700\nw0 w1 w2")


def test_write_ass_format(tmp_path):
    p = str(tmp_path / "c.ass")
    write_ass(build_lines(_words(2)), p)
    txt = open(p, encoding="utf-8").read()
    assert "[V4+ Styles]" in txt and "Dialogue:" in txt and "w0 w1" in txt


def test_ts_helpers():
    assert _ts(61.5) == "00:01:01,500"
    assert _ass_ts(61.5) == "0:01:01.50"


def test_even_split_fallback():
    words = _even_split("a b c d", 4.0)
    assert len(words) == 4
    assert words[0].start == 0.0 and words[-1].end == 4.0
    assert _even_split("", 4.0) == [] and _even_split("a b", 0) == []


def test_srt_offset_shifts_all(tmp_path):
    p = str(tmp_path / "c.srt")
    lines = build_lines(_words(8), max_words=4)
    write_srt(lines, p, offset=10.0)
    txt = open(p, encoding="utf-8").read()
    assert "00:00:10,000 -->" in txt
