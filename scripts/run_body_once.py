"""モードB「手動1冊」本文編集ループ 実行CLI（編集長 ⇄ 著者・弱章のみ改稿）。

  uv run python -m scripts.run_body_once --book-id b_makasekata                # mock（決定的・課金ゼロ）
  uv run python -m scripts.run_body_once --book-id b_makasekata --llm vertex   # 実Pro（要GCP・課金）

本文3〜5章・最高1R。編集長が本文5観点で採点→弱章のみ改稿→承認、の証跡（必然性=基準1の画）を出す。
mock は課金なし。vertex は実Pro（本文=読者が読む唯一の成果物）。
"""

from __future__ import annotations

import argparse
import json
import os

from publishr_schema import load_books, load_personas


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")


def main() -> int:
    parser = argparse.ArgumentParser(description="モードB 手動1冊 本文編集ループ")
    parser.add_argument("--book-id", default="b_makasekata", help="対象書籍ID（fixtures/books.json）")
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--rounds", type=int, default=2, help="最大改稿ラウンド数（既定2・本番3まで）")
    parser.add_argument("--json", action="store_true", help="結果を JSON で出力")
    args = parser.parse_args()

    book = next((b for b in load_books() if b.id == args.book_id), None)
    if book is None:
        raise SystemExit(f"書籍が見つかりません: {args.book_id}")
    persona = next((p for p in load_personas() if p.id == book.author_persona_id), None)
    if args.llm == "vertex":
        _ensure_vertex_env()

    from publishr_agents.mode_b import write_body_loop

    print(f"== モードB 本文編集ループ（book={book.id} llm={args.llm} rounds={args.rounds}）==")
    result = write_body_loop(book, persona=persona, rounds=args.rounds, llm=args.llm)

    if args.json:
        print(json.dumps(result._asdict(), ensure_ascii=False, indent=2))
        return 0

    print(f"著者: {persona.name if persona else '?'} / 章数: {len(result.chapters)} / editRounds: {result.edit_rounds}")
    for i, v in enumerate(result.verdicts, 1):
        print(f"  R{i}: score={v['score']} decision={v['decision']} weakChapters={v['weakChapters']}")
        if v.get("editorFeedback"):
            print(f"      feedback: {v['editorFeedback']}")
    print(f"改稿した章（弱章のみ）: {result.revised_chapters}")

    # C5.6: 編集長⇄著者の差し戻しループ（対立②）を Langfuse に best-effort 計装（キー無なら no-op）。
    from publishr_agents.observability import trace_pipeline

    status = trace_pipeline(
        {
            "theme": book.title,
            "approved": result.body_verdict.get("decision") == "approve",
            "editing_rounds": [{"round": i, **v} for i, v in enumerate(result.verdicts, 1)],
        }
    )
    print(f"Langfuse(editing_loop): {status}")

    print("\n--- 本文（先頭2章プレビュー） ---")
    for ch in result.chapters[:2]:
        print(ch["text"])

    ok = len(result.chapters) >= 1 and result.body_verdict.get("decision") == "approve"
    print(f"判定: {'OK（編集長承認・本文生成）' if ok else 'WEAK/未承認'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
