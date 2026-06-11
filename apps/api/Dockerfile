# ==============================================================================
# Publishr BFF (FastAPI) — Cloud Run 用 Dockerfile
# build context: モノレポルート（apps/api ディレクトリではなくルートから実行）
#
#   gcloud run deploy publishr-api \
#     --source . \
#     --dockerfile apps/api/Dockerfile \
#     --region asia-east1 \
#     --project publishr-498123
# ==============================================================================

FROM python:3.12-slim

WORKDIR /app

# モノレポ内の依存パッケージをコピー（apps/api が参照するもの）
COPY packages/shared-schema/py      packages/shared-schema/py
COPY packages/shared-schema/fixtures packages/shared-schema/fixtures
COPY packages/prompts                packages/prompts
COPY agents                          agents
COPY apps/api                        apps/api

# pip で依存順にインストール（publishr-schema → publishr-agents → publishr-api）
RUN pip install --no-cache-dir \
    ./packages/shared-schema/py \
    ./agents \
    ./apps/api

# publishr_schema.loader は repo レイアウト基準で fixtures を探す。pip install 後は
# その相対パスが壊れるため、コンテナ内の COPY 先を明示する（これが無いと起動時 500）。
ENV PUBLISHR_FIXTURES_DIR=/app/packages/shared-schema/fixtures

EXPOSE 8080

# Cloud Run は PORT 環境変数（既定 8080）でポートを指定する。sh 経由で展開する。
CMD ["sh", "-c", "uvicorn publishr_api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
