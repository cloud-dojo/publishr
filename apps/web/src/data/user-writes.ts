// ユーザー入力の直書き（Firestore直 or mockのlocalStorageフォールバック）。
// 正本: docs/design/api-contract.md §2-a（initialProfile）/ §3-a（favoriteAuthors）。
// Firebase設定済み時は Firestore 直書き、未設定（mock）時は localStorage に保存して
// 画面遷移を確認できるようにする（フェーズ3の単独実装用フォールバック）。
"use client";

import { arrayRemove, arrayUnion, doc, setDoc, updateDoc } from "firebase/firestore";

import { DEMO_USER_ID } from "./config";
import type { InitialProfileInput } from "./profileOptions";
import { getDb, getFirebaseAuth } from "@/lib/firebase";

export type ConnectSource = "drive" | "calendar" | "tasks";

export function currentUid(): string {
  return getFirebaseAuth()?.currentUser?.uid ?? DEMO_USER_ID;
}

const LS = {
  profile: (uid: string) => `publishr.initialProfile.${uid}`,
  sources: (uid: string) => `publishr.connectedSources.${uid}`,
};

// --- 初期プロフィール（localStorageキャッシュ＋Firestore） ---
// localStorage に必ずキャッシュする（getInitialProfile が読む先＝アカウント反映の正）。
// Firestore 書き込みは失敗してもデモ導線を止めない安全網（ルール未反映・権限拒否でも継続）。
export async function saveInitialProfile(profile: InitialProfileInput): Promise<void> {
  const uid = currentUid();
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LS.profile(uid), JSON.stringify(profile));
  }
  const db = getDb();
  if (db) {
    try {
      await setDoc(doc(db, "users", uid), { initialProfile: profile }, { merge: true });
    } catch (e) {
      console.warn("initialProfile の Firestore 保存に失敗（localStorage で継続）", e);
    }
  }
}

export function getInitialProfile(): InitialProfileInput | null {
  const uid = currentUid();
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LS.profile(uid));
  return raw ? (JSON.parse(raw) as InitialProfileInput) : null;
}

// --- 観測ソース接続状態 ---
export async function setSourceConnected(source: ConnectSource, enabled: boolean): Promise<void> {
  const uid = currentUid();
  const db = getDb();
  if (db) {
    await setDoc(
      doc(db, "users", uid),
      { connectedSources: { [source]: { enabled } } },
      { merge: true }
    );
    return;
  }
  if (typeof window !== "undefined") {
    const cur = getConnectedSources();
    cur[source] = enabled;
    window.localStorage.setItem(LS.sources(uid), JSON.stringify(cur));
  }
}

export function getConnectedSources(): Record<ConnectSource, boolean> {
  const uid = currentUid();
  const empty = { drive: false, calendar: false, tasks: false };
  if (typeof window === "undefined") return empty;
  const raw = window.localStorage.getItem(LS.sources(uid));
  return raw ? { ...empty, ...(JSON.parse(raw) as Record<ConnectSource, boolean>) } : empty;
}

/**
 * デモ用の連携トグル：localStorage のみに保存する（実OAuth未実装のMVP）。
 * Firestore の connectedSources はサーバ（Admin）が書く前提でルール上クライアント
 * 書き込みが禁止されているため、ここでは Firestore に触れない。
 */
export function setSourceConnectedLocal(source: ConnectSource, enabled: boolean): void {
  if (typeof window === "undefined") return;
  const uid = currentUid();
  const cur = getConnectedSources();
  cur[source] = enabled;
  window.localStorage.setItem(LS.sources(uid), JSON.stringify(cur));
}

// --- お気に入り著者（Firestore直書き・arrayUnion/Remove） ---
export interface FavoriteAuthorEntry {
  personaId: string;
  name: string;
  savedAt: string;
}

export async function addFavoriteAuthor(entry: FavoriteAuthorEntry): Promise<void> {
  const uid = currentUid();
  const db = getDb();
  if (db) {
    await updateDoc(doc(db, "users", uid), { favoriteAuthors: arrayUnion(entry) });
  }
  // mock時はUI側のローカル状態で扱う（永続化は任意）。
}

export async function removeFavoriteAuthor(entry: FavoriteAuthorEntry): Promise<void> {
  const uid = currentUid();
  const db = getDb();
  if (db) {
    await updateDoc(doc(db, "users", uid), { favoriteAuthors: arrayRemove(entry) });
  }
}
