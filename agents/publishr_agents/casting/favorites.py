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

import hashlib
from typing import Any, Optional

from publishr_schema import AuthorCasting, GeneratedPersonaSet


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


# ── 「お気に入りの誰かを配本ごと約N%で1冊だけ起用」する決定的ゲート ──────────────
# 確率はここ（オーケストレーション層が呼ぶ純関数）が握る＝LLMの気まぐれや mock の
# 「あれば必ず混入」に依存しない。同一配本(seed)で再現的・seed が変われば配本ごとに振り直す。
# 設計: docs/design/agent-io-contract.md §5-3a / mvp-scope.md §9（比率は将来A/B）。
FAVORITE_FEATURE_PCT_DEFAULT = 25  # 既定25%（≒「4冊中1冊はお気に入りの誰か」の体感）。0=無効・100=必ず。


def _favorite_id(fav: dict[str, Any]) -> str:
    return str(fav.get("personaId") or fav.get("name") or "")


def _bucket(key: str) -> int:
    """key を 0..99 の決定的バケットへ。

    hashlib を使う＝プロセス間で安定（組込み hash() は PYTHONHASHSEED で実行ごとに揺れ、
    eval/pipeline/テストの再現性を壊すため不可）。
    """
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % 100


def choose_favorite_feature(
    plan_ids: list[str],
    favorite_authors: Optional[list[dict[str, Any]]],
    *,
    seed: str = "",
    pct: int = FAVORITE_FEATURE_PCT_DEFAULT,
) -> Optional[tuple[int, dict[str, Any]]]:
    """この配本で「お気に入りの誰かを1冊だけ起用するか」を決定的に決める（純粋）。

    返り値 ``(idx, favorite)``: ``plan_ids[idx]`` の枠をこの favorite にする。起用しないなら None。
    - 判定は ``(seed, お気に入り集合)`` に対して決定的＝同一配本(seed)で再現的・seed（配本トークン）が
      変われば配本ごとに新たに抽選する。
    - お気に入りが複数なら「誰か1人」を決定的に選ぶ（ユーザー意図＝“お気に入りの誰か”が約 pct% で再登板）。
    - お気に入り空 / plan_ids 空 / ``pct<=0`` は None。``pct>=100`` は必ず起用。
    """
    favs = [f for f in (favorite_authors or []) if _favorite_id(f)]
    if not favs or not plan_ids or pct <= 0:
        return None
    sig = "|".join(sorted(_favorite_id(f) for f in favs))
    if pct < 100 and _bucket(f"feature|{seed}|{sig}") >= pct:
        return None  # 抽選はずれ＝この配本はお気に入り起用なし（通常著者のみ）。
    fav = favs[_bucket(f"who|{seed}|{sig}") % len(favs)]
    idx = _bucket(f"where|{seed}|{sig}") % len(plan_ids)
    return idx, fav


def reconcile_author_favorite_id(
    casting: AuthorCasting,
    favorite_authors: Optional[list[dict[str, Any]]],
) -> AuthorCasting:
    """AuthorCasting（3候補→1選抜）の from_favorite 枠を登録お気に入りIDへ固定（純粋・非破壊）。

    cast_personas 側の reconcile_favorite_ids と同方針＝vertex が personaId を新規生成しても
    ★継続（front の ``favorites.has(id)`` 一致）が成立する。裏付けの無い from_favorite は降格。
    chosen が候補の from_favorite と同一実体なら固定後の値へ追従させる。
    """
    favs = [f for f in (favorite_authors or []) if f.get("personaId")]

    def _stamp(p: Any) -> Any:
        if not p.from_favorite:
            return p
        if not favs:
            return p.model_copy(update={"from_favorite": False})  # 裏付け無し＝降格
        fav = next((f for f in favs if f.get("name") == p.name), favs[0])
        return p.model_copy(update={"persona_id": fav["personaId"], "name": fav.get("name", p.name)})

    new_candidates = []
    stamped_by_oldid: dict[str, Any] = {}
    for c in casting.candidates:
        nc = _stamp(c)
        new_candidates.append(nc)
        if c.from_favorite:
            stamped_by_oldid[c.persona_id] = nc
    chosen = casting.chosen
    if chosen is not None:
        chosen = stamped_by_oldid.get(chosen.persona_id) or _stamp(chosen)
    return casting.model_copy(update={"candidates": new_candidates, "chosen": chosen})
