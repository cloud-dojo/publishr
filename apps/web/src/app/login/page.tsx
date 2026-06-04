"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { isFirebaseConfigured } from "@/data/config";
import { getInitialProfile } from "@/data/user-writes";
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
        // 初期プロフィール未設定なら登録へ。判定の本実装はフェーズ3接続時に Firestore 読取で行う。
        if (user) router.push("/onboarding");
        else setError("ログインに失敗しました。");
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
        <div className="auth-brand">
          Publishr<span className="dot">.</span>
        </div>
        <p className="auth-tagline">百万部のベストセラーより、あなたのための一冊。</p>
        <p className="auth-lead">
          あなたの仕事と関心を読み、編集部が自律的に企画します。まずはGoogleでログインしてください。
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
