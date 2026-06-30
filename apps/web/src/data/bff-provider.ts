// bffプロバイダ: FastAPI BFF 経由。状態遷移中はポーリングで追従。
import type {
  Book,
  FeedbackInput,
  Persona,
  Plan,
  ReadingStateInput,
  User,
} from "@publishr/shared-schema";

import { apiUrl, DEMO_OWNER_UID, DEMO_USER_ID, timing } from "./config";
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

  protected async load(): Promise<void> {
    const [books, plans, personas, user] = await Promise.all([
      jget<Book[]>("/books"),
      jget<Plan[]>("/plans"),
      jget<Persona[]>("/personas"),
      // 実デモ owner（佐倉=demo_uid）のユーザーを読む。旧 "u_sakura" は Firestore 未存在で
      // 挨拶/プロフィールが空になっていた（uid不整合）。
      jget<User>(`/users/${DEMO_OWNER_UID}`).catch(() => null),
    ]);
    books.forEach((b) => this.books.set(b.id, b));
    plans.forEach((p) => this.plans.set(p.id, p));
    personas.forEach((p) => this.personas.set(p.id, p));
    if (user) {
      this.users.set(user.id, user);
      // 無認証ショーケースのページは getUser(uid ?? DEMO_USER_ID) で引くため、
      // DEMO_USER_ID キーにも同じ佐倉ユーザーを載せて解決できるようにする。
      this.users.set(DEMO_USER_ID, user);
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
    await jpost<{ ok: boolean; booksAdded: number }>("/api/trigger/planning", { userId, themeKind });
    await this.refreshBooks();
  }
}
