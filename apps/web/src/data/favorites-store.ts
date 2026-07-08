// お気に入り著者の軽量リアクティブストア（useSyncExternalStore）。
// - mock: localStorage に personaId を保存して画面間・再読込でも保持。
// - Firebase設定時: user-writes 経由で Firestore にも反映（arrayUnion/Remove）。
// モックアップの favoritesStore 相当。著者一覧／著者詳細の双方から使える。
"use client";

import { useSyncExternalStore } from "react";
import { doc, onSnapshot } from "firebase/firestore";

import { getDb, watchAuth } from "@/lib/firebase";

import { DEMO_USER_ID, dataSource } from "./config";
import {
  addFavoriteAuthor,
  currentUid,
  removeFavoriteAuthor,
  type FavoriteAuthorEntry,
} from "./user-writes";

let favorites = new Set<string>();
// どの uid 分を読み込んだか。null = 未読込。auth 変化でこれと異なる uid に
// なったら読み直す（同一タブでのアカウント切替に追従）。
let hydratedUid: string | null = null;
let authWatched = false;
let firestoreUid: string | null = null;
let firestoreUnsub: (() => void) | null = null;
const listeners = new Set<() => void>();
const EMPTY: Set<string> = new Set();

const lsKey = () => `publishr.favoriteAuthors.${currentUid()}`;

function emit(): void {
  favorites = new Set(favorites); // 参照を変えて購読側に変更を伝える
  listeners.forEach((l) => l());
}

function persist(): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(lsKey(), JSON.stringify([...favorites]));
  }
}

function persistFor(uid: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(`publishr.favoriteAuthors.${uid}`, JSON.stringify([...favorites]));
  }
}

/** 指定 uid のお気に入りを localStorage から読み直す（uid が変わった時のみ）。 */
function hydrateFor(uid: string): void {
  if (typeof window === "undefined" || uid === hydratedUid) return;
  hydratedUid = uid;
  let next = new Set<string>();
  const raw = window.localStorage.getItem(`publishr.favoriteAuthors.${uid}`);
  if (raw) {
    try {
      next = new Set(JSON.parse(raw) as string[]);
    } catch {
      /* ignore */
    }
  }
  favorites = next;
  emit();
}

function watchFirestoreFavorites(uid: string): void {
  const db = getDb();
  // bff/mock は佐倉の共有 Firestore を読まない（他ゲストのお気に入りが混ざる汚染を防ぐ）。
  // 実ユーザー別の永続・購読は firestore モードのみ。
  if (!db || dataSource !== "firestore" || uid === firestoreUid) return;
  firestoreUnsub?.();
  firestoreUid = uid;
  firestoreUnsub = onSnapshot(
    doc(db, "users", uid),
    (snap) => {
      const favoriteAuthors = snap.exists() ? snap.data().favoriteAuthors : null;
      if (!Array.isArray(favoriteAuthors)) return;
      favorites = new Set(
        favoriteAuthors
          .map((x) => (typeof x?.personaId === "string" ? x.personaId : null))
          .filter((x): x is string => Boolean(x))
      );
      persistFor(uid);
      emit();
    },
    (err) => {
      console.warn("favoriteAuthors の Firestore 購読に失敗（localStorage で継続）", err);
    }
  );
}

/** 初回購読時に auth を監視し、ログイン状態に応じて該当ユーザー分へ切り替える。 */
function ensureAuthWatch(): void {
  if (authWatched || typeof window === "undefined") return;
  authWatched = true;
  hydrateFor(currentUid()); // まず現在の uid（未ログインなら DEMO）で読み込み
  watchFirestoreFavorites(currentUid());
  watchAuth((u) => {
    const uid = u?.uid ?? DEMO_USER_ID;
    hydrateFor(uid);
    watchFirestoreFavorites(uid);
  });
}

/**
 * ログアウト時に per-client のお気に入り作家をリセットする（bff ショーケースの初期化整合）。
 * localStorage の favoriteAuthors.* を全消し＋メモリ状態を空にして再購読者へ通知。次の auth 変化で
 * hydrateFor が空を読み直す。bff/mock は Firestore に書いていないので localStorage だけで完結する。
 */
export function clearLocalFavorites(): void {
  if (typeof window !== "undefined") {
    for (const key of Object.keys(window.localStorage)) {
      if (key.startsWith("publishr.favoriteAuthors.")) window.localStorage.removeItem(key);
    }
  }
  favorites = new Set();
  hydratedUid = null;
  emit();
}

export function toggleFavorite(entry: FavoriteAuthorEntry): void {
  if (favorites.has(entry.personaId)) {
    favorites.delete(entry.personaId);
    void removeFavoriteAuthor({ personaId: entry.personaId });
  } else {
    favorites.add(entry.personaId);
    void addFavoriteAuthor(entry);
  }
  persist();
  emit();
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  ensureAuthWatch();
  return () => {
    listeners.delete(cb);
  };
}

function getSnapshot(): Set<string> {
  return favorites;
}

function getServerSnapshot(): Set<string> {
  return EMPTY;
}

export function useFavorites(): Set<string> {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
