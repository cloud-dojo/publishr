"""C1.8 学習ループの素材: 過去本の反応・ユーザの選択を「企画に効く嗜好シグナル」に集約する純関数。

reader（STEP1）がこれを readingBehavior（feedbackSummary/stylePreference/recentReads）へ織り込み、
STEP2企画は readerProfile 経由で受け取る＝配線を増やさず学習ループを閉じる。
**反応/選択が無ければすべて空**＝決定的 mock の既存出力を変えない（追加分は FB/選択が有る時だけ発火）。
"""

from __future__ import annotations

from typing import Optional

from publishr_schema import Book, User

_HI_RATING = 4  # ★4以上＝刺さった
_DROP_PCT = 20  # 読了率20%未満＝離脱気味
# readingReaction は web 側が "good"/"bad"（理由付きは "good:<理由>"/"bad:<理由>"）で書く。
# 旧 "helpful"/"meh" も後方互換で受ける。
_POS_REACTION = {"good", "helpful", "like"}  # いいね系
_NEG_REACTION = {"bad", "meh", "unhelpful", "dislike"}  # いまいち系
_MAX = 3
_IMPRESSION_EXCERPT = 160  # 自由記述感想の抜粋上限（プロンプトに入る量を抑える）


def _reaction_polarity(raw: Optional[str]) -> str:
    """readingReaction（"good"/"bad" 単体 or "good:<理由>"/"bad:<理由>"）の極性 pos/neg/""。"""
    head = (raw or "").split(":", 1)[0].strip().lower()
    if head in _POS_REACTION:
        return "pos"
    if head in _NEG_REACTION:
        return "neg"
    return ""


def has_feedback(book: Book) -> bool:
    f = book.feedback
    return bool(
        f.rating or f.wants_sequel or f.dropped or f.read_percent or f.reading_reaction or f.impression
    )


def summarize_feedback(past_books: Optional[list[Book]]) -> str:
    """過去本の feedback を内容サマリ文字列にする（反応が1つも無ければ ""）。

    刺さった（★4+ or いいね）／続編希望／離脱・不発（dropped or 低読了率 or いまいち）を題名で示す。
    """
    books = [b for b in (past_books or []) if has_feedback(b)]
    if not books:
        return ""
    parts: list[str] = [f"過去{len(books)}冊の反応"]
    rated = [b for b in books if b.feedback.rating]
    if rated:
        avg = sum(int(b.feedback.rating or 0) for b in rated) / len(rated)
        parts.append(f"平均★{avg:.1f}")
    hi = [
        b.title
        for b in books
        if (b.feedback.rating or 0) >= _HI_RATING
        or _reaction_polarity(b.feedback.reading_reaction) == "pos"
    ]
    if hi:
        parts.append("刺さった: " + "・".join(list(dict.fromkeys(hi))[:_MAX]))
    sequel = [b.title for b in books if b.feedback.wants_sequel]
    if sequel:
        parts.append("続編希望: " + "・".join(list(dict.fromkeys(sequel))[:_MAX]))
    miss = [
        b.title
        for b in books
        if b.feedback.dropped
        or (0 < int(b.feedback.read_percent or 0) < _DROP_PCT)
        or _reaction_polarity(b.feedback.reading_reaction) == "neg"
    ]
    if miss:
        parts.append("離脱/不発: " + "・".join(list(dict.fromkeys(miss))[:_MAX]))
    # 自由記述感想（untrusted）。抜粋して「データ」と明示ラベルで足す＝reader プロンプト側の
    # インジェクションガードと合わせて『指示でなく嗜好の手掛かり』として読ませる。
    notes = [
        f"「{(b.feedback.impression or '').strip()[:_IMPRESSION_EXCERPT]}」"
        for b in books
        if (b.feedback.impression or "").strip()
    ][:_MAX]
    if notes:
        parts.append("感想(ユーザー記述・データ): " + " ".join(notes))
    return "／".join(parts)


def style_preference_from_user(user: Optional[User]) -> str:
    """お気に入り作家の作風＋初期プロフィールの読み口から嗜好文字列（無ければ ""）。"""
    if user is None:
        return ""
    bits: list[str] = []
    styles: list[str] = []
    for f in user.favorite_authors or []:
        if not isinstance(f, dict):
            continue
        vs = str(f.get("voiceStyle") or "").strip()
        fmt = str(f.get("format") or "").strip()
        combo = "×".join(x for x in (vs, fmt) if x)
        if combo:
            styles.append(combo)
    styles = list(dict.fromkeys(styles))[:_MAX]
    if styles:
        bits.append("好みの作風: " + "・".join(styles))
    ip = user.initial_profile
    genres = list(ip.reading_genres) if (ip and ip.reading_genres) else []
    if genres:
        bits.append("読み口: " + "・".join(genres[:_MAX]))
    return "／".join(bits)


def recent_read_titles(past_books: Optional[list[Book]], *, max_n: int = _MAX) -> list[str]:
    """既読タイトル（次サイクルの被り回避の材料・無ければ空）。"""
    return [b.title for b in (past_books or [])][:max_n]
