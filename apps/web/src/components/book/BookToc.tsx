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
        </div>
      ))}
    </>
  );
}
