import { useSyncExternalStore } from "react";
import { user } from "./user";

/*
 * お気に入り著者の共有ストア（モックの簡易グローバル状態）。
 * 読書ページ・著者詳細・著者一覧で同じ状態を共有する。
 * 実装では users/{uid}.favoriteAuthors への直書き（arrayUnion/arrayRemove）に差し替える。
 */

let favorites = new Set<string>(
  user.favoriteAuthors.map((f) => f.personaId)
);

const listeners = new Set<() => void>();

function emit() {
  // Set参照を更新してスナップショットの同一性を変える
  favorites = new Set(favorites);
  listeners.forEach((l) => l());
}

export function toggleFavorite(personaId: string): boolean {
  if (favorites.has(personaId)) {
    favorites.delete(personaId);
    emit();
    return false;
  }
  favorites.add(personaId);
  emit();
  return true;
}

export function isFavorite(personaId: string): boolean {
  return favorites.has(personaId);
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function getSnapshot() {
  return favorites;
}

/* お気に入りSetを購読するフック */
export function useFavorites(): Set<string> {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
