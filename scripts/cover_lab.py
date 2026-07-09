"""表紙ラボ（別ライン・実Imagen・課金あり）— step5_cover の coverPrompt を実生成して見る。

この対話フローでは実行しない＝**ユーザーが別途実行**してコスト管理する。代表的な数冊
（voiceStyle×format を散らした見本）について Flash で coverPrompt を作り、実 Imagen で
各 N 枚生成して `publishr_other/cover_lab/<timestamp>/` に保存、使用 coverPrompt を
`prompts.json` にログする。装画の出来を目で見て採否を決め、良ければ採用プロンプトを確定する。

使い方（Windows 企業TLS 対応・ADC 必須）:
  uv run --with truststore python -m scripts.cover_lab --n 3                                     # 既定 imagen-4（文字焼き込みが大幅減）
  uv run --with truststore python -m scripts.cover_lab --n 2 --model imagen-3.0-generate-002     # 旧モデルと比較
  uv run --with truststore python -m scripts.cover_lab --books 2 --n 4                           # 先頭2冊×4枚

注意:
- 実 Imagen は画像課金。--n×--books 枚を生成する（既定 2×4=8枚）。
- 既定モデルは **imagen-4.0-generate-001**（imagen-3 は日本語/英字を題字に焼き込みやすいため）。
  もし model-not-found 等で失敗する場合は `--model imagen-4.0-generate-preview-06-06` を試す。
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

# Windows 企業TLS 回避（memory: publishr-windows-vertex-ssl）。
os.environ.pop("SSLKEYLOGFILE", None)
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001
    pass


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    # Flash(coverPrompt) と Imagen の双方を us-central1 に寄せる（Pro/Imagen クォータ実績）。
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    os.environ.setdefault("PUBLISHR_IMAGEN_LOCATION", "us-central1")
    # ラボはローカル保存（GCS へ上げない）。
    os.environ.pop("PUBLISHR_COVER_BUCKET", None)


# 代表的な被験書（voiceStyle×format を散らす）＝ coverPrompt の作風翻訳を見るための見本。
# 各冊は「1冊ぶんの企画書（STEP2 PlanProposal の確定版）」を模した形＝表紙は企画書ベースの1対1で回す。
_SAMPLE_BOOKS = [
    {"id": "lab_logical", "title": "任せ方の設計図", "coreMessage": "権限は気分でなく構造で配る。",
     "voiceStyle": "ロジカル", "format": "自己啓発",
     "emotionalTone": "静かに背中を押す", "bookRole": "ハンドブック",
     "keyInsights": ["権限を構造で配る", "任せる範囲を線で引く", "信頼の段階的移譲"],
     "targetSegment": "初めて年上の実力者を率いる新任マネージャー", "readerSituation": "任せ方に迷う移行期"},
    {"id": "lab_thoughtful", "title": "問いが組織を変える", "coreMessage": "答えを配るのでなく、問いを残す。",
     "voiceStyle": "思想的", "format": "問答",
     "emotionalTone": "静かに問いを灯す", "bookRole": "内省・対話",
     "keyInsights": ["答えでなく問いを残す", "問いが思考を耕す", "余白としての問い"],
     "targetSegment": "指示が多すぎると感じるリーダー", "readerSituation": "自走しないチームに悩む局面"},
    {"id": "lab_sensory", "title": "余白の経営", "coreMessage": "間（ま）が判断の質を決める。",
     "voiceStyle": "感覚的", "format": "エッセイ",
     "emotionalTone": "落ち着いて整える", "bookRole": "エッセイ・内省",
     "keyInsights": ["間が判断を決める", "余白を設計する", "急がない速さ"],
     "targetSegment": "多忙で即断を迫られる管理職", "readerSituation": "余白なく疲弊している局面"},
    {"id": "lab_gritty", "title": "現場で決めきる", "coreMessage": "撤退条件まで決めて、初めて決定だ。",
     "voiceStyle": "泥臭い・現場", "format": "ケース",
     "emotionalTone": "凛と決める", "bookRole": "ケース・ストーリー",
     "keyInsights": ["撤退条件まで決める", "決めきる胆力", "現場で線を引く"],
     "targetSegment": "撤退判断を先送りしがちな現場リーダー", "readerSituation": "決めきれず長引くプロジェクト"},
]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="表紙ラボ（実Imagen・課金あり・別ライン実行）")
    p.add_argument("--n", type=int, default=2, help="各被験書あたりの生成枚数（モデルの揺れを見る）")
    p.add_argument("--books", type=int, default=len(_SAMPLE_BOOKS), help="被験書の数（先頭から）")
    p.add_argument("--model", default="imagen-4.0-generate-001",
                   help="PUBLISHR_IMAGEN_MODEL 上書き（ラボ既定 imagen-4.0-generate-001。旧比較は imagen-3.0-generate-002）")
    p.add_argument("--out", default="publishr_other/cover_lab", help="出力ルート")
    args = p.parse_args(argv)

    _ensure_vertex_env()
    if args.model:
        os.environ["PUBLISHR_IMAGEN_MODEL"] = args.model

    from publishr_agents.cover.imagen import generate_cover_image  # noqa: PLC0415
    from publishr_agents.cover.vertex_agent import design_covers_vertex  # noqa: PLC0415
    from publishr_schema import GeneratedPersona  # noqa: PLC0415

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    model = os.environ.get("PUBLISHR_IMAGEN_MODEL", "imagen-3.0-generate-002")
    samples = _SAMPLE_BOOKS[: args.books]
    print(f"== 表紙ラボ: model={model} books={len(samples)} n={args.n} → {out_dir} ==", flush=True)

    # 1冊＝1企画書を別々に渡す（1対1）。plan に企画書の項目を載せ、表紙を企画書ベースで生成する。
    books = [
        {
            "personaId": b["id"],
            "bookDraft": {"bookId": b["id"], "title": b["title"], "coreMessage": b["coreMessage"]},
            "plan": {
                "emotionalTone": b["emotionalTone"], "bookRole": b["bookRole"],
                "keyInsights": b["keyInsights"], "targetSegment": b["targetSegment"],
                "readerSituation": b["readerSituation"],
            },
        }
        for b in samples
    ]
    personas = [
        GeneratedPersona(persona_id=b["id"], name="lab", voice_style=b["voiceStyle"], format=b["format"])
        for b in samples
    ]

    # 1) coverPrompt を Flash で生成（画像はまだ作らない＝安い）。
    designed = design_covers_vertex(books, personas, enable_imagen=False)
    log: list[dict] = []
    for b, d in zip(samples, designed):
        cp = str(d.get("coverPrompt", "") or "")
        print(f"\n◆ {b['title']}（{b['voiceStyle']}×{b['format']}）", flush=True)
        print(f"  coverPrompt: {cp[:240]}{'…' if len(cp) > 240 else ''}", flush=True)
        log.append({"id": b["id"], "title": b["title"], "voiceStyle": b["voiceStyle"],
                    "format": b["format"], "coverPrompt": cp})
        if not cp:
            print("  （coverPrompt 空＝スキップ）", flush=True)
            continue
        # 2) 同じ coverPrompt で N 枚生成（モデルの揺れ・出来を見る）。
        for n in range(args.n):
            bid = f"{b['id']}_v{n + 1}"
            try:
                path = generate_cover_image(cp, book_id=bid, out_dir=str(out_dir))
                print(f"    [{n + 1}/{args.n}] {path}", flush=True)
            except Exception as exc:  # noqa: BLE001 — 1枚の失敗で全体を止めない
                print(f"    [{n + 1}/{args.n}] 失敗: {exc}", flush=True)

    (out_dir / "prompts.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 完了: {out_dir}（画像PNG＋prompts.json）。画像を見て採否を判断してください。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
