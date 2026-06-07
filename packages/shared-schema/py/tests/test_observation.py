"""STEP0 観測スキーマ（ObservationBundle・ConnectedSources）の妥当性テスト。

契約 docs/design/agent-io-contract.md §2 の camelCase JSON が型付きで読め、
snake_case でアクセスでき、round-trip で §2 の camelCase 形状に戻ることを確認する。
"""

from __future__ import annotations

from publishr_schema import ConnectedSources, ObservationBundle, User


def test_observation_bundle_typed_from_contract_json():
    """§2 の出力例 JSON を型付き ObservationBundle に読み込み、型付きアクセスできる。"""
    bundle = ObservationBundle.model_validate(
        {
            "userId": "u_sakura",
            "collectedAt": "2026-06-05T06:00:00Z",
            "drive": {
                "files": [
                    {
                        "fileId": "drv_001",
                        "name": "企画書",
                        "mimeType": "application/vnd.ms-powerpoint",
                        "folderLabel": "業務",
                        "textExcerpt": "本文抜粋",
                        "modifiedTime": "2026-05-26T08:12:00Z",
                    }
                ]
            },
            "calendar": {
                "events": [
                    {
                        "title": "役員中間報告",
                        "start": "2026-06-05T15:00:00+09:00",
                        "end": "2026-06-05T16:00:00+09:00",
                        "attendeesCount": 6,
                        "recurring": False,
                    }
                ]
            },
            "tasks": {
                "items": [
                    {
                        "title": "ストーリーライン骨子",
                        "due": "2026-06-04",
                        "status": "needsAction",
                        "notes": "至急",
                    }
                ]
            },
            "readingFB": {
                "highlights": [
                    {"bookId": "b1", "text": "期待役割の合意", "createdAt": "2026-06-01T00:00:00Z"}
                ],
                "feedback": [
                    {
                        "bookId": "b1",
                        "rating": 5,
                        "wantsSequel": True,
                        "readPercent": 0.8,
                        "dropped": False,
                    }
                ],
            },
        }
    )
    assert bundle.user_id == "u_sakura"
    assert bundle.collected_at == "2026-06-05T06:00:00Z"
    assert bundle.drive.files[0].file_id == "drv_001"
    assert bundle.drive.files[0].folder_label == "業務"
    assert bundle.drive.files[0].text_excerpt == "本文抜粋"
    assert bundle.calendar.events[0].attendees_count == 6
    assert bundle.tasks.items[0].status == "needsAction"
    assert bundle.reading_fb.highlights[0].book_id == "b1"
    assert bundle.reading_fb.feedback[0].read_percent == 0.8
    assert bundle.reading_fb.feedback[0].wants_sequel is True


def test_observation_bundle_roundtrip_keeps_contract_keys():
    """by_alias の dump が §2 の camelCase キー（特に readingFB）に戻る。"""
    bundle = ObservationBundle(user_id="u_sakura", collected_at="2026-06-05T06:00:00Z")
    dumped = bundle.model_dump(by_alias=True)
    assert dumped["userId"] == "u_sakura"
    assert dumped["collectedAt"] == "2026-06-05T06:00:00Z"
    # readingFB は to_camel だと readingFb になってしまうので明示エイリアスで矯正している
    assert "readingFB" in dumped
    assert "readingFb" not in dumped
    assert dumped["drive"] == {"files": []}
    assert dumped["readingFB"] == {"highlights": [], "feedback": []}


def test_observation_bundle_empty_defaults():
    """初回（readingFB 空・各ソース空）でも妥当に構築できる。"""
    bundle = ObservationBundle(user_id="u", collected_at="2026-06-05T06:00:00Z")
    assert bundle.drive.files == []
    assert bundle.calendar.events == []
    assert bundle.tasks.items == []
    assert bundle.reading_fb.highlights == []
    assert bundle.reading_fb.feedback == []


def test_connected_sources_drive_folder_ids_and_labels():
    """Picker 由来の folderIds[]/labels[]（フォルダ単位）を型付きで保持する。"""
    cs = ConnectedSources.model_validate(
        {
            "drive": {
                "enabled": True,
                "folderIds": ["fld_work", "fld_hobby"],
                "labels": [
                    {"folderId": "fld_work", "label": "業務"},
                    {"folderId": "fld_hobby", "label": "趣味"},
                ],
            },
            "calendar": {"enabled": True, "calendarIds": ["primary"]},
            "tasks": {"enabled": True},
        }
    )
    assert cs.drive is not None
    assert cs.drive.folder_ids == ["fld_work", "fld_hobby"]
    assert cs.drive.labels[0].folder_id == "fld_work"
    assert cs.drive.labels[0].label == "業務"
    assert cs.calendar.calendar_ids == ["primary"]
    assert cs.tasks.enabled is True
    # round-trip で camelCase キーに戻る
    dumped = cs.model_dump(by_alias=True)
    assert dumped["drive"]["folderIds"] == ["fld_work", "fld_hobby"]
    assert dumped["drive"]["labels"][0]["folderId"] == "fld_work"


def test_user_accepts_connected_sources():
    """User が connectedSources を受け付ける（既存フィールドは不変）。"""
    user = User.model_validate(
        {
            "id": "u_sakura",
            "name": "佐倉 美咲",
            "initial": "佐",
            "profile": {
                "role": "マーケ課長",
                "workTheme": "新任マネジメント",
                "estimatedInterests": [],
                "serendipityTolerance": "中",
            },
            "connectedSources": {
                "drive": {"enabled": True, "folderIds": ["fld_work"]},
            },
        }
    )
    assert user.connected_sources is not None
    assert user.connected_sources.drive.folder_ids == ["fld_work"]
    # connectedSources 無しでも従来どおり構築できる（後方互換）
    legacy = User.model_validate(
        {
            "id": "u",
            "name": "n",
            "initial": "n",
            "profile": {
                "role": "r",
                "workTheme": "w",
                "estimatedInterests": [],
                "serendipityTolerance": "中",
            },
        }
    )
    assert legacy.connected_sources is None
