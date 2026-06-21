"""お気に入り著者IDの整合（backend 非依存・純粋）。

vertex の casting LLM は `fromFavorite=true` は立てても `personaId` を**新規生成**しがちで、
登録時の(run-unique)IDが失われる → front の `favorites.has(persona.id)` と一致せず
「お気に入り作家が次runに引き継がれない」(deterministic は personaId を echo するので動くが、
本番 vertex で破綻する)。casting 後にここで from_favorite 枠の `persona_id`/`name` を
登録済みお気に入りの値へ**決定論的に再スタンプ**して固定する（LLMの気まぐれIDに依存しない）。

persist_mapping の `_persona_uid` は from_favorite なら run-token を付けず `persona_id` を
そのまま使う＝ここで固定したIDが run をまたいで安定し、★認識・新刊の著者紐付けが成立する。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import GeneratedPersonaSet


def reconcile_favorite_ids(
    persona_set: GeneratedPersonaSet,
    favorite_authors: Optional[list[dict[str, Any]]],
) -> GeneratedPersonaSet:
    """from_favorite な枠の persona_id/name を登録済みお気に入りへ固定（純粋・非破壊）。

    - 名前一致を優先し、無ければ登録順で割当（LLMが名前を変えても order で拾える）。
    - お気に入りの裏付けが無い from_favorite 枠は通常枠へ降格＝安定IDを誤付与しない。
    """
    favs = [f for f in (favorite_authors or []) if f.get("personaId")]
    if not favs:
        # 裏付けが無いのに from_favorite が立っていたら降格（run-unique 化）。
        if any(p.from_favorite for p in persona_set.personas):
            demoted = [
                p.model_copy(update={"from_favorite": False}) if p.from_favorite else p
                for p in persona_set.personas
            ]
            return persona_set.model_copy(update={"personas": demoted})
        return persona_set

    by_name = {f.get("name"): f for f in favs if f.get("name")}
    remaining = list(favs)
    out = []
    for p in persona_set.personas:
        if not p.from_favorite:
            out.append(p)
            continue
        fav = by_name.get(p.name)
        if fav is not None and fav in remaining:
            remaining.remove(fav)
        elif remaining:
            fav = remaining.pop(0)
        else:
            fav = None
        if fav is not None:
            out.append(
                p.model_copy(
                    update={"persona_id": fav["personaId"], "name": fav.get("name", p.name)}
                )
            )
        else:
            out.append(p.model_copy(update={"from_favorite": False}))
    return persona_set.model_copy(update={"personas": out})
