"""フロント firestore-provider.ts が呼ぶ /api/* エンドポイント。

既存の /books/{id}/reserve・/pipeline/run とは別に、フロントの API 契約（api-contract.md §1）
に合わせた簡潔なエントリポイントを提供する。
Bearer トークンは MVP ではオプション（存在すれば uid を検証、なければ settings.demo_uid へ
フォールバック）。
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import RedirectResponse
from publishr_schema import Book

from ..config import settings
from ..deps import get_repository
from ..repositories.protocol import RepositoryProtocol
from ..schemas import ReserveInput, TriggerPlanningInput
from ..services import reservation_service, write_queue
from ..services.trigger_guard import TriggerError, TriggerGuard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# 手動トリガーのガード（C4前ゲート: 許可uid・レート制限・実行中ロック）。プロセス内で共有。
trigger_guard = TriggerGuard(
    min_interval_sec=settings.trigger_min_interval_sec,
    allowed_uids=settings.allowed_trigger_uids,
)


def _ensure_firebase_app() -> None:
    """verify_id_token 前に firebase_admin app を遅延初期化（冪等・mock/firestore 両対応）。

    従来 app は firestore リポジトリでしか初期化されず、mock モードでは未初期化＝verify が
    必ず落ちて /api/auth/google/start が 401 になっていた。ここで初期化することで UI の
    Google 連携が mock でも通る。Auth エミュレータ利用時は firebase_admin が
    `FIREBASE_AUTH_EMULATOR_HOST` を自動参照する（projectId は emulator と一致させる）。
    """
    import os  # noqa: PLC0415

    import firebase_admin  # noqa: PLC0415

    if firebase_admin._apps:
        return
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    options = {"projectId": project_id} if project_id else None
    firebase_admin.initialize_app(options=options)


def _verify_uid(authorization: Optional[str]) -> Optional[str]:
    """Bearer の Firebase IDトークンを検証して uid を返す。無/不正なら None（記録のみ）。"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            _ensure_firebase_app()
            import firebase_admin.auth as fb_auth  # noqa: PLC0415

            decoded = fb_auth.verify_id_token(token)
            return str(decoded["uid"])
        except Exception as exc:  # noqa: BLE001 — 失敗は記録のみ（呼び出し側が方針を決める）
            logger.warning("id-token verify failed: %s", type(exc).__name__)
    return None


def _uid_from_token(authorization: Optional[str] = Header(default=None)) -> str:
    """Bearer から uid。無/不正は settings.demo_uid（非課金/閲覧系のデモ用フォールバック）。"""
    return _verify_uid(authorization) or settings.demo_uid


def require_reserve_uid(authorization: Optional[str] = Header(default=None)) -> str:
    """課金アクション（予約→実Vertex執筆）用の uid 解決。

    `settings.require_reserve_auth` が True のとき、有効な Firebase IDトークンを必須にし、
    無/不正なら 401（＝完全な外部はブロック・ログイン済みなら誰でも可・allowlist無し）。
    False（既定/ローカルmock）では従来どおり demo_uid にフォールバック。
    """
    uid = _verify_uid(authorization)
    if uid:
        return uid
    if settings.require_reserve_auth:
        raise HTTPException(status_code=401, detail="ログインが必要です（執筆依頼は認証ユーザーのみ）")
    return settings.demo_uid


@router.get("/books/{book_id}/body")
def api_get_book_body(
    book_id: str,
    repo: RepositoryProtocol = Depends(get_repository),
    uid: str = Depends(_uid_from_token),
) -> dict:
    """本文を返す（C3.3）。GCS退避時はサーバ側で **非公開** バケットから読む（オブジェクトを晒さない）。

    フロント: firestore-provider が bodyUrl 有り＆body 空の本をこの口で hydrate する。
    所有者チェック: book.ownerUid が設定済みなら要求 uid と一致を要求（不一致は403）。
    inline（既定/mock）は book.body をそのまま返す＝従来の読書導線は不変。
    """
    book = repo.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"book {book_id} が見つかりません")
    if book.owner_uid and uid and book.owner_uid != uid:
        raise HTTPException(status_code=403, detail="この本を読む権限がありません")
    if settings.require_reserve_auth and not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    if book.body:
        return {"body": book.body}
    from ..services.body_store import get_body_store  # noqa: PLC0415

    store = get_body_store()
    if store is not None and book.body_url:
        return {"body": store.get(book_id, book.body_url) or ""}
    return {"body": ""}


