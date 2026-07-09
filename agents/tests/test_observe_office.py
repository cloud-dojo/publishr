"""(2) _extract_office_text: Drive 上の Office(.docx/.xlsx/.pptx) 本文抽出の offline ユニットテスト。

ネットワーク不要（生バイト列を直接渡す純粋関数）。解析ライブラリ(python-docx/openpyxl/
python-pptx＝google extra)が入っている時のみ実行し、無ければ importorskip で skip する。
"""

from __future__ import annotations

import io

import pytest

from publishr_agents.observe.google_source import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    _extract_office_text,
)


def _docx_bytes(paragraphs: list[str]) -> bytes:
    docx = pytest.importorskip("docx")
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _xlsx_bytes(rows: list[list[str]]) -> bytes:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pptx_bytes(lines: list[str]) -> bytes:
    pptx = pytest.importorskip("pptx")
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    tf = slide.shapes.add_textbox(0, 0, 100, 100).text_frame
    tf.text = lines[0]
    for extra in lines[1:]:
        tf.add_paragraph().text = extra
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_extract_docx_text():
    out = _extract_office_text(DOCX_MIME, _docx_bytes(["新任マネージャーのメモ", "権限委譲がテーマ"]))
    assert "新任マネージャーのメモ" in out
    assert "権限委譲がテーマ" in out


def test_extract_xlsx_text():
    out = _extract_office_text(XLSX_MIME, _xlsx_bytes([["名前", "役割"], ["佐倉", "課長"]]))
    assert "佐倉" in out and "課長" in out


def test_extract_pptx_text():
    out = _extract_office_text(PPTX_MIME, _pptx_bytes(["中期戦略メモ", "差別化ポイント"]))
    assert "中期戦略メモ" in out
    assert "差別化ポイント" in out


def test_unsupported_mime_returns_empty():
    # 旧バイナリ(.doc 等)は非対応＝空文字（従来挙動の維持）。
    assert _extract_office_text("application/msword", b"\x00\x01") == ""


def test_corrupt_bytes_degrade_to_empty():
    # 壊れたバイト列でも例外を投げず空文字に縮退する（観測は継続）。
    assert _extract_office_text(DOCX_MIME, b"not a real docx") == ""
