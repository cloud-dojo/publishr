// お気に入り著者の軽量リアクティブストア（useSyncExternalStore）。
// - mock: localStorage に personaId を保存して画面間・再読込でも保持。
// - Firebase設定時: user-writes 経由で Firestore にも反映（arrayUnion/Remove）。
// モックアップの favoritesStore 相当。著者一覧／著者詳細の双方から使える。
"use client";

import { useSyncExternalStore } from "react";

import {
  addFavoriteAuthor,
  currentUid,
  removeFavoriteAuthor,
  type FavoriteAuthorEntry,
} from "./user-writes";

let favorites = new Set<string>();
let hydrated = false;
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

function hydrateOnce(): void {
  if (hydrated || typeof window === "undefined") return;
  hydrated = true;
  const raw = window.localStorage.getItem(lsKey());
  if (raw) {
    try {
      favorites = new Set(JSON.parse(raw) as string[]);
      emit();
    } catch {
      /* ignore */
    }
  }
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
  hydrateOnce();
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
