"use client";

import { useEffect, useState, type ReactNode } from "react";

import { getProvider } from "@/data";
import { DEMO_OWNER_UID, dataSource } from "@/data/config";
import { clearLocalFavorites } from "@/data/favorites-store";
import { signOutUser, watchAuth } from "@/lib/firebase";

/**
 * 無認証公開ショーケース（bff）のログイン整合ガード。
 *
 * bff モードは佐倉(DEMO_OWNER_UID)のデモ書店を全訪問者に見せる読み取り専用ビュー。
 * BFF は owner_uid=demo_uid にスコープ済みで、誰がサインインしていても /books は佐倉の本を返す。
 * そのため実 Google アカウント（＝佐倉のデモ垢 DEMO_OWNER_UID 以外）でサインインしていると、
 * 佐倉のデモ本が「〇〇さんの書店」として本人のものと誤認される。これを防ぐため、実アカウントの
 * サインイン時はシェル全体（書店・本棚・サイドバー等）を中立の案内に差し替える。
 *
 * - 匿名（未サインイン）        → children（佐倉のデモ書店・従来どおり）
 * - デモアカウント（=佐倉uid）  → children（佐倉のデモ書店・デモログインの意図どおり）
 * - 実 Google アカウント        → 中立の案内＋ログアウト導線（佐倉のデータは非表示）
 *
 * bff 以外（mock/firestore）では常に children を返す＝実ユーザー別ビューを妨げない。
 */
export function ShowcaseGate({ children }: { children: ReactNode }) {
  const [uid, setUid] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  useEffect(
    () =>
      watchAuth((u) => {
        setUid(u?.uid ?? null);
        setDisplayName(u?.displayName ?? null);
      }),
    []
  );

  const blocked = dataSource === "bff" && uid !== null && uid !== DEMO_OWNER_UID;
  if (!blocked) return <>{children}</>;

  return <ShowcaseNotice name={displayName} />;
}

/** 実アカウントのサインイン中に佐倉のデモ本の代わりに出す中立の案内。 */
function ShowcaseNotice({ name }: { name: string | null }) {
  const [busy, setBusy] = useState(false);
  const onLogout = async () => {
    setBusy(true);
    try {
      // ログアウトで per-client のローカル状態（本棚・お気に入り）をリセット（次セッションを原状へ）。
      void getProvider().clearLocalLibrary();
      clearLocalFavorites();
      // サインアウトで watchAuth が null を通知 → blocked=false → 佐倉のデモ書店へ戻る。
      await signOutUser();
    } catch (err) {
      console.error(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-frame">
      <div className="auth-card panel">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="auth-logo" src="/favicon.svg" alt="Publishr" width={64} height={64} />
        <div className="auth-brand">
          Publishr<span className="dot">.</span>
        </div>
        <div className="auth-divider" />
        <p className="auth-hero">
          {name ? (
            <>
              ようこそ、<b>{name}</b> さん。
            </>
          ) : (
            <>ようこそ。</>
          )}
        </p>
        <p className="auth-lead">
          ここは佐倉さんの書店のショーケースです。
          あなた専用の書店は、現在この公開ページではご利用いただけません。
        </p>
        <button
          type="button"
          className="btn btn--gold btn--block"
          onClick={onLogout}
          disabled={busy}
        >
          {busy ? "ログアウト中…" : "ログアウトして書店を見る"}
        </button>
      </div>
    </div>
  );
}
