"""モードA: 観測→読者→企画→キャスティング→プレビュー→装丁 を実行し arrivals へ永続する BFFサービス。

旧 canned v1（`run_pipeline`）を置き換える本実装。LLM は `settings.publishr_llm`（既定 mock＝課金ゼロ・
決定的）、観測は fixture（M2 縦通し優先・実Google接続は別経路）。成果は Book と著者 Persona として repo に
upsert し、企画会議の却下→採用を `reject_log` に載せた `PipelineResult` を返す。
予約制廃止改定（2026-06-23）: set_pipeline 経路は配本 run で全4冊を本文まで作り切って
Book[arrivals/published/ownerUid] にする（予約不要・閲覧は直接可）。旧・単一テーマ経路は draft のまま。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from publishr_agents import PipelineResult, RejectLogEntry
from publishr_agents.mode_a import (
    make_published_books,
    map_mode_a_set_to_books,
    run_mode_a_pipeline,
    run_mode_a_set_pipeline,
)
from publishr_agents.observe import FixtureObservationSource
from publishr_agents.persist_mapping import map_mode_a_to_books, persist_arrivals
from publishr_schema import User, load_users

from ..config import settings
from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
# 観測アンカー（mock 決定的・水朝6/3＝役員報告が±14日窓内）。
_DEMO_NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)
# C1.8 学習ループに渡す過去本の上限。published はフルドキュメント（本文込み）で読むため、
# 蔵書の線形増加をここで頭打ちにする（新しい順に切る＝最近の反応を優先）。
_PAST_BOOKS_MAX = 50


def _load_user(repo: RepositoryProtocol, user_id: str) -> User:
    # まず repo（firestore なら OAuth/Picker が保存した connectedSources を持つ実ユーザー）。
    # 無ければ fixtures にフォールバック（オフライン/mock・CLI 経路の従来挙動を保持）。
    user = repo.get_user(user_id)
    if user is None:
        user = next((u for u in load_users() if u.id == user_id), None)
    if user is None:
        # 入力値はエコーせず（列挙オラクル回避）、サーバログにのみ残す。
        logger.warning("mode_a: user not found: %r", user_id)
        raise NotFoundError("user not found")
    return user


def _google_credentials(uid: str):
    """token_store(uid) の保存トークンから Credentials を作る（file/secret_manager 両対応）。

    未保存なら None。生トークンはログに出さない。失効していれば refresh_token で更新する。
    """
    import json  # noqa: PLC0415

    from ..services.token_store import get_token_store  # noqa: PLC0415

    token_json = get_token_store().load(uid)
    if not token_json:
        return None
    from google.auth.transport.requests import Request  # noqa: PLC0415
    from google.oauth2.credentials import Credentials  # noqa: PLC0415
    from publishr_agents.observe.google_source import resolve_scopes  # noqa: PLC0415

    creds = Credentials.from_authorized_user_info(json.loads(token_json), resolve_scopes())
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _observation_source(user: User, observe_uid: Optional[str]):
    """観測ソースを決める。settings.observe=google かつ接続済み＆トークン有りなら実Google。

    それ以外（既定 fixture／未接続／トークン無し／構築失敗）は決定的 fixture へフォールバック＝
    デモが空/エラーで壊れない。mock 既定では常に fixture（従来挙動・差分ゼロ）。
    """
    if settings.observe != "google":
        return FixtureObservationSource()
    cs = user.connected_sources
    drive_ready = bool(cs and cs.drive and cs.drive.enabled and cs.drive.folder_ids)
    feed_ready = bool(
        cs and ((cs.calendar and cs.calendar.enabled) or (cs.tasks and cs.tasks.enabled))
    )
    if not (observe_uid and (drive_ready or feed_ready)):
        logger.info("observe: user=%s 未接続 → fixture", getattr(user, "id", "?"))
        return FixtureObservationSource()
    try:
        creds = _google_credentials(observe_uid)
        if creds is None:
            logger.info("observe: uid 連携トークン無し → fixture")
            return FixtureObservationSource()
        from publishr_agents.observe.google_source import GoogleObservationSource  # noqa: PLC0415

        logger.info("observe: 実Google 観測を使用（接続済み）")
        return GoogleObservationSource(credentials=creds)
    except Exception as exc:  # noqa: BLE001 — 実Google失敗はデモ継続のため fixture へ縮退
        logger.warning("observe: 実Google 構築失敗 → fixture: %s", type(exc).__name__)
        return FixtureObservationSource()


def _reject_log(planning: dict[str, Any], plan: Any) -> list[RejectLogEntry]:
    """企画会議の verdictHistory を採否ログへ。round1 却下→round2 採用 が見える形。"""
    title = plan.tentative_title
    feedback = planning.get("rejectionFeedback") or ""
    out: list[RejectLogEntry] = []
    for v in planning.get("verdictHistory", []):
        if v.get("decision") == "approve":
            out.append(
                RejectLogEntry(
                    round=v["round"], candidate=title, persona="企画リーダー",
                    verdict="採用", reason=f"スコア{v.get('score')}で承認",
                )
            )
        else:
            out.append(
                RejectLogEntry(
                    round=v["round"], candidate=title, persona="企画リーダー",
                    verdict="却下", reason=feedback or f"スコア{v.get('score')}が基準未達",
                )
            )
    return out


def _reject_log_set(planning: dict[str, Any]) -> list[RejectLogEntry]:
    """セット企画（4テーマ）の verdictHistory を採否ログへ。round1 差し戻し→round2 承認が見える形。

    候補名は「今週の4冊（ポートフォリオ）」、判定者は編集長（セットゲート）。
    差し戻し理由は rejectLog 先頭の rejectionFeedback を使う。
    """
    feedback = ""
    if planning.get("rejectLog"):
        feedback = planning["rejectLog"][0].get("rejectionFeedback") or ""
    candidate = "今週の4冊（ポートフォリオ）"
    out: list[RejectLogEntry] = []
    for v in planning.get("verdictHistory", []):
        if v.get("decision") == "approve":
            out.append(
                RejectLogEntry(
                    round=v["round"], candidate=candidate, persona="編集長",
                    verdict="採用", reason=f"セット総合{v.get('score')}で承認",
                )
            )
        else:
            out.append(
                RejectLogEntry(
                    round=v["round"], candidate=candidate, persona="編集長",
                    verdict="却下", reason=feedback or f"セット総合{v.get('score')}が基準未達",
                )
            )
    return out


def run(
    repo: RepositoryProtocol,
    user_id: str,
    *,
    owner_uid: Optional[str] = None,
    observe_uid: Optional[str] = None,
    llm: Optional[str] = None,
    now: Optional[datetime] = None,
    theme_kind: str = "honmei",
    run_id: Optional[str] = None,
) -> PipelineResult:
    """モードAを1回実行し、生成本を arrivals へ upsert して PipelineResult を返す。

    owner_uid 省略時は user_id を所有者にする（mock/単一ユーザー）。firestore では呼び出し側が
    検証済み Firebase uid を渡す。observe_uid は実Google観測のトークン解決に使う認証uid。
    llm 省略時は settings.publishr_llm。
    settings.set_pipeline（既定True）= 4テーマ1-1-1-1のセット配本（予約制廃止改定 2026-06-23）。
    """
    user = _load_user(repo, user_id)
    owner = owner_uid or user_id
    mode_llm = llm or settings.publishr_llm
    created = datetime.now(JST).isoformat()
    # I-38: run_id があれば book/persona ID を run 単位で決定的にする（Pub/Sub 再配信で同一IDに
    # upsert＝重複入荷を防ぐ）。run_id 無し（mock/直呼び）は run_token=None＝created_at 由来で従来不変。
    run_token = ("r" + "".join(c for c in run_id if c.isalnum())[-24:]) if run_id else None

    # 観測ソース: 実Google（接続済み）か fixture（既定/フォールバック）。
    source = _observation_source(user, observe_uid)
    is_google = type(source).__name__ == "GoogleObservationSource"
    # fixture は決定的アンカー（役員報告が±14日窓内）。実Googleは「今」を基準に±14日を読む。
    anchor = now or (datetime.now(JST) if is_google else _DEMO_NOW)

    # C1.8 学習ループ: ユーザの過去公開本のうち「反応 or 注釈（ハイライト/しおり）がある」ものを
    # 新しい順（last_read_at 優先）・上限 _PAST_BOOKS_MAX で読者分析へ渡す
    # （set/旧単一テーマ 両経路共通。シグナルが1冊も無ければ空＝mock 既定挙動は不変）。
    from publishr_agents.reader.preferences import has_learning_signal, recent_first  # noqa: PLC0415

    past_books = recent_first(
        [
            b
            for b in repo.list_books(status="published")
            if has_learning_signal(b) and (not b.owner_uid or b.owner_uid == owner)
        ]
    )[:_PAST_BOOKS_MAX]

    if settings.set_pipeline:
        set_result = run_mode_a_set_pipeline(
            user,
            source=source,
            now=anchor,
            reader_llm=mode_llm,
            llm=mode_llm,
            preview_llm=mode_llm,
            # ⚠️ DORMANT: 表紙画像生成 park により cover_llm / enable_imagen は現行 no-op（mode_a は無視）。
            cover_llm=mode_llm,
            enable_imagen=settings.enable_imagen,
            theme_kind=theme_kind,
            threshold=70,
            past_books=past_books,
            # お気に入り起用の抽選 seed＝配本トークン（再配信は同一・別配本は振り直し）。
            # run_token 無し（mock/直呼び）は created（wall-clock）＝手動トリガごとに振り直す。
            seed=run_token or created,
            favorite_pct=settings.favorite_feature_pct,
            max_books=settings.set_max_books,
        )
        books, personas = map_mode_a_set_to_books(
            set_result, owner_uid=owner, created_at=created, run_token=run_token
        )
        # 予約制廃止改定: 配本 run で全4冊を本文まで作り切って published にする（一気通貫・予約不要）。
        books = make_published_books(
            books, personas, llm=mode_llm, rounds=settings.body_edit_rounds
        )
        persist_arrivals(repo, books, personas)
        return PipelineResult(
            books=books,
            reject_log=_reject_log_set(set_result.planning),
            # I-39 保険: proposal_id は vertex_set で必ず採番されるが、万一 None が混じっても
            # PipelineResult(list[str]) を落とさないよう除去する。
            approved_plan_ids=[mb.plan.proposal_id for mb in set_result.books if mb.plan.proposal_id],
        )

    # ── 旧・単一テーマ（ロールバック用キルスイッチ PUBLISHR_SET_PIPELINE=0）──

    result = run_mode_a_pipeline(
        user,
        source=source,
        now=anchor,
        reader_llm=mode_llm,
        llm=mode_llm,
        preview_llm=mode_llm,
        # ⚠️ DORMANT: 表紙画像生成 park により cover_llm / enable_imagen は現行 no-op（mode_a は無視）。
        cover_llm=mode_llm,
        enable_imagen=settings.enable_imagen,
        theme=None,
        theme_kind=theme_kind,
        threshold=70,
        limit=settings.max_books_per_run,
        past_books=past_books,
        seed=run_token or created,
        favorite_pct=settings.favorite_feature_pct,
    )
    books, personas = map_mode_a_to_books(
        result.plan,
        result.shelved,
        result.personas,
        owner_uid=owner,
        created_at=created,
        run_token=run_token,
    )
    persist_arrivals(repo, books, personas)

    # 企画したら本文まで自動で書く（手動「予約」を介さない）。1冊=1執筆ジョブで投入し、
    # 重い本文生成は既存の Mode B 経路（worker→write_body_loop→published・C3.3）に委ねる。
    _autowrite_books(repo, [b.id for b in books], owner)

    # Langfuse: 企画の「必然性の証跡」を1トレースで送る（C5.6）。best-effort。
    try:
        from publishr_agents.observability import trace_pipeline  # noqa: PLC0415

        planning = result.planning or {}
        status = trace_pipeline(
            {
                "theme": getattr(result.plan, "tentative_title", None)
                or getattr(result.plan, "core_message", None),
                "approved": True,
                "planning_rounds": planning.get("verdictHistory") or [],
                "grounding_urls": planning.get("groundingUrls") or [],
            }
        )
        logger.info("langfuse trace_pipeline: %s (books=%d)", status, len(books))
    except Exception as exc:  # noqa: BLE001 — 計装失敗は致命でない
        logger.warning("langfuse trace_pipeline failed: %s", type(exc).__name__)

    return PipelineResult(
        books=[repo.get_book(b.id) or b for b in books],  # mock は published＋body 反映後を返す
        reject_log=_reject_log(result.planning, result.plan),
        approved_plan_ids=[result.plan.proposal_id],
    )


def _autowrite_books(repo: RepositoryProtocol, book_ids: list[str], owner: str) -> None:
    """企画直後に各 book を自動執筆へ投入する（draft→reserved→執筆）。

    - pubsub（本番）: reserve→`write_queue.enqueue` で 1冊1ジョブの非同期執筆（worker が published 化）。
    - mock（既定/テスト/ローカル）: reserve→`process_write_job` を同期インライン実行（決定的・event loop
      不要。`schedule_advance` の create_task は threadpool で loop 不在＝使わない）。
    - cap 超過(ConflictError)等は log してスキップ＝その本は draft のまま（企画全体は失敗させない）。
    - publish 失敗時も `reserve_and_enqueue` が予約を draft へ戻す＝reserved 孤児（「準備中」滞留）を作らない。
    """
    from . import reservation_service, write_queue  # noqa: PLC0415 — 循環回避の lazy import

    for book_id in book_ids:
        try:
            if settings.queue == "pubsub":
                # 予約→publish を1単位で（失敗時は予約巻き戻し＝reserved 孤児を作らない）。
                write_queue.reserve_and_enqueue(repo, book_id, owner_uid=owner)
            else:
                reservation_service.reserve_now(repo, book_id, owner_uid=owner)
                reservation_service.process_write_job(repo, book_id)  # mock: 同期インライン
        except Exception as exc:  # noqa: BLE001 — 1冊の失敗で企画全体を落とさない
            logger.warning("autowrite skipped book=%s: %s", book_id, type(exc).__name__)
