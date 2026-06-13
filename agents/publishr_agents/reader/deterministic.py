"""STEP1 読者分析の決定的オフライン実装（PUBLISHR_LLM=mock・既定）。

ObservationBundle を素直に読み、ReaderProfile3Layer(§3) を組み立てる。高度な推定はしない
（契約「書いてあることから素直に」）。本格的な分析は実Vertex（vertex_agent）が担う。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from publishr_schema import (
    Book,
    EvidenceRef,
    ObservationBundle,
    ReaderBase,
    ReaderBehavior,
    ReaderCurrentWork,
    ReaderProfile3Layer,
    UpcomingEvent,
    User,
)

from .preferences import recent_read_titles, style_preference_from_user, summarize_feedback

_SEREN = {"高": "high", "中": "mid", "低": "low"}
_ORG = re.compile(r"部下\d+名[^、。/]*")
_MAX = 3


def _serendipity(value: str) -> str:
    if value in ("low", "mid", "high"):
        return value
    return _SEREN.get(value, "mid")


def _org_scale(role: str) -> str:
    m = _ORG.search(role or "")
    return m.group(0) if m else ""


def _parse(iso: str) -> datetime | None:
    s = (iso or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _now_context(collected_at: str) -> tuple[timezone, str]:
    """観測の collected_at から (基準tz, 基準日付) を得る。隠れ時計は持たない。"""
    dt = _parse(collected_at)
    if dt is None:
        return timezone.utc, (collected_at or "")[:10]
    tz = dt.tzinfo or timezone.utc
    return tz, dt.astimezone(tz).date().isoformat()


def _event_date(iso: str, tz: timezone) -> str:
    """イベント開始を基準tzの壁時計日付(YYYY-MM-DD)へ正規化（Google live の UTC ずれ対策）。"""
    dt = _parse(iso)
    if dt is None:
        return (iso or "")[:10]
    if dt.tzinfo is None:
        return (iso or "")[:10]
    return dt.astimezone(tz).date().isoformat()


def _base(user: User | None, prev: ReaderProfile3Layer | None) -> ReaderBase:
    # ① base は安定情報。前回があれば据え置く（再分析しない）。
    if prev is not None and prev.base is not None and (prev.base.industry or prev.base.position):
        return prev.base
    ip = user.initial_profile if user else None
    role = user.profile.role if user else ""
    if ip is not None:
        return ReaderBase(
            industry=ip.industry,
            job_type=ip.job_type,
            position=ip.position,
            org_scale=_org_scale(role),
            reading_genres=list(ip.reading_genres),
        )
    if user is not None:
        return ReaderBase(position=role, org_scale=_org_scale(role))
    return ReaderBase()


def analyze_reader_deterministic(
    observation: ObservationBundle,
    *,
    user: User | None = None,
    prev_profile: ReaderProfile3Layer | None = None,
    past_books: list[Book] | None = None,
) -> ReaderProfile3Layer:
    base = _base(user, prev_profile)
    now_tz, cutoff = _now_context(observation.collected_at)

    # ② currentWork ＝ 分析の主戦場。観測の具体（固有名・日付）を拾い evidence を付す。
    evidence: list[EvidenceRef] = []

    # challenges ＝ タスクの notes（悩み・課題の所在）上位3
    challenges: list[str] = []
    for t in observation.tasks.items:
        note = (t.notes or "").strip()
        if not note:
            continue
        challenges.append(note)
        evidence.append(EvidenceRef(claim=note, source=f"tasks:{t.title}"))
        if len(challenges) >= _MAX:
            break

    # activeWorkThemes ＝ 未完了タスクの上位3
    active = [t.title for t in observation.tasks.items if t.status == "needsAction"][:_MAX]

    # upcomingKeyEvents ＝ now 以降の予定を参加人数降順 上位3（控える重要局面）
    future = sorted(
        (e for e in observation.calendar.events if _event_date(e.start, now_tz) >= cutoff),
        key=lambda e: e.attendees_count,
        reverse=True,
    )[:_MAX]
    upcoming = [UpcomingEvent(title=e.title, date=_event_date(e.start, now_tz)) for e in future]
    # 各重要局面に evidence を1つ付す（契約 §3「各推定に evidence を1つ以上」）。
    evidence.extend(EvidenceRef(claim=e.title, source=f"calendar:{e.title}") for e in future)

    if observation.drive.files:
        f0 = observation.drive.files[0]
        evidence.append(EvidenceRef(claim=f0.name, source=f"drive:{f0.name}"))

    bits: list[str] = []
    if base.position:
        bits.append(base.position)
    if upcoming:
        bits.append(f"直近の重要局面: {upcoming[0].title}（{upcoming[0].date}）")
    elif active:
        bits.append(f"進行中: {active[0]}")
    current = ReaderCurrentWork(
        current_situation="。".join(bits),
        active_work_themes=active,
        challenges=challenges,
        upcoming_key_events=upcoming,
        evidence=evidence,
    )

    # ③ readingBehavior ＝ readingFB＋過去本の反応・ユーザの選択（C1.8 学習ループ）。
    # past_books/お気に入り/読み口が無ければ従来どおり空＝決定的 mock の出力は不変。
    fb = observation.reading_fb
    feedback_summary = summarize_feedback(past_books) or (
        f"{len(fb.feedback)}件の評価" if fb.feedback else ""
    )
    behavior = ReaderBehavior(
        recent_reads=recent_read_titles(past_books),  # 既読＝次サイクルの被り回避材料
        highlights_summary=(f"{len(fb.highlights)}件のハイライト" if fb.highlights else ""),
        feedback_summary=feedback_summary,
        serendipity_tolerance=_serendipity(user.profile.serendipity_tolerance if user else "mid"),
        style_preference=style_preference_from_user(user),
    )

    return ReaderProfile3Layer(base=base, current_work=current, reading_behavior=behavior)
