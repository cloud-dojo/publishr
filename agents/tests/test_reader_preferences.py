"""C1.8 学習ループの嗜好集約（reader/preferences.py）の単体テスト（決定的・オフライン）。

反応/選択が無ければ空＝既存 mock 出力を変えない、が最重要の不変条件。
"""

from __future__ import annotations

from publishr_schema import Book, Feedback, ReadingAnnotation, User, UserProfile
from publishr_schema.models import InitialProfile

from publishr_agents.reader.preferences import (
    has_learning_signal,
    recent_first,
    recent_read_titles,
    style_preference_from_user,
    summarize_annotations,
    summarize_feedback,
)


def _book(bid: str, title: str, **fb) -> Book:
    return Book(
        id=bid,
        plan_id=f"pl_{bid}",
        status="published",
        author_persona_id="p_x",
        title=title,
        cover_variant="midnight",
        shelf="library",
        feedback=Feedback(**fb),
    )


def _annot(aid: str, kind: str, text: str = "", note: str | None = None) -> ReadingAnnotation:
    return ReadingAnnotation(id=aid, kind=kind, paragraph_index=0, text=text, note=note)


def test_summarize_feedback_empty_is_blank():
    assert summarize_feedback(None) == ""
    assert summarize_feedback([]) == ""
    # feedback 全て既定（反応なし）の本は無視＝空。
    assert summarize_feedback([_book("b1", "無反応本")]) == ""


def test_summarize_feedback_classifies_hits_sequel_miss():
    # web が実際に書く readingReaction＝"good"/"bad" 単体 と "good:<理由>"/"bad:<理由>" の両方を含める。
    books = [
        _book("b1", "刺さった本", rating=5, wants_sequel=True),
        _book("b2", "離脱本", read_percent=5, dropped=True),
        _book("b3", "いいね本", reading_reaction="good:面白い"),
        _book("b4", "いまいち本", reading_reaction="bad"),
    ]
    s = summarize_feedback(books)
    assert "過去4冊の反応" in s
    assert "刺さった: 刺さった本・いいね本" in s
    assert "続編希望: 刺さった本" in s
    assert "離脱/不発:" in s and "離脱本" in s and "いまいち本" in s


def test_summarize_feedback_includes_impression_as_labeled_data():
    """自由記述感想は『データ』ラベル付きで抜粋（160字）して足す（感想だけでも学習対象）。"""
    long_note = "主人公の決断に共感した。" + "あ" * 300
    books = [_book("b1", "感想本", impression=long_note)]
    s = summarize_feedback(books)
    assert "感想(ユーザー記述・データ)" in s  # 指示でなくデータと明示
    assert "主人公の決断に共感した" in s
    assert "あ" * 161 not in s  # 抜粋上限160で切る


def test_impression_only_counts_as_feedback():
    from publishr_agents.reader.preferences import has_feedback

    assert has_feedback(_book("b1", "感想のみ本", impression="良かった")) is True
    assert has_feedback(_book("b2", "無反応本")) is False


def test_style_preference_from_user():
    user = User(
        id="u1",
        name="x",
        initial="X",
        profile=UserProfile(role="課長", work_theme="", serendipity_tolerance="mid"),
        initial_profile=InitialProfile(
            industry="食品", job_type="マーケ", position="課長",
            reading_genres=["事例で学ぶ", "実践ハウツー"],
        ),
        favorite_authors=[{"name": "霧島", "voiceStyle": "理性的", "format": "ケース"}],
    )
    s = style_preference_from_user(user)
    assert "好みの作風: 理性的×ケース" in s
    assert "読み口: 事例で学ぶ・実践ハウツー" in s
    # 選択が無ければ空。
    bare = User(id="u2", name="y", initial="Y",
                profile=UserProfile(role="", work_theme="", serendipity_tolerance="mid"))
    assert style_preference_from_user(bare) == ""
    assert style_preference_from_user(None) == ""


def test_recent_read_titles():
    assert recent_read_titles(None) == []
    titles = recent_read_titles([_book("b1", "A"), _book("b2", "B"), _book("b3", "C"), _book("b4", "D")])
    assert titles == ["A", "B", "C"]  # max 3


