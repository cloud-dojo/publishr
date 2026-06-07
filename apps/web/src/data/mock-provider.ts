// mockプロバイダ: フィクスチャ種・タイマー状態機械（API不要・デモ安全網）。
import { fixtures } from "@publishr/shared-schema";
import type { FeedbackInput, ReadingStateInput } from "@publishr/shared-schema";

import {
  CANNED_APPROVED_PLAN_IDS,
  CANNED_CANDIDATES,
  CANNED_DEBATE,
  CANNED_OBSERVATION,
  CANNED_READER_PROFILE,
  cannedBody,
} from "./canned";
import { timing } from "./config";
import { BaseProvider } from "./provider";
import { EXTRA_LIBRARY_BOOKS, SAMPLE_BODIES } from "./sampleLibrary";

export class MockProvider extends BaseProvider {
  protected async load(): Promise<void> {
    // デモが常に新鮮になるよう、draft の入荷日時(createdAt)を実行時に直近7日内へ生成。
    // 旧「press棚の draft（もうすぐ）」概念は廃止し、関心(arrivals)の draft として扱う。
    const now = Date.now();
    fixtures.books.forEach((b, i) => {
      const shelf = b.shelf === "press" && b.status === "draft" ? "arrivals" : b.shelf;
      const createdAt =
        b.status === "draft"
          ? new Date(now - (i % 6) * 86_400_000).toISOString() // 0〜5日前（ウィンドウ内）
          : new Date(now - 30 * 86_400_000).toISOString();
      this.books.set(b.id, { ...b, shelf, createdAt });
    });
    // 読書ページ検証用：追加蔵書をマージ＋薄い body を複数章ダミーに差し替え（mock専用）。
    EXTRA_LIBRARY_BOOKS.forEach((b) => this.books.set(b.id, b));
    this.books.forEach((b, id) => {
      const body = SAMPLE_BODIES[id];
      if (body) this.books.set(id, { ...b, body });
    });
    fixtures.plans.forEach((p) => this.plans.set(p.id, p));
    fixtures.personas.forEach((p) => this.personas.set(p.id, p));
    fixtures.users.forEach((u) => this.users.set(u.id, u));
    this.observation = CANNED_OBSERVATION;
    this.readerProfile = CANNED_READER_PROFILE;
    this.candidates = CANNED_CANDIDATES;
    this.approvedPlanIds = CANNED_APPROVED_PLAN_IDS;
    this.debate = CANNED_DEBATE;
    this.seedNotifications();
  }

  /** デモ初期表示用に、4種の通知を決定的にシードする（mock専用）。 */
  private seedNotifications(): void {
    const now = Date.now();
    const all = [...this.books.values()];
    const freshDraft = all.filter((b) => b.status === "draft");
    const published = all.filter((b) => b.status === "published");
    const arrivalCount = Math.min(3, Math.max(1, freshDraft.length));
    // 書庫着の本（執筆完了済み＝published を優先）。
    const lib = published[0] ?? all.find((b) => b.body) ?? all[0];
    // お気に入り作家の「新しい一冊」＝ lib とは別の draft（新刊）を優先。
    const favBook = freshDraft.find((b) => b.id !== lib?.id) ?? freshDraft[0] ?? all[0];
    const favPersona = favBook ? this.personas.get(favBook.authorPersonaId) : undefined;
    const favName = favPersona?.name ?? "あなたのお気に入りの作家";

    // 新しい順に積みたいので、古い→新しい の順で push（listNotifications で再ソート）。
    this.notifications = [
      {
        id: "ntf_seed_delivery",
        kind: "delivery",
        title: lib ? `『${lib.title}』が書庫に届きました` : "予約した本が書庫に届きました",
        body: "執筆が完了しました。まずは本の概要をご覧いただけます。",
        createdAt: new Date(now - 3 * 3_600_000).toISOString(),
        read: true,
        href: lib ? `/books/${lib.id}` : "/library",
        bookId: lib?.id,
      },
      {
        id: "ntf_seed_favorite",
        kind: "favoriteAuthor",
        title: favBook
          ? `お気に入りの作家 ${favName} の新しい一冊が入荷しました`
          : `お気に入りの作家 ${favName} が、次の一冊を構想中です`,
        body: favBook
          ? "どんな本を書いたのか、概要をご覧いただけます。"
          : "新しい一冊が入荷した際に、ここでご案内します。",
        createdAt: new Date(now - 40 * 60_000).toISOString(),
        read: false,
        href: favBook ? `/books/${favBook.id}` : "/authors",
        bookId: favBook?.id,
        personaId: favPersona?.id,
      },
      {
        id: "ntf_seed_arrival",
        kind: "arrival",
        title: `今朝、あなたのために${arrivalCount}冊が入荷しました`,
        body: "いま、あなたの関心にまっすぐ応える一冊たちです。",
        createdAt: new Date(now - 3 * 60_000).toISOString(),
        read: false,
        href: "/",
      },
    ];
  }

  async reserve(id: string): Promise<void> {
    const book = this.books.get(id);
    if (!book || book.status !== "draft") return;
    this.books.set(id, { ...book, status: "reserved" });
    this.notify();

    setTimeout(() => {
      const b = this.books.get(id);
      if (!b || b.status !== "reserved") return;
      this.books.set(id, { ...b, status: "writing" });
      this.notify();

      setTimeout(() => {
        const b2 = this.books.get(id);
        if (!b2 || b2.status !== "writing") return;
        this.books.set(id, {
          ...b2,
          status: "published",
          body: b2.body ?? cannedBody(id),
        });
        this.notify();
        // 執筆完了 → 書庫着 の通知（ライブ生成）。まず本の概要ページへ誘導する。
        this.pushNotification({
          kind: "delivery",
          title: `『${b2.title}』が書き上がりました`,
          body: "書庫に届きました。まずは本の概要をご覧いただけます。",
          createdAt: new Date().toISOString(),
          href: `/books/${id}`,
          bookId: id,
        });
      }, timing.writingToPublished);
    }, timing.reserveToWriting);
  }

  async sendFeedback(id: string, feedback: FeedbackInput): Promise<void> {
    const book = this.books.get(id);
    if (!book) return;
    this.books.set(id, { ...book, feedback: { ...book.feedback, ...feedback } });
    this.notify();
  }

  async updateReadingState(id: string, state: ReadingStateInput): Promise<void> {
    const book = this.books.get(id);
    if (!book) return;
    this.books.set(id, {
      ...book,
      granularity: state.granularity ?? book.granularity,
      annotations: state.annotations ?? book.annotations ?? [],
    });
    this.notify();
  }

  async runPipeline(): Promise<void> {
    this.observation = CANNED_OBSERVATION;
    this.readerProfile = CANNED_READER_PROFILE;
    this.candidates = CANNED_CANDIDATES;
    this.approvedPlanIds = CANNED_APPROVED_PLAN_IDS;
    this.debate = CANNED_DEBATE;
    this.notify();
  }
}
