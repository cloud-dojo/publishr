"""Firestore リポジトリ実装（Firebase Admin SDK）。

Cloud Run 上では Application Default Credentials が自動で使われる。
ローカル開発時は GOOGLE_APPLICATION_CREDENTIALS 環境変数に
サービスアカウントキー JSON のパスを設定する。

ownerUid フィルタ:
  Admin SDK はセキュリティルールをバイパスするため、アプリ側で
  ownerUid フィルタを適用してユーザーデータを分離する。
  MVP では settings.demo_uid を owner_uid として渡す（単一ユーザー前提）。
  C4.9 Firebase Auth 接続後は per-request uid に差し替える。

複合インデックス:
  ownerUid + status / shelf など複数フィールドの where を組み合わせると
  Firestore が複合インデックスを要求する場合がある。エラー時は
  コンソールの URL に従って firestore.indexes.json に追加する（C3.2）。
"""

from __future__ import annotations

import re
import threading
from typing import Optional

from publishr_schema import Book, Persona, Plan, User

# planningJobs/{run_id} 用のドキュメントID安全化。禁止文字（Firestore ID は
# [A-Za-z0-9_-] 以外・`/`・制御文字を含めない）を `_` に落とす。予約 `__.*__`・`.`・`..`・
# 空・過長は下の _safe_doc_id で追加処理する。正規の run_id（planning_uid_ts_hex）は不変。
_SAFE_DOC_ID_RE = re.compile(r"[^A-Za-z0-9_-]")
_RESERVED_ID_RE = re.compile(r"__.*__")

# ---------------------------------------------------------------------------
# Firebase Admin SDK 初期化（プロセス全体で 1 回のみ）
# ---------------------------------------------------------------------------
_init_lock = threading.Lock()
_initialized = False


def _ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        import firebase_admin

        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _initialized = True


# ---------------------------------------------------------------------------
# FirestoreRepository
# ---------------------------------------------------------------------------

