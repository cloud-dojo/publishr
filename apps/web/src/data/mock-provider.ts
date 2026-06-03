// mockプロバイダ: フィクスチャ種・タイマー状態機械（API不要・デモ安全網）。
import { fixtures } from "@publishr/shared-schema";
import type { FeedbackInput } from "@publishr/shared-schema";

import { CANNED_DEBATE, CANNED_OBSERVATION, CANNED_READER_PROFILE, cannedBody } from "./canned";
import { timing } from "./config";
import { BaseProvider } from "./provider";

export class MockProvider extends BaseProvider {
  protected async load(): Promise<void> {
    fixtures.books.forEach((b) => this.books.set(b.id, b));
    fixtures.plans.forEach((p) => this.plans.set(p.id, p));
    fixtures.personas.forEach((p) => this.personas.set(p.id, p));
    fixtures.users.forEach((u) => this.users.set(u.id, u));
    this.observation = CANNED_OBSERVATION;
    this.readerProfile = CANNED_READER_PROFILE;
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

  async runPipeline(): Promise<void> {
    this.observation = CANNED_OBSERVATION;
    this.readerProfile = CANNED_READER_PROFILE;
    this.debate = CANNED_DEBATE;
    this.notify();
  }
}
