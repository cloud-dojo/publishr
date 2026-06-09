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

    # 同時に予約できる本の上限（reserved+writing の合計・I-16）。モードBコストの天井。
    max_concurrent_reservations: int = Field(
        default=5, validation_alias="PUBLISHR_MAX_CONCURRENT_RESERVATIONS"
    )

    # 執筆ジョブのキュー: mock = in-process（既定・課金ゼロ）/ pubsub = Cloud Pub/Sub（C2.2）。
    queue: str = Field(default="mock", validation_alias="QUEUE")
    pubsub_topic: str = Field(default="publishr-writing", validation_alias="PUBSUB_TOPIC")
    # Pub/Sub push の OIDC 検証用（worker endpoint の audience＝自URL・許可する push SA email）。
    pubsub_push_audience: str = Field(default="", validation_alias="PUBSUB_PUSH_AUDIENCE")
    pubsub_push_sa: str = Field(default="", validation_alias="PUBSUB_PUSH_SA")

    # 予約後の状態遷移タイマー（秒）。デモ用に短く。
    reserve_to_writing_sec: float = 2.0
    writing_to_published_sec: float = 5.0

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://publishr--publishr-498123.asia-east1.hosted.app",
    ]

    # FirestoreRepository のオーナーフィルタ用（MVP 単一ユーザー）。
    # 本番では per-request uid に差し替える（C4.9 Firebase Auth 接続後）。
    demo_uid: str = ""

    # 手動トリガー（POST /api/trigger/planning）のガード（C4前ゲート）。
    # allowed_trigger_uids が空 = dev（全許可）。
    # TODO(C4.9/本番): publishr_llm=vertex（実課金）かつ allowlist 空のままデプロイすると
    # 誰でもトリガー＝LLM課金/DoS。本番は許可 uid を必須にし、日次コスト上限も併用する。
    allowed_trigger_uids: list[str] = []
    # 同一 uid の連打を防ぐ最小間隔（秒）。mock は高速だが暴発防止に効かせる。
    trigger_min_interval_sec: float = 5.0


settings = Settings()
