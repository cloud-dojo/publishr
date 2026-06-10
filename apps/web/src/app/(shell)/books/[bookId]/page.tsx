"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";

import { BookCover } from "@/components/book/BookCover";
import { BookToc } from "@/components/book/BookToc";
import { Topbar } from "@/components/shell/Topbar";
import { useActions, useProvider } from "@/data/hooks";

export default function BookDetailPage() {
  const params = useParams<{ bookId: string }>();
  const router = useRouter();
  const provider = useProvider();
  const { reserve } = useActions();
  const [busy, setBusy] = useState(false);

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

  const onReserve = async () => {
    setBusy(true);
    await reserve(book.id);
    router.push(`/writing/${book.id}`);
  };

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
            coverUrl={book.coverUrl}
            title={book.title}
            subtitle={book.subtitle}
            author={persona?.name}
            titleSize={25}
          />
          <div className="detail-actions">
            {book.status === "draft" && (
              <button className="btn btn--gold btn--block" onClick={onReserve} disabled={busy}>
                {busy ? "依頼を送っています…" : "この本を執筆依頼する →"}
              </button>
            )}
            {(book.status === "reserved" || book.status === "writing") && (
              <Link className="btn btn--gold btn--block" href={`/writing/${book.id}`}>
                執筆の様子を見る →
              </Link>
            )}
            {book.status === "published" && (
              <Link className="btn btn--gold btn--block" href={`/read/${book.id}`}>
                いま読む →
              </Link>
            )}
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
                  <div className="eyebrow">A glimpse before you reserve</div>
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
              {book.status === "draft" && (
                <div className="row gap12" style={{ marginTop: 24 }}>
                  <button className="btn btn--gold" onClick={onReserve} disabled={busy}>
                    続きを執筆依頼する →
                  </button>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {persona?.name} が本文を書き始めます（明朝に入荷）
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function statusLabel(status: string): string {
  switch (status) {
    case "draft":
      return "企画段階（本文は未執筆）";
    case "reserved":
      return "執筆依頼中";
    case "writing":
      return "執筆中";
    case "published":
      return "入荷済み（読めます）";
    default:
      return status;
  }
}
