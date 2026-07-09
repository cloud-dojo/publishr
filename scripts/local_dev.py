"""Run the local API and Web dev servers from one command.

Existing servers are reused so the command does not fail when a port is
already occupied by a previous dev session.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / ".dev-logs"
API_URL = "http://127.0.0.1:8000/healthz"
WEB_PORTS = (3000, 3001, 3002)
# Next.js 16 の dev サーバは localhost(=IPv6 ::1) に bind するため、IPv4/IPv6 両方を試す。
# socket.create_connection に渡すのでブラケットなしの生ホスト表記にする。
WEB_HOSTS = ("127.0.0.1", "::1")


def is_up(url: str, timeout: float = 1.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except URLError:
        return False
    except OSError:
        return False


def wait_for(name: str, url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_up(url):
            print(f"{name} ready: {url}")
            return
        time.sleep(0.5)
    raise RuntimeError(f"{name} did not become ready: {url}")


def web_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host else host
    return f"http://{display_host}:{port}"


def port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    # 生存確認は TCP connect のみで行う。ルート `/` を GET すると Next dev(Turbopack)が
    # 全グラフをオンデマンドコンパイルし、WSL2 ごとハングする原因になるため避ける。
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def find_web_url() -> str | None:
    for port in WEB_PORTS:
        for host in WEB_HOSTS:
            if port_is_open(host, port):
                return web_url(host, port)
    return None


def wait_for_web(timeout: float = 60.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        url = find_web_url()
        if url:
            print(f"Web ready: {url}")
            return url
        time.sleep(0.5)
    raise RuntimeError("Web did not become ready on ports 3000-3002")


def start(name: str, command: list[str], env: dict[str, str] | None = None) -> subprocess.Popen:
    print(f"Starting {name}: {' '.join(command)}")
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"{name.lower()}.log"
    log_file = log_path.open("w")
    print(f"  {name} logs -> {log_path}")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    process.log_file = log_file  # type: ignore[attr-defined]
    return process


def stop(process: subprocess.Popen) -> None:
    log_file = getattr(process, "log_file", None)
    try:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
    finally:
        if log_file is not None:
            log_file.close()


def main() -> int:
    started: list[tuple[str, subprocess.Popen]] = []

    try:
        if is_up(API_URL):
            print(f"API already running: {API_URL}")
        else:
            api = start(
                "API",
                [sys.executable, "-m", "uvicorn", "publishr_api.main:app", "--port", "8000"],
            )
            started.append(("API", api))
            wait_for("API", API_URL)

        current_web_url = find_web_url()
        if current_web_url:
            print(f"Web already running: {current_web_url}")
        else:
            env = os.environ.copy()
            env.setdefault("NEXT_PUBLIC_DATA_SOURCE", "bff")
            env.setdefault("NEXT_PUBLIC_API_URL", "http://localhost:8000")
            web = start("Web", ["npm", "--prefix", "apps/web", "run", "dev"], env=env)
            started.append(("Web", web))
            current_web_url = wait_for_web(timeout=60)

        print("")
        print("Local dev is ready.")
        print("  API: http://localhost:8000/docs")
        print(f"  Web: {current_web_url}")

        if not started:
            print("Nothing was started by this command; existing servers are being used.")
            return 0

        print("Press Ctrl-C to stop the servers started by this command.")
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nStopping local dev servers...")
        return 0
    finally:
        for _name, process in reversed(started):
            stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
