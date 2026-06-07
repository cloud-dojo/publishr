"""Google API レスポンス → ObservationBundle 要素モデルへの純粋マッピング。

google クライアントに依存しない（dict in / model out）ため、実APIを叩かずユニットテスト
できる。実I/Oは google_source.py 側。形状の正本は各 Google API v3/v1 のレスポンス。
"""

from __future__ import annotations

from typing import Any

from publishr_schema import CalendarEvent, DriveFile, TaskItem


def map_drive_file(raw: dict[str, Any], folder_label: str, text_excerpt: str = "") -> DriveFile:
    """Drive files.list の1要素＋抽出本文 → DriveFile。folderLabel は呼び出し側が解決。"""
    return DriveFile(
        file_id=raw["id"],
        name=raw.get("name", ""),
        mime_type=raw.get("mimeType", ""),
        folder_label=folder_label,
        text_excerpt=text_excerpt,
        modified_time=raw.get("modifiedTime", ""),
    )


def map_calendar_event(raw: dict[str, Any]) -> CalendarEvent:
    """Calendar events.list の1要素 → CalendarEvent。dateTime 優先、終日は date。"""
    start = raw.get("start", {}) or {}
    end = raw.get("end", {}) or {}
    return CalendarEvent(
        title=raw.get("summary", ""),
        start=start.get("dateTime") or start.get("date") or "",
        end=end.get("dateTime") or end.get("date") or "",
        attendees_count=len(raw.get("attendees", []) or []),
        recurring=bool(raw.get("recurringEventId")),
    )


def map_task_item(raw: dict[str, Any]) -> TaskItem:
    """Tasks tasks.list の1要素 → TaskItem。"""
    return TaskItem(
        title=raw.get("title", ""),
        due=raw.get("due"),
        status=raw.get("status", "needsAction"),
        notes=raw.get("notes", "") or "",
    )
