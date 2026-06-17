"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AuthSync } from "@/components/AuthSync";
import { ConnectSources } from "@/components/ConnectSources";
import { DEMO_USER_ID } from "@/data/config";
import { useProvider } from "@/data/hooks";
import { watchAuth } from "@/lib/firebase";

function ConnectInner() {
  const router = useRouter();
  const params = useSearchParams();
  // OAuth callback は /connect?connected=1 に戻す。完了表示＋実状態の確認導線にする。
  const justConnected = params.get("connected") === "1";

  // ログイン中ユーザーの実 connectedSources（サーバ正本）を取得して ConnectSources に渡す。
  // FirestoreProvider は AuthSync の setOwnerUid 後に users ドキュメントを購読するので、
  // OAuth 完了で更新された連携状態が（再ログイン無しで）流れ込む。
  const provider = useProvider();
  const [uid, setUid] = useState<string | null>(null);
  useEffect(() => watchAuth((u) => setUid(u?.uid ?? null)), []);
  const user = provider.getUser(uid ?? DEMO_USER_ID);

  return (
    <div className="auth-frame">
      <div className="auth-card panel">
        <span className="eyebrow">Connect your sources</span>
        <h1 className="auth-title">あなたの仕事を、読み取らせてください。</h1>
        {justConnected ? (
          <p className="auth-lead">
            ✓ Google との連携が完了しました。下の状態を確認し、Drive は読み取り対象フォルダを選んでください。
          </p>
        ) : (
          <p className="auth-lead">
            以下の3つを読み取り、あなたにいま必要な一冊を企画します。読み取りは自動の企画にのみ使われます。
          </p>
        )}

        <ConnectSources initial={user?.connectedSources} />

        <button type="button" className="btn btn--ghost btn--block" onClick={() => router.push("/")}>
          書店へ進む →
        </button>
      </div>
    </div>
  );
}

export default function ConnectPage() {
  return (
    <>
      {/* Firebase Auth → FirestoreProvider.setOwnerUid()。(auth) には Shell が無いので個別に張る */}
      <AuthSync />
      <Suspense fallback={<div className="auth-frame" />}>
        <ConnectInner />
      </Suspense>
    </>
  );
}
