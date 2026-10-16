"""Batch runner with JSON checkpoints: N topics -> N videos, resumable.

State file records per-topic status (pending/done/failed). Re-running with
--resume skips everything already done — safe to run on a schedule.

    openreel batch topics.txt --out-dir ./videos
    openreel batch topics.txt --out-dir ./videos --resume
"""
from __future__ import annotations

import json
import os
import re

from .config import Settings
from .pipeline import run_pipeline


def _slug(topic: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return s[:50] or "video"


def load_state(state_path: str, topics: list[str]) -> dict:
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
    else:
        state = {}
    for t in topics:
        state.setdefault(t, {"status": "pending"})
    return state


def save_state(state_path: str, state: dict):
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def run_batch(topics: list[str], out_dir: str, settings: Settings,
              state_path: str | None = None, resume: bool = False,
              duration_minutes: float = 3.0, progress=None, **pipeline_kw) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    state_path = state_path or os.path.join(out_dir, "batch_state.json")
    state = load_state(state_path, topics)

    def log(msg):
        (progress or print)(msg)

    for i, topic in enumerate(topics):
        st = state[topic]
        if resume and st["status"] == "done":
            log(f"[{i+1}/{len(topics)}] skip (done): {topic}")
            continue
        out_path = os.path.join(out_dir, f"{_slug(topic)}.mp4")
        log(f"[{i+1}/{len(topics)}] creating: {topic}")
        try:
            result = run_pipeline(settings, out_path, topic=topic,
                                  duration_minutes=duration_minutes,
                                  progress=log, **pipeline_kw)
            st.update(status="done", output=result.video_path,
                      duration=round(result.duration, 1))
        except Exception as exc:  # noqa: BLE001 - batch must survive one failure
            st.update(status="failed", error=str(exc)[:300])
            log(f"  FAILED: {exc}")
        save_state(state_path, state)
    done = sum(1 for v in state.values() if v["status"] == "done")
    log(f"Batch complete: {done}/{len(topics)} videos done -> {out_dir}")
    return state
