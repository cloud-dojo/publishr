// bffプロバイダ: FastAPI BFF 経由。状態遷移中はポーリングで追従。
import type {
  Book,
  Feedback,
  FeedbackInput,
  Granularity,
  Persona,
  Plan,
  ReadingAnnotation,
  ReadingStateInput,
  User,
} from "@publishr/shared-schema";

import { apiUrl, DEMO_OWNER_UID, DEMO_USER_ID, getDemoClientId, timing } from "./config";
import { BaseProvider } from "./provider";

// per-client ローカルオーバーレイ（無認証ショーケース用）。
// 無認証デモは佐倉(DEMO_OWNER_UID)の本を全訪問者で共有表示するビュー。訪問者の操作をバックエンド
// （共有の佐倉データ）へ書くと全訪問者に波及し、かつ匿名は所有者データを書くべきでない。そこで
// 「読者ごとの状態」＝本棚の保存(archivedAt)/除外(dropped)・フィードバック(feedback: 読了率/評価/感想)・
// 読書状態(granularity/annotations=ハイライト等)を localStorage の per-client オーバーレイに持ち、
// /books 取得のたびに適用する（ハードリロードでも保持）。他の訪問者・他端末には波及しない。
// ログアウトで clearLocalLibrary が丸ごと消す＝次セッションは原状。お気に入り著者(favorites-store)と同設計。
type LibraryOverlayEntry = {
  archivedAt?: string;
  dropped?: boolean;
  feedback?: Partial<Feedback>; // 読了率/評価/感想などの読者ごと蓄積（佐倉共有には書かない）
  granularity?: Granularity;
  annotations?: ReadingAnnotation[]; // ハイライト/付箋/ブックマーク（配列まるごと）
};
const LIBRARY_OVERLAY_KEY = `publishr.bff.libraryOverlay.${DEMO_OWNER_UID}`;

