// firestoreプロバイダ: 読み取りは onSnapshot 購読、低リスク書き込みは Firestore 直、
// 予約/手動トリガーは Cloud Run API（Firebase IDトークン付与）。
// 方針の正本: docs/design/api-contract.md §1 / docs/design/tech-architecture.md §3。
//
// ⚠️ 前提（一瀬さんと確定が必要・本接続前の「1回だけ同期」項目）:
//   - Firestore ドキュメントが shared-schema（@publishr/shared-schema）の形で保存される
//     こと（books は doc.id=Book.id、ownerUid フィールドで所有者分離）。
//   - セキュリティルールのデプロイ（直書きが通る前提）。
//   - Cloud Run API 3本のURL・CORS（apiUrl / NEXT_PUBLIC_API_URL）。
// 既定の mock 運用には影響しない（dataSource==="firestore" の時のみ生成）。

import {
  collection,
  doc,
  onSnapshot,
  query,
  updateDoc,
  where,
  type Firestore,
} from "firebase/firestore";

import type {
  Book,
  FeedbackInput,
  Persona,
  Plan,
  ReadingStateInput,
  User,
} from "@publishr/shared-schema";

import { getDb, getFirebaseAuth } from "@/lib/firebase";

import { apiUrl } from "./config";
import { BaseProvider } from "./provider";

export class FirestoreProvider extends BaseProvider {
  private db: Firestore;
  private ownerUid: string | null = null;
  private unsubs: Array<() => void> = [];
  // GCS退避(C3.3)された本文の取得済みキャッシュ（id→本文）。snapshot 再取得で books が
  // 作り直されても本文を消さずに復元するために保持する（id→body）。
  private bodyCache = new Map<string, string>();

  constructor() {
    super();
    const db = getDb();
    if (!db) {
      throw new Error(
        "FirestoreProvider には Firebase 設定が必要です（NEXT_PUBLIC_FIREBASE_*）。"
      );
    }
    this.db = db;
  }

  /** 認証済みユーザーの uid を設定して購読を張り直す。 */
  setOwnerUid(uid: string | null): void {
    if (uid === this.ownerUid) return;
    this.ownerUid = uid;
    this.subscribeAll();
  }

  protected async load(): Promise<void> {
    // 初期 uid は現在のサインインユーザー。未ログインなら購読は setOwnerUid 後に張る。
    this.ownerUid = getFirebaseAuth()?.currentUser?.uid ?? null;
    this.subscribeAll();
  }

  private clearSubs(): void {
    this.unsubs.forEach((u) => u());
    this.unsubs = [];
  }

  private subscribeAll(): void {
    this.clearSubs();
    if (!this.ownerUid) return;
    const uid = this.ownerUid;

    // 棚: 自分の本のみ（ownerUid 一致）
    this.unsubs.push(
      onSnapshot(query(collection(this.db, "books"), where("ownerUid", "==", uid)), (snap) => {
        this.books.clear();
        snap.forEach((d) => {
          const b = { id: d.id, ...d.data() } as Book;
          // 既に GCS から hydrate 済みの本文を復元（snapshot で body="" に戻して読書ページを
          // 序文だけに退行させない・C3.3）。Firestore 側に実体があればそちらを優先。
          const cached = this.bodyCache.get(d.id);
          if (cached && !b.body) b.body = cached;
          this.books.set(d.id, b);
        });
        this.notify();
        void this.hydrateBodies();
      })
    );

    // 企画
    this.unsubs.push(
      onSnapshot(collection(this.db, "plans"), (snap) => {
        this.plans.clear();
        snap.forEach((d) => this.plans.set(d.id, { id: d.id, ...d.data() } as Plan));
        this.notify();
      })
    );

    // 著者ペルソナ
    this.unsubs.push(
      onSnapshot(collection(this.db, "personas"), (snap) => {
        this.personas.clear();
        snap.forEach((d) => this.personas.set(d.id, { id: d.id, ...d.data() } as Persona));
        this.notify();
      })
    );

    // 自分のユーザードキュメント
    this.unsubs.push(
      onSnapshot(doc(this.db, "users", uid), (d) => {
        if (d.exists()) this.users.set(d.id, { id: d.id, ...d.data() } as User);
        this.notify();
      })
    );
  }

  // --- 予約: Cloud Run API（IDトークン付与）。状態遷移は Firestore 購読で受け取る ---
  async reserve(id: string): Promise<void> {
    await this.apiPost("/api/reserve", { bookId: id });
    // status は books 購読で draft→reserved→writing→published と流れてくる（ポーリング不要）。
  }

  // --- 簡易FB: Firestore 直書き（books/{id}.feedback） ---
  async sendFeedback(id: string, feedback: FeedbackInput): Promise<void> {
    const book = this.books.get(id);
    // 読了率の更新＝読書イベント。最後に読んだ時刻を刻む（「最近読んだ本」の並び順）。
    const stamped: FeedbackInput =
      feedback.readPercent !== undefined
        ? { ...feedback, lastReadAt: new Date().toISOString() }
        : feedback;
    await updateDoc(doc(this.db, "books", id), {
      feedback: { ...book?.feedback, ...stamped },
    });
  }

  // --- 読書状態: Firestore 直書き ---
  async updateReadingState(id: string, state: ReadingStateInput): Promise<void> {
    const patch: Record<string, unknown> = {};
    if (state.granularity !== undefined) patch.granularity = state.granularity;
    if (state.annotations !== undefined) patch.annotations = state.annotations;
    await updateDoc(doc(this.db, "books", id), patch);
  }

  // --- 手動トリガー（デモ用）: Cloud Run API ---
  async runPipeline(userId: string): Promise<void> {
    await this.apiPost("/api/trigger/planning", { userId });
  }

  // 本文が GCS 退避（bodyUrl 有り＆body 空・C3.3）された本だけ、API でサーバ側 read して埋める。
  // inline 運用では body が常に入っているので何もしない（mock/従来の読書導線は不変）。
  // 取得した本文は bodyCache に保持し、以降の snapshot 再取得でも復元する（消えない）。
  private async hydrateBodies(): Promise<void> {
    const targets = [...this.books.values()].filter(
      (b) => b.bodyUrl && !b.body && !this.bodyCache.has(b.id)
    );
    for (const b of targets) {
      try {
        const data = (await this.apiGet(`/api/books/${b.id}/body`)) as { body?: string };
        if (data?.body) {
          this.bodyCache.set(b.id, data.body); // snapshot を越えて保持
          const cur = this.books.get(b.id);
          if (cur) {
            this.books.set(b.id, { ...cur, body: data.body });
            this.notify();
          }
        }
        // 本文が空（まだ書かれていない）なら cache に入れず、次の snapshot で再試行する。
      } catch {
        // 失敗は次の購読更新で再試行（cache に入れていないので再度 target になる）。
      }
    }
  }

  private async apiGet(path: string): Promise<unknown> {
    const token = await getFirebaseAuth()?.currentUser?.getIdToken();
    const res = await fetch(`${apiUrl}${path}`, {
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
    if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
    return res.json();
  }

  private async apiPost(path: string, body: unknown): Promise<unknown> {
    const token = await getFirebaseAuth()?.currentUser?.getIdToken();
    const res = await fetch(`${apiUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
    return res.json().catch(() => ({}));
  }
}
