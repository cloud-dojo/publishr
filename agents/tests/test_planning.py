"""STEP2 企画3階層（C1.3）の決定的オフラインテスト。

ReaderProfile → 調査サブ×3 → 企画担当者 → 企画リーダー（スコア差し戻し→escalate）の
決定的経路を実LLMなしで検証する。基準1（reject→再提出→approve の証跡）が核。
正本: docs/design/agent-io-contract.md §4 / packages/prompts/step2_*.md。
"""

from __future__ import annotations

from publishr_schema import LeaderVerdict, PlanProposal, ReaderProfile3Layer

from publishr_agents.planning import run_planning
from publishr_agents.planning.deterministic import derive_theme, run_planning_deterministic


def _profile() -> ReaderProfile3Layer:
    return ReaderProfile3Layer.model_validate(
        {
            "base": {
                "industry": "食品・飲料メーカー",
                "jobType": "マーケティング・ブランド",
                "position": "課長・マネージャー（2026/04新任）",
                "orgScale": "部下7名（年上のベテラン佐藤健一42歳を含む）",
                "readingGenres": ["すぐ使える実践書・ハウツー"],
            },
            "currentWork": {
                "currentSituation": "新任2ヶ月。年上部下の任せ方に悩み6/5役員報告を控える",
                "activeWorkThemes": ["新任マネジメント（年上部下対応・権限委譲）", "春リニューアル意思決定"],
                "challenges": ["年上で実力者の佐藤さんにどこまで任せるかの距離感"],
                "upcomingKeyEvents": [{"title": "役員中間報告", "date": "2026-06-05"}],
                "evidence": [{"claim": "任せ方に悩む", "source": "drive:1on1メモ"}],
            },
            "readingBehavior": {"serendipityTolerance": "mid", "stylePreference": "実務的・対話的"},
        }
    )


# ── テーマ導出 ─────────────────────────────────────────────
def test_derive_theme_from_profile():
    theme = derive_theme(_profile())
    assert theme  # 空でない
    assert "マネジメント" in theme or "権限委譲" in theme or "任せ" in theme


def test_serendipity_theme_differs_from_honmei():
    """themeKind=serendipity は『関心の隣』へずらした別テーマになる（§4 同一構造で切替）。"""
    honmei = derive_theme(_profile(), "honmei")
    serendipity = derive_theme(_profile(), "serendipity")
    assert serendipity != honmei
    s = run_planning_deterministic(_profile(), theme_kind="serendipity")
    assert s["theme"] == serendipity
    assert s["approvedPlan"] is not None


# ── 3サブ生成 ──────────────────────────────────────────────
def test_three_research_subs_present():
    result = run_planning_deterministic(_profile())
    assert result["subReaderContext"] is not None
    assert result["subMarket"] is not None
    assert result["subThemeInsight"] is not None
    # B 市場は marketGap（差別化材料・サブの存在意義）を返す
    assert result["subMarket"]["marketGap"]


# ── reject→再提出→approve（基準1の核）────────────────────────
def test_reject_then_resubmit_then_approve_trace():
    result = run_planning_deterministic(_profile(), threshold=70)
    history = result["verdictHistory"]
    assert len(history) >= 2, "差し戻し→再提出で2ラウンド以上"
    assert history[0]["decision"] == "revise"  # round1 は差し戻し
    assert history[0]["score"] < 70
    assert history[-1]["decision"] == "approve"  # 最終は採用
    assert history[-1]["score"] >= 70
    assert result["rounds"] >= 2


def test_round1_rejection_feedback_recorded():
    """差し戻し理由（却下証跡）が残る＝基準1の生命線。"""
    result = run_planning_deterministic(_profile(), threshold=70)
    assert result["rejectionFeedback"], "round1 の差し戻し理由が残る"


# ── 承認 PlanProposal（8項目・marketGap反映）──────────────────
def test_approved_plan_has_eight_fields_and_diff():
    result = run_planning_deterministic(_profile(), threshold=70)
    plan = PlanProposal.model_validate(result["approvedPlan"])
    assert plan.tentative_title
    assert plan.reader_situation
    assert plan.why_now_for_you
    assert plan.core_message
    assert plan.diff_from_market  # ⑤ 差別化（subMarket.marketGap 由来）
    assert plan.key_insights      # ⑥
    assert plan.agenda_outline    # ⑦
    assert plan.recommended_author_types  # ⑧


def test_leader_verdict_validates_as_schema():
    result = run_planning_deterministic(_profile(), threshold=70)
    for v in result["verdictHistory"]:
        LeaderVerdict.model_validate(v)  # 例外なく検証できる形


# ── 高閾値で3R強制承認（棚を空にしない）──────────────────────
def test_high_threshold_forces_approve_at_round3():
    result = run_planning_deterministic(_profile(), threshold=101)
    assert result["rounds"] == 3
    assert result["forced_approve"] is True
    assert result["approvedPlan"] is not None  # 強制でも承認案は出る


# ── 決定性 ─────────────────────────────────────────────────
def test_deterministic_is_stable():
    a = run_planning_deterministic(_profile(), threshold=70)
    b = run_planning_deterministic(_profile(), threshold=70)
    assert a == b


# ── dispatcher ────────────────────────────────────────────
def test_run_planning_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("PUBLISHR_LLM", raising=False)
    result = run_planning(_profile())
    assert result["approvedPlan"] is not None


def test_run_planning_unknown_mode_raises(monkeypatch):
    monkeypatch.setenv("PUBLISHR_LLM", "bogus")
    try:
        run_planning(_profile())
    except ValueError as e:
        assert "bogus" in str(e)
    else:
        raise AssertionError("unknown PUBLISHR_LLM で ValueError を期待")
