"""One-command local E2E smoke check for the Publishr MVP."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API_BASE = "http://127.0.0.1:8000"
WEB_PORTS = (3000, 3001, 3002)
DEMO_USER_ID = "u_tadokoro"


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


def web_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def find_web_url() -> str | None:
    for port in WEB_PORTS:
        url = web_url(port)
        status = http_status(url)
        if status is not None and status < 500:
            return url
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


def start(name: str, command: list[str], env: dict[str, str] | None = None) -> subprocess.Popen:
    print(f"Starting {name}: {' '.join(command)}")
    return subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)


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

    draft_books = request_json("GET", "/books?status=draft")
    if not draft_books:
        raise SmokeError("no draft book available after pipeline run")
    book_id = draft_books[0]["id"]
    reserved = request_json("POST", f"/books/{book_id}/reserve")
    if reserved.get("status") != "reserved":
        raise SmokeError(f"reserve did not move to reserved: {reserved}")
    print(f"Reserve ok: {book_id}")

    deadline = time.monotonic() + 15
    published: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        book = request_json("GET", f"/books/{book_id}")
        if book.get("status") == "published":
            published = book
            break
        time.sleep(0.75)
    if published is None:
        raise SmokeError(f"book did not become published in time: {book_id}")
    if not published.get("body"):
        raise SmokeError(f"published book has no body: {book_id}")
    print(f"State machine ok: {book_id} -> published")

    feedback = request_json(
        "POST",
        f"/books/{book_id}/feedback",
        {"rating": 5, "wantsSequel": True, "readPercent": 100},
    )
    if feedback.get("feedback", {}).get("rating") != 5:
        raise SmokeError(f"feedback was not saved: {feedback}")
    print("Feedback ok: rating=5 wantsSequel=true")

    web_status = http_status(web_base)
    if web_status is None or web_status >= 500:
        raise SmokeError(f"web is not serving successfully: status={web_status}")
    print(f"Web ok: {web_base} status={web_status}")


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
        return 1
    finally:
        for _name, process in reversed(started):
            stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
