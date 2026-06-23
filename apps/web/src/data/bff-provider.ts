// bffプロバイダ: FastAPI BFF 経由。状態遷移中はポーリングで追従。
import type {
  Book,
  FeedbackInput,
  Persona,
  PipelineResult,
  Plan,
  ReadingStateInput,
  User,
} from "@publishr/shared-schema";

import { apiUrl, timing } from "./config";
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
      jget<User>("/users/u_sakura").catch(() => null),
    ]);
    books.forEach((b) => this.books.set(b.id, b));
    plans.forEach((p) => this.plans.set(p.id, p));
    personas.forEach((p) => this.personas.set(p.id, p));
    if (user) this.users.set(user.id, user);
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

  async updateReadingState(id: string, state: ReadingStateInput): Promise<void> {
    const book = await jpost<Book>(`/books/${id}/reading-state`, state);
    this.books.set(id, book);
    this.notify();
  }

  async runPipeline(userId: string): Promise<void> {
    const result = await jpost<PipelineResult>("/pipeline/run", { userId });
    result.plans.forEach((p) => this.plans.set(p.id, p));
    result.books.forEach((b) => this.books.set(b.id, b));
    this.observation = result.observation;
    this.readerProfile = result.readerProfile;
    this.candidates = result.candidates;
    this.approvedPlanIds = result.approvedPlanIds;
    this.debate = result.rejectLog;
    this.notify();
  }
}
