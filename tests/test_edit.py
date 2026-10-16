"""Filtergraph + timeline tests — pure functions, no ffmpeg needed."""
import pytest

from openreel.config import Settings
from openreel.edit.render import build_filtergraph, escape_filter_path, FILTER_PRESETS
from openreel.edit.timeline import Segment, assemble_segments, total_duration
from openreel.visuals.base import VisualAsset
from openreel.voice.base import VoiceResult, WordBoundary
from openreel.captions.builder import CaptionLine


def _seg(i, dur, kind="image", visual_none=False):
    v = None if visual_none else VisualAsset(kind=kind, path=f"/tmp/{kind}{i}",
                                             source="test")
    return Segment(index=i, text=f"scene {i}",
                   audio=VoiceResult(audio_path=f"/tmp/a{i}.mp3", duration=dur),
                   visual=v,
                   captions=[CaptionLine(0.0, dur, f"cap {i}")])


def _settings():
    s = Settings()
    s.aspect = "16:9"
    return s


def test_assemble_segments_absolute_offsets():
    segs = assemble_segments(["a", "b"],
                             [VoiceResult("x", duration=5.0), VoiceResult("y", duration=7.0)],
                             [None, None],
                             [[CaptionLine(1.0, 2.0, "hi")], [CaptionLine(0.5, 1.0, "yo")]])
    assert segs[0].start == 0.0 and segs[1].start == 5.0
    assert segs[1].captions[0].start == 5.5  # shifted by scene start
    assert total_duration(segs) == 12.0


def test_filtergraph_two_images_has_xfade_and_labels():
    fg, total = build_filtergraph([_seg(0, 4.0), _seg(1, 6.0)], _settings())
    assert "xfade=transition=fade" in fg
    assert "acrossfade" in fg
    assert "[vout]" in fg and "[aout]" in fg
    # total = 4 + 6 - fade(0.5)
    assert total == pytest.approx(9.5)


def test_filtergraph_single_segment_no_xfade():
    fg, total = build_filtergraph([_seg(0, 4.0)], _settings())
    assert "xfade" not in fg and "acrossfade" not in fg
    assert total == pytest.approx(4.0)


def test_filtergraph_video_visual_trims_and_loops():
    fg, _ = build_filtergraph([_seg(0, 4.0, kind="video")], _settings())
    assert "trim=start=0:end=4.000" in fg


def test_filtergraph_missing_visual_uses_color_source():
    fg, _ = build_filtergraph([_seg(0, 4.0, visual_none=True)], _settings())
    assert "color=c=0x101018" in fg


def test_filtergraph_mixed_inputs_index_correctly():
    # segment 0 has no visual -> video input idx 0 belongs to segment 1
    segs = [_seg(0, 4.0, visual_none=True), _seg(1, 4.0)]
    fg, _ = build_filtergraph(segs, _settings())
    assert "[0:v]scale=" in fg  # seg 1's image is input 0
    assert "[1:a]" in fg and "[2:a]" in fg  # audio inputs follow video inputs


def test_filtergraph_music_mixes():
    fg, _ = build_filtergraph([_seg(0, 4.0)], _settings(), with_music=True)
    assert "amix=inputs=2" in fg and "volume=0.12" in fg


def test_filtergraph_empty_raises():
    with pytest.raises(ValueError):
        build_filtergraph([], _settings())


def test_filter_presets_all_valid():
    for name in FILTER_PRESETS:
        fg, _ = build_filtergraph([_seg(0, 4.0)], _settings(), filter_preset=name)
        assert "[vout]" in fg


def test_escape_filter_path():
    assert escape_filter_path("a'b:c,d[e]") == "a\\'b\\:c\\,d\\[e\\]"


def test_fade_shrinks_for_short_segments():
    fg, _ = build_filtergraph([_seg(0, 0.9), _seg(1, 0.9)], _settings())
    # fade = min(0.5, 0.9/3 = 0.3)
    assert "duration=0.300" in fg
