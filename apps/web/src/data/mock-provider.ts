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
