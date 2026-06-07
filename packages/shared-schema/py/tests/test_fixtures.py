"""フィクスチャ・パース契約テスト: 共有JSONが全てモデルに適合し、
参照整合性（book → plan / persona）が保たれていることを保証する。"""

from __future__ import annotations

from publishr_schema.loader import (
    load_books,
    load_keep_notes,
    load_personas,
    load_plans,
    load_users,
)


def test_users_parse():
    users = load_users()
    assert any(u.id == "u_sakura" for u in users)
    sakura = next(u for u in users if u.id == "u_sakura")
    assert sakura.profile.estimated_interests


def test_personas_parse_ten():
    personas = load_personas()
    assert len(personas) == 10, "MVPは作家ペルソナ10件"
    assert "p_kirishima" in {p.id for p in personas}


def test_plans_parse():
    plans = load_plans()
    assert any(p.id == "plan_makase" for p in plans)
    makase = next(p for p in plans if p.id == "plan_makase")
    assert makase.agenda_outline and makase.core_message


def test_books_cover_all_statuses():
    books = load_books()
    statuses = {b.status for b in books}
    assert {"draft", "writing", "published"}.issubset(statuses)
    assert len(books) >= 8


def test_books_referential_integrity():
    plan_ids = {p.id for p in load_plans()}
    persona_ids = {p.id for p in load_personas()}
    for b in load_books():
        assert b.plan_id in plan_ids, f"未知のplanId: {b.id} -> {b.plan_id}"
        assert b.author_persona_id in persona_ids, (
            f"未知のauthorPersonaId: {b.id} -> {b.author_persona_id}"
        )


def test_keep_notes_parse():
    notes = load_keep_notes()
    assert len(notes) >= 5
    assert all(n.user_id == "u_sakura" for n in notes)


def test_camel_alias_roundtrip():
    """camelCase で出力できる（API応答互換）。"""
    book = load_books()[0]
    dumped = book.model_dump(by_alias=True)
    assert "planId" in dumped and "authorPersonaId" in dumped
    assert "readPercent" in dumped["feedback"]