async function jget<T>(path: string): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`);
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

async function jpost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export class BffProvider extends BaseProvider {
  private polling = false;
  private trackedBookIds = new Set<string>();
  // 本文を遅延 hydrate 中/済みの bookId（getBook からの多重フェッチ防止）。
  private hydratingBody = new Set<string>();

  protected async load(): Promise<void> {
    // 書店トップのカード表示に要る最小データ（本＋企画理由）を先に描画し、著者名・ユーザーは
    // 後追いで埋める。4本を Promise.all で待つと最も重いレスポンスが初回描画をゲートするため、
    // 届いた順に notify する（本カードは著者名 ?? "" のフォールバックがあり、名前は少し遅れて入る）。
    const booksP = jget<Book[]>("/books").then((books) => {
      this.setBooksWithOverlay(books);
      this.notify();
    });
    const plansP = jget<Plan[]>("/plans").then((plans) => {
      plans.forEach((p) => this.plans.set(p.id, p));
      this.notify();
    });
    const personasP = jget<Persona[]>("/personas").then((personas) => {
      personas.forEach((p) => this.personas.set(p.id, p));
      this.notify();
    });
    // 実デモ owner（佐倉=demo_uid）のユーザーを読む。旧 "u_sakura" は Firestore 未存在で
    // 挨拶/プロフィールが空になっていた（uid不整合）。ユーザー取得失敗は致命でない（挨拶が中立に落ちるだけ）。
    const userP = jget<User>(`/users/${DEMO_OWNER_UID}`)
      .then((user) => {
        if (!user) return;
        this.users.set(user.id, user);
        // 無認証ショーケースのページは getUser(uid ?? DEMO_USER_ID) で引くため、
        // DEMO_USER_ID キーにも同じ佐倉ユーザーを載せて解決できるようにする。
        this.users.set(DEMO_USER_ID, user);
        this.notify();
      })
      .catch(() => {});
    await Promise.all([booksP, plansP, personasP, userP]);
  }

  // 一覧(/books)は本文(body)を落として配るため、本文が要る読書/概要ページで getBook が呼ばれた
  // ときにだけ GET /books/{id}（本文込み・無認証で読める）で遅延 hydrate する。トップの BookCard は
  // getBook を呼ばない＝過剰取得にならない。取得後は notify で読書ページが本文込みに再描画される。
  getBook(id: string): Book | undefined {
    const book = this.books.get(id);
    if (book && !book.body && !this.hydratingBody.has(id)) {
      this.hydratingBody.add(id);
      void this.hydrateBody(id);
    }
    return book;
  }

  private async hydrateBody(id: string): Promise<void> {
    try {
      const full = await jget<Book>(`/books/${encodeURIComponent(id)}`);
      const cur = this.books.get(id);
      if (full.body) {
        this.books.set(id, cur ? { ...cur, body: full.body } : full);
        this.notify();
      }
    } catch (err) {
      console.error(err);
      this.hydratingBody.delete(id); // 失敗は次回 getBook で再試行
    }
  }

  private async refreshBooks(): Promise<void> {
    const books = await jget<Book[]>("/books");
    this.books.clear();
    this.setBooksWithOverlay(books);
    this.notify();
  }

  // --- 書庫オーバーレイ（localStorage・per-client）------------------------------
  private readOverlay(): Record<string, LibraryOverlayEntry> {
    if (typeof window === "undefined") return {};
    try {
      const raw = window.localStorage.getItem(LIBRARY_OVERLAY_KEY);
      return raw ? (JSON.parse(raw) as Record<string, LibraryOverlayEntry>) : {};
    } catch {
      return {};
    }
  }

  private writeOverlay(overlay: Record<string, LibraryOverlayEntry>): void {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(LIBRARY_OVERLAY_KEY, JSON.stringify(overlay));
    } catch {
      /* localStorage 不可（quota/プライベートモード）でもデモは続行する */
    }
  }

  /**
   * ログアウト時に per-client オーバーレイ（本棚の保存/除外・feedback・読書状態/ハイライト）を丸ごと
   * 消し、次セッション（匿名/ゲスト）を原状へ戻す。overlay キーは DEMO_OWNER_UID 固定でログイン uid に
   * 依存しないため、消さないとログイン→操作→ログアウト→再ログインで状態が残り続ける。レート計数の
   * demoClientId は消さない（別キー・別責務）。/books を取り直して in-memory の重ね状態も落とす。
   */
  async clearLocalLibrary(): Promise<void> {
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(LIBRARY_OVERLAY_KEY);
      } catch {
        /* localStorage 不可でも続行 */
      }
    }
    try {
      await this.refreshBooks();
    } catch (err) {
      console.error(err);
    }
  }

  private mergeOverlay(book: Book, entry: LibraryOverlayEntry | undefined): Book {
    if (!entry) return book;
    let merged = book;
    if (entry.archivedAt) merged = { ...merged, archivedAt: entry.archivedAt };
    // 読者ごとの feedback/読書状態を佐倉の共有dataより優先して重ねる（per-client）。
    if (entry.feedback) merged = { ...merged, feedback: { ...merged.feedback, ...entry.feedback } };
    if (entry.granularity !== undefined) merged = { ...merged, granularity: entry.granularity };
    if (entry.annotations) merged = { ...merged, annotations: entry.annotations };
    // dropped は最後（本棚から外した本は feedback.dropped=true を確実に立てる）。
    if (entry.dropped) merged = { ...merged, feedback: { ...merged.feedback, dropped: true } };
    return merged;
  }

  /** /books 取得直後に per-client オーバーレイ（保存/除外）を重ねて books マップへ格納する。 */
  private setBooksWithOverlay(books: Book[]): void {
    const overlay = this.readOverlay();
    books.forEach((b) => this.books.set(b.id, this.mergeOverlay(b, overlay[b.id])));
  }

  private startPolling(): void {
    if (this.polling) return;
    this.polling = true;
    const tick = async () => {
      try {
        await this.refreshBooks();
      } catch (err) {
        console.error(err);
      }
      for (const id of [...this.trackedBookIds]) {
        const book = this.books.get(id);
        if (!book || book.status === "published") {
          this.trackedBookIds.delete(id);
        }
      }
      const active = this.trackedBookIds.size > 0;
      if (active) {
        setTimeout(tick, timing.pollInterval);
      } else {
        this.polling = false;
      }
    };
    setTimeout(tick, timing.pollInterval);
  }

  watchBook(id: string): void {
    const book = this.books.get(id);
    if (!book || (book.status !== "reserved" && book.status !== "writing")) return;
    this.trackedBookIds.add(id);
    this.startPolling();
  }

  // 無認証ショーケースでは feedback（読了率/評価/感想）も per-client のローカル操作。バックエンド
  // （共有の佐倉data）へは書かず localStorage オーバーレイに蓄積する＝他の訪問者・他端末に波及しない。
  // readPercent 更新は読書イベントなので lastReadAt を刻む（firestore-provider と同方針）。
  async sendFeedback(id: string, feedback: FeedbackInput): Promise<void> {
    const book = this.books.get(id);
    if (!book) return;
    const stamped: FeedbackInput =
      feedback.readPercent !== undefined
        ? { ...feedback, lastReadAt: new Date().toISOString() }
        : feedback;
    this.books.set(id, { ...book, feedback: { ...book.feedback, ...stamped } });
    const overlay = this.readOverlay();
    this.writeOverlay({
      ...overlay,
      [id]: { ...overlay[id], feedback: { ...overlay[id]?.feedback, ...stamped } },
    });
    this.notify();
  }

  // 無認証ショーケースでは「本棚に保存/外す」は per-client のローカル操作。バックエンド（共有の
  // 佐倉データ）へは書かず localStorage オーバーレイに永続する＝ハードリロードでも保持し、他の訪問者
  // の書店にも波及しない。書店/書庫の表示は archivedAt / feedback.dropped で判定される（lib/arrival）。
  async saveToLibrary(id: string): Promise<void> {
    const book = this.books.get(id);
    if (!book) return;
    const archivedAt = new Date().toISOString();
    this.books.set(id, { ...book, archivedAt });
    const overlay = this.readOverlay();
    this.writeOverlay({ ...overlay, [id]: { ...overlay[id], archivedAt } });
    this.notify();
  }

  async removeFromLibrary(id: string): Promise<void> {
    const book = this.books.get(id);
    if (!book) return;
    this.books.set(id, { ...book, feedback: { ...book.feedback, dropped: true } });
    const overlay = this.readOverlay();
    this.writeOverlay({ ...overlay, [id]: { ...overlay[id], dropped: true } });
    this.notify();
  }

  // 読書状態（granularity・注釈/ハイライト）も per-client のローカル操作。佐倉共有には書かず
  // localStorage オーバーレイに持つ＝ハイライトが他の訪問者の本文に出ない。annotations は配列まるごと差替。
  async updateReadingState(id: string, state: ReadingStateInput): Promise<void> {
    const book = this.books.get(id);
    if (!book) return;
    const patch: Partial<Book> = {};
    if (state.granularity !== undefined) patch.granularity = state.granularity;
    if (state.annotations !== undefined) patch.annotations = state.annotations;
    this.books.set(id, { ...book, ...patch });
    const overlay = this.readOverlay();
    const entry: LibraryOverlayEntry = { ...overlay[id] };
    if (state.granularity !== undefined) entry.granularity = state.granularity;
    if (state.annotations !== undefined) entry.annotations = state.annotations;
    this.writeOverlay({ ...overlay, [id]: entry });
    this.notify();
  }

  async runPipeline(userId: string, themeKind?: string): Promise<void> {
    await jpost<{ ok: boolean; booksAdded: number }>("/api/trigger/planning", {
      userId,
      themeKind,
      // ②G: 無認証ライブ生成の per-client 日次上限の計数単位。
      clientId: getDemoClientId(),
    });
    await this.refreshBooks();
  }
}