# ── ハイライト/しおりの取り込み（highlightsSummary の素材） ──────────────
def test_summarize_annotations_empty_is_blank():
    assert summarize_annotations(None) == ""
    assert summarize_annotations([]) == ""
    assert summarize_annotations([_book("b1", "注釈なし本")]) == ""


def test_summarize_annotations_counts_and_labeled_excerpts():
    """件数＋本文抜粋（ユーザー選択・データのラベル付き・抜粋キャップ120字）。"""
    long_text = "権限委譲は手放すことではない。" + "あ" * 300
    b1 = _book("b1", "任せ方の本").model_copy(update={
        "annotations": [
            _annot("a1", "highlight", text=long_text),
            _annot("a2", "note", text="現場の声", note="うちのチームでも試す"),
            _annot("a3", "bookmark"),
        ]
    })
    b2 = _book("b2", "しおりだけ本").model_copy(update={"annotations": [_annot("a4", "bookmark")]})
    s = summarize_annotations([b1, b2])
    assert "過去2冊にハイライト2件・しおり2件" in s
    assert "刺さった箇所(ユーザー選択・データ)" in s  # 指示でなくデータと明示
    assert "権限委譲は手放すことではない" in s and "(『任せ方の本』)" in s
    assert "あ" * 121 not in s  # 抜粋上限120で切る
    assert "メモ(ユーザー記述・データ)" in s and "うちのチームでも試す" in s


def test_summarize_annotations_caps_excerpts_at_three():
    """件数は全量・抜粋は先頭3件まで（データが増えても出力は頭打ち）。"""
    anns = [_annot(f"a{i}", "highlight", text=f"抜粋{i}") for i in range(5)]
    b = _book("b1", "多注釈本").model_copy(update={"annotations": anns})
    s = summarize_annotations([b])
    assert "ハイライト5件" in s
    assert "抜粋0" in s and "抜粋2" in s
    assert "抜粋3" not in s


def test_has_learning_signal_covers_feedback_or_annotations():
    assert has_learning_signal(_book("b1", "反応本", rating=4)) is True
    annotated = _book("b2", "注釈のみ本").model_copy(
        update={"annotations": [_annot("a1", "highlight", text="x")]}
    )
    assert has_learning_signal(annotated) is True
    assert has_learning_signal(_book("b3", "無反応本")) is False


def test_recent_first_orders_by_last_read_then_created():
    """last_read_at 優先・無ければ created_at の新しい順（抜粋が最近の関心を反映する）。"""
    older = _book("b1", "古い本").model_copy(update={"created_at": "2026-06-01T00:00:00+09:00"})
    newer = _book("b2", "新しい本").model_copy(update={"created_at": "2026-07-01T00:00:00+09:00"})
    read_recently = _book(
        "b3", "最近読んだ本", last_read_at="2026-07-08T00:00:00+09:00"
    ).model_copy(update={"created_at": "2026-05-01T00:00:00+09:00"})
    out = recent_first([older, newer, read_recently])
    assert [b.title for b in out] == ["最近読んだ本", "新しい本", "古い本"]
    # 同値（キー無し）は元の順序を保つ＝決定的。
    plain = [_book("b4", "P"), _book("b5", "Q")]
    assert [b.title for b in recent_first(plain)] == ["P", "Q"]


def test_recent_first_normalizes_mixed_timezones():
    """last_read_at(UTC書き)と created_at(JST書き)の混在でも実時刻順（辞書順比較の逆転を防ぐ）。"""
    # A: 実時刻 2026-07-08T23:00Z。B: 実時刻 2026-07-08T16:00Z（=07-09T01:00+09:00）＝Aより古い。
    a = _book("b1", "実は新しい本", last_read_at="2026-07-08T23:00:00+00:00")
    b = _book("b2", "実は古い本").model_copy(update={"created_at": "2026-07-09T01:00:00+09:00"})
    assert [x.title for x in recent_first([b, a])] == ["実は新しい本", "実は古い本"]
