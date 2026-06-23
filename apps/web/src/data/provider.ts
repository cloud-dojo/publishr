// データプロバイダ抽象。mock ↔ bff ↔（将来）firestore の差し替えの継ぎ目。
// UI/フックはこの BaseProvider にのみ依存する。
import type {
  AppNotification,
  Book,
  FeedbackInput,
  Observation,
  Persona,
  Plan,
  PlanningCandidate,
  ReadingStateInput,
  ReaderProfile,
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
  protected observation: Observation | null = null;
  protected readerProfile: ReaderProfile | null = null;
  protected candidates: PlanningCandidate[] = [];
  protected approvedPlanIds: string[] = [];
  protected notifications: AppNotification[] = [];
  private notifSeq = 0;
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
  getCandidates(): PlanningCandidate[] {
    return this.candidates;
  }
  getApprovedPlanIds(): string[] {
    return this.approvedPlanIds;
  }
  getObservation(): Observation | null {
    return this.observation;
  }
  getReaderProfile(): ReaderProfile | null {
    return this.readerProfile;
  }

  // --- 通知 -----------------------------------------------------------------
  /** 新しい順に通知を返す。 */
  listNotifications(): AppNotification[] {
    return [...this.notifications].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }
  unreadNotificationCount(): number {
    return this.notifications.reduce((n, x) => n + (x.read ? 0 : 1), 0);
  }
  markNotificationRead(id: string): void {
    const n = this.notifications.find((x) => x.id === id);
    if (n && !n.read) {
      n.read = true;
      this.notify();
    }
  }
  markAllNotificationsRead(): void {
    let changed = false;
    this.notifications.forEach((n) => {
      if (!n.read) {
        n.read = true;
        changed = true;
      }
    });
    if (changed) this.notify();
  }
  /** 通知を1件積む（先頭に追加し、UIへ通知）。 */
  protected pushNotification(
    n: Omit<AppNotification, "id" | "read"> & { read?: boolean }
  ): void {
    this.notifications.unshift({
      id: `ntf_${++this.notifSeq}`,
      read: n.read ?? false,
      ...n,
    });
    this.notify();
  }
  /** 指定作家の本を1冊返す（新刊=draft を優先、excludeId は除外）。 */
  protected bookByPersona(personaId: string, excludeId?: string): Book | undefined {
    const list = [...this.books.values()].filter(
      (b) => b.authorPersonaId === personaId && b.id !== excludeId
    );
    return list.find((b) => b.status === "draft") ?? list[0];
  }
  /** お気に入り作家登録時の通知。その作家の本の概要ページへ誘導する。 */
  notifyFavoriteAuthor(personaId: string, personaName: string, excludeBookId?: string): void {
    if (this.notifications.some((n) => n.kind === "favoriteAuthor" && n.personaId === personaId)) {
      return; // 二重登録防止
    }
    const target = this.bookByPersona(personaId, excludeBookId);
    this.pushNotification({
      kind: "favoriteAuthor",
      title: `${personaName} をお気に入りに登録しました`,
      body: target
        ? `${personaName} の一冊の概要をご覧いただけます。`
        : `${personaName} が次の一冊を書きはじめたら、ここでご案内します。`,
      createdAt: new Date().toISOString(),
      href: target ? `/books/${target.id}` : "/authors",
      bookId: target?.id,
      personaId,
    });
  }

  abstract sendFeedback(id: string, feedback: FeedbackInput): Promise<void>;
  abstract updateReadingState(id: string, state: ReadingStateInput): Promise<void>;
  abstract runPipeline(userId: string): Promise<void>;

  /**
   * 初回体験：登録直後に「最初の本棚」を仕立てる。
   * 既定は本生成パイプラインのトリガー（firestore は Cloud Run、結果は購読で反映）。
   * MockProvider は決定的な時間差入荷でこれを上書きする。
   * profile は any にせず、UI層の初期プロフィール型を data/hooks 経由で渡す。
   */
  async runFirstRun(userId: string, profile?: unknown): Promise<void> {
    void profile; // 既定はパイプライン起動のみ（profile は mock 実装で使用）
    await this.runPipeline(userId);
  }

  watchBook(id: string): void {
    void id;
  }
}
