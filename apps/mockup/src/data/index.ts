/*
 * データ集約 + 派生セレクタ（純関数）。
 * これらは後で Firestore リアルタイム購読（onSnapshot）へ差し替える境界になる。
 * 画面コンポーネントは Firestore を直接知らず、このモジュール経由でのみデータに触れる。
 */
import { books, bookById, OWNER } from "./books";
import { plans, planById } from "./plans";
import { personas, personaById } from "./personas";
import { highlights } from "./highlights";
import { user } from "./user";
import { bodySample } from "./bodySample";
import type { Book, BookStatus, Highlight, HighlightKind } from "./types";

export { books, plans, personas, highlights, user, bodySample, OWNER };
export { bookById, planById, personaById };
export * from "./types";

/* --- 書籍 --- */
export const getBooksByStatus = (status: BookStatus): Book[] =>
  books.filter((b) => b.ownerUid === OWNER && b.status === status);

export const getBook = (id: string): Book =>
  bookById(id) ?? books[0]; // 不明IDは先頭にフォールバック（デモ中に壊れない）

export const getBooksByAuthor = (personaId: string): Book[] =>
  books.filter((b) => b.authorPersonaId === personaId);

/* 棚（わたしの書庫）= draft 以外（入荷前の新刊は含めない） */
export const getLibraryBooks = (): Book[] =>
  books.filter((b) => b.ownerUid === OWNER && b.status !== "draft");

/* --- 企画 --- */
export const getPlan = (id: string) => planById(id);

/* --- 著者 --- */
export const getPersona = (id: string) => personaById(id);

/* --- ハイライト --- */
export const getHighlightsByKind = (kind: HighlightKind | "all"): Highlight[] =>
  kind === "all" ? highlights : highlights.filter((h) => h.kind === kind);

export interface HighlightGroup {
  bookId: string;
  bookTitle: string;
  items: Highlight[];
}

export const getHighlightsGroupedByBook = (
  kind: HighlightKind | "all" = "all"
): HighlightGroup[] => {
  const list = getHighlightsByKind(kind);
  const order: string[] = [];
  const map = new Map<string, Highlight[]>();
  for (const h of list) {
    if (!map.has(h.bookId)) {
      map.set(h.bookId, []);
      order.push(h.bookId);
    }
    map.get(h.bookId)!.push(h);
  }
  return order.map((bookId) => ({
    bookId,
    bookTitle: bookById(bookId)?.title ?? "（不明な書籍）",
    items: map.get(bookId)!,
  }));
};

/* ハイライトのタグ頻度（テーマ分類「関心の地図」用） */
export const getHighlightTagCloud = (): { tag: string; count: number }[] => {
  const counts = new Map<string, number>();
  for (const h of highlights) {
    for (const t of h.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count);
};

/* --- 書庫統計（クライアントサイド計算） --- */
export interface LibraryStats {
  total: number; // 総冊数（棚の本）
  finished: number; // 読了
  avgRating: number; // 平均★
  highlightCount: number; // ハイライト数
}

export const getLibraryStats = (): LibraryStats => {
  const shelf = getLibraryBooks();
  const finishedBooks = shelf.filter((b) => b.status === "published");
  const rated = shelf.filter((b) => typeof b.feedback?.rating === "number");
  const avg =
    rated.length === 0
      ? 0
      : rated.reduce((s, b) => s + (b.feedback!.rating ?? 0), 0) / rated.length;
  return {
    total: shelf.length,
    finished: finishedBooks.length,
    avgRating: Math.round(avg * 10) / 10,
    highlightCount: highlights.length,
  };
};

/* サイドバー「直近の本」3冊（最近の既読 + 予約） */
export const getRecentBooks = (): Book[] =>
  [...getBooksByStatus("published"), ...getBooksByStatus("reserved")].slice(0, 3);
