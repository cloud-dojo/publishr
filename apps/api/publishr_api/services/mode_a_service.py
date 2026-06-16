"""モードA: 観測→読者→企画→キャスティング→プレビュー→装丁 を実行し arrivals へ永続する BFFサービス。

旧 canned v1（`run_pipeline`）を置き換える本実装。LLM は `settings.publishr_llm`（既定 mock＝課金ゼロ・
決定的）、観測は fixture（M2 縦通し優先・実Google接続は別経路）。成果は Book[arrivals/draft/ownerUid] と
著者 Persona として repo に upsert し、企画会議の却下→採用を `reject_log` に載せた `PipelineResult` を返す。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from publishr_agents import PipelineResult, RejectLogEntry
from publishr_agents.mode_a import run_mode_a_pipeline
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


def run(
    repo: RepositoryProtocol,
    user_id: str,
    *,
    owner_uid: Optional[str] = None,
    observe_uid: Optional[str] = None,
    llm: Optional[str] = None,
    now: Optional[datetime] = None,
) -> PipelineResult:
    """モードAを1回実行し、生成本を arrivals へ upsert して PipelineResult を返す。

    owner_uid 省略時は user_id を所有者にする（mock/単一ユーザー）。firestore では呼び出し側が
    検証済み Firebase uid を渡す。observe_uid は実Google観測のトークン解決に使う認証uid。
    llm 省略時は settings.publishr_llm。
    """
    user = _load_user(repo, user_id)
    owner = owner_uid or user_id
    mode_llm = llm or settings.publishr_llm

    # 観測ソース: 実Google（接続済み）か fixture（既定/フォールバック）。
    source = _observation_source(user, observe_uid)
    is_google = type(source).__name__ == "GoogleObservationSource"
    # fixture は決定的アンカー（役員報告が±14日窓内）。実Googleは「今」を基準に±14日を読む。
    anchor = now or (datetime.now(JST) if is_google else _DEMO_NOW)

    # C1.8 学習ループ: ユーザの過去公開本のうち「反応がある」ものを読者分析へ渡す。
    # 反応ゼロなら空＝読者分析の出力は従来どおり不変（mock差分ゼロ）。
    from publishr_agents.reader.preferences import has_feedback  # noqa: PLC0415

    # owner スコープ（mockのlist_booksは全件のため明示フィルタ＝firestoreと同義・他者本の混入防止）。
    past_books = [
        b
        for b in repo.list_books(status="published")
        if has_feedback(b) and (not b.owner_uid or b.owner_uid == owner)
    ]

    result = run_mode_a_pipeline(
        user,
        source=source,
        now=anchor,
        reader_llm=mode_llm,
        llm=mode_llm,
        preview_llm=mode_llm,
        cover_llm=mode_llm,
        enable_imagen=settings.enable_imagen,
        theme=None,
        theme_kind="honmei",
        threshold=70,
        limit=settings.max_books_per_run,
        past_books=past_books,
    )
    books, personas = map_mode_a_to_books(
        result.plan,
        result.shelved,
        result.personas,
        owner_uid=owner,
        created_at=datetime.now(JST).isoformat(),
    )
    persist_arrivals(repo, books, personas)

    # 企画したら本文まで自動で書く（手動「予約」を介さない）。1冊=1執筆ジョブで投入し、
    # 重い本文生成は既存の Mode B 経路（worker→write_body_loop→published・C3.3）に委ねる
    # ＝per-book 非同期で push の ack 期限(600s)に収まる・並列・新規本文コードなし。
    _autowrite_books(repo, [b.id for b in books], owner)

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
    """
    from . import reservation_service, write_queue  # noqa: PLC0415 — 循環回避の lazy import

    for book_id in book_ids:
        try:
            reservation_service.reserve_now(repo, book_id, owner_uid=owner)
            if settings.queue == "pubsub":
                write_queue.enqueue(repo, book_id)  # 非同期（per-book worker）
            else:
                reservation_service.process_write_job(repo, book_id)  # mock: 同期インライン
        except Exception as exc:  # noqa: BLE001 — 1冊の失敗で企画全体を落とさない
            logger.warning("autowrite skipped book=%s: %s", book_id, type(exc).__name__)
