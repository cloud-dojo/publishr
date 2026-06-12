"""インメモリのモックリポジトリ（フィクスチャ種・状態機械）。

イミュータブル更新: 既存レコードは変更せず、差し替えで保持する。
将来の FirestoreRepository は同じ RepositoryProtocol を満たして差し替える。"""

from __future__ import annotations

from typing import Optional

from publishr_schema import (
    Book,
    Persona,
    Plan,
    User,
    load_books,
    load_personas,
    load_plans,
    load_users,
)


class MockRepository:
    def __init__(self) -> None:
        self._books: dict[str, Book] = {b.id: b for b in load_books()}
        self._plans: dict[str, Plan] = {p.id: p for p in load_plans()}
        self._personas: dict[str, Persona] = {p.id: p for p in load_personas()}
        self._users: dict[str, User] = {u.id: u for u in load_users()}

    def list_books(
        self, status: Optional[str] = None, shelf: Optional[str] = None
    ) -> list[Book]:
        items = list(self._books.values())
        if status:
            items = [b for b in items if b.status == status]
        if shelf:
            items = [b for b in items if b.shelf == shelf]
        return items

    def get_book(self, book_id: str) -> Optional[Book]:
        return self._books.get(book_id)

    def upsert_book(self, book: Book) -> Book:
        self._books[book.id] = book
        return book

    def list_plans(self) -> list[Plan]:
        return list(self._plans.values())

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def list_personas(self) -> list[Persona]:
        return list(self._personas.values())

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        return self._personas.get(persona_id)

    def upsert_persona(self, persona: Persona) -> Persona:
        self._personas[persona.id] = persona
        return persona

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def upsert_user(self, user: User) -> User:
        """connectedSources 等の更新（イミュータブル差し替え）。"""
        self._users[user.id] = user
        return user
