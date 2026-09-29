"""Local desktop window wrapper for the existing Streamlit app."""
from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
STARTUP_TIMEOUT_SECONDS = 45


def find_free_port() -> int:
    """Return a currently available loopback TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_streamlit(url: str, process: subprocess.Popen, timeout: float = STARTUP_TIMEOUT_SECONDS) -> None:
    """Wait for the health endpoint, or report early exit/startup timeout."""
    deadline = time.monotonic() + timeout
    health_url = url.rstrip("/") + "/_stcore/health"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Streamlit exited during startup (code {process.returncode}). "
                "Run install-local.bat and try again."
            )
        try:
            with urllib.request.urlopen(health_url, timeout=1.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise TimeoutError(f"Streamlit did not become ready within {timeout:.0f}s: {last_error!r}")


def stop_server(process: subprocess.Popen | None) -> None:
    """Stop the local Streamlit child when the desktop window closes."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    try:
        import webview
    except ImportError:
        print("Desktop components are missing. Run install-local.bat first.")
        return 2

    app_file = APP_DIR / "app.py"
    if not app_file.is_file():
        print(f"Could not find the checker app: {app_file}")
        return 2

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    command = [
        sys.executable, "-m", "streamlit", "run", str(app_file),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]
    process: subprocess.Popen | None = None
    try:
        process = subprocess.Popen(command, cwd=APP_DIR)
        wait_for_streamlit(url, process)
        webview.create_window(
            "Kfir Toolbox — Electrical Design Checker",
            url,
            width=1440,
            height=920,
            min_size=(980, 680),
        )
        webview.start()
        return 0
    except Exception as exc:
        print(f"Could not start Kfir Toolbox: {exc}")
        return 1
    finally:
        stop_server(process)


if __name__ == "__main__":
    raise SystemExit(main())
