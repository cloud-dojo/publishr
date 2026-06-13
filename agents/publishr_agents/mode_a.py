"""モードA 完全縦串の共有オーケストレーション（STEP0観測→1読者→2企画→3著者→4プレビュー→5装丁）。

CLI（run_mode_a.py / seed_arrivals.py）と BFF サービス（mode_a_service.py）が共通で使う単一の
入口。各 STEP は既存モジュールに委譲し、ここは「順番に呼んで成果をまとめる」だけ（mock挙動不変）。

`llm` 系は段階別に切替可（コスト制御）。既定は全 mock＝LLM 課金ゼロ・決定的。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, NamedTuple, Optional

from publishr_schema import Book, PlanProposal, User


class ModeAResult(NamedTuple):
    """モードAの成果一式。"""

    plan: PlanProposal           # 採用企画
    shelved: list[dict[str, Any]]  # 装丁付き BookDraft（書店に並ぶ形）
    personas: list[Any]          # 使用した生成著者（GeneratedPersona）
    planning: dict[str, Any]     # 企画会議の生ログ（verdictHistory/rejectionFeedback 等＝却下→採用の証跡）


def run_mode_a_pipeline(
    user: User,
    *,
    source: Any,
    now: datetime,
    reader_llm: str = "mock",
    llm: str = "mock",
    preview_llm: str = "mock",
    cover_llm: str = "mock",
    enable_imagen: bool = False,
    theme: Optional[str] = None,
    theme_kind: str = "honmei",
    threshold: int = 70,
    limit: Optional[int] = None,
    past_books: Optional[list[Book]] = None,
) -> ModeAResult:
    """観測→読者→企画→キャスティング→プレビュー→装丁 を一気通貫で回す。

    source は ObservationSource（FixtureObservationSource / GoogleObservationSource）。
    各 *_llm は "mock" | "vertex"。limit はプレビューで生成する冊数（コスト制御）。
    past_books＝ユーザの過去公開本（C1.8 学習ループ＝反応/選択を読者分析に反映・無ければ no-op）。
    """
    from .casting import cast_personas
    from .cover import design_covers
    from .observe import collect_observation
    from .planning import run_planning
    from .preview import run_preview
    from .reader import analyze_reader

    bundle = collect_observation(user, now=now, source=source)
    profile = analyze_reader(bundle, user=user, past_books=past_books, llm=reader_llm)
    planning = run_planning(
        profile, theme=theme, theme_kind=theme_kind, threshold=threshold, llm=llm
    )
    plan = PlanProposal.model_validate(planning["approvedPlan"])
    persona_set = cast_personas(
        plan, reader_profile=profile, favorite_authors=list(user.favorite_authors or []), llm=llm
    )
    books = run_preview(plan, persona_set.personas, reader_profile=profile, limit=limit, llm=preview_llm)
    shelved = design_covers(books, persona_set.personas, llm=cover_llm, enable_imagen=enable_imagen)
    return ModeAResult(plan=plan, shelved=shelved, personas=list(persona_set.personas), planning=planning)
