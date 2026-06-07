"use client";

/**
 * Firebase Auth の認証状態を DataProvider（FirestoreProvider）に橋渡しするコンポーネント。
 *
 * FirestoreProvider.setOwnerUid(uid) が呼ばれて初めて onSnapshot の購読が始まる。
 * このコンポーネントを Shell レイアウトに配置することで、ログイン直後に
 * Firestore の書籍・プラン・著者データが自動的に流れ込む。
 *
 * MockProvider / BffProvider には setOwnerUid が無いため ?. でフォールバック安全。
 */

import { useEffect } from "react";

import { watchAuth } from "@/lib/firebase";
import { getProvider } from "@/data";

export function AuthSync() {
  useEffect(() => {
    // watchAuth は onAuthStateChanged のラッパー。unsubscribe 関数を返す。
    return watchAuth((user) => {
      const provider = getProvider();
      // FirestoreProvider のみ setOwnerUid を持つ。他プロバイダは no-op。
      if ("setOwnerUid" in provider && typeof (provider as any).setOwnerUid === "function") {
        (provider as any).setOwnerUid(user?.uid ?? null);
      }
    });
  }, []);

  return null; // UI を持たない純粋な副作用コンポーネント
}
