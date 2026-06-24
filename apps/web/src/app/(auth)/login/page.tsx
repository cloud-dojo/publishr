"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { isFirebaseConfigured } from "@/data/config";
import { getInitialProfile, hasCompletedOnboarding } from "@/data/user-writes";
import { signInWithGoogle } from "@/lib/firebase";

export default function LoginPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onLogin = async () => {
    setBusy(true);
    setError(null);
    try {
      if (isFirebaseConfigured) {
        const user = await signInWithGoogle();
        if (user) {
          // 初期設定済みならトップ、未設定ならオンボーディングへ（Firestore優先で判定）。
          const done = await hasCompletedOnboarding(user.uid);
          router.push(done ? "/" : "/onboarding");
        } else {
          setError("ログインに失敗しました。");
        }
      } else {
        // mock: 認証なしで体験フローへ。登録済みならトップ、未登録ならオンボーディング。
        router.push(getInitialProfile() ? "/" : "/onboarding");
      }
    } catch {
      setError("ログインに失敗しました。もう一度お試しください。");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-frame">
      <div className="auth-card panel">
        {/* ロゴ */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="auth-logo" src="/favicon.svg" alt="Publishr" width={64} height={64} />

        {/* ブランド名 */}
        <div className="auth-brand">
          Publishr<span className="dot">.</span>
        </div>

        {/* 金色セパレーター */}
        <div className="auth-divider" />

        {/* キーフレーズ */}
        <p className="auth-hero">
          百万部のベストセラーより、<br />
          あなたのための一冊。
        </p>

        {/* サブコピー */}
        <p className="auth-lead">
          あなたの仕事と関心を読み、編集部が自律的に企画します。
        </p>

        <button type="button" className="btn btn--gold btn--block" onClick={onLogin} disabled={busy}>
          {busy ? "サインイン中…" : "Googleでログイン"}
        </button>
        {error && <p className="auth-error">{error}</p>}
        {!isFirebaseConfigured && (
          <p className="auth-note">
            ※ 現在はデモモード（mock）。Firebase 設定後に実際のGoogleログインに切り替わります。
          </p>
        )}
      </div>
    </div>
  );
}
