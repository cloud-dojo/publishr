"use client";

/**
 * 未認証ユーザーをログイン画面へ送るガード。
 *
 * 背景: firestore モード（本番）でログアウト状態のままシェルを開くと、
 * provider は uid=null で動き、UI は fixtures のデモペルソナ（佐倉美咲）に
 * フォールバックする。その結果「ログインしているつもりが実は未認証」で
 * シード/デモ表示が出てしまい、実ユーザーのデータと取り違える事故が起きる。
 * そこで Firebase 設定時のみ、未認証なら /login へ誘導して状態を明示する。
 *
 * onAuthStateChanged は永続セッション復元後に初回発火するため、
 * そこで user=null なら「未ログイン確定」と判断してよい（誤リダイレクトしない）。
 * mock（isFirebaseConfigured=false）では何もしない＝ローカルデモは従来どおり。
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { isFirebaseConfigured } from "@/data/config";
import { watchAuth } from "@/lib/firebase";

export function AuthGuard() {
  const router = useRouter();
  useEffect(() => {
    if (!isFirebaseConfigured) return; // mock/オフラインでは認証不要
    return watchAuth((user) => {
      if (!user) router.replace("/login");
    });
  }, [router]);
  return null; // UI を持たない副作用コンポーネント
}
