"""モードB: 本文編集ループ（編集長 ⇄ 著者1人）。

予約された1冊について、著者が章を執筆 → 編集長が本文ルーブリック5観点で採点 →
弱い章のみ改稿（全文再生成しない＝コスト抑制）。手動1冊スライスは本文3〜5章・最高1R。
mock 既定＝決定的・課金ゼロ。実Pro は `PUBLISHR_LLM=vertex`（ゲート作業として隔離）。

必然性の証跡（基準1の画＝編集長が著者を採点して差し戻す）は `verdicts`（BodyVerdict 列）と
`revised_chapters` に残す。
"""

from __future__ import annotations

from typing import Any, NamedTuple, Optional

from publishr_schema import Book, Persona


class BodyResult(NamedTuple):
    """本文編集ループの成果一式。"""

    book_id: str
    chapters: list[dict[str, Any]]   # [{no, title, text}]（弱章は改稿後）
    body: str                        # 章を連結した markdown 本文
    verdicts: list[dict[str, Any]]   # 各ラウンドの BodyVerdict（採点・弱章・差し戻し理由）
    body_verdict: dict[str, Any]     # 最終ラウンドの BodyVerdict（vertex 正規化全失敗時のみ {}）
    edit_rounds: int                 # 到達ラウンド数（1=初稿のみ / 2=1R改稿）
    # 改稿章＝採用章リスト内の **スライス位置（1-indexed）**。agenda の no ラベル("序"/"01")ではない。
    revised_chapters: list[int]
    # 改稿予算(rounds)を使い切った時点で本当は基準未達だったか（企画リーダーの forced_approve と同義）。
    # mock は rounds 尽きで decision を "approve" に上書きするため body_verdict.decision だけでは
    # 判別できない＝この専用フラグで見分ける。vertex は decision が revise のまま返ることもある
    # （実Vertexで確認済み・7/1レビュー）。いずれも True＝published にはするが本当は未承認。
    forced_approve: bool = False


def write_body_loop(
    book: Book,
    *,
    persona: Optional[Persona] = None,
    reader_profile: Any = None,
    rounds: int = 1,
    llm: str = "mock",
) -> BodyResult:
    """1冊の本文編集ループを回す。

    手動1冊スライスでは `rounds` は「改稿するか否か」の意味で使う（`>=1` で弱章を1回改稿、
    `0` で初稿のみ）。最高3R/約100pのフルループは C2.3 で別途。

    方針（企画リーダーの「3R未達は最良案承認」と統一）: rounds を使い切っても編集長が基準未達の
    ままなら、それでも published にする（デモを止めない）。ただし `forced_approve=True` で
    その事実を残す＝「読める本が必ず出る」ことと「品質担保の事実を隠さない」を両立させる。
    """
    if llm == "mock":
        from .deterministic import run_body_loop_deterministic

        return run_body_loop_deterministic(
            book, persona=persona, reader_profile=reader_profile, rounds=rounds
        )
    if llm == "vertex":
        from .vertex_agent import run_body_loop_vertex

        return run_body_loop_vertex(
            book, persona=persona, reader_profile=reader_profile, rounds=rounds
        )
    raise ValueError(f"unknown llm={llm!r}（mock|vertex）")
