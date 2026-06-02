// bffプロバイダ: FastAPI BFF 経由。状態遷移中はポーリングで追従。
import type {
  Book,
  FeedbackInput,
  Persona,
  PipelineResult,
  Plan,
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

  protected async load(): Promise<void> {
    const [books, plans, personas, user] = await Promise.all([
      jget<Book[]>("/books"),
      jget<Plan[]>("/plans"),
      jget<Persona[]>("/personas"),
      jget<User>("/users/u_tadokoro").catch(() => null),
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
      const active = [...this.books.values()].some(
        (b) => b.status === "reserved" || b.status === "writing",
      );
      if (active) {
        setTimeout(tick, timing.pollInterval);
      } else {
        this.polling = false;
      }
    };
    setTimeout(tick, timing.pollInterval);
  }

  async reserve(id: string): Promise<void> {
    const book = await jpost<Book>(`/books/${id}/reserve`);
    this.books.set(id, book);
    this.notify();
    this.startPolling();
  }

  async sendFeedback(id: string, feedback: FeedbackInput): Promise<void> {
    const book = await jpost<Book>(`/books/${id}/feedback`, feedback);
    this.books.set(id, book);
    this.notify();
  }

  async runPipeline(userId: string): Promise<void> {
    const result = await jpost<PipelineResult>("/pipeline/run", { userId });
    result.books.forEach((b) => this.books.set(b.id, b));
    this.debate = result.rejectLog;
    this.notify();
  }
}
