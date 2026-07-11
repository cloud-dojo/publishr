// ユーザー入力の直書き（Firestore直 or mockのlocalStorageフォールバック）。
// Firebase設定済み時は Firestore 直書き、未設定（mock）時は localStorage に保存して
// 画面遷移を確認できるようにする（フェーズ3の単独実装用フォールバック）。
"use client";

import { arrayRemove, arrayUnion, doc, getDoc, setDoc, updateDoc } from "firebase/firestore";

import { DEMO_USER_ID, dataSource } from "./config";
import type { InitialProfileInput } from "./profileOptions";
import { getDb, getFirebaseAuth } from "@/lib/firebase";

export type ConnectSource = "drive" | "calendar" | "tasks";

export function currentUid(): string {
  return getFirebaseAuth()?.currentUser?.uid ?? DEMO_USER_ID;
}

const LS = {
  profile: (uid: string) => `publishr.initialProfile.${uid}`,
  sources: (uid: string) => `publishr.connectedSources.${uid}`,
  firstRun: (uid: string) => `publishr.firstRun.${uid}`,
};

// --- 初回体験ステータス（localStorage・uid別） ---
// "generating": 登録直後、最初の本棚を生成中。 "ready": 初回入荷完了。
// null: 未登録 or 既存ユーザー（通常表示）。Firestore ルールは users の
// 任意フィールド書込を許さないため localStorage で持つ（デモ/初回導線用）。
export type FirstRunStatus = "generating" | "ready";

export function getFirstRunStatus(uidOverride?: string): FirstRunStatus | null {
  if (typeof window === "undefined") return null;
  const uid = uidOverride ?? currentUid();
  const raw = window.localStorage.getItem(LS.firstRun(uid));
  return raw === "generating" || raw === "ready" ? raw : null;
}

export function setFirstRunStatus(status: FirstRunStatus, uidOverride?: string): void {
  if (typeof window === "undefined") return;
  const uid = uidOverride ?? currentUid();
  window.localStorage.setItem(LS.firstRun(uid), status);
}

// --- 初期プロフィール（localStorageキャッシュ＋Firestore） ---
// localStorage に必ずキャッシュする（getInitialProfile が読む先＝アカウント反映の正）。
// Firestore 書き込みは失敗してもデモ導線を止めない安全網（ルール未反映・権限拒否でも継続）。
export async function saveInitialProfile(profile: InitialProfileInput): Promise<void> {
  const uid = currentUid();
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LS.profile(uid), JSON.stringify(profile));
  }
  const db = getDb();
  // Firestore 反映は firestore モードのみ。bff ではゲスト＝佐倉uid が佐倉の共有 initialProfile を
  // 上書きし他ゲストに波及するため書かない。bff/mock は上の localStorage が per-client 永続を担う。
  if (db && dataSource === "firestore") {
    try {
      await setDoc(doc(db, "users", uid), { initialProfile: profile }, { merge: true });
    } catch (e) {
      console.warn("initialProfile の Firestore 保存に失敗（localStorage で継続）", e);
    }
  }
}

/**
 * ログアウト時に per-client の初期プロフィール/初回状態/連携トグルを消す（bff リセット整合）。
 * bff/mock は Firestore に書いていないので localStorage を消せば原状へ戻る（uid別キーを全消し）。
 */
export function clearLocalProfile(): void {
  if (typeof window === "undefined") return;
  for (const key of Object.keys(window.localStorage)) {
    if (
      key.startsWith("publishr.initialProfile.") ||
      key.startsWith("publishr.firstRun.") ||
      key.startsWith("publishr.connectedSources.")
    ) {
      window.localStorage.removeItem(key);
    }
  }
}

export function getInitialProfile(): InitialProfileInput | null {
  const uid = currentUid();
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LS.profile(uid));
  return raw ? (JSON.parse(raw) as InitialProfileInput) : null;
}

/**
 * 初期設定（オンボーディング）が済んでいるか。
 * Firestore の users/{uid}.initialProfile を優先し、失敗時は localStorage で判定する。
 * skipped も「フローを通った」とみなし済み扱い（再ログインで再度オンボーディングに送らない）。
 */
export async function hasCompletedOnboarding(uidOverride?: string): Promise<boolean> {
  const uid = uidOverride ?? currentUid();
  const db = getDb();
  if (db) {
    try {
      const snap = await getDoc(doc(db, "users", uid));
      const ip = snap.exists() ? snap.data().initialProfile : null;
      if (ip) return true;
    } catch (e) {
      console.warn("initialProfile の Firestore 読取に失敗（localStorage で判定）", e);
    }
  }
  // localStorage フォールバック（同一ブラウザでの再ログイン）。
  if (typeof window !== "undefined") {
    return window.localStorage.getItem(LS.profile(uid)) != null;
  }
  return false;
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
  voiceStyle: string;
  format: string;
  savedAt: string;
}

type FavoriteAuthorPatch = FavoriteAuthorEntry | Pick<FavoriteAuthorEntry, "personaId">;

export async function addFavoriteAuthor(entry: FavoriteAuthorEntry): Promise<void> {
  const uid = currentUid();
  const db = getDb();
  // Firestore 反映は firestore モードのみ。bff（無認証ショーケース）ではゲスト＝佐倉uidのため
  // 共有 user doc に書くと他ゲストに波及・永続する（汚染）。bff/mock は favorites-store の
  // localStorage が per-client 永続を担う。
  if (db && dataSource === "firestore") {
    await setDoc(doc(db, "users", uid), { favoriteAuthors: arrayUnion(entry) }, { merge: true });
  }
}

export async function removeFavoriteAuthor(entry: FavoriteAuthorPatch): Promise<void> {
  const uid = currentUid();
  const db = getDb();
  if (db && dataSource === "firestore") {
    const ref = doc(db, "users", uid);
    const snap = await getDoc(ref);
    const current = (snap.exists() ? snap.data().favoriteAuthors : []) as FavoriteAuthorEntry[];
    const matches = current.filter((x) => x?.personaId === entry.personaId);
    if (matches.length > 0) {
      await updateDoc(ref, { favoriteAuthors: arrayRemove(...matches) });
    }
  }
}
