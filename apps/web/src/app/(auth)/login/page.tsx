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
  const [demoBusy, setDemoBusy] = useState(false);

  const getNextPath = () => {
    const rawNext = new URLSearchParams(window.location.search).get("next");
    // "/\evil.com" は WHATWG URL 解析で "//evil.com" 相当になりオープンリダイレクトになる。
    // 先頭 "/" かつ "//" でなく、バックスラッシュを含まない相対パスだけ許可する。
    return rawNext?.startsWith("/") && !rawNext.startsWith("//") && !rawNext.includes("\\")
      ? rawNext
      : "/";
  };

  const onLogin = async () => {
    setBusy(true);
    setError(null);
    try {
      if (isFirebaseConfigured) {
        const user = await signInWithGoogle();
        if (user) {
          // 初期設定済みならトップ、未設定ならオンボーディングへ（Firestore優先で判定）。
          const done = await hasCompletedOnboarding(user.uid);
          router.push(done ? getNextPath() : "/onboarding");
        } else {
          setError("ログインに失敗しました。");
        }
      } else {
        // mock: 認証なしで体験フローへ。登録済みならトップ、未登録ならオンボーディング。
        router.push(getInitialProfile() ? getNextPath() : "/onboarding");
      }
    } catch {
      setError("ログインに失敗しました。もう一度お試しください。");
    } finally {
      setBusy(false);
    }
  };

  const onDemoLogin = async () => {
    setDemoBusy(true);
    setError(null);
    try {
      // パスワードレス（ワンクリック）: BFF が佐倉uidのカスタムトークンを返す。
      const resp = await fetch(`${apiUrl}/api/demo-token`, { method: "POST" });
      if (!resp.ok) {
        setError("ゲストログインに失敗しました。");
        return;
      }
      const { token } = await resp.json();
      const user = await signInWithDemoToken(token);
      if (user) {
        const done = await hasCompletedOnboarding(user.uid);
        router.push(done ? getNextPath() : "/onboarding");
      } else {
        setError("ゲストログインに失敗しました。");
      }
    } catch {
      setError("ゲストログインに失敗しました。もう一度お試しください。");
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

        {/* ゲストログイン（Firebase設定済みのみ表示・I-32）: パスワード不要のワンクリック。
            佐倉uidのセッションになり、佐倉の書店をそのまま体験できる。 */}
        {isFirebaseConfigured && (
          <>
            <div className="auth-or">または</div>
            <div className="auth-demo">
              <p className="auth-demo-label">アカウント登録なしで体験する</p>
              <button
                type="button"
                className="btn btn--outline btn--block"
                onClick={onDemoLogin}
                disabled={demoBusy}
              >
                {demoBusy ? "ログイン中…" : "ゲストログイン"}
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
