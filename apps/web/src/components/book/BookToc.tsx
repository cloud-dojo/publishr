import Link from "next/link";

import type { Book } from "@publishr/shared-schema";

import { bookChapters } from "@/data/bookText";

/**
 * 本の目次（章一覧）。目次ページと本の概要ページで共用。
 * - 本文（body）がある本：実際の章を導出し、クリックで読書ページの該当章へジャンプ。
 * - 本文が無い本（下書き）：企画用アジェンダを非リンクで表示（読めないのでジャンプさせない）。
 */
export function BookToc({ book }: { book: Book }) {
  const chapters = bookChapters(book.body);

  if (chapters.length > 0) {
    return (
      <>
        {chapters.map((c) => (
          <Link
            key={c.index}
            href={`/read/${book.id}?ch=${c.index}`}
            className="agenda-item agenda-item--link"
          >
            <div className="ag-no" style={{ whiteSpace: "nowrap" }}>{c.no}</div>
            <div>
              <div className="ag-t">{c.title}</div>
            </div>
          </Link>
        ))}
      </>
    );
  }

  // 本文が GCS 退避済み（bodyUrl 有り）でまだ未 hydrate（body 空）の間は、後で実章一覧に
  // 差し替わる計画アジェンダ（"全○章"）を先に出さない＝古い章立てが一瞬見えるちらつきを防ぐ。
  // ※ bodyUrl が無い純粋な下書き（未執筆）は従来どおり計画アジェンダをプレビュー表示する。
  if (book.bodyUrl && !book.body) {
    return <div className="muted">目次を読み込み中…</div>;
  }

  // フォールバック：本文未執筆の下書きは計画アジェンダを表示
  if (book.agenda.length === 0) {
    return <div className="muted">目次は準備中です。</div>;
  }
  return (
    <>
      {book.agenda.map((item) => (
        <div key={item.no} className={`agenda-item ${item.locked ? "locked" : ""}`}>
          <div className="ag-no">{item.no}</div>
          <div>
            <div className="ag-t">{item.title}</div>
            <div className="ag-d">{item.desc}</div>
          </div>
          {item.note && <div className="ag-lock">{item.note}</div>}
        </div>
      ))}
    </>
  );
}
