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
from publishr_agents.mode_a import (
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


def _load_user(user_id: str) -> User:
    # MVP: モードAの観測は fixture 由来（connectedSources を持つ）ため、ここは fixtures から
    # ユーザーを引く。per-user の実 Firestore ロードは C4.9（実Auth接続）で対応する。
    user = next((u for u in load_users() if u.id == user_id), None)
    if user is None:
        # 入力値はエコーせず（列挙オラクル回避）、サーバログにのみ残す。
        logger.warning("mode_a: user not found: %r", user_id)
        raise NotFoundError("user not found")
    return user


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
    llm: Optional[str] = None,
    now: Optional[datetime] = None,
    theme_kind: str = "honmei",
) -> PipelineResult:
    """モードAを1回実行し、生成本を arrivals へ upsert して PipelineResult を返す。

    owner_uid 省略時は user_id を所有者にする（mock/単一ユーザー）。firestore では呼び出し側が
    検証済み Firebase uid を渡す。llm 省略時は settings.publishr_llm。
    settings.set_pipeline（既定True）= 4テーマ1-1-1-1のセット配本（予約制廃止改定 2026-06-23）。
    """
    user = _load_user(user_id)
    owner = owner_uid or user_id
    mode_llm = llm or settings.publishr_llm
    anchor = now or _DEMO_NOW
    created = datetime.now(JST).isoformat()

    if settings.set_pipeline:
        set_result = run_mode_a_set_pipeline(
            user,
            source=FixtureObservationSource(),
            now=anchor,
            reader_llm=mode_llm,
            llm=mode_llm,
            preview_llm=mode_llm,
            cover_llm=mode_llm,
            enable_imagen=settings.enable_imagen,
            theme_kind=theme_kind,
            threshold=70,
        )
        books, personas = map_mode_a_set_to_books(set_result, owner_uid=owner, created_at=created)
        persist_arrivals(repo, books, personas)
        return PipelineResult(
            books=books,
            reject_log=_reject_log_set(set_result.planning),
            approved_plan_ids=[mb.plan.proposal_id for mb in set_result.books],
        )

    # ── 旧・単一テーマ（ロールバック用キルスイッチ PUBLISHR_SET_PIPELINE=0）──
    result = run_mode_a_pipeline(
        user,
        source=FixtureObservationSource(),
        now=anchor,
        reader_llm=mode_llm,
        llm=mode_llm,
        preview_llm=mode_llm,
        cover_llm=mode_llm,
        enable_imagen=settings.enable_imagen,
        theme=None,
        theme_kind=theme_kind,
        threshold=70,
        limit=settings.max_books_per_run,
    )
    books, personas = map_mode_a_to_books(
        result.plan,
        result.shelved,
        result.personas,
        owner_uid=owner,
        created_at=created,
    )
    persist_arrivals(repo, books, personas)
    return PipelineResult(
        books=books,
        reject_log=_reject_log(result.planning, result.plan),
        approved_plan_ids=[result.plan.proposal_id],
    )
