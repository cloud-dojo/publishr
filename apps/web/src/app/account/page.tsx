"use client";

import { Topbar } from "@/components/shell/Topbar";
import { DEMO_USER_ID } from "@/data/config";
import { useProvider } from "@/data/hooks";
import { MOCK_HIGHLIGHTS } from "@/data/mock-highlights";

const CONNECTED = [
  { name: "Google Drive", icon: "📁" },
  { name: "Google Calendar", icon: "📅" },
  { name: "Google Tasks", icon: "✓" },
];

function Mini({ n, label }: { n: number; label: string }) {
  return (
    <div className="acct-mini">
      <span className="am-num">{n}</span>
      <span className="am-label">{label}</span>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="acct-info">
      <span className="ai-label">{label}</span>
      <span className="ai-value">{value}</span>
    </div>
  );
}

export default function AccountPage() {
  const provider = useProvider();
  const user = provider.getUser(DEMO_USER_ID);
  const total = provider.listBooks().filter((b) => b.shelf === "library").length;

  if (!user) {
    return (
      <>
        <Topbar greeting={<b>アカウント</b>} />
        <section className="page section">
          <div className="muted">{provider.ready ? "ユーザーが見つかりません。" : "読み込み中…"}</div>
        </section>
      </>
    );
  }

  return (
    <>
      <Topbar greeting={<b>アカウント</b>} />

      <header className="acct-head page">
        <span className="acct-avatar">{user.initial}</span>
        <div className="acct-headmeta">
          <span className="eyebrow">Your account</span>
          <h1 className="acct-name">{user.name}</h1>
          <span className="acct-role">{user.profile.role}</span>
        </div>
        <div className="acct-stats">
          <Mini n={total} label="蔵書" />
          <Mini n={MOCK_HIGHLIGHTS.length} label="ハイライト" />
          <Mini n={0} label="お気に入り作家" />
        </div>
      </header>

      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Registered profile</div>
            <div className="section-title">登録情報</div>
          </div>
        </div>
        <div className="acct-info-grid">
          <Info label="役割" value={user.profile.role} />
          <Info label="いまの仕事テーマ" value={user.profile.workTheme} />
          <Info label="セレンディピティ許容度" value={user.profile.serendipityTolerance} />
        </div>
        <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
          ※ 業界・職種・役職など初期プロフィールの登録／編集は、フェーズ3（Firebase
          Auth＋Firestore直書き）で接続します。
        </p>
      </section>

      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Your interests</div>
            <div className="section-title">いまの関心</div>
            <div className="section-sub">ここを更新すると、来週の企画の方向が変わります。</div>
          </div>
        </div>
        <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
          {user.profile.estimatedInterests.map((opt) => (
            <span key={opt} className="chip on">
              {opt}
            </span>
          ))}
        </div>
      </section>

      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Connected sources</div>
            <div className="section-title">データ連携</div>
          </div>
        </div>
        <div className="acct-sources">
          {CONNECTED.map((s) => (
            <div key={s.name} className="acct-source panel">
              <span className="as-icon">{s.icon}</span>
              <span className="as-name">{s.name}</span>
              <span className="as-state">✓ 連携済み（デモ）</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
