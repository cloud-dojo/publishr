"""フロント firestore-provider.ts が呼ぶ /api/* エンドポイント。

既存の /books/{id}/reserve・/pipeline/run とは別に、フロントの API 契約（api-contract.md §1）
に合わせた簡潔なエントリポイントを提供する。
Bearer トークンは MVP ではオプション（存在すれば uid を検証、なければ settings.demo_uid へ
フォールバック）。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header
from publishr_schema import Book

from ..config import settings
from ..deps import get_repository
from ..repositories.protocol import RepositoryProtocol
from ..schemas import ReserveInput, TriggerPlanningInput
from ..services import pipeline_service, reservation_service

router = APIRouter(prefix="/api", tags=["api"])


def _uid_from_token(authorization: Optional[str] = Header(default=None)) -> str:
    """Bearer トークンから uid を取得。失敗時は settings.demo_uid にフォールバック。"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            import firebase_admin.auth as fb_auth  # noqa: PLC0415

            decoded = fb_auth.verify_id_token(token)
            return str(decoded["uid"])
        except Exception:
            pass
    return settings.demo_uid


@router.post("/reserve", response_model=Book)
async def api_reserve(
    payload: ReserveInput,
    repo: RepositoryProtocol = Depends(get_repository),
    _uid: str = Depends(_uid_from_token),
) -> Book:
    """本を予約する（draft → reserved → writing → published タイマー起動）。
    フロント: firestore-provider.ts POST /api/reserve { bookId }"""
    book = reservation_service.reserve_now(repo, payload.book_id)
    reservation_service.schedule_advance(repo, payload.book_id)
    return book


@router.post("/trigger/planning")
def api_trigger_planning(
    payload: TriggerPlanningInput,
    repo: RepositoryProtocol = Depends(get_repository),
    uid: str = Depends(_uid_from_token),
) -> dict:
    """企画パイプラインを手動起動する（デモ用・許可 uid のみ）。
    フロント: firestore-provider.ts POST /api/trigger/planning { userId }"""
    user_id = payload.user_id or uid or settings.demo_uid
    result = pipeline_service.run(repo, user_id)
    return {"ok": True, "booksAdded": len(result.books)}
