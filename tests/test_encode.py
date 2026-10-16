import os
import socket
import threading

import pytest

from openreel.edit import encode
from openreel.edit.encode import (
    encoder_video_args, find_ffmpeg, select_encoder,
)


def test_select_encoder_preference_passthrough():
    assert select_encoder("/bin/false", "nvenc") == "nvenc"
    assert select_encoder("/bin/false", "x264") == "x264"
    with pytest.raises(ValueError):
        select_encoder("/bin/false", "bogus")


def test_select_encoder_auto_picks_first_available(monkeypatch):
    monkeypatch.setattr(encode, "_encoders_cache", None)
    monkeypatch.setattr(encode, "_ffmpeg_encoders",
                        lambda b: " V..... h264_nvenc  NVIDIA NVENC  V..... libx264")
    monkeypatch.setattr(encode, "_probe_encoder", lambda b, t: True)
    assert select_encoder("ffmpeg", "auto") == "nvenc"
    monkeypatch.setattr(encode, "_encoders_cache", None)


def test_select_encoder_skips_broken_hardware(monkeypatch):
    """Listed but driverless (e.g. nvenc without GPU) falls through to x264."""
    monkeypatch.setattr(encode, "_encoders_cache", None)
    monkeypatch.setattr(encode, "_ffmpeg_encoders",
                        lambda b: " V..... h264_nvenc  V..... libx264")
    monkeypatch.setattr(encode, "_probe_encoder",
                        lambda b, t: t != "h264_nvenc")
    assert select_encoder("ffmpeg", "auto") == "x264"
    monkeypatch.setattr(encode, "_encoders_cache", None)


def test_select_encoder_auto_falls_back_to_x264(monkeypatch):
    monkeypatch.setattr(encode, "_encoders_cache", None)
    monkeypatch.setattr(encode, "_ffmpeg_encoders", lambda b: " V..... libx264")
    assert select_encoder("ffmpeg", "auto") == "x264"
    monkeypatch.setattr(encode, "_encoders_cache", None)


def test_encoder_video_args_x264_speeds():
    fast = encoder_video_args("x264", "fast")
    assert fast[fast.index("-preset") + 1] == "ultrafast"
    assert encoder_video_args("x264", "balanced")[3] == "veryfast"
    assert encoder_video_args("x264", "quality")[3] == "medium"
    for args in (fast,):
        assert "-crf" in args


def test_encoder_video_args_hardware():
    assert encoder_video_args("nvenc")[1] == "h264_nvenc"
    assert encoder_video_args("qsv")[1] == "h264_qsv"
    assert encoder_video_args("videotoolbox")[1] == "h264_videotoolbox"
    assert encoder_video_args("amf")[1] == "h264_amf"
    with pytest.raises(ValueError):
        encoder_video_args("bogus")


def test_find_ffmpeg_prefers_path(monkeypatch):
    monkeypatch.setattr(encode.shutil, "which", lambda n: "/usr/bin/ffmpeg")
    assert find_ffmpeg() == "/usr/bin/ffmpeg"


def test_find_ffmpeg_missing_raises(monkeypatch):
    monkeypatch.setattr(encode.shutil, "which", lambda n: None)
    monkeypatch.setitem(__import__("sys").modules, "imageio_ffmpeg", None)
    # force ImportError path
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "imageio_ffmpeg":
            raise ImportError("nope")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="ffmpeg not found"):
        find_ffmpeg()


def test_render_video_uses_fast_preset(monkeypatch, tmp_path):
    import openreel.edit.render as rmod
    from openreel.config import Settings
    from openreel.edit.timeline import Segment
    from openreel.visuals.base import VisualAsset
    from openreel.voice.base import VoiceResult

    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        class P:
            returncode = 0
            stderr = ""
        return P()

    monkeypatch.setattr(rmod, "find_ffmpeg", lambda: "/usr/bin/ffmpeg")
    monkeypatch.setattr(rmod, "select_encoder", lambda b, p: "x264")
    monkeypatch.setattr(rmod.subprocess, "run", fake_run)
    seg = Segment(index=0, text="hi",
                  audio=VoiceResult("/tmp/a.mp3", [], 2.0),
                  visual=VisualAsset("image", "/tmp/i.png", "t"))
    out = str(tmp_path / "o.mp4")
    rmod.render_video([seg], Settings(), out, speed="fast")
    cmd = seen["cmd"]
    assert cmd[cmd.index("-preset") + 1] == "ultrafast"
    assert "[aout]" in cmd[cmd.index("-filter_complex") + 1]


def test_wait_for_port():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "launcher", os.path.join(os.path.dirname(__file__), "..", "launcher.py"))
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    assert launcher.wait_for_port(port, timeout=3) is True
    srv.close()
    assert launcher.wait_for_port(port, timeout=1) is False
