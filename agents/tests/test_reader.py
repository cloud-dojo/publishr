"""STEP1 読者分析（C1.2）の決定的オフラインテスト。

ObservationBundle(+initialProfile+prevProfile) → ReaderProfile3Layer の決定的抽出を、
実LLMを使わず検証する。正本: packages/prompts/step1_reader_analyst.md。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from publishr_schema import (
    ObservationBundle,
    ReaderProfile3Layer,
    User,
    load_users,
)

from publishr_agents.observe import FixtureObservationSource, collect_observation
from publishr_agents.reader import analyze_reader
from publishr_agents.reader.deterministic import analyze_reader_deterministic

JST = timezone(timedelta(hours=9))
# 水朝の本命 run。6/5 役員中間報告会などが「控える重要局面」になるアンカー。
NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)


def _sakura() -> User:
    return next(u for u in load_users() if u.id == "u_sakura")


def _bundle() -> ObservationBundle:
    return collect_observation(_sakura(), now=NOW, source=FixtureObservationSource())


# ── 構造・型 ───────────────────────────────────────────────
def test_deterministic_returns_valid_three_layer_profile():
    profile = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert isinstance(profile, ReaderProfile3Layer)
    assert profile.base is not None
    assert profile.current_work is not None
    assert profile.reading_behavior is not None


# ── base ──────────────────────────────────────────────────
def test_base_org_scale_extracted_from_role():
    """user.profile.role の『部下7名』を org_scale に拾う。"""
    profile = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert "部下7名" in profile.base.org_scale


def test_base_preserved_from_prev_profile():
    """prevProfile があれば base は据え置く（① 再分析しない）。"""
    prev = ReaderProfile3Layer.model_validate(
        {"base": {"industry": "FIXED", "jobType": "KEEP", "orgScale": "前回の規模"}}
    )
    profile = analyze_reader_deterministic(_bundle(), user=_sakura(), prev_profile=prev)
    assert profile.base.industry == "FIXED"
    assert profile.base.org_scale == "前回の規模"


# ── currentWork（分析の主戦場・観測ソースに紐づく）──────────────
def test_current_work_challenges_from_task_notes():
    """challenges はタスクの notes（悩みの所在）から拾う。"""
    profile = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert profile.current_work.challenges, "challenges が空でない"
    # fixture tsk_001 notes『自信が持てず手が止まっている』等が反映される
    joined = " ".join(profile.current_work.challenges)
    assert "自信" in joined or "佐藤" in joined or "期待役割" in joined


def test_current_work_upcoming_events_are_future_and_include_key_event():
    """upcomingKeyEvents は now 以降のみ。デモの核（役員中間報告会）を拾う。"""
    profile = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert profile.current_work.upcoming_key_events, "控える重要局面が空でない"
    for ev in profile.current_work.upcoming_key_events:
        assert ev.date >= "2026-06-03"  # NOW(JST) 以降
    titles = " ".join(e.title for e in profile.current_work.upcoming_key_events)
    assert "役員" in titles  # 6/5 役員中間報告会を拾えている


def test_current_work_evidence_tied_to_observation_sources():
    """各 evidence は観測ソース（drive:/calendar:/tasks:）に紐づく（入荷理由の根拠）。"""
    profile = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert profile.current_work.evidence, "evidence が空でない（一般論回避）"
    assert all(
        e.source.startswith(("drive:", "calendar:", "tasks:"))
        for e in profile.current_work.evidence
    )


# ── readingBehavior（初回空・serendipity 写像）────────────────
def test_reading_behavior_serendipity_mapped_and_empty_first_cycle():
    profile = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert profile.reading_behavior.serendipity_tolerance == "mid"  # 「中」→mid
    # readingFB 空（初回）→ 学習シグナルは空
    assert profile.reading_behavior.recent_reads == []


# ── 決定性 ─────────────────────────────────────────────────
def test_deterministic_is_stable():
    a = analyze_reader_deterministic(_bundle(), user=_sakura())
    b = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert a.model_dump(by_alias=True) == b.model_dump(by_alias=True)


# ── dispatcher（PUBLISHR_LLM）──────────────────────────────
def test_analyze_reader_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("PUBLISHR_LLM", raising=False)
    profile = analyze_reader(_bundle(), user=_sakura())
    assert isinstance(profile, ReaderProfile3Layer)
    assert profile.current_work.evidence


def test_analyze_reader_unknown_mode_raises(monkeypatch):
    monkeypatch.setenv("PUBLISHR_LLM", "bogus")
    try:
        analyze_reader(_bundle(), user=_sakura())
    except ValueError as e:
        assert "bogus" in str(e)
    else:
        raise AssertionError("unknown PUBLISHR_LLM で ValueError を期待")


# ── C1.8 学習ループ ───────────────────────────────────────
def test_learning_loop_reflects_feedback_when_present():
    """past_books の反応が readingBehavior（feedbackSummary/recentReads）に出る。"""
    from publishr_schema import Book, Feedback

    past = [
        Book(
            id="b1", plan_id="p1", status="published", author_persona_id="px",
            title="任せ方の本", cover_variant="midnight", shelf="library",
            feedback=Feedback(rating=5, wants_sequel=True),
        )
    ]
    prof = analyze_reader_deterministic(_bundle(), user=_sakura(), past_books=past)
    assert "刺さった: 任せ方の本" in prof.reading_behavior.feedback_summary
    assert "任せ方の本" in prof.reading_behavior.recent_reads


def test_learning_loop_reflects_annotations_when_present():
    """past_books のハイライト/しおりが readingBehavior.highlightsSummary に出る。"""
    from publishr_schema import Book, ReadingAnnotation

    past = [
        Book(
            id="b1", plan_id="p1", status="published", author_persona_id="px",
            title="任せ方の本", cover_variant="midnight", shelf="library",
            annotations=[
                ReadingAnnotation(
                    id="a1", kind="highlight", paragraph_index=2,
                    text="権限委譲は手放すことではない",
                ),
                ReadingAnnotation(id="a2", kind="bookmark", paragraph_index=5, text=""),
            ],
        )
    ]
    prof = analyze_reader_deterministic(_bundle(), user=_sakura(), past_books=past)
    s = prof.reading_behavior.highlights_summary
    assert "ハイライト1件・しおり1件" in s
    assert "権限委譲は手放すことではない" in s


def test_learning_loop_noop_without_feedback():
    """past_books 無し＝従来どおり（feedbackSummary/recentReads/stylePreference 空）＝mock不変。"""
    prof = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert prof.reading_behavior.recent_reads == []
    assert prof.reading_behavior.feedback_summary == ""
    assert prof.reading_behavior.highlights_summary == ""
    assert prof.reading_behavior.style_preference == ""


# ── アカウント選択の反映（今の関心 / 新しい出会いの幅）──────────────
def test_serendipity_maps_account_words():
    """新しい出会いの幅の4語（profileOptions）を low/mid/high に写す＋既存(高/中/低)も維持。"""
    from publishr_agents.reader.deterministic import _serendipity

    assert _serendipity("いつもの専門を深く") == "low"
    assert _serendipity("広く新しい刺激を") == "high"
    assert _serendipity("バランス重視") == "mid"
    assert _serendipity("中") == "mid"
    assert _serendipity("謎ワード") == "mid"  # 未知は mid 既定


def test_recent_interests_merged_into_active_themes():
    """今の関心（initialProfile.recentInterests）が activeWorkThemes に合流＋evidence が付く。"""
    from publishr_schema.models import InitialProfile

    user = _sakura().model_copy(
        update={
            "initial_profile": InitialProfile(
                industry="食品", job_type="マーケ", position="課長",
                recent_interests=["評価・フィードバック", "新任マネジメント"],
            )
        }
    )
    prof = analyze_reader_deterministic(_bundle(), user=user)
    assert "評価・フィードバック" in prof.current_work.active_work_themes
    assert any(e.source == "initialProfile:recentInterests" for e in prof.current_work.evidence)


def test_recent_interests_noop_when_absent():
    """initialProfile=null（fixture）なら関心の合流なし＝従来どおり（mock不変）。"""
    prof = analyze_reader_deterministic(_bundle(), user=_sakura())
    assert not any(
        e.source == "initialProfile:recentInterests" for e in prof.current_work.evidence
    )
