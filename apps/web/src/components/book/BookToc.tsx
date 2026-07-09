import Link from "next/link";

import type { Book } from "@publishr/shared-schema";

import { bookChapters } from "@/data/bookText";

const KANJI_NUMBERS: Record<string, string> = {
  一: "1",
  二: "2",
  三: "3",
  四: "4",
  五: "5",
  六: "6",
  七: "7",
  八: "8",
  九: "9",
  十: "10",
};

function asciiNumber(s: string): string {
  return s.replace(/[０-９]/g, (ch) => String(ch.charCodeAt(0) - 0xff10));
}

function normalizedNumber(s: string): string {
  const ascii = KANJI_NUMBERS[s] ?? asciiNumber(s);
  const n = Number(ascii);
  return Number.isFinite(n) ? String(n) : ascii;
}

function chapterNo(no: string, title: string, chapterIndex: number): string {
  const raw = no.trim();
  const heading = title.trim();
  if (/^(序章|序|はじめに|まえがき)$/.test(raw) || /^(はじめに|まえがき)$/.test(heading)) {
    return "はじめに";
  }
  if (/^(終章|終|おわりに|あとがき)$/.test(raw) || /^(おわりに|あとがき)$/.test(heading)) {
    return "おわりに";
  }
  const numbered = raw.match(/^(?:第)?([0-9０-９一二三四五六七八九十]+)章$/);
  if (numbered) return `${normalizedNumber(numbered[1])}章`;
  if (/^[0-9０-９]+$/.test(raw)) return `${normalizedNumber(raw)}章`;
  return raw || `${chapterIndex + 1}章`;
}

function visibleTitle(no: string, title: string): string {
  const label = chapterNo(no, title, 0);
  const t = title.trim();
  return t === label || /^(はじめに|まえがき|おわりに|あとがき)$/.test(t) ? "" : t;
}

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
        {chapters.map((c) => {
          const title = visibleTitle(c.no, c.title);
          return (
            <Link
              key={c.index}
              href={`/read/${book.id}?ch=${c.index}`}
              className="agenda-item agenda-item--link"
            >
              <div className="ag-no">{chapterNo(c.no, c.title, c.index)}</div>
              <div>
                {title && <div className="ag-t">{title}</div>}
              </div>
            </Link>
          );
        })}
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
          <div className="ag-no">{chapterNo(item.no, item.title, 0)}</div>
          <div>
            <div className="ag-t">{item.title}</div>
            <div className="ag-d">{item.desc}</div>
          </div>
        </div>
      ))}
    </>
  );
}
