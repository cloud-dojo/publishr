"""BFF設定（環境変数 / .env）。"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # mock = インメモリ(MVP) / firestore = 実Firestore(将来)
    data_source: str = "mock"
    # mock = 決定的キャンド(MVP) / vertex = Vertex Gemini(将来)
    publishr_llm: str = "mock"
    # プロンプトの few-shot 注入: on(既定) / off(dev コスト節約)。採点系は常時ON固定（render.py）。
    prompt_fewshot: str = "on"

    # 予約後の状態遷移タイマー（秒）。デモ用に短く。
    reserve_to_writing_sec: float = 2.0
    writing_to_published_sec: float = 5.0

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # FirestoreRepository のオーナーフィルタ用（MVP 単一ユーザー）。
    # 本番では per-request uid に差し替える（C4.9 Firebase Auth 接続後）。
    demo_uid: str = ""


settings = Settings()
