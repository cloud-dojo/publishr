// 本文（Markdown）解析の共通ユーティリティ。
// 読書ページ（ページ分割・ハイライト）と /highlights（章名導出）で共用する。
// 仕様：`## ` で始まる行＝章見出し、空行区切り＝段落。段落は本全体で通し番号 pi。

// 見出し(chapter)のハイライト用 pi は、段落 pi(0,1,2…)と衝突しない別レンジを使う。
// これにより段落の pi を据え置いたまま（既存ハイライト非破壊で）見出しも注釈可能にする。
export const CHAPTER_PI_BASE = 1_000_000;

export type ReaderBlock =
  | { kind: "chapter"; text: string; pi: number }
  | { kind: "para"; text: string; pi: number; chapter: string; lead: boolean; bold: Array<[number, number]> }
  | { kind: "subhead"; text: string; pi: number; chapter: string }
  | { kind: "list"; items: string[]; ordered: boolean; pi: number; chapter: string }
  | { kind: "mermaid"; text: string; pi: number; chapter: string };

// インライン Markdown（**強調**）を解析し、記号を除いたクリーンテキストと
// 太字レンジ（クリーンテキスト座標）に分ける。ハイライトのオフセット計算は描画後の
// テキスト基準なので、格納テキストから `**` を必ず除いておく（座標ズレ防止）。
export function parseInline(raw: string): { text: string; bold: Array<[number, number]> } {
  const bold: Array<[number, number]> = [];
  let text = "";
  let i = 0;
  while (i < raw.length) {
    if (raw[i] === "*" && raw[i + 1] === "*") {
      const close = raw.indexOf("**", i + 2);
      if (close !== -1) {
        const inner = raw.slice(i + 2, close);
        const start = text.length;
        text += inner;
        if (inner) bold.push([start, text.length]);
        i = close + 2;
        continue;
      }
    }
    text += raw[i];
    i++;
  }
  return { text, bold };
}

