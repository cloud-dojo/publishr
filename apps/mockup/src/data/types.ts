/*
 * Firestoreスキーマ準拠の型定義。
 * フィールド名は UI仕様書 §3 / Publishr_技術アーキテクチャ §3 に合わせ、
 * 後で実Firestore購読へ差し替える境界とする。
 * モックでは coverUrl の代わりに coverFamily（CSSグラデ名）を使う。
 */

export type BookStatus = "draft" | "reserved" | "writing" | "published";
export type ThemeKind = "honmei" | "serendipity";
export type CoverFamily =
  | "navy"
  | "green"
  | "brown"
  | "ink"
  | "wine"
  | "gold";

export interface Feedback {
  rating?: number; // 1-5
  dropped?: boolean;
  read?: number; // 0-100 (%)
  wantsSequel?: boolean;
}

export interface Book {
  bookId: string;
  ownerUid: string;
  title: string;
  subtitle?: string;
  coverFamily: CoverFamily; // 実装では coverUrl (GCS)
  status: BookStatus;
  themeKind: ThemeKind;
  authorPersonaId: string;
  planId: string;
  prefaceSample: string;
  feedback?: Feedback;
  writingProgress?: number; // 0-100。バックが書くか未確認（仕様TODO）
}

export interface AgendaItem {
  no: string;
  title: string;
  note?: string;
}

export interface Plan {
  planId: string;
  reason: string; // 入荷理由・あなたへの文脈
  readerSituation: string; // 解決する課題
  coreMessage: string; // 核心メッセージ
  agendaOutline: AgendaItem[]; // 目次
}

export interface Persona {
  personaId: string;
  name: string;
  style: string; // スタイルタグ（短文・カンマ区切り表示用）
  styleTags: string[]; // チップ表示用
  avatarChar: string; // 丸アイコンの漢字1文字
  background: string; // 経歴・専門性
  voice: string; // 文体・書き方の特徴
  thought: string; // 思想・世界観
  expertise: string[]; // 専門・テーマ
  quote: string; // 著者名言
  pastBookIds: string[]; // この著者の既読本
}

export type HighlightKind = "highlight" | "note" | "bookmark";

export interface Highlight {
  id: string;
  bookId: string;
  kind: HighlightKind;
  text: string;
  chapter?: string;
  note?: string; // 付箋メモ
  tags: string[];
  savedAt: string; // ISO8601
}

export interface FavoriteAuthor {
  personaId: string;
  name: string;
  style: string;
  savedAt: string;
}

export interface InitialProfile {
  industry: string;
  jobType: string;
  position: string;
  recentInterests: string[];
  readingGenres: string[];
}

export interface User {
  uid: string;
  displayName: string;
  email: string;
  role: string; // 役職・所属（アカウント画面で表示）
  avatarChar: string;
  initialProfile: InitialProfile;
  favoriteAuthors: FavoriteAuthor[];
}

/* 読書本文（GCSのMD相当をモック） */
export interface BodyBlock {
  type: "dropcap" | "p" | "note";
  text: string;
  // dropcap: 先頭1文字をドロップキャップに
  // p内の {{...}} はハイライト済みスパンとしてレンダリング
}

export interface BookBody {
  bookId: string;
  chapterLabel: string; // "Chapter 05"
  chapterTitle: string; // "権限の設計図"
  blocks: BodyBlock[];
}
