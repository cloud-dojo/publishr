"use client";

import { useRouter } from "next/navigation";

import { ConnectSources } from "@/components/ConnectSources";

export default function ConnectPage() {
  const router = useRouter();

  return (
    <div className="auth-frame">
      <div className="auth-card panel">
        <span className="eyebrow">Connect your sources</span>
        <h1 className="auth-title">あなたの仕事を、読み取らせてください。</h1>
        <p className="auth-lead">
          以下の3つを読み取り、あなたにいま必要な一冊を企画します。読み取りは自動の企画にのみ使われます。
        </p>

        <ConnectSources />

        <button type="button" className="btn btn--ghost btn--block" onClick={() => router.push("/")}>
          書店へ進む →
        </button>
      </div>
    </div>
  );
}
