"""(3) run_observe --folder-label 用の純粋パーサ parse_folder_labels のテスト。

CLI の "folderId=ラベル" 列を DriveFolderLabel 列へ変換する。observe の folder_label_map が
これを folderId→label 解決に使い、Drive ファイルへ folderLabel を付与する（fixture/google 共通）。
"""

from __future__ import annotations

from publishr_schema import DriveFolderLabel

from publishr_agents.observe.transform import parse_folder_labels


def test_parses_single_pair():
    out = parse_folder_labels(["abc123=業務"])
    assert out == [DriveFolderLabel(folder_id="abc123", label="業務")]


def test_parses_multiple_pairs_in_order():
    out = parse_folder_labels(["abc=業務", "xyz=趣味"])
    assert [(l.folder_id, l.label) for l in out] == [("abc", "業務"), ("xyz", "趣味")]


def test_trims_whitespace_around_id_and_label():
    out = parse_folder_labels(["  abc = 業務メモ  "])
    assert out == [DriveFolderLabel(folder_id="abc", label="業務メモ")]


def test_label_may_contain_equals_sign():
    out = parse_folder_labels(["abc=a=b=c"])
    assert out == [DriveFolderLabel(folder_id="abc", label="a=b=c")]


def test_ignores_entries_without_equals():
    assert parse_folder_labels(["justanid"]) == []


def test_ignores_empty_id_or_label():
    assert parse_folder_labels(["=label", "id=", "  =  "]) == []


def test_empty_input_yields_empty_list():
    assert parse_folder_labels([]) == []
    assert parse_folder_labels(None) == []
