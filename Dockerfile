# Publishr BFF (FastAPI) — Cloud Run 用 Dockerfile
# gcloud run deploy --source . で使用（build context = モノレポルート）。
# ★これが本番ビルドに使われる正本（gcloud は root の Dockerfile を自動で拾う）。
# apps/api/Dockerfile は同内容のコピー＝両方を同期させること（差分があると本番だけ壊れる）。

FROM python:3.12-slim

WORKDIR /app

# モノレポ内の依存パッケージをコピー
COPY packages/shared-schema/py       packages/shared-schema/py
COPY packages/shared-schema/fixtures packages/shared-schema/fixtures
COPY packages/prompts                 packages/prompts
COPY agents                           agents
COPY apps/api                         apps/api

# pip で依存順にインストール。本番の任意機能は extra で同梱:
#  - agents[google] = 実Google連携（観測 Drive/Calendar/Tasks ＋ OAuth code 交換
#    google-auth-oauthlib ＋ Office本文抽出）。DATA_SOURCE=firestore＋C4.1 callback に必須。
#  - apps/api[gcs,secret-manager] = 本文GCSオフロード(C3.3)・OAuthトークン保存(C4.1)。
RUN pip install --no-cache-dir \
    ./packages/shared-schema/py \
    "./agents[google]" \
    "./apps/api[gcs,secret-manager]"

# publishr_schema.loader は repo レイアウト基準で fixtures を探す。pip install 後は
# その相対パスが壊れるため、コンテナ内の COPY 先を明示する（これが無いと起動時 500）。
ENV PUBLISHR_FIXTURES_DIR=/app/packages/shared-schema/fixtures
# mode_b 実Vertex 等は packages/prompts/*.md を読む（pip install 後は相対パスが壊れるため明示）。
ENV PUBLISHR_PROMPTS_DIR=/app/packages/prompts

# 非root実行: アプリRCE/依存脆弱性の被害を局限する（Cloud Run は任意UIDを許容）。
# --create-home で HOME を用意し、ライブラリのキャッシュ書込みを appuser 配下に収める。
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Cloud Run は PORT 環境変数（既定 8080）でポートを指定する。sh 経由で展開する。
CMD ["sh", "-c", "uvicorn publishr_api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
