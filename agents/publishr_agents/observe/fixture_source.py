"""決定的なオフライン観測ソース。

`packages/shared-schema/fixtures/personas/{userId}/{drive,calendar,tasks}.json`
から ObservationBundle を組み立てる。実Google APIを叩かず、開発・CI・
Eval・デモ再現性のための既定ソース。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from publishr_schema import (
    CalendarEvent,
    DriveFile,
    ObservationBundle,
    ReadingFB,
    TaskItem,
    User,
    fixtures_dir,
)

from .transform import build_observation_bundle, folder_label_map


def _load_persona(user_id: str, name: str) -> dict:
    path: Path = fixtures_dir() / "personas" / user_id / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class FixtureObservationSource:
    """fixtures から決定的に観測束を生成するソース（PUBLISHR_OBSERVE=fixture・既定）。"""

    def collect(self, user: User, *, now: datetime) -> ObservationBundle:
        cs = user.connected_sources
        # Drive は Picker 選択 folderIds 配下のみ（§2・C1.1.2）。実APIと同じ folderId スコープ。
        folder_ids: set[str] = set()
        label_of: dict[str, str] = {}
        if cs and cs.drive and cs.drive.enabled:
            folder_ids = set(cs.drive.folder_ids)
            label_of = folder_label_map(cs)

        drive_raw = _load_persona(user.id, "drive.json").get("files", [])
        drive_files = [
            DriveFile(
                file_id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                folder_label=label_of.get(f.get("folderId", ""), f.get("folderLabel", "")),
                text_excerpt=f.get("content", ""),
                modified_time=f.get("modifiedTime", ""),
            )
            for f in drive_raw
            if f.get("folderId") in folder_ids
        ]

        cal_raw = _load_persona(user.id, "calendar.json").get("events", [])
        calendar_events = [
            CalendarEvent(
                title=e.get("summary", ""),
                start=e["start"],
                end=e.get("end", ""),
                attendees_count=e.get("attendeesCount", 0),
                recurring=e.get("recurring", False),
            )
            for e in cal_raw
        ]

        tasks_raw = _load_persona(user.id, "tasks.json").get("tasks", [])
        tasks_items = [
            TaskItem(
                title=t.get("title", ""),
                due=t.get("due"),
                status=t.get("status", "needsAction"),
                notes=t.get("notes", "") or "",
            )
            for t in tasks_raw
        ]

        # readingFB は STEP0 では空（初回サイクル・§2）。集約は I-9（BFF/Firestore）で別途。
        return build_observation_bundle(
            user_id=user.id,
            now=now,
            drive_files=drive_files,
            calendar_events=calendar_events,
            tasks_items=tasks_items,
            reading_fb=ReadingFB(),
        )
