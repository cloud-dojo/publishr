"use client";

/**
 * 認証状態が確定するまでシェルの中身を描画しないゲート（フラッシュ防止＋未認証リダイレクト）。
 *
 * 背景: firestore モードでは onAuthStateChanged が「永続セッション復元後」に初回発火する。
 * それまでの間、各コンポーネントは uid=null のフォールバック（fixtures のデモ＝佐倉 や「ゲスト」）
 * を一瞬描画してしまう。ログイン済みユーザーにも他人/ゲストの残像が一瞬見える（#9）。
 * そこで認証が確定するまでローディングを出し、確定後（ログイン済み）だけ children を描画する。
 * 未ログイン確定なら /login へ送る（旧 AuthGuard の役割を統合）。
 * mock（isFirebaseConfigured=false）では即解決＝従来どおり。
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { isFirebaseConfigured } from "@/data/config";
import { watchAuth } from "@/lib/firebase";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  // mock は認証不要＝即解決。firestore は onAuthStateChanged の初回発火を待つ。
  const [ready, setReady] = useState(!isFirebaseConfigured);

  useEffect(() => {
    if (!isFirebaseConfigured) return;
    return watchAuth((user) => {
      if (!user) {
        router.replace("/login"); // 未ログイン確定
        return;
      }
      setReady(true); // ログイン確定＝この時点で初めて実 uid のデータを出す
    });
  }, [router]);

  if (!ready) {
    return (
      <div className="app-loading" aria-busy="true">
        読み込み中…
      </div>
    );
  }
  return <>{children}</>;
}
