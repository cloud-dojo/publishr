"""C1.8 学習ループの嗜好集約（reader/preferences.py）の単体テスト（決定的・オフライン）。

反応/選択が無ければ空＝既存 mock 出力を変えない、が最重要の不変条件。
"""

from __future__ import annotations

from publishr_schema import Book, Feedback, User, UserProfile
from publishr_schema.models import InitialProfile

from publishr_agents.reader.preferences import (
    recent_read_titles,
    style_preference_from_user,
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