class FirestoreRepository:
    """Firestore を永続ストアとして使うリポジトリ。

    Args:
        owner_uid: クエリ対象ユーザーの Firebase Auth UID。
                   空文字の場合は ownerUid フィルタをかけない（全件）。
    """

    _BOOKS = "books"
    _PLANS = "plans"
    _PERSONAS = "personas"
    _USERS = "users"

    def __init__(self, owner_uid: str = "") -> None:
        _ensure_initialized()
        from firebase_admin import firestore as fb_firestore  # noqa: PLC0415

        self._db = fb_firestore.client()
        self._owner_uid = owner_uid

    # ── books ──────────────────────────────────────────────────────────────

    def list_books(
        self, status: Optional[str] = None, shelf: Optional[str] = None
    ) -> list[Book]:
        q = self._db.collection(self._BOOKS)
        if self._owner_uid:
            q = q.where("ownerUid", "==", self._owner_uid)
        if status:
            q = q.where("status", "==", status)
        if shelf:
            q = q.where("shelf", "==", shelf)
        return [self._to_book(doc) for doc in q.stream()]

    def get_book(self, book_id: str) -> Optional[Book]:
        # ID 直指定でも owner を検証する。Admin SDK は rules をバイパスするため、これが無いと
        # ID を知れば他 owner の book を読める（IDOR）。owner_uid="" の全件モードは従来どおり素通し。
        doc = self._db.collection(self._BOOKS).document(book_id).get()
        if not doc.exists or not self._owned(doc):
            return None
        return self._to_book(doc)

    def upsert_book(self, book: Book) -> Book:
        """Book をそのまま Firestore へ保存（set = 全フィールド上書き）。

        status 遷移・feedback 更新などで使う。
        exclude_none=True で未設定フィールドを除外する。
        """
        data = book.model_dump(by_alias=True, exclude_none=True)
        self._db.collection(self._BOOKS).document(book.id).set(data)
        return book

    def reserve_book_atomic(
        self, book_id: str, *, owner_uid: str = "", max_concurrent: int = 5
    ) -> Book:
        """Firestore transaction で「count確認 → 条件付き draft→reserved」を原子化（I-20）。

        owner の reserved+writing 件数を txn 内で数え、cap 未満かつ draft のときだけ遷移する。
        レースで6冊目が通る/同一draftが二重に reserved になるのを防ぐ。ownerUid+status の
        複合インデックスを要求された場合はエラーURLに従い firestore.indexes.json へ追加（C3.2）。
        """
        from firebase_admin import firestore as fb_firestore  # noqa: PLC0415

        from ..errors import ConflictError, NotFoundError  # noqa: PLC0415

        owner = owner_uid or self._owner_uid
        book_ref = self._db.collection(self._BOOKS).document(book_id)

        @fb_firestore.transactional
        def _txn(txn) -> Book:
            snap = book_ref.get(transaction=txn)
            if not snap.exists:
                raise NotFoundError(f"book {book_id} が見つかりません")
            data = self._raw(snap)
            book_owner = data.get("ownerUid")
            if owner and book_owner and book_owner != owner:
                # 他 owner の draft を予約（＝実Vertex執筆の発火）できないようにする。
                # 存在秘匿のため read 系 IDOR と同じく NotFound を返す（P0-1 の write 版）。
                raise NotFoundError(f"book {book_id} が見つかりません")
            if data.get("status") != "draft":
                raise ConflictError(f"予約できません（現在の状態: {data.get('status')}）")
            q = self._db.collection(self._BOOKS).where("status", "in", ["reserved", "writing"])
            if owner:
                q = q.where("ownerUid", "==", owner)
            active = sum(1 for _ in q.stream(transaction=txn))
            if active >= max_concurrent:
                raise ConflictError(
                    f"同時に予約できるのは最大{max_concurrent}冊までです（予約中の本を読み終えてから）"
                )
            txn.update(book_ref, {"status": "reserved"})
            data["status"] = "reserved"
            return Book.model_validate(data)

        return _txn(self._db.transaction())

    # ── plans ──────────────────────────────────────────────────────────────

    def list_plans(self) -> list[Plan]:
        q = self._db.collection(self._PLANS)
        if self._owner_uid:
            q = q.where("ownerUid", "==", self._owner_uid)
        return [self._to_plan(doc) for doc in q.stream()]

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        # get_book と同じ owner ガード。Plan モデルは owner_uid を持たない（extra=ignore で脱落）
        # ため、_owned は検証前の raw doc の ownerUid を見る。
        doc = self._db.collection(self._PLANS).document(plan_id).get()
        if not doc.exists or not self._owned(doc):
            return None
        return self._to_plan(doc)

    # ── personas ───────────────────────────────────────────────────────────

    def list_personas(self) -> list[Persona]:
        """personas は ownerUid なし（認証済み全ユーザーが読める設計）。"""
        return [self._to_persona(doc)
                for doc in self._db.collection(self._PERSONAS).stream()]

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        doc = self._db.collection(self._PERSONAS).document(persona_id).get()
        return self._to_persona(doc) if doc.exists else None

    def upsert_persona(self, persona: Persona) -> Persona:
        """生成著者を personas コレクションへ保存（ownerUid なし・全員読める設計）。"""
        data = persona.model_dump(by_alias=True, exclude_none=True)
        self._db.collection(self._PERSONAS).document(persona.id).set(data)
        return persona

    # ── users ──────────────────────────────────────────────────────────────

    def list_users(self) -> list[User]:
        """MVP: owner_uid が設定されていれば自分の 1 件のみ返す。"""
        if self._owner_uid:
            user = self.get_user(self._owner_uid)
            return [user] if user else []
        return [self._to_user(doc)
                for doc in self._db.collection(self._USERS).stream()]

    def get_user(self, user_id: str) -> Optional[User]:
        # User はドキュメント ID がそのまま owner（別の ownerUid フィールドは無い）。スコープ済み
        # リポジトリは自分の doc だけ返す（list_users と同じ方針）＝他 uid の profile/接続情報を
        # ID 直指定で読めないようにする。owner_uid="" の全件モードは従来どおり任意 uid を返す。
        if self._owner_uid and user_id != self._owner_uid:
            return None
        doc = self._db.collection(self._USERS).document(user_id).get()
        return self._to_user(doc) if doc.exists else None

    def upsert_user(self, user: User) -> User:
        """connectedSources 等を更新。merge=True で既存フィールド（profile 等）を保持する。

        OAuth callback / Drive Picker のサーバ書込で使う（生トークンは Firestore に置かない）。
        """
        data = user.model_dump(by_alias=True, exclude_none=True)
        self._db.collection(self._USERS).document(user.id).set(data, merge=True)
        return user

    # ── 企画 run の冪等ロック（I-38: 再配信ストーム対策）──────────────────────
    _PLANNING_JOBS = "planningJobs"

    @staticmethod
    def _safe_doc_id(run_id: str) -> str:
        """run_id を Firestore ドキュメントID として安全化する（決定的）。

        run_id はユーザー入力（TriggerPlanningInput.run_id）や pubsub payload 由来で未検証。
        禁止文字（`/`・`.`・制御文字等）を `_` に落とし、予約パターン `__.*__`・`.`・`..`・空・
        過長を回避する。これをしないと `.document("__x__")` 等が InvalidArgument(400)→worker 500
        →Pub/Sub 再配信ストームになる（demo_rate の _safe_key と同型の境界防御）。
        正規の run_id（planning_uid_ts_hex）は [A-Za-z0-9_-] のみなので不変＝冪等キー維持。
        """
        safe = _SAFE_DOC_ID_RE.sub("_", run_id)[:256]
        if not safe or _RESERVED_ID_RE.fullmatch(safe) or safe in (".", ".."):
            safe = f"run-{safe}"
        return safe

    def begin_planning_run(self, run_id: str, owner_uid: str, user_id: str) -> bool:
        """planningJobs/{runId} を transaction で「無ければ作成し True／既存なら False」。

        重い planning worker が ack_deadline 超過で Pub/Sub 再配信されても、同一 run_id の2回目
        以降は False＝即 ack（204）で skip し、重複入荷（storm）を止める。サーバ専用コレクション
        （クライアント read 無し＝Admin がルールをバイパス・rules 追加不要）。
        """
        if not run_id:
            return False
        from firebase_admin import firestore as fb_firestore  # noqa: PLC0415

        ref = self._db.collection(self._PLANNING_JOBS).document(self._safe_doc_id(run_id))

        @fb_firestore.transactional
        def _txn(txn) -> bool:
            snap = ref.get(transaction=txn)
            if snap.exists:
                return False  # 既に running/completed/failed → 再配信は skip
            txn.set(ref, {
                "runId": run_id, "ownerUid": owner_uid, "userId": user_id,
                "status": "running",
                "createdAt": fb_firestore.SERVER_TIMESTAMP,
                "startedAt": fb_firestore.SERVER_TIMESTAMP,
            })
            return True

        return _txn(self._db.transaction())

    def complete_planning_run(self, run_id: str, book_ids: list[str]) -> None:
        if not run_id:
            return
        from firebase_admin import firestore as fb_firestore  # noqa: PLC0415

        self._db.collection(self._PLANNING_JOBS).document(self._safe_doc_id(run_id)).set(
            {"status": "completed", "bookIds": list(book_ids),
             "completedAt": fb_firestore.SERVER_TIMESTAMP},
            merge=True,
        )

    def fail_planning_run(self, run_id: str, error_type: str) -> None:
        if not run_id:
            return
        from firebase_admin import firestore as fb_firestore  # noqa: PLC0415

        self._db.collection(self._PLANNING_JOBS).document(self._safe_doc_id(run_id)).set(
            {"status": "failed", "errorType": error_type,
             "completedAt": fb_firestore.SERVER_TIMESTAMP},
            merge=True,
        )

    # ── private helpers ────────────────────────────────────────────────────

    def _owned(self, doc) -> bool:
        """スコープ owner での ID 直指定取得を許すか（books/plans 用）。

        owner_uid="" の全件モード（recompute_estimates / 複数 owner 集計）は常に許可。
        owner_uid 指定時は doc の ownerUid が一致する時だけ許可＝list_* の where と同じ境界を
        get_* にも課し、Admin SDK が rules をバイパスしても他 owner を ID 直指定で読めなくする。
        """
        if not self._owner_uid:
            return True
        data = doc.to_dict() or {}
        return data.get("ownerUid") == self._owner_uid

    @staticmethod
    def _raw(doc) -> dict:
        """DocumentSnapshot → dict（document ID を id フィールドとして補完）。"""
        data = doc.to_dict() or {}
        data.setdefault("id", doc.id)
        return data

    def _to_book(self, doc) -> Book:
        return Book.model_validate(self._raw(doc))

    def _to_plan(self, doc) -> Plan:
        return Plan.model_validate(self._raw(doc))

    def _to_persona(self, doc) -> Persona:
        return Persona.model_validate(self._raw(doc))

    def _to_user(self, doc) -> User:
        return User.model_validate(self._raw(doc))
