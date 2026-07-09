"""Google OAuth 連携 + Drive Picker フォルダ書込（api-contract.md §4）。

- GET  /api/auth/google/start    : Firebase uid → 署名 state 付き同意URL（{authUrl}）。
- GET  /api/auth/google/callback : state 検証 → code 交換 → token 保存 → connectedSources 更新。
- POST /api/connect/drive-folders: Picker（C1.1.2・フロント担当 UI）が選んだフォルダIDをサーバ保存。

セキュリティ前提（§4）: state は短命・署名付き・uid 紐付き。検証不能な callback は 403。
refresh token・access token・code はログに出さない。OAuth 未設定（state 鍵 / client_id 空）
の環境では start/callback は 503（mock/local では UI 側がモックトグルへ縮退する）。
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from publishr_schema import (
    CalendarConnection,
    ConnectedSources,
    DriveConnection,
    DriveFolderLabel,
    TasksConnection,
)

from ..config import settings
from ..deps import get_repository
from ..repositories.protocol import RepositoryProtocol
from ..schemas import DriveFoldersInput
from ..services import oauth_service
from ..services.rate_limit import auth_limiter
from ..services.token_store import get_token_store
from .api import _verify_uid  # 既存の Firebase IDトークン検証を再利用

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["auth"])

# OAuth state の nonce 単回化（replay 防止・C4.9）。プロセス内で共有。テストは reset()。
nonce_store = oauth_service.NonceStore()


def _oauth_ready() -> bool:
    return bool(settings.oauth_state_secret and settings.google_oauth_client_id)


# ── OAuth 開始 ─────────────────────────────────────────────────────────────────


@router.get("/auth/google/start")
def google_start(authorization: Optional[str] = Header(default=None)) -> dict:
    """Firebase IDトークン検証 → uid → Google 同意画面の authUrl を返す。"""
    if not _oauth_ready():
        raise HTTPException(status_code=503, detail="OAuth 連携は未設定です")
    uid = _verify_uid(authorization)
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です（Google 連携には認証が必要）")
    auth_limiter.hit(f"oauth_start:{uid}", now=time.time())  # C4.9 連打制限（→429）
    auth_url, _state = oauth_service.build_auth_url(
        uid,
        client_id=settings.google_oauth_client_id,
        redirect_uri=settings.oauth_redirect_uri,
        secret=settings.oauth_state_secret,
        now=time.time(),
    )
    return {"authUrl": auth_url}


# ── OAuth コールバック ───────────────────────────────────────────────────────────


def _mark_sources_connected(repo: RepositoryProtocol, uid: str, granted_scopes: list[str]) -> None:
    """付与スコープに応じて connectedSources.{drive,calendar,tasks}.enabled を更新。

    drive.folderIds は Picker（drive-folders）由来のため保持する（enabled のみ更新）。
    """
    from publishr_agents.observe.google_source import ALL_SCOPES

    user = repo.get_user(uid)
    if user is None:
        # 観測自体は fixture でも回るが、接続状態は記録できない（404 にはしない）。
        logger.warning("oauth callback: user not found uid=%s", uid)
        return
    cs = user.connected_sources or ConnectedSources()
    drive = cs.drive or DriveConnection()
    calendar = cs.calendar or CalendarConnection()
    tasks = cs.tasks or TasksConnection()
    new_cs = ConnectedSources(
        drive=drive.model_copy(update={"enabled": ALL_SCOPES["drive"] in granted_scopes}),
        calendar=calendar.model_copy(update={"enabled": ALL_SCOPES["calendar"] in granted_scopes}),
        tasks=tasks.model_copy(update={"enabled": ALL_SCOPES["tasks"] in granted_scopes}),
    )
    repo.upsert_user(user.model_copy(update={"connected_sources": new_cs}))


@router.get("/auth/google/callback")
def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    repo: RepositoryProtocol = Depends(get_repository),
) -> RedirectResponse:
    """Google からの戻り。state 検証 → code 交換 → token 保存 → connectedSources 更新。"""
    if not _oauth_ready():
        raise HTTPException(status_code=503, detail="OAuth 連携は未設定です")
    try:
        payload = oauth_service.verify_state_payload(
            state, secret=settings.oauth_state_secret, now=time.time()
        )
    except oauth_service.StateError as exc:
        # 生 state はログに出さない（理由種別のみ）。
        logger.warning("oauth callback rejected: %s", type(exc).__name__)
        raise HTTPException(status_code=403, detail="state 検証に失敗しました") from exc
    # nonce 単回化（同じ callback の再生＝replay を弾く・C4.9）。
    if not nonce_store.consume(payload["nonce"], now=time.time()):
        logger.warning("oauth callback rejected: nonce replay/missing")
        raise HTTPException(status_code=403, detail="state 検証に失敗しました")
    uid = payload["uid"]
    try:
        result = oauth_service.exchange_code(
            code,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            redirect_uri=settings.oauth_redirect_uri,
        )
    except Exception as exc:  # noqa: BLE001 — code/トークンはログに出さない
        logger.warning("oauth code exchange failed: %s", type(exc).__name__)
        raise HTTPException(status_code=400, detail="トークン交換に失敗しました") from exc
    get_token_store().save(uid, result.token_json)
    _mark_sources_connected(repo, uid, result.granted_scopes)
    logger.info("oauth connected uid=%s scopes=%d", uid, len(result.granted_scopes))
    return RedirectResponse(url=f"{settings.web_app_url}/connect?connected=1", status_code=302)


# ── Drive Picker フォルダ書込（C1.1.2）─────────────────────────────────────────────


def _resolve_connect_uid(authorization: Optional[str]) -> str:
    """connectedSources 書込の uid を解決（本人のみ・サーバ書込＝§4-1 注記）。

    fail-closed: 実データを持つ firestore では検証済み uid を必須にする。実ユーザーデータの
    無いローカル mock（in-memory fixtures）でのみ demo_uid に縮退する（匿名書込は無害）。
    """
    uid = _verify_uid(authorization)
    if uid:
        return uid
    if settings.data_source == "mock" and settings.demo_uid:
        return settings.demo_uid
    raise HTTPException(status_code=401, detail="ログインが必要です")


def _ensure_folder_id(fid: str) -> str:
    """Picker 由来の不透明 folderId を検証。observe の Drive クエリ（q=）を壊す文字は 400。"""
    if not fid or "'" in fid or "\\" in fid or len(fid) > 256:
        raise HTTPException(status_code=400, detail=f"不正なフォルダIDです: {fid!r}")
    return fid


@router.post("/connect/drive-folders")
def set_drive_folders(
    payload: DriveFoldersInput,
    repo: RepositoryProtocol = Depends(get_repository),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Picker で選んだフォルダIDを connectedSources.drive.folderIds[] にサーバ保存する。"""
    uid = _resolve_connect_uid(authorization)
    auth_limiter.hit(f"drive_folders:{uid}", now=time.time())  # C4.9 連打制限（→429）
    user = repo.get_user(uid)
    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    clean_ids = [_ensure_folder_id(fid) for fid in payload.folder_ids]
    labels = [
        DriveFolderLabel(folder_id=_ensure_folder_id(item.folder_id), label=item.label[:32])
        for item in (payload.labels or [])
    ]
    cs = user.connected_sources or ConnectedSources()
    drive = (cs.drive or DriveConnection()).model_copy(
        update={"folder_ids": clean_ids, "labels": labels}
    )
    saved = repo.upsert_user(
        user.model_copy(update={"connected_sources": cs.model_copy(update={"drive": drive})})
    )
    connected = saved.connected_sources or ConnectedSources()
    return {"ok": True, "connectedSources": connected.model_dump(by_alias=True)}
