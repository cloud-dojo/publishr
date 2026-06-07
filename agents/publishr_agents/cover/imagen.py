"""実 Imagen 画像生成（ENABLE_IMAGEN=true 時のみ・隔離・課金あり）。

google.genai（Vertex 経由）で Imagen を呼び、表紙画像を生成してローカルに保存し coverUrl を返す。
Imagen はリージョン制約があるため `PUBLISHR_IMAGEN_LOCATION`（既定 us-central1）で別管理。
本番では GCS 署名URL等に置換（C3.3）。dev はローカル `.dev-logs/covers/`（gitignore）に保存。
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
    """coverPrompt から Imagen で1枚生成し、PNG をローカル保存して保存先パスを返す。"""
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

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    # book_id はデータ由来。パストラバーサル防止にサニタイズ。
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", book_id)
    out_file = out_path / f"{safe_id}.png"
    out_file.write_bytes(data)
    logger.info("cover image saved: %s (%d bytes)", out_file, len(data))
    return str(out_file)
