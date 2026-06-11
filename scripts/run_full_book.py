"""本番相当の1冊（実Vertex本文＋実Imagen表紙）を生成し、ローカルmock閲覧用に反映する。

  GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  uv run python -m scripts.run_full_book --src-book b_makasekata --chapters 6 --chars 6000 --rounds 1

実LLM/Imagen **課金あり**。元本(agenda/persona/plan)を使って:
  ① mode_b 実Vertex で本文を長文生成（編集長⇄著者・弱章のみ改稿）
  ② coverPrompt から実Imagen で表紙1枚（apps/web/public/covers/ へ保存）
  ③ 生成本文＋coverUrl を web mock fixtures に **新規book** として追加
→ ローカル本番ビルド（next build/start・mock）で `/read/{dst}`・`/books/{dst}` を閲覧。
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from publishr_schema import load_books, load_personas

_WEB_FIXTURES = Path("apps/web/src/lib/shared-schema/fixtures/books.json")
_COVERS_DIR = "apps/web/public/covers"


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")


def _cover_prompt(book) -> str:
    return (
        "A sophisticated, minimal book-cover illustration for a Japanese business book. "
        f"Theme/title: {book.title}. Core message: {book.core_message or ''}. "
        "Abstract symbolic art, elegant muted color palette, professional, calm. "
        "Absolutely NO text, NO letters, NO words. Portrait 3:4 composition."
    )


def _upsert_web_fixture(book_dict: dict) -> None:
    """web mock fixtures(books.json) に book を追加/置換して書き戻す。"""
    data = json.loads(_WEB_FIXTURES.read_text(encoding="utf-8"))
    data = [b for b in data if b.get("id") != book_dict["id"]]
    data.append(book_dict)
    _WEB_FIXTURES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _upsert_firestore(book_dict: dict, persona, owner_uid: str) -> None:
    """生成本＋著者を **ライブFirestore** に upsert（live demo 用・owner スコープ）。

    本は owner_uid 所有で books/{id} に、著者は global の personas/{id} に置く（web は personas を
    owner 非依存で読む）。表紙PNGは apps/web/public/covers/ にあり App Hosting が配信する。
    """
    import firebase_admin  # noqa: PLC0415
    from firebase_admin import firestore  # noqa: PLC0415

    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    db = firestore.client()
    doc = dict(book_dict)
    doc["ownerUid"] = owner_uid
    db.collection("books").document(doc["id"]).set(doc)
    if persona is not None:
        db.collection("personas").document(persona.id).set(persona.model_dump(by_alias=True))
    print(f"✅ Firestore upsert: books/{doc['id']} owner={owner_uid} / personas/{persona.id if persona else '-'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="本番相当の1冊（実Vertex本文＋実Imagen表紙）を生成・閲覧反映")
    parser.add_argument("--src-book", default="b_makasekata", help="元本ID（agenda/persona/planを使う）")
    parser.add_argument("--dst-id", default="b_fullbook", help="生成本のID（fixtures新規）")
    parser.add_argument("--chapters", type=int, default=6, help="採用章数（PUBLISHR_BODY_MAX_CHAPTERS）")
    parser.add_argument("--chars", type=int, default=6000, help="各章の目標文字数（PUBLISHR_BODY_CHARS_PER_CHAPTER）")
    parser.add_argument("--rounds", type=int, default=1, help="最高改稿ラウンド（編集長⇄著者）")
    parser.add_argument("--no-imagen", action="store_true", help="表紙Imagenをスキップ（本文のみ）")
    parser.add_argument(
        "--firestore-owner",
        default=None,
        help="指定時、生成本をライブFirestoreのこのownerUidにもupsert（live demo用・要ADC）",
    )
    args = parser.parse_args()

    _ensure_vertex_env()
    os.environ["PUBLISHR_BODY_MAX_CHAPTERS"] = str(args.chapters)
    os.environ["PUBLISHR_BODY_CHARS_PER_CHAPTER"] = str(args.chars)

    src = next((b for b in load_books() if b.id == args.src_book), None)
    if src is None:
        raise SystemExit(f"元本が見つかりません: {args.src_book}")
    persona = next((p for p in load_personas() if p.id == src.author_persona_id), None)

    t0 = time.monotonic()
    # ① 本文（実Vertex・長文・編集ループ）
    from publishr_agents.mode_b import write_body_loop

    print(f"== 本文生成（実Vertex・{args.chapters}章×~{args.chars}字・最高{args.rounds}R）==", flush=True)
    tb = time.monotonic()
    result = write_body_loop(src, persona=persona, rounds=args.rounds, llm="vertex")
    body_sec = time.monotonic() - tb
    body = result.body
    print(f"  本文 {len(body)}字 / {len(result.chapters)}章 / editRounds={result.edit_rounds} / ⏱{body_sec:.0f}秒", flush=True)
    for i, v in enumerate(result.verdicts, 1):
        print(f"    R{i}: score={v['score']} decision={v['decision']} weak={v['weakChapters']}", flush=True)

    # ② 表紙（実Imagen）
    cover_url = None
    cover_sec = 0.0
    if not args.no_imagen:
        from publishr_agents.cover.imagen import generate_cover_image

        print("== 表紙生成（実Imagen・3:4）==", flush=True)
        tc = time.monotonic()
        path = generate_cover_image(_cover_prompt(src), book_id=args.dst_id, out_dir=_COVERS_DIR)
        cover_sec = time.monotonic() - tc
        cover_url = f"/covers/{Path(path).name}"
        print(f"  保存: {path} → coverUrl={cover_url} / ⏱{cover_sec:.0f}秒", flush=True)

    # ③ web mock fixtures へ新規book反映（既存元本の体裁を流用）
    base = src.model_dump(by_alias=True)
    chapters = len(result.chapters)
    base.update(
        {
            "id": args.dst_id,
            "title": f"{src.title}（実生成版）",
            "status": "published",
            "shelf": "library",
            "body": body,
            "coverUrl": cover_url,
            "editRound": result.edit_rounds,
            "estimatedChapters": chapters,
            "estimatedMinutes": max(10, len(body) // 600),
        }
    )
    _upsert_web_fixture(base)
    if args.firestore_owner:
        _upsert_firestore(base, persona, args.firestore_owner)
    total_sec = time.monotonic() - t0
    print(f"\n✅ web mock fixtures に {args.dst_id} を反映（body {len(body)}字・cover={cover_url}）")
    print(f"⏱ 計時: 本文 {body_sec:.0f}秒 ＋ 表紙 {cover_sec:.0f}秒 ＝ 合計 {total_sec:.0f}秒", flush=True)
    print("   閲覧: NEXT_PUBLIC_DATA_SOURCE=mock で本番ビルド→ /read/" + args.dst_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
