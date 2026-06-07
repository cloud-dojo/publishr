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
COPY agents                          agents
COPY apps/api                        apps/api

# pip で依存順にインストール（publishr-schema → publishr-agents → publishr-api）
RUN pip install --no-cache-dir \
    ./packages/shared-schema/py \
    ./agents \
    ./apps/api

EXPOSE 8000

# Cloud Run は PORT 環境変数でポートを渡す場合がある。uvicorn はデフォルト 8000。
CMD ["uvicorn", "publishr_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
