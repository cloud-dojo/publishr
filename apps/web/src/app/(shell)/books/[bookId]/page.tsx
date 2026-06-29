"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { BookCover } from "@/components/book/BookCover";
import { BookToc } from "@/components/book/BookToc";
import { Topbar } from "@/components/shell/Topbar";
import { bookChapters } from "@/data/bookText";
import { isArchivedBook } from "@/lib/arrival";
import { coverSrc } from "@/data/config";
import { useActions, useProvider } from "@/data/hooks";

// 推定分量の分の係数。バックエンド persist_mapping._MINUTES_PER_CHAPTER と一致させる。
const MINUTES_PER_CHAPTER = 8;

export default function BookDetailPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const { saveToLibrary } = useActions();

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

  // 企画会議の証跡（却下→再提出ループ）はユーザー向けの本詳細には出さない（読者は「なぜ自分に・核心
  // メッセージ・目次・序文」だけで判断できればよい）。編集の裏側＝証跡は別導線で見せる方針。
  const archived = isArchivedBook(book);

  // 企画(plan)は本番Firestoreには永続化されず Book に畳み込まれる（agents/persist_mapping）。
  // plan があれば優先（mock/local＝従来表示そのまま）、無ければ Book 自身のフィールドで描く（prod）。
  const whyNow = plan?.reason ?? book.deliveryReason ?? "";
  const situation = plan?.readerSituation ?? book.problemToSolve ?? "";
  const situationLabel = plan?.readerSituation ? "想定する局面" : "解決する課題";
  const coreMessage = plan?.coreMessage ?? book.coreMessage ?? "";
  const hasRationale = Boolean(whyNow || situation || coreMessage);

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
            {/* 書店にある本＝まず「書庫に入庫」。入庫した本（書庫）は期限で消えず残り続け、
                そこで初めて「いま読む」を出す。入庫後は同画面で archived が反転しCTAが切り替わる。 */}
            {archived ? (
              <Link className="btn btn--gold btn--block" href={`/read/${book.id}`}>
                いま読む →
              </Link>
            ) : (
              <button
                type="button"
                className="btn btn--gold btn--block"
                onClick={() => void saveToLibrary(book.id)}
              >
                書庫に入庫する
              </button>
            )}
            {persona && (
              <Link className="btn btn--ghost btn--block" href={`/author/${persona.id}`}>
                ✦ {persona.name} を知る
              </Link>
            )}
          </div>
          <div className="detail-meta-line">
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

          {hasRationale && (
            <div className="frame">
              {whyNow && (
                <div className="frame-row spot">
                  <div className="fr-key">なぜ、いまあなたに</div>
                  <div className="fr-val">{whyNow}</div>
                </div>
              )}
              {situation && (
                <div className="frame-row">
                  <div className="fr-key">{situationLabel}</div>
                  <div className="fr-val">{situation}</div>
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
                  <p key={i} className={i === prefaceParagraphs.length - 1 ? "ex-fade" : ""}>
                    {p}
                  </p>
                ))}
              </div>
              <div className="row gap12" style={{ marginTop: 24 }}>
                {archived ? (
                  <Link className="btn btn--gold" href={`/read/${book.id}`}>
                    全文を読む →
                  </Link>
                ) : (
                  <button
                    type="button"
                    className="btn btn--gold"
                    onClick={() => void saveToLibrary(book.id)}
                  >
                    書庫に入庫して読む →
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
