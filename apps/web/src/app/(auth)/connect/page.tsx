"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { ConnectSources } from "@/components/ConnectSources";
import { DEMO_USER_ID } from "@/data/config";
import { useProvider } from "@/data/hooks";
import { watchAuth } from "@/lib/firebase";

function ConnectPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const provider = useProvider();

  const [uid, setUid] = useState<string | null>(null);
  useEffect(() => watchAuth((u) => setUid(u?.uid ?? null)), []);

  const user = provider.getUser(uid ?? DEMO_USER_ID);
  const justConnected = searchParams.get("connected") === "1";
  const allConnected =
    (user?.connectedSources?.drive?.enabled &&
      user?.connectedSources?.calendar?.enabled &&
      user?.connectedSources?.tasks?.enabled) ??
    false;

  return (
    <div className="auth-frame">
      <div className="auth-card panel">
        <span className="eyebrow">Connect your sources</span>
        <h1 className="auth-title">あなたの仕事を、読み取らせてください。</h1>

        {justConnected && (
          <p className="auth-note" style={{ color: "var(--color-success, #4caf50)" }}>
            ✓ Googleアカウントとの連携が完了しました。
          </p>
        )}

        <p className="auth-lead">
          以下の3つを読み取り、あなたにいま必要な一冊を企画します。読み取りは自動の企画にのみ使われます。
        </p>

        <ConnectSources initial={user?.connectedSources} />

        <button
          type="button"
          className="btn btn--ghost btn--block"
          style={{ marginTop: "var(--space-4, 1rem)" }}
          onClick={() => router.push("/")}
        >
          {allConnected ? "書店へ進む →" : "あとで連携する"}
        </button>
      </div>
    </div>
  );
}

export default function ConnectPage() {
  return (
    <Suspense>
      <ConnectPageInner />
    </Suspense>
  );
}
