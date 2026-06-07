# Publishr BFF (FastAPI) — Cloud Run 用 Dockerfile
# gcloud run deploy --source . で使用（build context = モノレポルート）
# apps/api/Dockerfile と同内容。gcloud run deploy が root の Dockerfile を自動で拾う。

FROM python:3.12-slim

WORKDIR /app

# モノレポ内の依存パッケージをコピー
COPY packages/shared-schema/py       packages/shared-schema/py
COPY packages/shared-schema/fixtures packages/shared-schema/fixtures
COPY agents                           agents
COPY apps/api                         apps/api

# pip で依存順にインストール
RUN pip install --no-cache-dir \
    ./packages/shared-schema/py \
    ./agents \
    ./apps/api

EXPOSE 8080

# Cloud Run は PORT 環境変数（既定 8080）でポートを指定する。sh 経由で展開する。
CMD ["sh", "-c", "uvicorn publishr_api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
