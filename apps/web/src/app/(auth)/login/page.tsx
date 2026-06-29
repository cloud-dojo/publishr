"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiUrl, isFirebaseConfigured } from "@/data/config";
import { getInitialProfile, hasCompletedOnboarding } from "@/data/user-writes";
import { signInWithDemoToken, signInWithGoogle } from "@/lib/firebase";

export default function LoginPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoPassword, setDemoPassword] = useState("");
  const [demoBusy, setDemoBusy] = useState(false);

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

  const onDemoLogin = async () => {
    if (!demoPassword) return;
    setDemoBusy(true);
    setError(null);
    try {
      const resp = await fetch(`${apiUrl}/api/demo-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: demoPassword }),
      });
      if (!resp.ok) {
        setError(resp.status === 401 ? "パスワードが違います。" : "デモログインに失敗しました。");
        return;
      }
      const { token } = await resp.json();
      const user = await signInWithDemoToken(token);
      if (user) {
        const done = await hasCompletedOnboarding(user.uid);
        router.push(done ? "/" : "/onboarding");
      } else {
        setError("デモログインに失敗しました。");
      }
    } catch {
      setError("デモログインに失敗しました。もう一度お試しください。");
    } finally {
      setDemoBusy(false);
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

        {/* デモアカウントログイン（Firebase設定済みのみ表示・I-32） */}
        {isFirebaseConfigured && (
          <>
            <div className="auth-or">または</div>
            <div className="auth-demo">
              <p className="auth-demo-label">デモアカウントでログイン</p>
              <div className="auth-demo-field">
                <span className="auth-demo-id-label">ID</span>
                <span className="auth-demo-id-value">publishr</span>
              </div>
              <div className="auth-demo-field">
                <span className="auth-demo-id-label">Password</span>
                <input
                  type="password"
                  className="auth-demo-input"
                  placeholder="パスワードを入力"
                  value={demoPassword}
                  onChange={(e) => setDemoPassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && onDemoLogin()}
                />
              </div>
              <button
                type="button"
                className="btn btn--outline btn--block"
                onClick={onDemoLogin}
                disabled={demoBusy || !demoPassword}
              >
                {demoBusy ? "ログイン中…" : "デモでログイン"}
              </button>
            </div>
          </>
        )}

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
