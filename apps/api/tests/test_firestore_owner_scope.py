"""FirestoreRepository の ID 直指定取得（get_book/get_plan/get_user）の owner スコープ検証。

Admin SDK は Firestore セキュリティルールをバイパスするため、`list_*` と同様に `get_*` でも
アプリ側で ownerUid を検証しないと「ID を知れば他 owner の book/plan/user を読める」IDOR に
なる（公開ショーケースの BFF は owner_uid=demo_uid にスコープ済みだが、get_* に穴があった）。

Firestore 接続不要の純ロジックテスト: __init__（firebase_admin 初期化）を回避し、フェイクの
`_db` を注入して document(id).get() の分岐だけを検証する。
"""

from __future__ import annotations

from typing import Optional

from publishr_api.repositories.firestore_repository import FirestoreRepository

OWNER = "owner_a"
OTHER = "owner_b"


# ── フェイク Firestore（document(id).get() の最小挙動）────────────────────────────
class _FakeSnap:
    def __init__(self, doc_id: str, data: Optional[dict]) -> None:
        self.id = doc_id
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[dict]:
        return dict(self._data) if self._data is not None else None


class _FakeDocRef:
    def __init__(self, doc_id: str, data: Optional[dict]) -> None:
        self._snap = _FakeSnap(doc_id, data)

    def get(self) -> _FakeSnap:
        return self._snap


class _FakeCollection:
    def __init__(self, docs: dict[str, dict]) -> None:
        self._docs = docs

    def document(self, doc_id: str) -> _FakeDocRef:
        return _FakeDocRef(doc_id, self._docs.get(doc_id))


class _FakeDb:
    def __init__(self, collections: dict[str, dict[str, dict]]) -> None:
        self._collections = collections

    def collection(self, name: str) -> _FakeCollection:
        return _FakeCollection(self._collections.get(name, {}))


def _repo(owner_uid: str, collections: dict[str, dict[str, dict]]) -> FirestoreRepository:
    repo = object.__new__(FirestoreRepository)  # __init__（firebase 初期化）を回避
    repo._db = _FakeDb(collections)  # type: ignore[attr-defined]
    repo._owner_uid = owner_uid  # type: ignore[attr-defined]
    return repo


def _book_doc(owner: str) -> dict:
    return {
        "id": "b1", "planId": "p1", "status": "published", "authorPersonaId": "persona1",
        "title": "T", "coverVariant": "v1", "shelf": "arrivals", "ownerUid": owner,
    }


def _plan_doc(owner: str) -> dict:
    # Plan モデルは owner_uid フィールドを持たない（extra=ignore で脱落）。
    # スコープ判定は検証前の raw doc の ownerUid を見る必要がある。
    return {
        "id": "p1", "reason": "r", "coreMessage": "c", "readerSituation": "s",
        "ownerUid": owner,
    }


def _user_doc(uid: str) -> dict:
    return {
        "id": uid, "name": "N", "initial": "N",
        "profile": {"role": "r", "workTheme": "w", "serendipityTolerance": "mid"},
    }


# ── books ───────────────────────────────────────────────────────────────────────
def test_get_book_same_owner_returns_book():
    repo = _repo(OWNER, {"books": {"b1": _book_doc(OWNER)}})
    book = repo.get_book("b1")
    assert book is not None and book.id == "b1"


def test_get_book_other_owner_returns_none():
    """ID を知っていても他 owner の book は読めない（IDOR 封じ）。"""
    repo = _repo(OWNER, {"books": {"b1": _book_doc(OTHER)}})
    assert repo.get_book("b1") is None


def test_get_book_unscoped_returns_any_owner():
    """owner_uid="" の全件モード（recompute/複数owner集計）は従来どおり owner を問わない。"""
    repo = _repo("", {"books": {"b1": _book_doc(OTHER)}})
    assert repo.get_book("b1") is not None


def test_get_book_missing_returns_none():
    repo = _repo(OWNER, {"books": {}})
    assert repo.get_book("nope") is None


# ── plans ───────────────────────────────────────────────────────────────────────
def test_get_plan_same_owner_returns_plan():
    repo = _repo(OWNER, {"plans": {"p1": _plan_doc(OWNER)}})
    plan = repo.get_plan("p1")
    assert plan is not None and plan.id == "p1"


def test_get_plan_other_owner_returns_none():
    repo = _repo(OWNER, {"plans": {"p1": _plan_doc(OTHER)}})
    assert repo.get_plan("p1") is None


def test_get_plan_unscoped_returns_any_owner():
    repo = _repo("", {"plans": {"p1": _plan_doc(OTHER)}})
    assert repo.get_plan("p1") is not None


# ── users（ドキュメント ID がそのまま owner。自分の doc だけ読める）────────────────
def test_get_user_self_returns_user():
    repo = _repo(OWNER, {"users": {OWNER: _user_doc(OWNER)}})
    user = repo.get_user(OWNER)
    assert user is not None and user.id == OWNER


def test_get_user_other_uid_returns_none():
    """スコープ済みリポジトリは自分以外の uid の User を返さない（profile/接続情報の流出封じ）。"""
    repo = _repo(OWNER, {"users": {OTHER: _user_doc(OTHER)}})
    assert repo.get_user(OTHER) is None


def test_get_user_unscoped_returns_any_uid():
    repo = _repo("", {"users": {OTHER: _user_doc(OTHER)}})
    assert repo.get_user(OTHER) is not None
