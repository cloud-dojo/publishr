"""STEP0 観測ツールのテスト（オフライン・決定的）。

純粋ヘルパ（窓/トリム/タスク絞り/ラベル解決/組み立て）と FixtureObservationSource
経由の collect_observation を、fixtures を使って実APIを叩かずに検証する。
正本: docs/design/agent-io-contract.md §2。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from publishr_schema import (
    CalendarEvent,
    ConnectedSources,
    DriveFile,
    ObservationBundle,
    TaskItem,
    User,
    load_users,
)

from publishr_agents.observe import (
    FixtureObservationSource,
    collect_observation,
)
from publishr_agents.observe.google_mapping import (
    map_calendar_event,
    map_drive_file,
    map_task_item,
)
from publishr_agents.observe.transform import (
    build_observation_bundle,
    folder_label_map,
    keep_task,
    trim_excerpt,
    within_window,
)

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 6, 6, 6, 0, tzinfo=JST)  # 土朝の企画 run を想定した固定アンカー


# ── 純粋ヘルパ ──────────────────────────────────────────────
def test_within_window_inside_and_boundaries():
    assert within_window("2026-06-05T15:00:00+09:00", NOW) is True       # 1日前
    assert within_window("2026-06-19T00:00:00+09:00", NOW) is True       # +13日
    assert within_window("2026-05-24T00:00:00+09:00", NOW) is True       # -13日


def test_within_window_outside_past_and_future():
    assert within_window("2026-05-04T09:30:00+09:00", NOW) is False      # -33日
    assert within_window("2026-07-10T00:00:00+09:00", NOW) is False      # +34日


def test_within_window_handles_z_suffix_and_date_only():
    assert within_window("2026-06-05T21:00:00Z", NOW) is True            # UTC 'Z'
    assert within_window("2026-06-04", NOW) is True                       # 日付のみ（naive）


def test_trim_excerpt_under_and_over_limit_multibyte():
    short = "あ" * 100
    assert trim_excerpt(short, limit=4000) == short                      # 上限以下は不変
    long = "あ" * 5000
    trimmed = trim_excerpt(long, limit=4000)
    assert len(trimmed) <= 4000                                          # 文字数（バイトではない）でトリム
    assert long.startswith(trimmed[:50])                                 # 冒頭優先


def test_keep_task_open_recent_and_old_completed():
    assert keep_task("2026-06-04", "needsAction", NOW) is True           # 未完了は採用
    assert keep_task(None, "needsAction", NOW) is True                   # due 無し未完了も採用
    assert keep_task("2026-06-05", "completed", NOW) is True             # 直近の完了は採用
    assert keep_task("2026-04-01", "completed", NOW) is False            # 古い完了は除外


def test_folder_label_map_from_connected_sources():
    cs = ConnectedSources.model_validate(
        {
            "drive": {
                "enabled": True,
                "folderIds": ["fld_work", "fld_hobby"],
                "labels": [
                    {"folderId": "fld_work", "label": "業務"},
                    {"folderId": "fld_hobby", "label": "趣味"},
                ],
            }
        }
    )
    assert folder_label_map(cs) == {"fld_work": "業務", "fld_hobby": "趣味"}
    assert folder_label_map(None) == {}
    assert folder_label_map(ConnectedSources()) == {}


# ── build_observation_bundle（横断ルールの一元化）──────────────
def test_build_bundle_applies_window_trim_and_filters():
    drive = [
        DriveFile(file_id="d1", name="n", mime_type="m", folder_label="業務",
                  text_excerpt="あ" * 5000, modified_time="2026-05-26T08:12:00Z"),
    ]
    calendar = [
        CalendarEvent(title="近い", start="2026-06-05T15:00:00+09:00", end="2026-06-05T16:00:00+09:00"),
        CalendarEvent(title="遠い", start="2026-05-04T09:30:00+09:00", end="2026-05-04T10:00:00+09:00"),
    ]
    tasks = [
        TaskItem(title="open", status="needsAction", due="2026-06-04"),
        TaskItem(title="old-done", status="completed", due="2026-04-01"),
    ]
    bundle = build_observation_bundle(
        user_id="u_sakura", now=NOW, drive_files=drive, calendar_events=calendar, tasks_items=tasks
    )
    assert isinstance(bundle, ObservationBundle)
    assert bundle.collected_at == NOW.isoformat()
    assert len(bundle.drive.files[0].text_excerpt) <= 4000               # トリム適用
    assert [e.title for e in bundle.calendar.events] == ["近い"]          # 窓で遠いを除外
    assert [t.title for t in bundle.tasks.items] == ["open"]             # 古い完了を除外
    assert bundle.reading_fb.highlights == []                            # 初回は空


# ── FixtureObservationSource 経由（fixtures 統合）─────────────
def _sakura() -> User:
    return next(u for u in load_users() if u.id == "u_sakura")


def test_collect_observation_fixture_produces_valid_bundle():
    bundle = collect_observation(_sakura(), now=NOW, source=FixtureObservationSource())
    assert isinstance(bundle, ObservationBundle)
    assert bundle.user_id == "u_sakura"
    assert bundle.collected_at == NOW.isoformat()
    # Drive: 選択フォルダ（業務）配下のみ・トリム済み
    assert len(bundle.drive.files) > 0
    assert all(f.folder_label == "業務" for f in bundle.drive.files)
    assert all(len(f.text_excerpt) <= 4000 for f in bundle.drive.files)
    assert all(f.file_id and f.name for f in bundle.drive.files)
    # Calendar: ±14日 窓内のみ
    assert len(bundle.calendar.events) > 0
    assert all(within_window(e.start, NOW) for e in bundle.calendar.events)
    # Tasks: 未完了が含まれ、古い完了は含まれない
    assert any(t.status == "needsAction" for t in bundle.tasks.items)
    assert all(keep_task(t.due, t.status, NOW) for t in bundle.tasks.items)
    # readingFB は初回空（§2）
    assert bundle.reading_fb.highlights == []
    assert bundle.reading_fb.feedback == []


def test_collect_observation_is_deterministic():
    src = FixtureObservationSource()
    a = collect_observation(_sakura(), now=NOW, source=src)
    b = collect_observation(_sakura(), now=NOW, source=src)
    assert a.model_dump(by_alias=True) == b.model_dump(by_alias=True)


def test_collect_observation_no_drive_connection_yields_empty_drive():
    user = _sakura().model_copy(update={"connected_sources": ConnectedSources()})
    bundle = collect_observation(user, now=NOW, source=FixtureObservationSource())
    assert bundle.drive.files == []


def test_collect_observation_scopes_to_selected_folder_ids():
    """Drive は選択 folderIds 配下のみ（C1.1.2）。未選択フォルダIDなら空。"""
    # 既定 u_sakura は fld_work を選択 → 業務ファイルが入る
    selected = collect_observation(_sakura(), now=NOW, source=FixtureObservationSource())
    assert len(selected.drive.files) > 0
    assert all(f.folder_label == "業務" for f in selected.drive.files)

    # 別フォルダだけ選択 → fixtures の業務ファイルはスコープ外で空
    other = _sakura().model_copy(
        update={
            "connected_sources": ConnectedSources.model_validate(
                {"drive": {"enabled": True, "folderIds": ["fld_other"]}}
            )
        }
    )
    assert collect_observation(other, now=NOW, source=FixtureObservationSource()).drive.files == []


def test_completed_tasks_within_window_are_included():
    """直近の完了タスク（窓内）は採用、古い完了は除外（§2 未完了＋直近完了）。"""
    bundle = collect_observation(_sakura(), now=NOW, source=FixtureObservationSource())
    completed = [t for t in bundle.tasks.items if t.status == "completed"]
    assert completed, "窓内の直近完了タスクが少なくとも1件は出ること"
    assert all(within_window(t.due, NOW) for t in completed if t.due)


# ── dispatcher（PUBLISHR_OBSERVE 解決）─────────────────────────
def test_collect_observation_defaults_to_fixture_source(monkeypatch):
    monkeypatch.delenv("PUBLISHR_OBSERVE", raising=False)
    bundle = collect_observation(_sakura(), now=NOW)  # source 未指定＝既定 fixture
    assert bundle.user_id == "u_sakura"
    assert len(bundle.drive.files) > 0


def test_collect_observation_unknown_mode_raises(monkeypatch):
    monkeypatch.setenv("PUBLISHR_OBSERVE", "bogus")
    try:
        collect_observation(_sakura(), now=NOW)
    except ValueError as e:
        assert "bogus" in str(e)
    else:
        raise AssertionError("unknown PUBLISHR_OBSERVE で ValueError を期待")


# ── Google API レスポンス → モデル マッピング（純粋・オフライン）───────
def test_map_drive_file_from_api_shape():
    raw = {
        "id": "1AbC",
        "name": "企画書",
        "mimeType": "application/vnd.google-apps.document",
        "modifiedTime": "2026-05-26T08:12:00.000Z",
    }
    df = map_drive_file(raw, folder_label="業務", text_excerpt="本文")
    assert isinstance(df, DriveFile)
    assert df.file_id == "1AbC"
    assert df.folder_label == "業務"
    assert df.text_excerpt == "本文"
    assert df.modified_time == "2026-05-26T08:12:00.000Z"


def test_map_calendar_event_datetime_attendees_recurring():
    raw = {
        "summary": "役員中間報告",
        "start": {"dateTime": "2026-06-05T15:00:00+09:00"},
        "end": {"dateTime": "2026-06-05T16:00:00+09:00"},
        "attendees": [{"email": "a"}, {"email": "b"}, {"email": "c"}],
        "recurringEventId": "rec_1",
    }
    ev = map_calendar_event(raw)
    assert isinstance(ev, CalendarEvent)
    assert ev.title == "役員中間報告"
    assert ev.start == "2026-06-05T15:00:00+09:00"
    assert ev.attendees_count == 3
    assert ev.recurring is True


def test_map_calendar_event_all_day_no_attendees():
    raw = {"summary": "全社休", "start": {"date": "2026-06-10"}, "end": {"date": "2026-06-11"}}
    ev = map_calendar_event(raw)
    assert ev.start == "2026-06-10"          # 終日は date を採用
    assert ev.attendees_count == 0
    assert ev.recurring is False


def test_map_task_item_fields():
    raw = {"title": "骨子作成", "due": "2026-06-04T00:00:00.000Z", "status": "needsAction", "notes": "至急"}
    t = map_task_item(raw)
    assert isinstance(t, TaskItem)
    assert t.title == "骨子作成"
    assert t.status == "needsAction"
    assert t.notes == "至急"
    # notes 欠落でも空文字
    assert map_task_item({"title": "x", "status": "completed"}).notes == ""
