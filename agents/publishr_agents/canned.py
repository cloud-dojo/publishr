"""決定的なキャンド出力（MVPの「脳」）。

実LLMの代わりに、観測・読者分析・企画候補・選抜ログ・入荷書籍を
フィクスチャと固定ロジックから生成する。再現可能でEvalに向く。"""

from __future__ import annotations

from collections import Counter

from publishr_schema import (
    Book,
    Plan,
    User,
    load_books,
    load_keep_notes,
    load_plans,
    load_users,
)

from .result import RejectLogEntry

# 今朝の入荷として produce する企画（フィクスチャの arrivals 棚に対応）
ARRIVAL_PLAN_IDS = ["plan_makase", "plan_toi", "plan_shijizero", "plan_suuji"]


def get_user(user_id: str | None) -> User | None:
    if not user_id:
        return None
    return {u.id: u for u in load_users()}.get(user_id)


def aggregate_keep_notes(user_id: str) -> dict:
    """STEP0観測: 指定ユーザーのKeepメモを集計し、ラベル頻度とシグナルを抽出。"""
    notes = [n for n in load_keep_notes() if n.user_id == user_id]
    label_counts = Counter(label for n in notes for label in n.labels)
    top_labels = [label for label, _ in label_counts.most_common(5)]

    signals: list[str] = []
    for n in notes:
        blob = f"{n.title} {n.text} {' '.join(n.labels)}"
        if "管掌範囲" in blob:
            signals.append("管掌範囲の拡大")
        if "1on1" in blob:
            signals.append("1on1の負荷増")
        if "属人化" in blob or "標準化" in blob:
            signals.append("属人化の懸念")
        if "定量" in blob or "数字" in blob:
            signals.append("定量報告の要請")
    # 出現順を保ったまま重複除去
    signals = list(dict.fromkeys(signals))

    return {"noteCount": len(notes), "topLabels": top_labels, "signals": signals}


def build_reader_profile(user: User | None, observation: dict) -> dict:
    """STEP1読者分析: 観測から Reader Profile を確定。"""
    return {
        "role": user.profile.role if user else "（不明）",
        "situation": "10名から30名規模への移行期。情報と意思決定が本人に集中し、現場が止まりはじめている局面。",
        "interests": list(user.profile.estimated_interests) if user else [],
        "signals": observation.get("signals", []),
        "serendipityTolerance": user.profile.serendipity_tolerance if user else "中",
    }


def planning_candidates() -> list[dict]:
    """STEP2: 主題（任せ方）に対する3つの永続ペルソナの企画候補。"""
    return [
        {"key": "practical", "persona": "実務直撃型", "candidate": "任せ方の設計図", "planId": "plan_makase"},
        {"key": "framework", "persona": "フレームワーク型", "candidate": "権限委譲5原則", "planId": None},
        {"key": "contrarian", "persona": "逆張り型", "candidate": "あえて抱え込め", "planId": None},
    ]


def selection_reject_log() -> list[RejectLogEntry]:
    """STEP2選抜ゲート（対立①）: R1で全却下→再提出、R2で採否確定。"""
    return [
        RejectLogEntry(round=1, candidate="任せ方の設計図", persona="実務直撃型", verdict="却下",
                       reason="方向性は良いが具体性が不足。30名の局面に寄せて再提出せよ。"),
        RejectLogEntry(round=1, candidate="権限委譲5原則", persona="フレームワーク型", verdict="却下",
                       reason="一般論に寄りすぎ。既製書との差別化を出して再提出。"),
        RejectLogEntry(round=1, candidate="あえて抱え込め", persona="逆張り型", verdict="却下",
                       reason="逆張りの意図は買うが論拠が粗い。根拠を添えて再提出。"),
        RejectLogEntry(round=2, candidate="任せ方の設計図", persona="実務直撃型", verdict="採用",
                       reason="局面に最も的中。30名移行期の『任せ方』に直結。"),
        RejectLogEntry(round=2, candidate="権限委譲5原則", persona="フレームワーク型", verdict="却下",
                       reason="依然として一般論。あなたの現場への接続が弱い。"),
        RejectLogEntry(round=2, candidate="あえて抱え込め", persona="逆張り型", verdict="保留",
                       reason="視点は鋭いが時期尚早。次回の候補として保留。"),
    ]


def arrival_plans() -> list[Plan]:
    plans = {p.id: p for p in load_plans()}
    return [plans[pid] for pid in ARRIVAL_PLAN_IDS if pid in plans]


def arrival_books() -> list[Book]:
    return [b for b in load_books() if b.shelf == "arrivals"]
