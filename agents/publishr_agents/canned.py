"""決定的なキャンド出力（MVPの「脳」）。

実LLMの代わりに、観測・読者分析・企画候補・選抜ログ・入荷書籍を
フィクスチャと固定ロジックから生成する。再現可能でEvalに向く。"""

from __future__ import annotations

from collections import Counter

from publishr_schema import (
    AgendaItem,
    Book,
    Persona,
    PlanningCandidate,
    Plan,
    User,
    load_books,
    load_keep_notes,
    load_personas,
    load_plans,
    load_users,
)

from .result import RejectLogEntry

_CANDIDATE_ORDER = {"practical": 0, "framework": 1, "contrarian": 2}


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
        {"key": "framework", "persona": "フレームワーク型", "candidate": "問いで動かす現場", "planId": "plan_toi"},
        {"key": "contrarian", "persona": "逆張り型", "candidate": "あえて抱え込め", "planId": "plan_shijizero"},
    ]


def normalize_candidates(candidates: list[dict]) -> list[PlanningCandidate]:
    """並列実行で順序が揺れても、企画者の既定順へ揃える。"""
    parsed = [PlanningCandidate.model_validate(c) for c in candidates]
    return sorted(parsed, key=lambda c: _CANDIDATE_ORDER.get(c.key, 99))


def selection_reject_log(candidates: list[PlanningCandidate]) -> list[RejectLogEntry]:
    """STEP2選抜ゲート（対立①）: R1で全却下→再提出、R2で採否確定。"""
    round1_reasons = {
        "practical": "方向性は良いが具体性が不足。30名の局面に寄せて再提出せよ。",
        "framework": "一般論に寄りすぎ。既製書との差別化を出して再提出。",
        "contrarian": "逆張りの意図は買うが論拠が粗い。根拠を添えて再提出。",
    }
    round2 = {
        "practical": ("採用", "局面に最も的中。30名移行期の『任せ方』に直結。"),
        "framework": ("採用", "指示を減らす問いの設計が、現場の自走課題に接続している。"),
        "contrarian": ("保留", "視点は鋭いが時期尚早。次回の候補として保留。"),
    }
    entries: list[RejectLogEntry] = []
    for c in candidates:
        entries.append(
            RejectLogEntry(
                round=1,
                candidate=c.candidate,
                persona=c.persona,
                verdict="却下",
                reason=round1_reasons.get(c.key, "根拠を補強して再提出。"),
            )
        )
    for c in candidates:
        verdict, reason = round2.get(c.key, ("却下", "あなたの現場への接続が弱い。"))
        entries.append(
            RejectLogEntry(
                round=2,
                candidate=c.candidate,
                persona=c.persona,
                verdict=verdict,
                reason=reason,
            )
        )
    return entries


def approved_plan_ids(candidates: list[PlanningCandidate], reject_log: list[RejectLogEntry]) -> list[str]:
    adopted = {e.candidate for e in reject_log if e.round == 2 and e.verdict == "採用"}
    return [c.plan_id for c in candidates if c.plan_id and c.candidate in adopted]


def arrival_plans(plan_ids: list[str] | None = None) -> list[Plan]:
    plans = {p.id: p for p in load_plans()}
    ids = ["plan_makase", "plan_toi", "plan_shijizero", "plan_suuji"] if plan_ids is None else plan_ids
    return [plans[pid] for pid in ids if pid in plans]


def arrival_books(plan_ids: list[str] | None = None) -> list[Book]:
    allowed = None if plan_ids is None else set(plan_ids)
    return [b for b in load_books() if b.shelf == "arrivals" and (allowed is None or b.plan_id in allowed)]


def _personas_by_style() -> dict[str, Persona]:
    return {p.style: p for p in load_personas()}


def _persona_for_plan(plan: Plan, base: Book) -> Persona:
    by_style = _personas_by_style()
    for style in plan.recommended_author_types:
        if style in by_style:
            return by_style[style]
    personas = {p.id: p for p in load_personas()}
    return personas[base.author_persona_id]


def _agenda_from_outline(plan: Plan, base: Book) -> list[AgendaItem]:
    desc_by_title = {item.title: item.desc for item in base.agenda}
    items: list[AgendaItem] = []
    last_index = len(plan.agenda_outline) - 1
    for i, outline in enumerate(plan.agenda_outline):
        no, _, title = outline.partition(":")
        title = title.strip() or outline
        locked = i >= max(2, last_index - 1)
        items.append(
            AgendaItem(
                no=no.strip() or f"{i + 1:02d}",
                title=title,
                desc=desc_by_title.get(title, plan.core_message if i == 0 else plan.differentiator),
                # MVPでは未執筆の後半章をロックして、予約後に開く体験を残す。
                locked=locked,
                note="★ いちおし" if "権限の設計図" in outline else ("🔒 執筆後" if locked else None),
            )
        )
    return items


def _join_signature(parts: list[str]) -> str:
    joined = ""
    for part in parts:
        joined += part
        if not part.endswith(("。", "！", "？")):
            joined += "。"
    return joined.rstrip("。")


def _preface(plan: Plan, persona: Persona) -> str:
    signature = _join_signature(persona.persona.signature) if persona.persona.signature else persona.persona.thought
    differentiator = plan.differentiator.rstrip("。")
    return (
        f"{signature}。{plan.reader_situation}\n\n"
        f"{plan.core_message}\n\n"
        f"この本では、{persona.name}の{persona.style}としての視点で、"
        f"{differentiator}という固有の切り口から章を進める。"
    )


def compose_arrival_books(plan_ids: list[str] | None = None) -> list[Book]:
    """採用企画と作家ペルソナから、序文とアジェンダを決定的に組み立てる。"""
    plans = {p.id: p for p in arrival_plans(plan_ids)}
    books: list[Book] = []
    for base in arrival_books(plan_ids):
        plan = plans.get(base.plan_id)
        if plan is None:
            books.append(base)
            continue
        persona = _persona_for_plan(plan, base)
        books.append(
            base.model_copy(
                update={
                    "author_persona_id": persona.id,
                    "preface_sample": _preface(plan, persona),
                    "agenda": _agenda_from_outline(plan, base),
                }
            )
        )
    return books


def cover_variant_for(plan_id: str, author_persona_id: str, title: str) -> str:
    """Imagen代替の決定的な装丁variant割当。globals.css の cover--b1..b10 に対応。"""
    plan_variants = {
        "plan_makase": "b1",
        "plan_toi": "b2",
        "plan_shijizero": "b3",
        "plan_suuji": "b4",
    }
    persona_variants = {
        "p_kirishima": "b1",
        "p_azumi": "b2",
        "p_yuki": "b3",
        "p_shiraishi": "b4",
    }
    if plan_id in plan_variants:
        return plan_variants[plan_id]
    if author_persona_id in persona_variants:
        return persona_variants[author_persona_id]
    return f"b{(sum(ord(ch) for ch in title) % 10) + 1}"


def assign_cover_variants(books: list[Book]) -> list[Book]:
    assigned: list[Book] = []
    for book in books:
        if book.shelf != "arrivals":
            assigned.append(book)
            continue
        assigned.append(
            book.model_copy(
                update={
                    "cover_variant": cover_variant_for(
                        book.plan_id,
                        book.author_persona_id,
                        book.title,
                    )
                }
            )
        )
    return assigned
