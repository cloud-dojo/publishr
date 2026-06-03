"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import type { Book } from "@publishr/shared-schema";

import { BookCover } from "@/components/book/BookCover";
import { DebateCandidates } from "@/components/writing/DebateCandidates";
import { Topbar } from "@/components/shell/Topbar";
import { useDebate, useProvider } from "@/data/hooks";

type StepState = "done" | "active" | "pending";

function stepStates(status: Book["status"]): {
  writing: StepState;
  editing: StepState;
  delivery: StepState;
} {
  if (status === "published") return { writing: "done", editing: "done", delivery: "done" };
  // reserved / writing
  return { writing: "active", editing: "pending", delivery: "pending" };
}

export default function WritingPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const debate = useDebate();
  const book = provider.getBook(params.bookId);

  useEffect(() => {
    if (!book || (book.status !== "reserved" && book.status !== "writing")) return;
    provider.watchBook(book.id);
  }, [book, provider]);

  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const s = stepStates(book.status);
  const isPublished = book.status === "published";
  const pct =
    book.feedback.readPercent > 0 ? `${book.feedback.readPercent}%` : isPublished ? "100%" : "執筆中";

  return (
    <>
      <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} />
      <div className="page-hero" style={{ paddingBottom: 6 }}>
        <div className="ph-eyebrow">Now in the press</div>
        <h1>
          あなたの一冊を、<span className="accent">{isPublished ? "書き上げました" : "執筆中"}</span>です。
        </h1>
        <p>あなたが選んだ瞬間、専属の編集部が動き出しました。企画から執筆までの工程をお見せします。</p>
      </div>

      <div className="stage">
        <div className={`writing-book ${isPublished ? "done" : "active"}`}>
          <BookCover variant={book.coverVariant} title={book.title} author={persona?.name} titleSize={22} />
          <div className={`pen-line ${isPublished ? "done" : "active"}`}>
            <i />
          </div>
          <div className="writing-status">
            {persona?.name} が{isPublished ? "書き上げました" : "執筆しています…"}
          </div>
          <div className="writing-pct">{pct}</div>
        </div>

        <div className="pipeline">
          <div className="step done">
            <div className="dot">✓</div>
            <div className="st-title">
              観測<span className="st-actor">Sense</span>
            </div>
            <div className="st-desc">指定フォルダ（Keepメモ）の業務メモ・読書のあしあとを収集。</div>
          </div>

          <div className="step done">
            <div className="dot">✓</div>
            <div className="st-title">
              読者分析<span className="st-actor">Reader Profile</span>
            </div>
            <div className="st-desc">
              いまの局面を推定。
              <span className="quote">
                役職：製造課長／局面：30名規模への移行期／関心：権限委譲・属人化
              </span>
            </div>
          </div>

          <div className="step done">
            <div className="dot">✓</div>
            <div className="st-title">
              企画会議<span className="st-actor">Editorial Debate</span>
            </div>
            <div className="st-desc">
              3名の企画 AI が異なる切り口で競合 → 企画リーダーが根拠つきで選抜（対立①・却下→再提出）。
            </div>
            <DebateCandidates entries={debate} />
          </div>

          <div className="step done">
            <div className="dot">✓</div>
            <div className="st-title">
              著者の割当<span className="st-actor">Casting</span>
            </div>
            <div className="st-desc">
              この企画に最も合う人格として{" "}
              <b style={{ color: "var(--gold-bright)" }}>
                {persona?.name}（{persona?.style}）
              </b>{" "}
              を選定。
            </div>
          </div>

          <div className={`step ${s.writing}`}>
            <div className="dot">{s.writing === "done" ? "✓" : "✎"}</div>
            <div className="st-title">
              執筆<span className="st-actor">Writing</span>
            </div>
            <div className="st-desc">{persona?.name} の文体・思想を着て、章ごとに本文を執筆。</div>
          </div>

          <div className={`step ${s.editing}`}>
            <div className="dot">{s.editing === "done" ? "✓" : "⟳"}</div>
            <div className="st-title">
              改稿<span className="st-actor">Editing（対立②）</span>
            </div>
            <div className="st-desc">別人格の編集者が薄い章・矛盾・文体の逸脱に赤を入れます。</div>
          </div>

          <div className={`step ${s.delivery}`}>
            <div className="dot">{s.delivery === "done" ? "✓" : "◷"}</div>
            <div className="st-title">
              納本<span className="st-actor">Delivery</span>
            </div>
            <div className="st-desc">書き上がり次第、あなたの書庫へ届きます。</div>
          </div>
        </div>
      </div>

      {isPublished && (
        <div className="daybreak">
          <div className="daybreak-rule">そして ──</div>
          <div className="arrival">
            <div className="a-ico">📖</div>
            <div style={{ flex: 1 }}>
              <div className="a-title">『{book.title}』が入荷しました</div>
              <div className="a-sub">
                {persona?.name} 著 ・ 全{book.estimatedChapters}章 ・ あなたのために書き下ろし
              </div>
            </div>
            <Link href={`/read/${book.id}`} className="btn btn--gold">
              いま読む →
            </Link>
          </div>
        </div>
      )}

      <div className="mock-note">
        <span className="mn-ico">◈</span>
        <span>
          予約→執筆→入荷はローカルのタイマー（実エージェントはキャンド出力）。企画会議のログは実パイプラインの reject_log です。
        </span>
      </div>
    </>
  );
}
