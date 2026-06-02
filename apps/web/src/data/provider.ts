// データプロバイダ抽象。mock ↔ bff ↔（将来）firestore の差し替えの継ぎ目。
// UI/フックはこの BaseProvider にのみ依存する。
import type {
  Book,
  FeedbackInput,
  Persona,
  Plan,
  RejectLogEntry,
  User,
} from "@publishr/shared-schema";

export type Listener = () => void;

export abstract class BaseProvider {
  protected books = new Map<string, Book>();
  protected plans = new Map<string, Plan>();
  protected personas = new Map<string, Persona>();
  protected users = new Map<string, User>();
  protected debate: RejectLogEntry[] = [];
  ready = false;

  private listeners = new Set<Listener>();
  private loadPromise: Promise<void> | null = null;

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  protected notify(): void {
    this.listeners.forEach((l) => l());
  }

  ensureLoaded(): Promise<void> {
    if (!this.loadPromise) {
      this.loadPromise = this.load()
        .then(() => {
          this.ready = true;
          this.notify();
        })
        .catch((err) => {
          console.error("data load failed:", err);
          this.ready = true;
          this.notify();
        });
    }
    return this.loadPromise;
  }

  protected abstract load(): Promise<void>;

  listBooks(): Book[] {
    return [...this.books.values()];
  }
  booksByShelf(shelf: Book["shelf"]): Book[] {
    return this.listBooks().filter((b) => b.shelf === shelf);
  }
  getBook(id: string): Book | undefined {
    return this.books.get(id);
  }
  listPlans(): Plan[] {
    return [...this.plans.values()];
  }
  getPlan(id: string): Plan | undefined {
    return this.plans.get(id);
  }
  listPersonas(): Persona[] {
    return [...this.personas.values()];
  }
  getPersona(id: string): Persona | undefined {
    return this.personas.get(id);
  }
  getUser(id: string): User | undefined {
    return this.users.get(id);
  }
  getDebate(): RejectLogEntry[] {
    return this.debate;
  }

  abstract reserve(id: string): Promise<void>;
  abstract sendFeedback(id: string, feedback: FeedbackInput): Promise<void>;
  abstract runPipeline(userId: string): Promise<void>;
}
