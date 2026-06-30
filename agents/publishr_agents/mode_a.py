"""モードA 完全縦串の共有オーケストレーション（STEP0観測→1読者→2企画→3著者→4プレビュー→5装丁）。

CLI（run_mode_a.py / seed_arrivals.py）と BFF サービス（mode_a_service.py）が共通で使う単一の
入口。各 STEP は既存モジュールに委譲し、ここは「順番に呼んで成果をまとめる」だけ（mock挙動不変）。

`llm` 系は段階別に切替可（コスト制御）。既定は全 mock＝LLM 課金ゼロ・決定的。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, NamedTuple, Optional

from publishr_schema import Book, GeneratedPersona, Persona, PlanProposal, User


class ModeAResult(NamedTuple):
    """モードAの成果一式（旧・単一テーマ）。"""

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
    seed: str = "",
    favorite_pct: int = 25,  # = favorites.FAVORITE_FEATURE_PCT_DEFAULT（配本ごとお気に入り起用確率%）
) -> ModeAResult:
    """観測→読者→企画→キャスティング→プレビュー→装丁 を一気通貫で回す。

    source は ObservationSource（FixtureObservationSource / GoogleObservationSource）。
    各 *_llm は "mock" | "vertex"。limit はプレビューで生成する冊数（コスト制御）。
    past_books＝ユーザの過去公開本（C1.8 学習ループ＝反応/選択を読者分析に反映・無ければ no-op）。
    お気に入り著者は配本ごとに約 favorite_pct%（既定25）で1枠に起用（seed で配本ごとに振り直し）。
    """
    from .casting import cast_personas
    from .casting.favorites import choose_favorite_feature
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
    # 確率はここが握る: 当たればお気に入りを casting へ渡し1枠に混入（外れれば通常著者のみ）。
    feature = choose_favorite_feature(
        ["plan"], list(user.favorite_authors or []), seed=seed, pct=favorite_pct
    )
    persona_set = cast_personas(
        plan, reader_profile=profile, favorite_authors=([feature[1]] if feature else []), llm=llm
    )
    books = run_preview(plan, persona_set.personas, reader_profile=profile, limit=limit, llm=preview_llm)
    # 採用企画（plan）を表紙へ渡す＝企画書ベースの1対1（vertex 経路のみ反映・mock は不変）。
    shelved = design_covers(books, persona_set.personas, llm=cover_llm, enable_imagen=enable_imagen, plan=plan)
    return ModeAResult(plan=plan, shelved=shelved, personas=list(persona_set.personas), planning=planning)


# ══════════════════════════════════════════════════════════════════════════
# v3 4テーマ1-1-1-1 縦串（予約制廃止改定 2026-06-23・本丸）
#   observe → reader → run_planning_set(4テーマ→4承認plan) →
#   各テーマ[キャスティング1著者 → プレビュー1冊 → 装丁] → 棚に4冊
#   旧 run_mode_a_pipeline（単一テーマ）は温存。本関数は additive な新パス。
# ══════════════════════════════════════════════════════════════════════════
class ModeABook(NamedTuple):
    """1テーマ＝1冊の成果（4テーマで4つ）。"""

    plan: PlanProposal                  # この冊の承認企画
    shelved: list[dict[str, Any]]       # 装丁付き BookDraft（新モデルは1冊）
    personas: list[GeneratedPersona]    # この冊の著者（1人）


class ModeASetResult(NamedTuple):
    """モードA セット成果（4テーマ・1-1-1-1）。"""

    books: list[ModeABook]       # 4テーマ＝4冊（1冊/テーマ）
    planning: dict[str, Any]     # セット企画ログ（themeAssignmentSet/planSetVerdict/rejectLog＝却下→採用の証跡）


def run_mode_a_set_pipeline(
    user: User,
    *,
    source: Any,
    now: datetime,
    reader_llm: str = "mock",
    llm: str = "mock",
    preview_llm: str = "mock",
    cover_llm: str = "mock",
    enable_imagen: bool = False,
    theme_kind: str = "honmei",
    threshold: int = 70,
    seed: str = "",
    favorite_pct: int = 25,  # = favorites.FAVORITE_FEATURE_PCT_DEFAULT（配本ごとお気に入り起用確率%）
    max_books: int | None = None,  # デモ用: 生成冊数の上限（None=全テーマ＝従来どおり）
) -> ModeASetResult:
    """観測→読者→セット企画(4テーマ)→各テーマ[キャスティング→プレビュー→装丁] を回し、棚に4冊並べる。

    各 *_llm は "mock" | "vertex"。1テーマ=1著者=1冊（多様性は配本属性＋テーマ別著者で担保）。
    お気に入り著者は「配本ごとに約 favorite_pct%（既定25）で誰か1人を1テーマだけ起用」する決定的抽選。
    seed（配本トークン）で配本ごとに振り直し・同一配本は再現的。
    """
    from .casting import cast_author
    from .casting.favorites import choose_favorite_feature
    from .cover import design_covers
    from .observe import collect_observation
    from .planning import run_planning_set
    from .preview import run_preview
    from .reader import analyze_reader

    bundle = collect_observation(user, now=now, source=source)
    profile = analyze_reader(bundle, user=user, llm=reader_llm)
    planning = run_planning_set(profile, theme_kind=theme_kind, threshold=threshold, llm=llm)
    plans = [PlanProposal.model_validate(p) for p in planning["planSet"]["plans"]]

    # デモ用コスト削減: 冊数を先頭 max_books 件に絞る（None=全テーマ＝従来どおり・非破壊）。
    # 企画(planning)は全テーマ走るが、重いキャスティング/プレビュー/装丁/本文を絞った冊数だけに限定。
    if max_books is not None and max_books > 0:
        plans = plans[:max_books]

    # 確率はここ（オーケストレーション層）が握る: 当たった1枠にだけ favorite を渡す＝
    # casting は「渡されたら起用」に保つ（mock の "あれば必ず混入" でも4冊を占有しない）。
    favorites = list(user.favorite_authors or [])
    feature = choose_favorite_feature(
        [p.proposal_id or "" for p in plans], favorites, seed=seed, pct=favorite_pct
    )
    out: list[ModeABook] = []
    for i, plan in enumerate(plans):
        fav_arg = [feature[1]] if (feature is not None and feature[0] == i) else []
        # 1テーマ=1冊：author_casting で3候補→1選抜。
        casting = cast_author(plan, reader_profile=profile, favorite_authors=fav_arg, llm=llm)
        chosen = []
        if casting.chosen:
            ch = casting.chosen
            # お気に入り再登板は登録 personaId を保持（★継続＝front の favorites.has(id) 一致／
            # 本IDは persist 側で run トークンを挟み毎run別冊に積み上がる）。それ以外は plan スコープに
            # 再id し、book id = arr_<personaId> の4冊間衝突（c1/c2/c3）を防ぐ（mock/vertex 両安全）。
            chosen = [
                ch
                if ch.from_favorite
                else ch.model_copy(update={"persona_id": f"cast_{plan.proposal_id}"})
            ]
        drafts = run_preview(plan, chosen, reader_profile=profile, limit=1, llm=preview_llm)
        # この1テーマの企画書（plan）を表紙へ渡す＝1企画書=1冊=1画像の1対1（vertex 経路のみ反映）。
        shelved = design_covers(drafts, chosen, llm=cover_llm, enable_imagen=enable_imagen, plan=plan)
        out.append(ModeABook(plan=plan, shelved=shelved, personas=chosen))
    return ModeASetResult(books=out, planning=planning)


def make_published_books(
    books: list[Book],
    personas: list[Persona],
    *,
    llm: str = "mock",
    rounds: int = 1,
) -> list[Book]:
    """各 draft 入荷本に modeB 本文編集ループで本文を書き切り published にする（配本runの仕上げ）。

    予約制廃止改定（2026-06-23）: 配本 run で全冊を本文まで作り切って published にする一気通貫。
    旧・予約→Pub/Sub worker（`reservation_service.process_write_job`）と同じ遷移をオフラインで行う
    ＝`status=published`／`body`（編集ループ後の本文）／`edit_round`／`feedback.read_percent=0`。
    著者は personas から `author_persona_id` で引く（無ければ modeB 側で汎用著者に縮退）。
    `llm` は "mock"|"vertex"・`rounds` は本文の最高改稿ラウンド。冪等: すでに本文付き published は素通し。
    """
    from .mode_b import write_body_loop

    by_id = {p.id: p for p in personas}
    out: list[Book] = []
    for book in books:
        if book.status == "published" and book.body:
            out.append(book)
            continue
        result = write_body_loop(
            book, persona=by_id.get(book.author_persona_id), rounds=rounds, llm=llm
        )
        fb = book.feedback.model_copy(update={"read_percent": 0})
        out.append(
            book.model_copy(
                update={
                    "status": "published",
                    "body": result.body,
                    "edit_round": result.edit_rounds,
                    "feedback": fb,
                }
            )
        )
    return out


def map_mode_a_set_to_books(
    result: ModeASetResult, *, owner_uid: str, created_at: str = "",
    run_token: Optional[str] = None,
) -> tuple[list[Book], list[Persona]]:
    """セット成果（4冊）を (Book[], Persona[]) に集約。各テーマ冊を既存 map_mode_a_to_books で変換し統合。

    run_token（I-38）は再配信冪等用の決定的 ID トークン。指定時は book ID を run 単位で固定する。
    """
    from .persist_mapping import map_mode_a_to_books

    all_books: list[Book] = []
    all_personas: list[Persona] = []
    seen: set[str] = set()
    for mb in result.books:
        bks, ps = map_mode_a_to_books(
            mb.plan, mb.shelved, mb.personas, owner_uid=owner_uid,
            created_at=created_at, run_token=run_token,
        )
        all_books.extend(bks)
        for p in ps:
            if p.id not in seen:
                seen.add(p.id)
                all_personas.append(p)
    return all_books, all_personas
