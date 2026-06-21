"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { BookCover } from "@/components/book/BookCover";
import { BookToc } from "@/components/book/BookToc";
import { Topbar } from "@/components/shell/Topbar";
import { bookChapters } from "@/data/bookText";
import { coverSrc } from "@/data/config";
import { useActions, useProvider } from "@/data/hooks";

// 推定分量の分の係数。バックエンド persist_mapping._MINUTES_PER_CHAPTER と一致させる。
const MINUTES_PER_CHAPTER = 8;

export default function BookDetailPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const { moveToLibrary } = useActions();

  const book = provider.getBook(params.bookId);
  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const plan = provider.getPlan(book.planId);
  const prefaceParagraphs = book.prefaceSample.split("\n\n").filter(Boolean);

  // 推定分量は本文があれば**実際に書かれた章数**で出す（計画アジェンダ数だと本文と食い違う）。
  // 本文未取得（GCS退避hydrate前 or 下書き）は従来どおり計画値にフォールバック。分も実章数で揃える。
  const actualChapters = book.body ? bookChapters(book.body).length : 0;
  const chapterCount = actualChapters > 0 ? actualChapters : book.estimatedChapters;
  const minuteCount = actualChapters > 0 ? actualChapters * MINUTES_PER_CHAPTER : book.estimatedMinutes;

  return (
    <>
      <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} />
      <div className="page-hero" style={{ paddingBottom: 0 }}>
        <div className="ph-eyebrow">Today&apos;s arrival · curated for you</div>
      </div>

      <div className="detail">
        <div className="detail-cover-col">
          <BookCover
            variant={book.coverVariant}
            coverUrl={coverSrc(book.id, book.coverUrl)}
            title={book.title}
            subtitle={book.subtitle}
            author={persona?.name}
            titleSize={25}
          />
          <div className="detail-actions">
            <Link className="btn btn--gold btn--block" href={`/read/${book.id}`}>
              いま読む →
            </Link>
            {persona && (
              <Link className="btn btn--ghost btn--block" href={`/author/${persona.id}`}>
                ✦ {persona.name} を知る
              </Link>
            )}
            {/* 書庫へ移動: 入荷一覧から外し書庫に残す（動的フィルタリング）。移動後は shelf=library
                になりこのボタンは消える（書庫には残る）。 */}
            {book.status === "published" && book.shelf !== "library" && (
              <button
                type="button"
                className="btn btn--ghost btn--block"
                onClick={() => void moveToLibrary(book.id)}
              >
                📚 書庫へ移動
              </button>
            )}
          </div>
          <div className="detail-meta-line">
            状態：<b>{statusLabel(book.status)}</b>
            <br />
            推定分量：<b>全{chapterCount}章・約{minuteCount}分</b>
            <br />
            装丁：<b>Imagen 生成</b>／企画：<b>編集会議 AI</b>
          </div>
        </div>

        <div>
          <div className="pitch-title">{book.title}</div>
          <div className="pitch-author">
            {persona?.name}
            {persona && <span> ― {persona.title}／{persona.style}</span>}
          </div>

          {plan && (
            <div className="frame">
              <div className="frame-row spot">
                <div className="fr-key">なぜ、いまあなたに</div>
                <div className="fr-val">{plan.reason}</div>
              </div>
              <div className="frame-row">
                <div className="fr-key">想定する局面</div>
                <div className="fr-val">{plan.readerSituation}</div>
              </div>
              <div className="frame-row">
                <div className="fr-key">核心メッセージ</div>
                <div className="fr-val">
                  <b>{plan.coreMessage}</b>
                </div>
              </div>
            </div>
          )}

          <div className="section" style={{ marginTop: 40 }}>
            <div className="section-head">
              <div>
                <div className="eyebrow">Table of contents</div>
                <div className="section-title">
                  アジェンダ<span className="accent">（目次）</span>
                </div>
              </div>
            </div>
            <BookToc book={book} />
          </div>

          {prefaceParagraphs.length > 0 && (
            <div className="section" style={{ marginTop: 40 }}>
              <div className="section-head">
                <div>
                  <div className="eyebrow">A glimpse before you read</div>
                  <div className="section-title">
                    序文の<span className="accent">サンプル</span>
                  </div>
                </div>
              </div>
              <div className="excerpt">
                <div className="ex-label">はじめに</div>
                {prefaceParagraphs.map((p, i) => (
                  <p key={i} className={i === prefaceParagraphs.length - 1 ? "ex-fade" : ""}>
                    {p}
                  </p>
                ))}
              </div>
              <div className="row gap12" style={{ marginTop: 24 }}>
                <Link className="btn btn--gold" href={`/read/${book.id}`}>
                  全文を読む →
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function statusLabel(status: string): string {
  switch (status) {
    // 予約撤去・自動執筆後は draft/reserved/writing は数十秒〜数分の一時状態＝「準備中」に集約。
    case "draft":
    case "reserved":
    case "writing":
      return "準備中（まもなく全文が読めます）";
    case "published":
      return "読めます";
    default:
      return status;
  }
}
