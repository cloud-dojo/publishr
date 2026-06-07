// お気に入り著者の軽量リアクティブストア（useSyncExternalStore）。
// - mock: localStorage に personaId を保存して画面間・再読込でも保持。
// - Firebase設定時: user-writes 経由で Firestore にも反映（arrayUnion/Remove）。
// モックアップの favoritesStore 相当。著者一覧／著者詳細の双方から使える。
"use client";

import { useSyncExternalStore } from "react";

import { watchAuth } from "@/lib/firebase";

import { DEMO_USER_ID } from "./config";
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

/** 初回購読時に auth を監視し、ログイン状態に応じて該当ユーザー分へ切り替える。 */
function ensureAuthWatch(): void {
  if (authWatched || typeof window === "undefined") return;
  authWatched = true;
  hydrateFor(currentUid()); // まず現在の uid（未ログインなら DEMO）で読み込み
  watchAuth((u) => hydrateFor(u?.uid ?? DEMO_USER_ID));
}

export function toggleFavorite(entry: FavoriteAuthorEntry): void {
  if (favorites.has(entry.personaId)) {
    favorites.delete(entry.personaId);
    void removeFavoriteAuthor(entry);
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