export function parseBook(body: string | null | undefined, fallback = ""): ReaderBlock[] {
  const src = body && body.trim() ? body : fallback;
  const blocks: ReaderBlock[] = [];
  let chapter = "";
  let pi = 0;
  let chapterOrd = 0;
  let firstPara = true;
  let buf: string[] = [];
  let mermaidBuf: string[] | null = null;
  let listBuf: string[] | null = null;
  let listOrdered = false;
  const flush = () => {
    if (buf.length) {
      const { text, bold } = parseInline(buf.join(""));
      blocks.push({ kind: "para", text, pi: pi++, chapter, lead: firstPara, bold });
      firstPara = false;
      buf = [];
    }
  };
  const flushList = () => {
    if (listBuf && listBuf.length) {
      blocks.push({ kind: "list", items: listBuf, ordered: listOrdered, pi: pi++, chapter });
      firstPara = false;
    }
    listBuf = null;
  };
  for (const line of src.split("\n")) {
    // mermaid フェンス内の処理
    if (mermaidBuf !== null) {
      if (line.trim() === "```") {
        flush();
        blocks.push({ kind: "mermaid", text: mermaidBuf.join("\n"), pi: pi++, chapter });
        mermaidBuf = null;
        firstPara = false;
      } else {
        mermaidBuf.push(line);
      }
      continue;
    }
    // mermaid フェンス開始
    if (line.trim() === "```mermaid") {
      flushList();
      flush();
      mermaidBuf = [];
      continue;
    }
    // 小見出し（### 〜 ###### …）。章見出し（## …）より先に判定する。
    const subm = line.match(/^#{3,6}\s+(.*)$/);
    if (subm) {
      flushList();
      flush();
      const { text } = parseInline(subm[1].trim());
      blocks.push({ kind: "subhead", text, pi: pi++, chapter });
      firstPara = false;
      continue;
    }
    if (line.startsWith("## ")) {
      flushList();
      flush();
      chapter = line.slice(3).trim();
      blocks.push({ kind: "chapter", text: chapter, pi: CHAPTER_PI_BASE + chapterOrd++ });
      continue;
    }
    const trimmed = line.trim();
    // 箇条書き（- / * / 1.）。`**強調` 始まりの段落と取り違えない。
    const ulm = !trimmed.startsWith("**") ? trimmed.match(/^[-*]\s+(.*)$/) : null;
    const olm = trimmed.match(/^\d+\.\s+(.*)$/);
    if (ulm || olm) {
      flush();
      if (listBuf === null) {
        listBuf = [];
        listOrdered = !!olm;
      }
      const item = ulm ? ulm[1] : olm![1];
      listBuf.push(parseInline(item).text);
      continue;
    }
    if (trimmed === "") {
      flush();
      flushList();
      continue;
    }
    flushList();
    buf.push(trimmed);
  }
  flush();
  flushList();
  return blocks;
}

/** 章見出しを「章番号」と「タイトル」に分解（章扉の大見出し用）。 */
export function splitChapter(heading: string): { no: string; title: string } {
  const m = heading.match(/^((?:第)?[0-9０-９一二三四五六七八九十百]+章|Chapter\s*\d+|序章?|終章?|序|終|はじめに|まえがき|おわりに|あとがき)\s*(.*)$/);
  if (m) return { no: m[1].trim(), title: m[2].trim() };
  return { no: "", title: heading.trim() };
}

/** 本文（body）から実際の章一覧を導出する。index は reader の .rd-opener 並び順と一致。 */
export function bookChapters(
  body: string | null | undefined
): { no: string; title: string; index: number }[] {
  const out: { no: string; title: string; index: number }[] = [];
  let index = 0;
  for (const b of parseBook(body)) {
    if (b.kind === "chapter") {
      const { no, title } = splitChapter(b.text);
      out.push({ no: no || `${index + 1}`, title: title || b.text, index });
      index++;
    }
  }
  return out;
}

function paragraphs(raw: string | null | undefined): string[] {
  return (raw ?? "").split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
}

function isIntroChapter(chapter: string): boolean {
  return /^(序章|序|はじめに|まえがき)/.test(chapter.trim());
}

function isOutroChapter(chapter: string): boolean {
  return /^(終章|終|おわりに|あとがき|最後に)/.test(chapter.trim());
}

/** 古いデモ本文に、独立した「はじめに」「おわりに」が無い場合だけ補う。 */
export function ensureBookFrame(
  body: string | null | undefined,
  prefaceSample: string | null | undefined,
  title: string
): string | null {
  if (!body?.trim()) return body ?? null;
  const chapters = bookChapters(body);
  const hasIntro = chapters.some((c) => isIntroChapter(c.no) || isIntroChapter(c.title));
  const hasOutro = chapters.some((c) => isOutroChapter(c.no) || isOutroChapter(c.title));
  const parts: string[] = [];

  if (!hasIntro) {
    const intro = paragraphs(prefaceSample).slice(0, 3);
    const introText = intro.length > 0
      ? intro.join("\n\n")
      : `この本は、いま必要な問いを立て直すための一冊です。${title}という主題を、明日からの行動につながる形で読み進めていきます。`;
    parts.push(`## はじめに\n\n${introText}`);
  }

  parts.push(body.trim());

  if (!hasOutro) {
    parts.push(
      `## おわりに\n\n${title}で扱ってきたことは、読み終えた瞬間に完結するものではありません。まずは、今日の仕事の中で一つだけ判断の置き方を変えてみてください。その小さな一歩が、次の局面を動かす入口になります。`
    );
  }

  return parts.join("\n\n");
}

/** 本の概要ページ用の試し読み断片。prefaceSample が短い時は本文冒頭から最大3段落を補う。 */
export function overviewExcerptParagraphs(
  body: string | null | undefined,
  prefaceSample: string | null | undefined,
  max = 3
): string[] {
  const sample = paragraphs(prefaceSample);
  const sampleChars = sample.join("").length;
  if (sample.length >= 2 || sampleChars >= 90 || !body?.trim()) {
    return sample.slice(0, max);
  }

  const blocks = parseBook(body);
  const intro: string[] = [];
  const allParagraphs: string[] = [];
  for (const b of blocks) {
    if (b.kind !== "para") continue;
    allParagraphs.push(b.text);
    if (isIntroChapter(b.chapter)) intro.push(b.text);
  }
  const fromBody = intro.length > 0 ? intro : allParagraphs;
  return (fromBody.length > 0 ? fromBody : sample).slice(0, max);
}

/** pi が属する章名を返す（段落・見出しの両方に対応。無ければ ""）。 */
export function chapterForPara(body: string | null | undefined, pi: number): string {
  for (const b of parseBook(body)) {
    if ((b.kind === "para" || b.kind === "subhead") && b.pi === pi) return b.chapter;
    if (b.kind === "chapter" && b.pi === pi) return b.text; // 見出し自身のハイライト
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
    // 各章：見出し＋その章の最初の段落のみ（小見出し/箇条書きはスキップ）
    const out: ReaderBlock[] = [];
    let tookParaInChapter = false;
    for (const b of blocks) {
      if (b.kind === "chapter") {
        out.push(b);
        tookParaInChapter = false;
      } else if (b.kind === "para" && !tookParaInChapter) {
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
    } else if (b.kind === "para") {
      out.push(b);
      if (++paraCount >= 1) break;
    }
  }
  return out;
}
