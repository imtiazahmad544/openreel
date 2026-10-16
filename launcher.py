"""OpenReel one-click launcher.

Double-click (launch.bat / launch.sh) or run `python launcher.py`:
  1. checks Python version
  2. ensures ffmpeg exists (installs a bundled static binary if missing)
  3. installs/updates Python dependencies + the Gradio UI
  4. starts the UI and opens it in your browser

No command line needed after this.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

MIN_PY = (3, 10)
UI_PORT = 7860
HERE = os.path.dirname(os.path.abspath(__file__))


def pip(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *args],
                   check=True)


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        print("[ok] ffmpeg found on PATH")
        return
    try:
        import imageio_ffmpeg  # noqa: F401
        print("[ok] ffmpeg: using bundled imageio-ffmpeg binary")
        return
    except ImportError:
        pass
    print("[..] ffmpeg not found — installing bundled static binary (one time)...")
    pip("imageio-ffmpeg")
    import imageio_ffmpeg  # noqa: F401
    print("[ok] ffmpeg ready (bundled binary)")


def ensure_deps() -> None:
    print("[..] checking Python packages (one time / on update)...")
    pip("-r", os.path.join(HERE, "requirements.txt"))
    try:
        import gradio  # noqa: F401
    except ImportError:
        print("[..] installing Gradio UI...")
        pip("gradio")
    print("[ok] dependencies ready")


def wait_for_port(port: int, timeout: int = 90) -> bool:
    for _ in range(timeout * 2):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    print("=== OpenReel launcher ===")
    if sys.version_info < MIN_PY:
        print(f"Python 3.10+ required (you have {sys.version.split()[0]})")
        return 1
    try:
        ensure_ffmpeg()
        ensure_deps()
    except subprocess.CalledProcessError as exc:
        print(f"dependency install failed: {exc}")
        return 1

    print("[..] starting OpenReel UI...")
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "app.py")])
    if wait_for_port(UI_PORT):
        url = f"http://127.0.0.1:{UI_PORT}"
        print(f"[ok] OpenReel is running at {url}")
        webbrowser.open(url)
        print("Close this window (Ctrl+C) to stop OpenReel.")
    else:
        print("[!!] UI did not start in time — see output above.")
        return 1
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nstopping...")
        proc.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
