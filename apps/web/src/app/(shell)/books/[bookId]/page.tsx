"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { BookCover } from "@/components/book/BookCover";
import { BookToc } from "@/components/book/BookToc";
import { Topbar } from "@/components/shell/Topbar";
import { overviewExcerptParagraphs } from "@/data/bookText";
import { isArchivedBook } from "@/lib/arrival";
import { coverSrc } from "@/data/config";
import { useActions, useProvider } from "@/data/hooks";

export default function BookDetailPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const { saveToLibrary } = useActions();

  const book = provider.getBook(params.bookId);
  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/", label: "‹ 書店へ戻る" }} />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const plan = provider.getPlan(book.planId);
  const prefaceParagraphs = overviewExcerptParagraphs(book.body, book.prefaceSample);

  // 企画会議の証跡（却下→再提出ループ）はユーザー向けの本詳細には出さない（読者は「なぜ自分に・核心
  // メッセージ・目次・序文」だけで判断できればよい）。編集の裏側＝証跡は別導線で見せる方針。
  const archived = isArchivedBook(book);

  // 企画(plan)は本番Firestoreには永続化されず Book に畳み込まれる（agents/persist_mapping）。
  // plan があれば優先（mock/local＝従来表示そのまま）、無ければ Book 自身のフィールドで描く（prod）。
  const whyNow = plan?.reason ?? book.deliveryReason ?? "";
  const coreMessage = plan?.coreMessage ?? book.coreMessage ?? "";
  const hasRationale = Boolean(whyNow || coreMessage);

  return (
    <>
      <Topbar back={{ href: "/", label: "‹ 書店へ戻る" }} />
      <div className="scaled-page">
      <div className="page-hero" style={{ paddingBottom: 0 }}>
        <div className="ph-eyebrow">{archived ? "From your bookshelf" : "From your bookstore"}</div>
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
            {/* 書店にある本＝まず「書庫に保存」。保存した本（書庫）は期限で消えず残り続け、
                そこで初めて読書CTAを出す。保存後は同画面で archived が反転しCTAが切り替わる。 */}
            {archived ? (
              <Link className="btn btn--gold btn--block" href={`/read/${book.id}`}>
                この本を読む →
              </Link>
            ) : (
              <button
                type="button"
                className="btn btn--gold btn--block"
                onClick={() => void saveToLibrary(book.id)}
              >
                本棚に保存する
              </button>
            )}
            {persona && (
              <Link className="btn btn--ghost btn--block" href={`/author/${persona.id}`}>
                ✦ {persona.name} を知る
              </Link>
            )}
          </div>
        </div>

        <div>
          <div className="pitch-title">{book.title}</div>
          <div className="pitch-author">
            {persona?.name}
            {persona && <span> ― {persona.title}／{persona.style}</span>}
          </div>

          {hasRationale && (
            <div className="frame">
              {whyNow && (
                <div className="frame-row spot">
                  <div className="fr-key">なぜ、いまあなたに</div>
                  <div className="fr-val">{whyNow}</div>
                </div>
              )}
              {coreMessage && (
                <div className="frame-row">
                  <div className="fr-key">核心メッセージ</div>
                  <div className="fr-val">
                    <b>{coreMessage}</b>
                  </div>
                </div>
              )}
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
                  <p key={i} className={prefaceParagraphs.length > 2 && i === prefaceParagraphs.length - 1 ? "ex-fade" : ""}>
                    {p}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