@router.post("/books/{book_id}/move-to-library", response_model=Book)
def api_move_to_library(
    book_id: str,
    repo: RepositoryProtocol = Depends(get_repository),
    uid: str = Depends(_uid_from_token),
) -> Book:
    """入荷一覧から書庫へ移す（shelf="library"・動的フィルタリング）。移動後は入荷から消え、
    書庫（status=published）には残る。所有者チェックは body エンドポイントと同方針（不一致403）。"""
    book = repo.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"book {book_id} が見つかりません")
    if book.owner_uid and uid and book.owner_uid != uid:
        raise HTTPException(status_code=403, detail="この本を移動する権限がありません")
    return reservation_service.move_to_library(repo, book_id)


@router.get("/books/{book_id}/cover")
def api_get_book_cover(
    book_id: str,
    repo: RepositoryProtocol = Depends(get_repository),
):
    """表紙画像を返す（Imagen・ENABLE_IMAGEN=true 時のみ存在）。本文C3.3と同方針で **非公開**
    GCSバケットからサーバ側 read して画像バイトを配信＝オブジェクトを外部に晒さない。

    `<img src>` から認証ヘッダを送れないため所有者チェックは課さない（表紙は書影アートで非機微）。
    coverUrl が無い/未退避なら404（フロントは CSS バリアントの装丁にフォールバック）。
    """
    book = repo.get_book(book_id)
    if book is None or not book.cover_url:
        raise HTTPException(status_code=404, detail=f"book {book_id} の表紙がありません")
    cover_url = book.cover_url
    if cover_url.startswith("http"):  # 既に外部URL（将来用）＝そのままリダイレクト
        return RedirectResponse(cover_url)

    from ..services.cover_store import get_cover_store  # noqa: PLC0415

    store = get_cover_store()
    data = store.get_bytes(book_id, cover_url) if store is not None else None
    if not data:
        raise HTTPException(status_code=404, detail=f"book {book_id} の表紙がありません")
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/reserve", response_model=Book, deprecated=True)
async def api_reserve(
    payload: ReserveInput,
    repo: RepositoryProtocol = Depends(get_repository),
    _uid: str = Depends(require_reserve_uid),
) -> Book:
    """旧予約モデルの互換エンドポイント。

    2026-06-23以降の通常配本は、配本バッチ内で全冊を本文つき published にする。
    このエンドポイントは旧ワーカー/冪等性テストの退避口としてだけ残す。
    """
    book = reservation_service.reserve_now(repo, payload.book_id, owner_uid=_uid)
    write_queue.enqueue(repo, payload.book_id)
    return book


@router.post("/trigger/planning")
def api_trigger_planning(
    payload: TriggerPlanningInput,
    repo: RepositoryProtocol = Depends(get_repository),
    uid: str = Depends(_uid_from_token),
) -> dict:
    """企画パイプライン（モードA）を手動起動する（デモ用・許可 uid のみ・連打/多重防止）。
    フロント: firestore-provider.ts POST /api/trigger/planning { userId }"""
    # 企画対象/所有者は **検証済み uid を最優先**（C4.9・body を信用しない）。本番では uid＝Firebase
    # 検証済み or demo_uid。body の userId（既定 "u_sakura"）は uid が無いローカル/mock のときだけ
    # 使う。これで「body 既定の u_sakura → fixtures の fld_work で実Drive 404」を防ぐ（#2）。
    user_id = uid or payload.user_id or settings.demo_uid
    owner = uid or settings.demo_uid or user_id
    key = uid or user_id or "anon"
    try:
        trigger_guard.acquire(key, now=time.monotonic())
    except TriggerError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    try:
        # 企画は重い（実Vertex数分）。pubsub なら enqueue して即返し（worker /api/worker/plan が実行）、
        # 生成本はフロントが Firestore 購読で受け取る。mock は in-process 即実行（決定的・オフライン）。
        # observe_uid=検証済み uid（実Google観測の per-uid トークン解決に使う）。
        queued = write_queue.enqueue_planning(
            repo, user_id=user_id, owner_uid=owner, observe_uid=uid
        )
    finally:
        # 例外時もロックを解放（恒久 409 を防ぐ）。
        trigger_guard.release(key, now=time.monotonic())
    logger.info("trigger ok key=%s queued=%s llm=%s", key, queued, settings.publishr_llm)
    return {"ok": True, "queued": queued}
