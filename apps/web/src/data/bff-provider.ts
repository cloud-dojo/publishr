// bffプロバイダ: FastAPI BFF 経由。状態遷移中はポーリングで追従。
import type {
  Book,
  FeedbackInput,
  Persona,
  Plan,
  ReadingStateInput,
  User,
} from "@publishr/shared-schema";

import { apiUrl, DEMO_OWNER_UID, DEMO_USER_ID, getDemoClientId, timing } from "./config";
import { BaseProvider } from "./provider";

// 書庫の per-client ローカルオーバーレイ（無認証ショーケース用）。
// 無認証デモは佐倉(DEMO_OWNER_UID)の本を全訪問者で共有表示する読み取り専用ビュー。「本棚に保存/外す」を
// バックエンドへ書くと全訪問者に波及し、かつ匿名は所有者データを書くべきでない。そこで保存(archivedAt)/
// 除外(dropped)は localStorage の per-client オーバーレイに持ち、/books 取得のたびに適用する
// （ハードリロードでも保持＝本棚から消えない）。お気に入り著者(favorites-store)と同じ設計。
type LibraryOverlayEntry = { archivedAt?: string; dropped?: boolean };
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

  private mergeOverlay(book: Book, entry: LibraryOverlayEntry | undefined): Book {
    if (!entry) return book;
    let merged = book;
    if (entry.archivedAt) merged = { ...merged, archivedAt: entry.archivedAt };
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

  async sendFeedback(id: string, feedback: FeedbackInput): Promise<void> {
    const book = await jpost<Book>(`/books/${id}/feedback`, feedback);
    this.books.set(id, book);
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

  async updateReadingState(id: string, state: ReadingStateInput): Promise<void> {
    const book = await jpost<Book>(`/books/${id}/reading-state`, state);
    this.books.set(id, book);
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
