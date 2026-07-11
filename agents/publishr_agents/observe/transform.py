"""STEP0 観測の決定的な横断ルール（純粋関数）。

ソース非依存の規則をここに集約する: ±14日の取得窓・テキストトリム・タスク絞り・
Drive フォルダラベル解決・ObservationBundle の組み立て。実APIにもfixtureにも同一適用。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from publishr_schema import (
    CalendarEvent,
    CalendarSource,
    ConnectedSources,
    DriveFile,
    DriveFolderLabel,
    DriveSource,
    ObservationBundle,
    ReadingFB,
    TaskItem,
    TasksSource,
)

DEFAULT_WINDOW_DAYS = 14
DEFAULT_EXCERPT_LIMIT = 4000


def _parse_dt(iso: str, fallback_tz: timezone | None) -> datetime:
    """ISO8601 を datetime に。'Z'・オフセット・日付のみを許容。naive は fallback_tz を付与。"""
    s = iso.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=fallback_tz or timezone.utc)
    return dt


def within_window(iso: str, now: datetime, days: int = DEFAULT_WINDOW_DAYS) -> bool:
    """now の ±days 日（過去・未来両方）に収まるか。"""
    dt = _parse_dt(iso, now.tzinfo)
    return now - timedelta(days=days) <= dt <= now + timedelta(days=days)


def trim_excerpt(text: str, limit: int = DEFAULT_EXCERPT_LIMIT) -> str:
    """1ファイルの抽出テキストを上限文字数（バイトではない）で冒頭優先トリム。"""
    if len(text) <= limit:
        return text
    return text[:limit]


def keep_task(due: str | None, status: str, now: datetime, days: int = DEFAULT_WINDOW_DAYS) -> bool:
    """Tasks 絞り: 未完了は常に採用、完了は ±days 内の直近のみ採用。"""
    if status == "completed":
        if not due:
            return False
        return within_window(due, now, days)
    return True


def parse_folder_labels(pairs: list[str] | None) -> list[DriveFolderLabel]:
    """CLI/設定の "folderId=ラベル" 列 → DriveFolderLabel 列（run_observe --folder-label 用）。

    '=' 区切りで最初の1個のみ分割（ラベルに '=' を含められる）。前後空白はトリム。
    '=' 無し・ID空・ラベル空は黙って無視する（folderId のみ＝ラベル未指定として扱う）。
    """
    out: list[DriveFolderLabel] = []
    for raw in pairs or []:
        if "=" not in raw:
            continue
        fid, label = raw.split("=", 1)
        fid, label = fid.strip(), label.strip()
        if fid and label:
            out.append(DriveFolderLabel(folder_id=fid, label=label))
    return out


def folder_label_map(connected_sources: ConnectedSources | None) -> dict[str, str]:
    """connectedSources.drive の folderId → folderLabel マップ（業務/趣味の読み分け用）。

    fixture/google 両ソースで Drive ファイルへ folderLabel を付与するのに使う。
    """
    if connected_sources is None or connected_sources.drive is None:
        return {}
    return {lb.folder_id: lb.label for lb in connected_sources.drive.labels}


def build_observation_bundle(
    *,
    user_id: str,
    now: datetime,
    drive_files: list[DriveFile],
    calendar_events: list[CalendarEvent],
    tasks_items: list[TaskItem],
    reading_fb: ReadingFB | None = None,
) -> ObservationBundle:
    """横断ルール（トリム・±14日窓・タスク絞り）を適用して ObservationBundle を組み立てる。

    ソース側は「どのファイル/イベントを取るか」だけ担い、決定的な後処理はここに一本化する。
    collected_at は呼び出し側の now の tz をそのまま保持する（I-19 の Firestore docID
    `YYYY-MM-DD` 導出時は tz を揃えること）。
    """
    trimmed_drive = [f.model_copy(update={"text_excerpt": trim_excerpt(f.text_excerpt)}) for f in drive_files]
    windowed_cal = [e for e in calendar_events if within_window(e.start, now)]
    filtered_tasks = [t for t in tasks_items if keep_task(t.due, t.status, now)]
    return ObservationBundle(
        user_id=user_id,
        collected_at=now.isoformat(),
        drive=DriveSource(files=trimmed_drive),
        calendar=CalendarSource(events=windowed_cal),
        tasks=TasksSource(items=filtered_tasks),
        reading_fb=reading_fb or ReadingFB(),
    )
