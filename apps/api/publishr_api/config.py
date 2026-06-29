"""BFF設定（環境変数 / .env）。"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # mock = インメモリ(MVP) / firestore = 実Firestore(将来)
    data_source: str = "mock"
    # 観測ソース: fixture（既定・佐倉のキャンド観測＝決定的） / google（実Drive/Calendar/Tasks）。
    # google でも、ユーザー未接続・トークン無し・取得失敗時は fixture へ自動フォールバック（C1.1）。
    observe: str = Field(default="fixture", validation_alias="PUBLISHR_OBSERVE")
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
    # モードB本文の「本全体」目標文字数（I-35）。配本runの著者へ {{body_volume}} として注入。
    # 既定12,000字（1万〜2万字帯）。dev で短くするなら PUBLISHR_BODY_CHAR_TARGET で下げる。
    body_char_target: int = Field(default=12_000, validation_alias="PUBLISHR_BODY_CHAR_TARGET")
    enable_imagen: bool = False
    # 配本パイプライン: True=4テーマ1-1-1-1のセット企画（予約制廃止改定 2026-06-23・既定）/
    # False=旧・単一テーマ（ロールバック用キルスイッチ）。
    set_pipeline: bool = Field(default=True, validation_alias="PUBLISHR_SET_PIPELINE")
    # お気に入り著者の「再登板（新刊）」を1配本で起用する確率（%）。既定25（≒4冊中1冊の体感）。
    # システム側で決定的に抽選（seed=配本トークン）。0=無効。比率/ランダム性は将来A/B（mvp-scope §9）。
    favorite_feature_pct: int = Field(default=25, validation_alias="PUBLISHR_FAVORITE_FEATURE_PCT")
    editor_rounds: int = Field(default=1, validation_alias="PUBLISHR_EDITOR_ROUNDS")
    # モードB本文編集ループの最高改稿ラウンド数（§6-2「最高3R」）。worker が mode_b に渡す。
    body_edit_rounds: int = Field(default=3, validation_alias="PUBLISHR_BODY_EDIT_ROUNDS")
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
    # 企画(モードA)の非同期キュー（重い実Vertex企画を /trigger/planning から切り離す）。
    pubsub_planning_topic: str = Field(
        default="publishr-planning", validation_alias="PUBSUB_PLANNING_TOPIC"
    )
    # 企画 worker（/api/worker/plan）push の OIDC audience（＝その push_endpoint URL）。
    pubsub_plan_push_audience: str = Field(
        default="", validation_alias="PUBSUB_PLAN_PUSH_AUDIENCE"
    )

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

    # 課金アクション（予約→実Vertex執筆）を認証ユーザー限定にする fail-closed フラグ。
    # True=有効な Firebase IDトークン必須・無/不正は401（完全な外部をブロック）。
    # 実課金デプロイ（PUBLISHR_LLM=vertex）では True 推奨。既定 False（ローカル/mockは匿名可）。
    require_reserve_auth: bool = Field(default=False, validation_alias="PUBLISHR_REQUIRE_RESERVE_AUTH")

    # 手動トリガー（POST /api/trigger/planning）のガード（C4前ゲート）。
    # allowed_trigger_uids が空 = dev（全許可）。
    # TODO(C4.9/本番): publishr_llm=vertex（実課金）かつ allowlist 空のままデプロイすると
    # 誰でもトリガー＝LLM課金/DoS。本番は許可 uid を必須にし、日次コスト上限も併用する。
    allowed_trigger_uids: list[str] = []
    # 同一 uid の連打を防ぐ最小間隔（秒）。mock は高速だが暴発防止に効かせる。
    trigger_min_interval_sec: float = 5.0
    # OAuth start / Drive フォルダ書込のレート制限（C4.9・同一 uid の最小間隔・秒）。
    auth_min_interval_sec: float = Field(
        default=3.0, validation_alias="PUBLISHR_AUTH_MIN_INTERVAL_SEC"
    )

    # ── Google OAuth 連携（Drive/Calendar/Tasks・api-contract.md §4）─────────────
    # OAuth クライアント（GCP コンソール発行・Web アプリ）。空なら start は 503。
    google_oauth_client_id: str = Field(default="", validation_alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field(
        default="", validation_alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    # Google 同意後の戻り先（このBFFの `/api/auth/google/callback`）。本番は実URLを設定。
    oauth_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/google/callback",
        validation_alias="PUBLISHR_OAUTH_REDIRECT_URI",
    )
    # state（CSRF/uid 紐付け）の HMAC 署名鍵。空なら OAuth 連携は無効（start/callback は 503）。
    oauth_state_secret: str = Field(default="", validation_alias="PUBLISHR_OAUTH_STATE_SECRET")
    # callback 完了後にフロントを戻す先（`/connect?connected=1`）。
    web_app_url: str = Field(
        default="http://localhost:3000", validation_alias="PUBLISHR_WEB_APP_URL"
    )
    # refresh token 保存先: file（既定・.secrets）/ secret_manager（本番・G1-5）。
    oauth_token_store: str = Field(default="file", validation_alias="PUBLISHR_OAUTH_TOKEN_STORE")
    # secret_manager 利用時の GCP プロジェクト。
    secret_manager_project: str = Field(
        default="", validation_alias="PUBLISHR_SECRET_MANAGER_PROJECT"
    )

    # ── モードB本文(body)の保存先（C3.3・GCSオフロード）─────────────────────────
    # inline（既定）= body を books ドキュメントにそのまま持つ（mock/dev・課金ゼロ・従来挙動）。
    # gcs = 本文を非公開バケットへ退避し、ドキュメントには bodyUrl だけ残す（本番・実GCP）。
    body_store: str = Field(default="inline", validation_alias="PUBLISHR_BODY_STORE")
    # gcs 退避先（非公開バケット・docs/infra/gcp-setup-log.md）。
    body_bucket: str = Field(
        default="publishr-contents-498123", validation_alias="PUBLISHR_BODY_BUCKET"
    )
    # 直接ダウンロード用 署名URL の有効秒（既定15分・通常はサーバ側readで本文を返す）。
    body_signed_url_ttl_sec: int = Field(
        default=900, validation_alias="PUBLISHR_BODY_SIGNED_URL_TTL_SEC"
    )
    # 表紙画像(Imagen)の退避先 GCS バケット（本文と同バケット・prefix covers/）。空なら
    # cover 配信エンドポイントは無効（GCS read 不可）。本文と同方針＝非公開・サーバ側 read。
    cover_bucket: str = Field(
        default="publishr-contents-498123", validation_alias="PUBLISHR_COVER_BUCKET"
    )


settings = Settings()
