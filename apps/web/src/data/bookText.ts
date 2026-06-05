// 本文（Markdown）解析の共通ユーティリティ。
// 読書ページ（ページ分割・ハイライト）と /highlights（章名導出）で共用する。
// 仕様：`## ` で始まる行＝章見出し、空行区切り＝段落。段落は本全体で通し番号 pi。

export type ReaderBlock =
  | { kind: "chapter"; text: string }
  | { kind: "para"; text: string; pi: number; chapter: string; lead: boolean };

export function parseBook(body: string | null | undefined, fallback = ""): ReaderBlock[] {
  const src = body && body.trim() ? body : fallback;
  const blocks: ReaderBlock[] = [];
  let chapter = "";
  let pi = 0;
  let firstPara = true;
  let buf: string[] = [];
  const flush = () => {
    if (buf.length) {
      blocks.push({ kind: "para", text: buf.join(""), pi: pi++, chapter, lead: firstPara });
      firstPara = false;
      buf = [];
    }
  };
  for (const line of src.split("\n")) {
    if (line.startsWith("## ")) {
      flush();
      chapter = line.slice(3).trim();
      blocks.push({ kind: "chapter", text: chapter });
      continue;
    }
    if (line.trim() === "") {
      flush();
      continue;
    }
    buf.push(line.trim());
  }
  flush();
  return blocks;
}

/** 章見出しを「章番号」と「タイトル」に分解（章扉の大見出し用）。 */
export function splitChapter(heading: string): { no: string; title: string } {
  const m = heading.match(/^(第[0-9０-９一二三四五六七八九十百]+章|Chapter\s*\d+|序章?|終章?|序|終)\s*(.*)$/);
  if (m) return { no: m[1].trim(), title: m[2].trim() };
  return { no: "", title: heading.trim() };
}

/** 段落番号 pi が属する章名を返す（無ければ ""）。 */
export function chapterForPara(body: string | null | undefined, pi: number): string {
  for (const b of parseBook(body)) {
    if (b.kind === "para" && b.pi === pi) return b.chapter;
  }
  return "";
}

/** 表示精度（granularity）でブロックを絞り込む。pi は元のまま保持（注釈キーの安定性）。 */
export function applyGranularity(
  blocks: ReaderBlock[],
  granularity: "full" | "summary" | "excerpt"
): ReaderBlock[] {
  if (granularity === "full") return blocks;
  if (granularity === "summary") {
    // 各章：見出し＋その章の最初の段落のみ
    const out: ReaderBlock[] = [];
    let tookParaInChapter = false;
    for (const b of blocks) {
      if (b.kind === "chapter") {
        out.push(b);
        tookParaInChapter = false;
      } else if (!tookParaInChapter) {
        out.push(b);
        tookParaInChapter = true;
      }
    }
    return out;
  }
  // excerpt: 最初の章見出し＋最初の段落だけ
  const out: ReaderBlock[] = [];
  let paraCount = 0;
  for (const b of blocks) {
    if (b.kind === "chapter") {
      if (out.length === 0) out.push(b);
      else break;
    } else {
      out.push(b);
      if (++paraCount >= 1) break;
    }
  }
  return out;
}
