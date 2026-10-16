import json
import os

from openreel.config import Settings
from openreel.batch import run_batch, load_state, save_state, _slug
from openreel.captions.builder import parse_srt, CaptionLine


def test_slug():
    assert _slug("Hello World! 123") == "hello-world-123"
    assert _slug("!!!") == "video"


def test_batch_state_roundtrip(tmp_path):
    p = str(tmp_path / "s.json")
    save_state(p, {"a": {"status": "done"}})
    assert load_state(p, ["a", "b"])["b"]["status"] == "pending"


def test_run_batch_checkpoints_and_resume(monkeypatch, tmp_path):
    import openreel.batch as bmod
    calls = []

    class FakeResult:
        video_path = "/tmp/x.mp4"
        duration = 60.0

    def fake_run(settings, out_path, **kw):
        calls.append(kw.get("topic"))
        if kw.get("topic") == "bad topic":
            raise RuntimeError("boom")
        return FakeResult()

    monkeypatch.setattr(bmod, "run_pipeline", fake_run)
    out_dir = str(tmp_path / "videos")
    state_path = str(tmp_path / "state.json")
    state = run_batch(["good one", "bad topic", "good two"], out_dir, Settings(),
                      state_path=state_path)
    assert state["good one"]["status"] == "done"
    assert state["bad topic"]["status"] == "failed"
    assert "boom" in state["bad topic"]["error"]
    assert len(calls) == 3  # batch survives one failure

    # resume skips done, retries failed
    calls.clear()
    state = run_batch(["good one", "bad topic", "good two"], out_dir, Settings(),
                      state_path=state_path, resume=True)
    assert calls == ["bad topic"]


def test_parse_srt_roundtrip(tmp_path):
    from openreel.captions.builder import write_srt
    p = str(tmp_path / "c.srt")
    lines = [CaptionLine(0.0, 1.5, "hello world"), CaptionLine(2.0, 3.25, "second line")]
    write_srt(lines, p)
    back = parse_srt(p)
    assert len(back) == 2
    assert back[0].text == "hello world" and back[0].end == 1.5
    assert back[1].start == 2.0


def test_cli_subcommand_parsing():
    from openreel.cli import build_parser
    ap = build_parser()
    a = ap.parse_args(["batch", "topics.txt", "--out-dir", "./v", "--resume"])
    assert a.cmd == "batch" and a.resume and a.out_dir == "./v"
    a = ap.parse_args(["shorts", "v.mp4", "--count", "2"])
    assert a.cmd == "shorts" and a.count == 2
    a = ap.parse_args(["repair", "m.json", "--scene", "1", "--revisualize"])
    assert a.cmd == "repair" and a.scene == 1 and a.revisualize


def test_cli_bare_flags_route_to_create():
    from openreel.cli import main
    # --free-stack short-circuits before any network/provider work
    assert main(["--topic", "x", "--free-stack"]) == 0
    assert main(["create", "--topic", "x", "--free-stack"]) == 0
