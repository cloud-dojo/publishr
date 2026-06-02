"""フィクスチャ（共有JSON）を pydantic モデルへ読み込むローダ。

フィクスチャは `packages/shared-schema/fixtures/*.json`。環境変数
`PUBLISHR_FIXTURES_DIR` で配置を上書きできる。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Book, KeepNote, Persona, Plan, User


def fixtures_dir() -> Path:
    override = os.environ.get("PUBLISHR_FIXTURES_DIR")
    if override:
        return Path(override)
    # loader.py: packages/shared-schema/py/publishr_schema/loader.py
    # parents[2] == packages/shared-schema
    return Path(__file__).resolve().parents[2] / "fixtures"


def _load(name: str) -> list[dict]:
    path = fixtures_dir() / name
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"フィクスチャが見つかりません: {path} （PUBLISHR_FIXTURES_DIR を確認）"
        ) from e


def load_users() -> list[User]:
    return [User.model_validate(d) for d in _load("users.json")]


def load_personas() -> list[Persona]:
    return [Persona.model_validate(d) for d in _load("personas.json")]


def load_plans() -> list[Plan]:
    return [Plan.model_validate(d) for d in _load("plans.json")]


def load_books() -> list[Book]:
    return [Book.model_validate(d) for d in _load("books.json")]


def load_keep_notes() -> list[KeepNote]:
    return [KeepNote.model_validate(d) for d in _load("keep_notes.json")]
