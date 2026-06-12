"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiUrl, isFirebaseConfigured, isPickerConfigured } from "@/data/config";
import { setSourceConnected, type ConnectSource } from "@/data/user-writes";
import { getFirebaseAuth } from "@/lib/firebase";
import { pickDriveFolders, type PickedFolder } from "@/lib/googlePicker";

const SOURCES: { key: ConnectSource; icon: string; name: string; desc: string }[] = [
  { key: "drive", icon: "📁", name: "Google Drive", desc: "業務資料・関心フォルダのテキストを読み取ります。" },
  { key: "calendar", icon: "📅", name: "Google Calendar", desc: "スケジュール・役割の文脈を読み取ります。" },
  { key: "tasks", icon: "✓", name: "Google Tasks", desc: "タスク・優先度の文脈を読み取ります。" },
];

export default function ConnectPage() {
  const router = useRouter();
  const [connected, setConnected] = useState<Record<ConnectSource, boolean>>({
    drive: false,
    calendar: false,
    tasks: false,
  });
  const [folders, setFolders] = useState<PickedFolder[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onConnect = async () => {
    if (isFirebaseConfigured) {
      // 本実装: GET /api/auth/google/start → authUrl へ遷移（3スコープ同意）。
      const token = await getFirebaseAuth()?.currentUser?.getIdToken();
      const res = await fetch(`${apiUrl}/api/auth/google/start`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = (await res.json()) as { authUrl?: string };
      if (data.authUrl) {
        window.location.href = data.authUrl;
        return;
      }
    }
    // mock: 同意フローを擬似的に完了
    await Promise.all([
      setSourceConnected("drive", true),
      setSourceConnected("calendar", true),
      setSourceConnected("tasks", true),
    ]);
    setConnected({ drive: true, calendar: true, tasks: true });
  };

  // Drive Picker: フォルダ選択 → サーバ保存（POST /api/connect/drive-folders・C1.1.2）。
  const onPickFolders = async () => {
    setError(null);
    setBusy(true);
    try {
      const picked = await pickDriveFolders();
      if (picked.length === 0) return; // キャンセル
      const token = await getFirebaseAuth()?.currentUser?.getIdToken();
      const res = await fetch(`${apiUrl}/api/connect/drive-folders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          folderIds: picked.map((f) => f.folderId),
          labels: picked.map((f) => ({ folderId: f.folderId, label: "" })),
        }),
      });
      if (!res.ok) throw new Error(`フォルダ保存に失敗しました (${res.status})`);
      setFolders(picked);
      await setSourceConnected("drive", true);
      setConnected((c) => ({ ...c, drive: true }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "フォルダ選択に失敗しました");
    } finally {
      setBusy(false);
    }
  };

  const allConnected = connected.drive && connected.calendar && connected.tasks;

  return (
    <div className="auth-frame">
      <div className="auth-card panel">
        <span className="eyebrow">Connect your sources</span>
        <h1 className="auth-title">あなたの仕事を、読み取らせてください。</h1>
        <p className="auth-lead">
          以下の3つを読み取り、あなたにいま必要な一冊を企画します。読み取りは自動の企画にのみ使われます。
        </p>

        <ul className="connect-list">
          {SOURCES.map((s) => (
            <li key={s.key} className="connect-item">
              <span className="ci-icon">{s.icon}</span>
              <span className="ci-meta">
                <span className="ci-name">{s.name}</span>
                <span className="ci-desc">{s.desc}</span>
              </span>
              <span className={`ci-state ${connected[s.key] ? "on" : ""}`}>
                {connected[s.key] ? "✓ 連携済み" : "未連携"}
              </span>
            </li>
          ))}
        </ul>

        <button type="button" className="btn btn--gold btn--block" onClick={onConnect}>
          {allConnected ? "再連携する" : "Googleアカウントで連携する"}
        </button>

        {isPickerConfigured && (
          <div className="connect-picker">
            <button
              type="button"
              className="btn btn--ghost btn--block"
              onClick={onPickFolders}
              disabled={busy}
            >
              {busy ? "選択中…" : folders.length ? "Driveフォルダを選び直す" : "Driveの対象フォルダを選ぶ"}
            </button>
            {folders.length > 0 && (
              <ul className="connect-list" aria-label="選択したフォルダ">
                {folders.map((f) => (
                  <li key={f.folderId} className="connect-item">
                    <span className="ci-icon">🗂️</span>
                    <span className="ci-meta">
                      <span className="ci-name">{f.name}</span>
                    </span>
                    <span className="ci-state on">対象</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {error && <p className="auth-note">⚠ {error}</p>}

        <button type="button" className="btn btn--ghost btn--block" onClick={() => router.push("/")}>
          {allConnected ? "書店へ進む →" : "あとで連携する"}
        </button>

        {!isFirebaseConfigured && (
          <p className="auth-note">※ デモモード。実際のOAuth同意はフェーズ4でCloud Run APIに接続します。</p>
        )}
      </div>
    </div>
  );
}
