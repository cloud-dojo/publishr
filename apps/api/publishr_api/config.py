"""BFF設定（環境変数 / .env）。"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # mock = インメモリ(MVP) / firestore = 実Firestore(将来)
    data_source: str = "mock"
    # mock = 決定的キャンド(MVP) / vertex = Vertex Gemini(将来)
    publishr_llm: str = "mock"
    # プロンプトの few-shot 注入: on(既定) / off(dev コスト節約)。採点系は常時ON固定（render.py）。
    prompt_fewshot: str = "on"

    # 実LLM実行プロファイル。未指定は dev、prod はデモ/録画時のみ明示する。
    publishr_run_profile: str = "dev"
    max_iterations: int = Field(default=3, validation_alias="PUBLISHR_MAX_ITERATIONS")
    max_books_per_run: int = Field(default=2, validation_alias="PUBLISHR_MAX_BOOKS_PER_RUN")
    body_pages_min: int = Field(default=3, validation_alias="PUBLISHR_BODY_PAGES_MIN")
    max_body_pages: int = Field(default=5, validation_alias="PUBLISHR_MAX_BODY_PAGES")
    enable_imagen: bool = False
    editor_rounds: int = Field(default=1, validation_alias="PUBLISHR_EDITOR_ROUNDS")
    timeout_seconds: int = Field(default=45, validation_alias="PUBLISHR_TIMEOUT_SECONDS")
    max_estimated_cost_jpy: float = Field(
        default=100.0,
        validation_alias="PUBLISHR_MAX_ESTIMATED_COST_JPY",
    )

    # 予約後の状態遷移タイマー（秒）。デモ用に短く。
    reserve_to_writing_sec: float = 2.0
    writing_to_published_sec: float = 5.0

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # FirestoreRepository のオーナーフィルタ用（MVP 単一ユーザー）。
    # 本番では per-request uid に差し替える（C4.9 Firebase Auth 接続後）。
    demo_uid: str = ""


settings = Settings()
