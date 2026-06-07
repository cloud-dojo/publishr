"""モードB: 後追い執筆ワーカー（キャンド本文生成）。

予約された1冊について、作家ペルソナを着た本文を生成する。
MVPでは決定的なキャンド出力。デモ本は品質を担保した本文を返す。"""

from __future__ import annotations

from publishr_schema import Book, Persona, load_personas

# デモ本（任せ方の設計図）第3章。品質傾斜配分により、ここだけ作り込む。
_MAKASE_BODY = """## 第3章 権限の設計図

佐倉さん。前の章で、あなたの7人のチームを一枚の地図に描いた。今度はその地図の上に、「どこまで渡すか」の線を引いていく。これが本書の核心だ。

多くのリーダーが委譲でつまずくのは、能力の問題ではない。渡す範囲を「気分」で決めているからだ。今日は任せる、来週はやっぱり口を出す――これでは部下は動けない。

そこで、あなたの現場に合わせた**三層モデル**を提案したい。第一層は「報告のみ」、第二層は「相談の上で実行」、第三層は「完全に委ねる」。7人それぞれを、この三層のどこに置くかを決める。

注意してほしいのは、この線は固定ではないということだ。四半期ごとに引き直してよい。むしろ、引き直す前提で設計するほうが現実的だ。

結論から言う。任せられないのは、あなたの度量の問題ではない。設計の問題だ。
"""


def _personas() -> dict[str, Persona]:
    return {p.id: p for p in load_personas()}


def write_body(book: Book) -> str:
    """予約された書籍の本文を生成（キャンド）。"""
    personas = _personas()
    persona = personas.get(book.author_persona_id)
    author_name = persona.name if persona else "担当作家"

    if book.id == "b_makasekata":
        return _MAKASE_BODY

    first = book.agenda[0].title if book.agenda else "第1章"
    return (
        f"## {first}\n\n"
        f"{book.preface_sample}\n\n"
        f"――{author_name} は、ここから章を書き継いでいく。"
    )
