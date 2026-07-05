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
      books.forEach((b) => this.books.set(b.id, b));
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
    books.forEach((b) => this.books.set(b.id, b));
    this.notify();
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

  async saveToLibrary(id: string): Promise<void> {
    const book = this.books.get(id);
    if (!book) return;
    this.books.set(id, { ...book, archivedAt: new Date().toISOString() });
    this.notify();
  }

  async removeFromLibrary(id: string): Promise<void> {
    const book = await jpost<Book>(`/books/${id}/feedback`, { dropped: true });
    this.books.set(id, book);
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
