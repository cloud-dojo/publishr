"""⚠️ PARKED（将来実装・画像生成）: 現行メインパイプライン未接続（今回スコープ外）。
削除せず将来実装用に温存する（表紙の画像/ロゴ生成は今回やらない方針）。

実 Imagen 画像生成（ENABLE_IMAGEN=true 時のみ・隔離・課金あり）。

google.genai（Vertex 経由）で Imagen を呼び、表紙画像を生成して coverUrl を返す。
Imagen はリージョン制約があるため `PUBLISHR_IMAGEN_LOCATION`（既定 us-central1）で別管理。
保存先（本文C3.3と同方針）:
  - 本番（`PUBLISHR_COVER_BUCKET` 設定時）= 非公開 GCS バケットへ退避し object パスを返す。
    フロントは BFF `/api/books/{id}/cover` でサーバ側 read 配信（GCSを外部に晒さない）。
  - dev（未設定）= ローカル `.dev-logs/covers/`（gitignore）。
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_IMAGEN_MODEL = "imagen-3.0-generate-002"
DEFAULT_IMAGEN_LOCATION = "us-central1"
DEFAULT_OUT_DIR = ".dev-logs/covers"


def generate_cover_image(prompt: str, *, book_id: str, out_dir: str = DEFAULT_OUT_DIR) -> str:
    """coverPrompt から Imagen で1枚生成し、保存先（GCS object パス or ローカルパス）を返す。"""
    from google import genai
    from google.genai import types

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    location = os.environ.get("PUBLISHR_IMAGEN_LOCATION", DEFAULT_IMAGEN_LOCATION)
    model = os.environ.get("PUBLISHR_IMAGEN_MODEL", DEFAULT_IMAGEN_MODEL)

    client = genai.Client(vertexai=True, project=project, location=location)
    resp = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="3:4"),
    )
    images = getattr(resp, "generated_images", None) or []
    img = images[0].image if images else None
    if img is None or not getattr(img, "image_bytes", None):
        # RAI セーフティ等で画像が返らない場合は理由を添えて明示エラー（呼出側で coverUrl=None 縮退）。
        reason = getattr(images[0], "rai_filtered_reason", None) if images else None
        raise RuntimeError(f"Imagen が画像を返しませんでした（book_id={book_id}, rai={reason}）")
    data = img.image_bytes

    # book_id はデータ由来。パストラバーサル防止にサニタイズ。
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", book_id)

    # 本番: 非公開 GCS バケットへ退避し object パスを coverUrl に。pipeline 段階の book_id は
    # run 間で衝突しうる（book_<personaId>）ため短い uuid を付け、run ごとに別オブジェクト
    # ＝過去本の表紙を上書きしない（入荷本の run ユニークIDと同方針）。
    bucket = os.environ.get("PUBLISHR_COVER_BUCKET", "").strip()
    if bucket:
        import uuid  # noqa: PLC0415

        from google.cloud import storage  # noqa: PLC0415

        name = f"covers/{safe_id}_{uuid.uuid4().hex[:8]}.png"
        storage.Client().bucket(bucket).blob(name).upload_from_string(
            data, content_type="image/png"
        )
        logger.info("cover image uploaded: gs://%s/%s (%d bytes)", bucket, name, len(data))
        return name

    # dev: ローカル `.dev-logs/covers/`（gitignore）に保存。
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"{safe_id}.png"
    out_file.write_bytes(data)
    logger.info("cover image saved: %s (%d bytes)", out_file, len(data))
    return str(out_file)
