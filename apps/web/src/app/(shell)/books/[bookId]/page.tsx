"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { BookCover } from "@/components/book/BookCover";
import { BookToc } from "@/components/book/BookToc";
import { Topbar } from "@/components/shell/Topbar";
import { coverSrc } from "@/data/config";
import { useProvider } from "@/data/hooks";

export default function BookDetailPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();

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
              <span className="btn btn--ghost btn--block" style={{ cursor: "default" }}>
                ✦ {persona.name} を知る
              </span>
            )}
          </div>
          <div className="detail-meta-line">
            状態：<b>{statusLabel(book.status)}</b>
            <br />
            推定分量：<b>全{book.estimatedChapters}章・約{book.estimatedMinutes}分</b>
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
