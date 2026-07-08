"""One-command local E2E smoke check for the Publishr MVP."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / ".dev-logs"
API_BASE = "http://127.0.0.1:8000"
WEB_PORTS = (3000, 3001, 3002)
# Next.js 16 の dev サーバは localhost(=IPv6 ::1) に bind するため、IPv4/IPv6 両方を試す。
# socket.create_connection に渡すのでブラケットなしの生ホスト表記にする。
WEB_HOSTS = ("127.0.0.1", "::1")
DEMO_USER_ID = "u_sakura"


class SmokeError(RuntimeError):
    pass


def http_status(url: str, timeout: float = 2.0) -> int | None:
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.status
    except HTTPError as error:
        return error.code
    except (URLError, OSError):
        return None


def wait_for(name: str, url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = http_status(url)
        if status is not None and status < 500:
            print(f"{name} ready: {url}")
            return
        time.sleep(0.5)
    raise SmokeError(f"{name} did not become ready: {url}")


def web_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host else host
    return f"http://{display_host}:{port}"


def port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    # 生存確認は TCP connect のみ。ルート `/` を GET すると Next dev(Turbopack)が
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
    raise SmokeError("Web did not become ready on ports 3000-3002")


def log_path_for(name: str) -> Path:
    return LOG_DIR / f"{name.lower()}.log"


def start(name: str, command: list[str], env: dict[str, str] | None = None) -> subprocess.Popen:
    print(f"Starting {name}: {' '.join(command)}")
    LOG_DIR.mkdir(exist_ok=True)
    log_path = log_path_for(name)
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


def tail(path: Path, lines: int = 20) -> str:
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(rows[-lines:])


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


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_servers() -> tuple[list[tuple[str, subprocess.Popen]], str]:
    started: list[tuple[str, subprocess.Popen]] = []

    if http_status(f"{API_BASE}/healthz") is None:
        api = start(
            "API",
            [sys.executable, "-m", "uvicorn", "publishr_api.main:app", "--port", "8000"],
        )
        started.append(("API", api))
    wait_for("API", f"{API_BASE}/healthz")

    current_web_url = find_web_url()
    if current_web_url is None:
        env = os.environ.copy()
        env.setdefault("NEXT_PUBLIC_DATA_SOURCE", "bff")
        env.setdefault("NEXT_PUBLIC_API_URL", "http://localhost:8000")
        web = start("Web", ["npm", "--prefix", "apps/web", "run", "dev"], env=env)
        started.append(("Web", web))
        current_web_url = wait_for_web(timeout=60)
    else:
        print(f"Web ready: {current_web_url}")

    return started, current_web_url


def run_e2e_flow(web_base: str) -> None:
    health = request_json("GET", "/healthz")
    if health.get("status") != "ok":
        raise SmokeError(f"unexpected healthz response: {health}")
    print(f"API health ok: dataSource={health.get('dataSource')} llm={health.get('llm')}")

    pipeline = request_json("POST", "/pipeline/run", {"userId": DEMO_USER_ID})
    books = pipeline.get("books", [])
    reject_log = pipeline.get("rejectLog", [])
    if not books:
        raise SmokeError("pipeline returned no books")
    if not any(entry.get("round") == 1 and entry.get("verdict") == "却下" for entry in reject_log):
        raise SmokeError("pipeline did not return the reject-then-resubmit log")
    print(f"Pipeline ok: books={len(books)} rejectLog={len(reject_log)}")

    published_books = request_json("GET", "/books?status=published")
    published_arrivals = [b for b in published_books if b.get("shelf") == "arrivals"]
    if not published_arrivals:
        raise SmokeError("no published arrival book available after pipeline run")
    book_id = published_arrivals[0]["id"]
    # 一覧は軽量化のため body を落とす（routers/books.py）。本文は読書ページと同じく
    # GET /books/{id} の遅延取得で確認する。
    published = request_json("GET", f"/books/{book_id}")
    if not published.get("body"):
        raise SmokeError(f"published book has no body: {book_id}")
    print(f"Published arrival ok: {book_id}")

    feedback = request_json(
        "POST",
        f"/books/{book_id}/feedback",
        {"rating": 5, "wantsSequel": True, "readPercent": 100},
    )
    if feedback.get("feedback", {}).get("rating") != 5:
        raise SmokeError(f"feedback was not saved: {feedback}")
    print("Feedback ok: rating=5 wantsSequel=true")

    # Web の配信確認は public/ の静的アセットで行う。ルート `/` を GET すると
    # Next dev(Turbopack)が全グラフをオンデマンドコンパイルし、WSL2 ごとハングする
    # 原因になるため避ける（public 配下はコンパイル不要で即応答）。
    web_probe = f"{web_base}/next.svg"
    web_status = http_status(web_probe)
    if web_status is None or web_status >= 500:
        raise SmokeError(f"web is not serving successfully: status={web_status} ({web_probe})")
    print(f"Web ok: {web_probe} status={web_status}")


def main() -> int:
    started: list[tuple[str, subprocess.Popen]] = []
    try:
        started, web_base = ensure_servers()
        run_e2e_flow(web_base)
        print("")
        print("Local E2E smoke passed.")
        return 0
    except Exception as error:
        print("")
        print(f"Local E2E smoke failed: {error}", file=sys.stderr)
        for name, _process in started:
            log_tail = tail(log_path_for(name))
            if log_tail:
                print(f"\n--- {name} log tail ({log_path_for(name)}) ---", file=sys.stderr)
                print(log_tail, file=sys.stderr)
        return 1
    finally:
        for _name, process in reversed(started):
            stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
